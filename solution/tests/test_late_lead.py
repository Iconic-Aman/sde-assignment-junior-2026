import csv
import json
import sqlite3
from pathlib import Path

from pipeline.cli import main


def _make_drop(path, lead_rows=None, events=None, batch="batch_001", events_file="events_0001.jsonl"):
    if lead_rows is not None:
        leads_dir = path / "leads" / "motor_renewal"
        leads_dir.mkdir(parents=True, exist_ok=True)
        with (leads_dir / f"{batch}.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["customer_name", "phone", "policy_number"])
            writer.writerows(lead_rows)
    if events is not None:
        events_dir = path / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        with (events_dir / events_file).open("w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")


def test_orphan_resolves_when_lead_arrives_in_drop2(tmp_path, monkeypatch):
    monkeypatch.setenv("PII_HMAC_KEY", "c" * 40)
    monkeypatch.setenv("PII_ENC_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    # drop_1: event only, no lead yet
    drop1 = tmp_path / "drop_1"
    _make_drop(drop1, lead_rows=None, events=[{
        "event_id": "evt_201", "event_type": "call.initiated",
        "workflow_id": "motor_renewal", "call_id": "call_201",
        "occurred_at": "2026-10-01T09:00:00Z",
        "phone": "9000000001", "payload": {}
    }], events_file="events_0001.jsonl")

    # drop_2: lead arrives for the same phone
    drop2 = tmp_path / "drop_2"
    _make_drop(drop2, lead_rows=[["Late Arriver", "9000000001", "MOT/201"]], events=None, batch="batch_002")

    db_path = tmp_path / "ledger.sqlite"

    main(["--db", str(db_path), "ingest", str(drop1)])

    with sqlite3.connect(db_path) as conn:
        orphan_after_drop1 = conn.execute(
            "SELECT COUNT(*) FROM linked_events WHERE lead_id IS NULL"
        ).fetchone()[0]

    assert orphan_after_drop1 == 1, "event must be orphan before lead arrives"

    main(["--db", str(db_path), "ingest", str(drop2)])

    with sqlite3.connect(db_path) as conn:
        orphan_after_drop2 = conn.execute(
            "SELECT COUNT(*) FROM linked_events WHERE lead_id IS NULL"
        ).fetchone()[0]

    assert orphan_after_drop2 == 0, "orphan must resolve after lead arrives in drop_2"
