from pipeline.parsers import parse_decimal


def test_decimal_formats():
    assert parse_decimal("Rs. 1,500") == "1500.00"
    assert parse_decimal("₹ 1500.50") == "1500.50"
    assert parse_decimal("INR 2000") == "2000.00"
    assert parse_decimal("1500") == "1500.00"
    assert parse_decimal("-12") is None
    assert parse_decimal("abc") is None
