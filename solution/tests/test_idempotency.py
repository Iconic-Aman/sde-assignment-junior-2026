import csv
import json
import sqlite3
from pathlib import Path

from pipeline.cli import main


def _create_sample_drop(path, batch_name, rows, events):
    leads_dir = path / "leads" / "motor_renewal"
    leads_dir.mkdir(parents=True, exist_ok=True)
    events_dir = path / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    with (leads_dir / f"{batch_name}.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_name", "phone", "policy_number", "policy_expiry", "premium_amount", "preferred_language"])
        writer.writerows(rows)

    with (events_dir / "events_0001.jsonl").open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


def test_double_ingest_changes_nothing(tmp_path, monkeypatch):
    monkeypatch.setenv("PII_HMAC_KEY", "b" * 40)
    monkeypatch.setenv("PII_ENC_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")

    drop1 = tmp_path / "drop_1"
    rows = [["Rohan Kumar", "9876543210", "MOT/101", "2026-11-01", "Rs. 2,000", "hi"]]
    events = [{
        "event_id": "evt_101", "event_type": "call.initiated",
        "workflow_id": "motor_renewal", "call_id": "call_101",
        "occurred_at": "2026-10-05T10:00:00Z", "phone": "9876543210",
        "payload": {}
    }]
    _create_sample_drop(drop1, "batch_001", rows, events)

    db_path = tmp_path / "ledger.sqlite"

    # First ingest
    main(["--db", str(db_path), "ingest", str(drop1)])
    with sqlite3.connect(db_path) as conn:
        leads_count_1 = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        events_count_1 = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        files_count_1 = conn.execute("SELECT COUNT(*) FROM ingested_files").fetchone()[0]

    assert leads_count_1 == 1
    assert events_count_1 == 1
    assert files_count_1 == 2  # 1 lead file + 1 event file

    # Second ingest of exact same drop
    main(["--db", str(db_path), "ingest", str(drop1)])
    with sqlite3.connect(db_path) as conn:
        leads_count_2 = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        events_count_2 = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        files_count_2 = conn.execute("SELECT COUNT(*) FROM ingested_files").fetchone()[0]

    assert leads_count_2 == leads_count_1
    assert events_count_2 == events_count_1
    assert files_count_2 == files_count_1
