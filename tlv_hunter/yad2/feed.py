"""Yad2's list pages (`PHASE_6.md` §6.1, §6.5): the feed in `__NEXT_DATA__` and the page's own
pagination links. Pure: reads HTML text, fetches nothing.

The feed comes in two shapes (spike §S2.2), both read: separate `private` and `agency` lists, or
one `yad2` list in a fixed pattern. The promoted lists beside them are ignored (#502 point 16).
"""

from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from tlv_hunter.yad2.pages import PageShapeError, query_data

FEED_QUERY = "realestate-rent-feed"
MAIN_LISTS = ("private", "agency", "yad2")
# Never read; named so that a reader of the feed sees what is left out on purpose.
PROMOTED_LISTS = ("platinum", "kingOfTheHar", "trio", "booster", "leadingBroker", "lookalike")
PRIVATE_AD_TYPE = "private"
PAGINATION_TEST_ID = "pagination-item-link"
YAD2_HOST = "www.yad2.co.il"


@dataclass(frozen=True)
class FeedItem:
    token: str
    private: bool
    """`adType` `private`: only these decide whether a page holds a new token (#514)."""


def feed_items(html: str) -> list[FeedItem]:
    """The main lists' listings in the page's own order: `private` then `agency`, or `yad2`."""
    data = query_data(html, FEED_QUERY)
    if not isinstance(data, dict):
        raise PageShapeError(f"the {FEED_QUERY!r} query holds no feed")
    lists = [data[name] for name in MAIN_LISTS if isinstance(data.get(name), list)]
    if not lists:
        raise PageShapeError(f"the feed holds none of {', '.join(MAIN_LISTS)}")
    items = []
    for ads in lists:
        for ad in ads:
            token = ad.get("token") if isinstance(ad, dict) else None
            if isinstance(token, str) and token:
                items.append(FeedItem(token=token, private=ad.get("adType") == PRIVATE_AD_TYPE))
    return items


def page_link(html: str, number: int, *, base: str) -> str | None:
    """The absolute URL of the page's own pagination link labelled `number`, or `None` when the
    page has none (the list's end). A link leaving Yad2 is never followed."""
    parser = _PaginationParser()
    parser.feed(html)
    parser.close()
    for label, href in parser.links:
        if label == str(number):
            url = urljoin(base, href)
            return url if urlparse(url).hostname == YAD2_HOST else None
    return None


class _PaginationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._href: str | None = None
        self._text = ""
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        href = found.get("href")
        if tag == "a" and found.get("data-testid") == PAGINATION_TEST_ID and href:
            self._href = href
            self._text = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._text.strip(), self._href))
            self._href = None

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text += data
