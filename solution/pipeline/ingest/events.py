import json

from pydantic import BaseModel, Field, StrictStr, ValidationError

from .registry import register_file
from ..parsers import normalize_phone, parse_timestamp
from ..pii import phone_hash


class EventRecord(BaseModel):
    event_id: StrictStr = Field(min_length=1)
    event_type: StrictStr = Field(min_length=1)
    workflow_id: StrictStr = Field(min_length=1)
    call_id: StrictStr | None = None
    occurred_at: StrictStr = Field(min_length=1)
    phone: StrictStr | None = None
    payload: dict = Field(default_factory=dict)


def ingest_event_file(connection, drop, path):
    with connection:
        file_id = register_file(connection, drop, path)
        if file_id is None:
            return
        totals = {"events_total": 0, "malformed_events": 0, "duplicate_events": 0}
        with path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                totals["events_total"] += 1
                try:
                    raw = json.loads(line)
                    if not isinstance(raw, dict) or not raw.get("event_id"):
                        raise ValueError("Missing event_id")
                    event = EventRecord.parse_obj(raw)
                    occurred = parse_timestamp(event.occurred_at)
                    event_type, workflow = event.event_type, event.workflow_id
                except (ValueError, TypeError, ValidationError, json.JSONDecodeError):
                    totals["malformed_events"] += 1
                    continue
                canonical = normalize_phone(event.phone or "")
                hashed = phone_hash(canonical) if canonical else None
                payload = event.payload
                disposition = payload.get("disposition_code") if isinstance(payload, dict) else None
                cursor = connection.execute(
                    "INSERT OR IGNORE INTO events(event_id, event_type, workflow_id, call_id, "
                    "occurred_at_utc, phone_hash, payload_json, disposition_code, file_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (event.event_id, event_type, workflow, event.call_id, occurred,
                     hashed, json.dumps(payload, sort_keys=True), disposition, file_id),
                )
                if cursor.rowcount == 0:
                    totals["duplicate_events"] += 1
        connection.execute(
            "UPDATE file_stats SET events_total=?, malformed_events=?, duplicate_events=? "
            "WHERE file_id=?",
            (*totals.values(), file_id),
        )
