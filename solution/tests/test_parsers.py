from pipeline.parsers import normalize_header, parse_timestamp


def test_header_normalization():
    assert normalize_header("  Policy__Expiry ") == "policy expiry"
    assert normalize_header("PHONE NUMBER") == "phone number"


def test_timestamp_formats():
    assert parse_timestamp("2026-10-05T13:20:21Z").endswith("+00:00")
    assert parse_timestamp("2026-10-05T13:20:21+05:30").endswith("+00:00")
    # naive treated as IST → UTC
    result = parse_timestamp("2026-10-05T13:20:21")
    assert "07:50:21" in result
