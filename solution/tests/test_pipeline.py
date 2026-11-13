import csv
import json
import sqlite3
from pathlib import Path

from pipeline.cli import main


def _event(event_id, event_type, payload=None):
    return {
        "event_id": event_id, "event_type": event_type, "workflow_id": "motor_renewal",
        "call_id": "call_1", "occurred_at": "2026-10-05T13:20:21Z",
        "phone": "9876543210", "payload": payload or {},
    }


def test_incremental_ingest_reports_and_protects_pii(tmp_path, monkeypatch):
    monkeypatch.setenv("PII_HMAC_KEY", "a" * 40)
    monkeypatch.setenv("PII_ENC_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
    drop1 = tmp_path / "drop_1"
    drop2 = tmp_path / "drop_2"
    (drop1 / "events").mkdir(parents=True)
    (drop2 / "leads" / "motor_renewal").mkdir(parents=True)
    items = [_event("e1", "call.initiated"), _event("e2", "call.connected"),
             _event("e3", "disposition.set", {"disposition_code": "renewed"})]
    event_file = drop1 / "events" / "events_0001.jsonl"
    event_file.write_text("\n".join(json.dumps(item) for item in items + [items[1]])
                          + "\n{bad json\n", encoding="utf-8")
    lead_file = drop2 / "leads" / "motor_renewal" / "batch_003.csv"
    with lead_file.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(["customer_name", "phone", "policy_number", "policy_expiry",
                         "premium_amount", "preferred_language"])
        writer.writerow(["Aarav Private", "9876543210", "MOT/1", "01-Dec-2026",
                         "Rs. 1,500", "en"])
        writer.writerow(["", "9876543211", "MOT/2", "", "", "en"])
    database = tmp_path / "ledger.sqlite"
    main(["--db", str(database), "ingest", str(drop1)])
    main(["--db", str(database), "ingest", str(drop1)])
    main(["--db", str(database), "ingest", str(drop2)])
    output = tmp_path / "reports"
    main(["--db", str(database), "report", "--out", str(output)])

    with (output / "lead_report.csv").open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 1
    assert rows[0]["bucket"] == "completed"
    assert rows[0]["current_disposition"] == "renewed"
    assert rows[0]["ever_success"] == "true"
    quality = json.loads((output / "data_quality.json").read_text(encoding="utf-8"))
    assert quality["events_total"] == 5
    assert quality["malformed_events"] == 1
    assert quality["duplicate_events_dropped"] == 1
    assert quality["orphan_events"] == 0
    assert quality["lead_rows_rejected"] == 1
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 3
    assert b"Aarav Private" not in database.read_bytes()
