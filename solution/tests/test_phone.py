from pipeline.parsers import normalize_header, normalize_phone, parse_date, parse_decimal


def test_phone_formats():
    assert normalize_phone("98765 43210") == "+919876543210"
    assert normalize_phone("91-98765-43210") == "+919876543210"
    assert normalize_phone("09876543210") == "+919876543210"
    assert normalize_phone("+919876543210") == "+919876543210"
    assert normalize_phone("9876543210") == "+919876543210"
    assert normalize_phone("+1 415 555 0134") is None
    assert normalize_phone("12345") is None
