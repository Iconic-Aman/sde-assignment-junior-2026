import re


def normalize_header(value):
    return re.sub(r"[_\s]+", " ", value.strip().lower())
