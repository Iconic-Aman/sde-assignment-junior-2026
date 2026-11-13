from pipeline.parsers import parse_decimal


def test_all_currency_prefixes():
    assert parse_decimal("Rs. 1,500") == "1500.00"
    assert parse_decimal("Rs 1500") == "1500.00"
    assert parse_decimal("₹ 1500.50") == "1500.50"
    assert parse_decimal("₹1500.50") == "1500.50"
    assert parse_decimal("INR 2000") == "2000.00"
    assert parse_decimal("inr 2000") == "2000.00"


def test_plain_numbers():
    assert parse_decimal("1500") == "1500.00"
    assert parse_decimal("1500.5") == "1500.50"
    assert parse_decimal("0") == "0.00"
    assert parse_decimal("1,00,000") is None   # Indian-style lakhs — not standard thousands


def test_rounding():
    assert parse_decimal("1500.005") == "1500.01"
    assert parse_decimal("1500.004") == "1500.00"


def test_invalid_decimals():
    assert parse_decimal("-12") is None
    assert parse_decimal("abc") is None
    assert parse_decimal("") is None
