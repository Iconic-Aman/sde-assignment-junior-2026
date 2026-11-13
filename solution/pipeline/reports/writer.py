import csv
import json
from collections import defaultdict
from itertools import groupby
from pathlib import Path

from ..db import load_schemas
from ..parsers import as_ist

REPORTS = {
    "batch_summary.csv": ["workflow_id", "batch_id", "total_leads", "yet_to_reach_out",
                          "in_progress_telephony_failed", "in_progress_dialed", "completed"],
    "daily_overview.csv": ["workflow_id", "date", "total_calls", "connected_calls",
                           "connectivity_rate", "success_leads"],
    "lead_report.csv": ["workflow_id", "external_ref", "batch_id", "phone_masked", "bucket",
                        "total_calls", "connected_calls", "last_call_at",
                        "current_disposition", "ever_success"],
    "rejections.csv": ["workflow_id", "batch_id", "row_number", "reason"],
}


def _write_csv(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _call_rows(connection):
    query = """
    SELECT l.*, d.is_terminal, d.is_success
    FROM linked_events l
    LEFT JOIN dispositions d ON d.workflow_id=l.workflow_id AND d.code=l.disposition_code
    WHERE l.lead_id IS NOT NULL AND l.call_id IS NOT NULL
    ORDER BY l.workflow_id, l.call_id, l.occurred_at_utc, l.seq
    """
    for key, group in groupby(connection.execute(query), key=lambda r: (r["workflow_id"], r["call_id"])):
        events = list(group)
        initiated = [r for r in events if r["event_type"] == "call.initiated"]
        if not initiated:
            continue
        start = min(initiated, key=lambda r: (r["occurred_at_utc"], r["seq"]))
        overrides = [r for r in events if r["event_type"] == "disposition.override" and r["is_terminal"] is not None]
        sets = [r for r in events if r["event_type"] == "disposition.set" and r["is_terminal"] is not None]
        pool = overrides or sets
        effective = max(pool, key=lambda r: (r["occurred_at_utc"], r["seq"])) if pool else None
        yield {
            "workflow_id": key[0], "call_id": key[1], "lead_id": start["lead_id"],
            "started": start["occurred_at_utc"],
            "connected": any(r["event_type"] == "call.connected" for r in events),
            "failed": any(r["event_type"] == "call.telephony_failed" for r in events),
            "code": effective["disposition_code"] if effective else "",
            "terminal": bool(effective["is_terminal"]) if effective else False,
            "success": bool(effective["is_success"]) if effective else False,
        }


def _quality(connection, schemas):
    stats = connection.execute(
        "SELECT COALESCE(SUM(rows_total),0), COALESCE(SUM(rows_rejected),0), "
        "COALESCE(SUM(duplicates_merged),0), COALESCE(SUM(field_warnings),0), "
        "COALESCE(SUM(events_total),0), COALESCE(SUM(malformed_events),0), "
        "COALESCE(SUM(duplicate_events),0) FROM file_stats"
    ).fetchone()
    reasons = {"invalid_phone": 0}
    for schema in schemas.values():
        reasons.update({"missing_required:" + f["name"]: 0 for f in schema["fields"] if f.get("required")})
    for row in connection.execute("SELECT reason, COUNT(*) n FROM rejections GROUP BY reason"):
        reasons[row["reason"]] = row["n"]
    orphan = connection.execute("SELECT COUNT(*) FROM linked_events WHERE lead_id IS NULL").fetchone()[0]
    unknown = connection.execute(
        "SELECT COUNT(*) FROM linked_events e LEFT JOIN dispositions d "
        "ON d.workflow_id=e.workflow_id AND d.code=e.disposition_code "
        "WHERE e.lead_id IS NOT NULL AND e.event_type LIKE 'disposition.%' AND d.code IS NULL"
    ).fetchone()[0]
    return {
        "lead_rows_total": stats[0], "lead_rows_rejected": stats[1],
        "rejections_by_reason": dict(sorted(reasons.items())),
        "duplicate_lead_rows_merged": stats[2], "field_warnings": stats[3],
        "events_total": stats[4], "malformed_events": stats[5],
        "duplicate_events_dropped": stats[6], "orphan_events": orphan,
        "unknown_disposition_events": unknown,
    }


def write_reports(connection, out, root):
    directory = Path(out)
    directory.mkdir(parents=True, exist_ok=True)
    schemas = load_schemas(root)
    leads = {}
    buckets = defaultdict(lambda: defaultdict(int))
    for row in connection.execute("SELECT * FROM leads"):
        fields = json.loads(row["fields_json"])
        for field in schemas[row["workflow_id"]]["fields"]:
            if fields.get(field["name"]) is None and "default" in field:
                fields[field["name"]] = field["default"]
        leads[row["id"]] = {
            "workflow_id": row["workflow_id"], "external_ref": row["external_ref"] or "",
            "batch_id": row["batch_id"], "phone": "+91******" + row["phone_last4"],
            "calls": 0, "connected": 0, "failed": 0, "terminal": False, "success": False,
            "last": None, "current": None, "bucket": "yet_to_reach_out",
        }
    daily = defaultdict(lambda: {"calls": 0, "connected": 0, "success": set()})
    for call in _call_rows(connection):
        lead = leads[call["lead_id"]]
        lead["calls"] += 1
        lead["connected"] += int(call["connected"])
        lead["failed"] += int(call["failed"])
        lead["terminal"] |= call["terminal"]
        lead["success"] |= call["success"]
        local = as_ist(call["started"])
        latest = (call["started"], call["call_id"], local.isoformat(timespec="seconds"))
        if lead["last"] is None or latest[:2] > lead["last"][:2]:
            lead["last"] = latest
        if call["code"] and (lead["current"] is None or latest[:2] > lead["current"][0]):
            lead["current"] = (latest[:2], call["code"])
        key = (call["workflow_id"], local.date().isoformat())
        daily[key]["calls"] += 1
        daily[key]["connected"] += int(call["connected"])
        if call["success"]:
            daily[key]["success"].add(call["lead_id"])
    for lead in leads.values():
        if lead["calls"] and lead["terminal"]:
            lead["bucket"] = "completed"
        elif lead["calls"] and lead["failed"] == lead["calls"]:
            lead["bucket"] = "in_progress_telephony_failed"
        elif lead["calls"]:
            lead["bucket"] = "in_progress_dialed"
        buckets[(lead["workflow_id"], lead["batch_id"])][lead["bucket"]] += 1
    bucket_names = ["yet_to_reach_out", "in_progress_telephony_failed", "in_progress_dialed", "completed"]
    batch_rows = [
        [wf, bt, sum(c.values())] + [c[n] for n in bucket_names]
        for (wf, bt), c in sorted(buckets.items())
    ]
    _write_csv(directory / "batch_summary.csv", REPORTS["batch_summary.csv"], batch_rows)
    daily_rows = [
        [wf, day, v["calls"], v["connected"], format(v["connected"] / v["calls"], ".4f"), len(v["success"])]
        for (wf, day), v in sorted(daily.items())
    ]
    _write_csv(directory / "daily_overview.csv", REPORTS["daily_overview.csv"], daily_rows)
    lead_rows = [
        [l["workflow_id"], l["external_ref"], l["batch_id"], l["phone"], l["bucket"],
         l["calls"], l["connected"], l["last"][2] if l["last"] else "",
         l["current"][1] if l["current"] else "", str(l["success"]).lower()]
        for l in sorted(leads.values(), key=lambda x: (x["workflow_id"], x["external_ref"]))
    ]
    _write_csv(directory / "lead_report.csv", REPORTS["lead_report.csv"], lead_rows)
    rejected = connection.execute(
        "SELECT workflow_id,batch_id,row_number,reason FROM rejections ORDER BY workflow_id,batch_id,row_number"
    )
    _write_csv(directory / "rejections.csv", REPORTS["rejections.csv"],
               ([r["workflow_id"], r["batch_id"], r["row_number"], r["reason"]] for r in rejected))
    (directory / "data_quality.json").write_text(
        json.dumps(_quality(connection, schemas), indent=2) + "\n", encoding="utf-8"
    )
