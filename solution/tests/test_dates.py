from pipeline.parsers import parse_date


def test_date_formats():
    assert parse_date("2026-12-01") == "2026-12-01"
    assert parse_date("01/12/2026") == "2026-12-01"
    assert parse_date("01-12-2026") == "2026-12-01"
    assert parse_date("01-Dec-2026") == "2026-12-01"
    assert parse_date("31/02/2026") is None
    assert parse_date("not-a-date") is None
