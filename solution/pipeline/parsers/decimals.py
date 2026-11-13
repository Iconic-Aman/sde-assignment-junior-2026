import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

_AMOUNT = re.compile(r"^(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?$")


def parse_decimal(value):
    value = re.sub(r"^(?:₹|INR|Rs\.?)\s*", "", value.strip(), flags=re.I)
    if not _AMOUNT.fullmatch(value):
        return None
    try:
        amount = Decimal(value.replace(",", ""))
        if amount < 0:
            return None
        return format(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")
    except InvalidOperation:
        return None
