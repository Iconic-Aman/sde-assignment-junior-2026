from pipeline.parsers import normalize_phone


# All 6 valid formats from spec
def test_all_six_valid_phone_formats():
    assert normalize_phone("9876543210") == "+919876543210"       # bare 10
    assert normalize_phone("98765 43210") == "+919876543210"      # spaces
    assert normalize_phone("09876543210") == "+919876543210"      # leading 0
    assert normalize_phone("919876543210") == "+919876543210"     # 91 prefix no +
    assert normalize_phone("91-98765-43210") == "+919876543210"   # dashes with 91
    assert normalize_phone("+919876543210") == "+919876543210"    # E.164


def test_invalid_phones():
    assert normalize_phone("+1 415 555 0134") is None   # US number
    assert normalize_phone("12345") is None              # too short
    assert normalize_phone("5876543210") is None         # starts with 5 (invalid)
    assert normalize_phone("") is None                   # empty
    assert normalize_phone(None) is None                 # None input
