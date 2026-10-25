"""Synthetic Yad2 pages for the collector's and the run's rules, in the saved pages' shapes
(`__NEXT_DATA__`, the feed query, the `"item"` query, the pagination links), with made-up tokens
and values only: no fixture, so these tests also run in the GitHub Action."""

import json
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from typing import Any

from tlv_hunter.parsing.ids import YAD2_SOURCE, compute_listing_id
from tlv_hunter.yad2.block import PageLoad, PageLoadError
from tlv_hunter.yad2.collector import LIST_URL
from tlv_hunter.yad2.mapping import PERMALINK

YAD2_HOSTS = frozenset({"www.yad2.co.il", "gw.yad2.co.il", "www.google.com"})


def token(n: int, kind: str = "p") -> str:
    """An 8-character made-up token: `p0000012` for a private listing, `a0000012` an agency's."""
    return f"{kind}{n:07d}"


def lid(value: str) -> str:
    return compute_listing_id(value, source=YAD2_SOURCE)


def page_url(number: int) -> str:
    return LIST_URL if number == 1 else f"{LIST_URL}&page={number}"


def _document(queries: list[dict[str, Any]], body: str = "") -> str:
    data = {"props": {"pageProps": {"dehydratedState": {"queries": queries}}}}
    return (
        "<html><head>"
        '<script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(data, ensure_ascii=False)}</script></head><body>{body}</body></html>"
    )


def list_html(tokens: Iterable[str], *, number: int, last: int = 167, mixed: bool = False) -> str:
    """A list page: `p…` tokens private, `a…` agency; the laptop's shape (two lists) or the
    server's (`mixed`, one `yad2` list); a promoted list beside them; links to the next pages."""
    ads = [{"token": t, "adType": "private" if t.startswith("p") else "commercial"} for t in tokens]
    if mixed:
        feed: dict[str, Any] = {"yad2": ads}
    else:
        feed = {
            "private": [ad for ad in ads if ad["adType"] == "private"],
            "agency": [ad for ad in ads if ad["adType"] != "private"],
        }
    feed["platinum"] = [{"token": "x0000001", "adType": "private"}]
    feed["pagination"] = {"total": 4438, "totalPages": last}
    query = {"queryKey": ["realestate-rent-feed", {"city": "5000"}], "state": {"data": feed}}
    links = "".join(
        f'<a data-testid="pagination-item-link" href="/realestate/rent/tel-aviv-area?area=1'
        f'&amp;city=5000&amp;page={n}"><span>{n}</span></a>'
        for n in range(number, min(number + 3, last) + 1)
    )
    return _document([query], links)


def listing_data(value: str, *, updated_at: str = "2026-10-24T14:30:00", **changes: Any) -> dict:
    d: dict[str, Any] = {
        "token": value,
        "adType": "private" if value.startswith("p") else "commercial",
        "dates": {"updatedAt": updated_at},
        "price": 6500,
        "metaData": {"description": f"דירה יפה {value}", "images": []},
        "address": {"city": {"text": "תל אביב יפו"}},
        "additionalDetails": {"property": {"id": 1, "text": "דירה"}},
        "customer": {"id": 1, "name": "שם בדוי"},
    }
    d.update(changes)
    return d


def listing_html(d: Mapping[str, Any]) -> str:
    return _document([{"queryKey": ["item", d["token"]], "state": {"data": dict(d)}}])


class FakeBrowser:
    """URL → what the page load gives: a `PageLoad`, HTML (served by Yad2, its API called), or
    an exception to raise. Every URL asked is recorded, in order."""

    def __init__(self, pages: Mapping[str, PageLoad | str | Exception]) -> None:
        self.pages = dict(pages)
        self.asked: list[str] = []

    def load(self, url: str) -> PageLoad:
        self.asked.append(url)
        page = self.pages.get(url)
        if page is None:
            raise PageLoadError(f"no page for {url}")
        if isinstance(page, Exception):
            raise page
        if isinstance(page, str):
            return PageLoad(url=url, final_url=url, html=page, hosts=YAD2_HOSTS)
        return page


def site(
    list_pages: Mapping[int, Iterable[str]],
    listings: Mapping[str, dict[str, Any]] | None = None,
    *,
    mixed: bool = False,
) -> dict[str, PageLoad | str | Exception]:
    """The pages of a made-up site: list pages by number, and a listing page for every token on
    them (`listings` overrides a token's data)."""
    pages: dict[str, PageLoad | str | Exception] = {}
    last = max(list_pages)
    for number, tokens in list_pages.items():
        tokens = list(tokens)
        pages[page_url(number)] = list_html(tokens, number=number, last=last, mixed=mixed)
        for value in tokens:
            d = (listings or {}).get(value) or listing_data(value)
            pages[PERMALINK.format(token=value)] = listing_html(d)
    return pages


def fixed_clock(at: datetime) -> Callable[[], datetime]:
    return lambda: at
