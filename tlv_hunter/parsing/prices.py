import re
from typing import NamedTuple

_CURRENCY_BY_SYMBOL = {"₪": "ILS"}
_PRICE_RE = re.compile(r"(?P<symbol>\D)(?P<amount>\d{1,3}(?:,\d{3})+|\d+)")


class ParsedPrice(NamedTuple):
    amount: int | None
    currency: str | None


UNPARSED_PRICE = ParsedPrice(None, None)


def parse_native_price(raw: str) -> ParsedPrice:
    match = _PRICE_RE.fullmatch(raw.strip())
    if match is None:
        return UNPARSED_PRICE
    currency = _CURRENCY_BY_SYMBOL.get(match["symbol"])
    if currency is None:
        return UNPARSED_PRICE
    return ParsedPrice(int(match["amount"].replace(",", "")), currency)
