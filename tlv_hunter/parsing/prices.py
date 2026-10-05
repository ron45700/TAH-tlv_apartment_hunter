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


# No monthly rent in Tel Aviv is below this: a lower native price means no price
# (DECISIONS.md #114).
NATIVE_PRICE_FLOOR = 500


def native_price_fallback(native_price: int | None) -> int | None:
    """The provider's price, used only when the text gives none (#95, #114)."""
    if native_price is None or native_price < NATIVE_PRICE_FLOOR:
        return None
    return native_price
