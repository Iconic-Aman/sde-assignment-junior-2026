from .headers import normalize_header
from .phone import normalize_phone
from .dates import parse_date
from .decimals import parse_decimal
from .timestamps import parse_timestamp, as_ist


def parse_field(value, field):
    value = (value or "").strip()
    if not value:
        return None, True
    kind = field["type"]
    if kind == "string":
        return value, True
    if kind == "phone":
        result = normalize_phone(value)
    elif kind == "date":
        result = parse_date(value)
    elif kind == "decimal":
        result = parse_decimal(value)
    elif kind == "enum":
        result = value.lower() if value.lower() in field.get("values", []) else None
    else:
        raise ValueError("Unsupported field type: " + kind)
    return result, result is not None
