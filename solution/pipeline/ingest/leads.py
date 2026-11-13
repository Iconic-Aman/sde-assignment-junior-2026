import csv
import json

from .registry import register_file
from ..parsers import normalize_header, parse_field
from ..pii import decrypt, encrypt, phone_hash


def _column_map(headers, schema):
    normalized = [normalize_header(item) for item in headers]
    result = {}
    for field in schema["fields"]:
        names = {normalize_header(field["name"])}
        names.update(normalize_header(alias) for alias in field.get("aliases", []))
        result[field["name"]] = next(
            (index for index, name in enumerate(normalized) if name in names), None
        )
    return result


def _merge_lead(connection, workflow, batch, values, private, canonical):
    hashed = phone_hash(canonical)
    existing = connection.execute(
        "SELECT * FROM leads WHERE workflow_id=? AND phone_hash=?", (workflow, hashed)
    ).fetchone()
    if existing is None:
        connection.execute(
            "INSERT INTO leads(workflow_id, phone_hash, phone_last4, external_ref, batch_id, "
            "fields_json, pii_enc) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (workflow, hashed, canonical[-4:], values.get("_reference"), batch,
             json.dumps(values, sort_keys=True), encrypt(json.dumps(private)) if private else None),
        )
        return False
    old_values = json.loads(existing["fields_json"])
    old_values.update({k: v for k, v in values.items() if v is not None})
    old_private = json.loads(decrypt(existing["pii_enc"]) or "{}")
    old_private.update({k: v for k, v in private.items() if v is not None})
    connection.execute(
        "UPDATE leads SET external_ref=COALESCE(?, external_ref), fields_json=?, pii_enc=? "
        "WHERE id=?",
        (values.get("_reference"), json.dumps(old_values, sort_keys=True),
         encrypt(json.dumps(old_private)) if old_private else None, existing["id"]),
    )
    return True


def ingest_lead_file(connection, drop, path, schema):
    with connection:
        file_id = register_file(connection, drop, path)
        if file_id is None:
            return
        counters = {"rows_total": 0, "rows_rejected": 0, "duplicates_merged": 0, "field_warnings": 0}
        batch, workflow = path.stem, schema["workflow_id"]
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            headers = next(reader, [])
            columns = _column_map(headers, schema)
            for row in reader:
                if not any(cell.strip() for cell in row):
                    continue
                counters["rows_total"] += 1
                values, private, canonical, warnings, reason = {}, {}, None, 0, None
                for field in schema["fields"]:
                    index = columns[field["name"]]
                    raw = row[index] if index is not None and index < len(row) else ""
                    value, valid = parse_field(raw, field)
                    if field["type"] == "phone":
                        canonical = value
                        if raw.strip() and not valid:
                            reason = "invalid_phone"
                            break
                    if not valid:
                        warnings += 1
                        value = None
                    if value is None and field.get("required"):
                        reason = "missing_required:" + field["name"]
                        break
                    if field.get("pii") and field["type"] != "phone":
                        private[field["name"]] = value
                    elif field["type"] != "phone":
                        values[field["name"]] = value
                    if field.get("reference"):
                        values["_reference"] = value
                row_number = counters["rows_total"]
                if reason:
                    counters["rows_rejected"] += 1
                    connection.execute(
                        "INSERT INTO rejections VALUES (?, ?, ?, ?)",
                        (workflow, batch, row_number, reason),
                    )
                    continue
                counters["field_warnings"] += warnings
                if _merge_lead(connection, workflow, batch, values, private, canonical):
                    counters["duplicates_merged"] += 1
        connection.execute(
            "UPDATE file_stats SET rows_total=?, rows_rejected=?, duplicates_merged=?, "
            "field_warnings=? WHERE file_id=?",
            (*counters.values(), file_id),
        )
