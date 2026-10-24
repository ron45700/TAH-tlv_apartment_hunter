"""Yad2's pages as served (`PHASE_6.md` §6.1): the Next.js data every page carries in
`<script id="__NEXT_DATA__">`. Pure: reads HTML text, fetches nothing."""

import json
from html.parser import HTMLParser
from typing import Any

NEXT_DATA_ID = "__NEXT_DATA__"
LISTING_QUERY = "item"


class PageShapeError(ValueError):
    """A page without the data a Yad2 page is read for."""


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._inside = False
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and ("id", NEXT_DATA_ID) in attrs:
            self._inside = True
            self.found.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._inside = False

    def handle_data(self, data: str) -> None:
        if self._inside:
            self.found[-1] += data


def next_data(html: str) -> dict[str, Any]:
    """The page's `__NEXT_DATA__` object; exactly one is expected."""
    parser = _NextDataParser()
    parser.feed(html)
    parser.close()
    if len(parser.found) != 1:
        raise PageShapeError(f"expected one {NEXT_DATA_ID} script, found {len(parser.found)}")
    data = json.loads(parser.found[0])
    if not isinstance(data, dict):
        raise PageShapeError(f"{NEXT_DATA_ID} is not an object")
    return data


def dehydrated_queries(html: str) -> list[Any]:
    """The page's React Query cache: `props.pageProps.dehydratedState.queries`."""
    try:
        queries = next_data(html)["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError) as error:
        raise PageShapeError(f"no dehydrated queries: {error!r}") from error
    if not isinstance(queries, list):
        raise PageShapeError("the dehydrated queries are not a list")
    return queries


def query_data(html: str, key: str) -> Any:
    """The `state.data` of the one query whose key starts with `key`."""
    found = [
        query
        for query in dehydrated_queries(html)
        if isinstance(query, dict)
        and isinstance(query.get("queryKey"), list)
        and query["queryKey"][:1] == [key]
    ]
    if len(found) != 1:
        raise PageShapeError(f"expected one {key!r} query, found {len(found)}")
    state = found[0].get("state")
    return state.get("data") if isinstance(state, dict) else None


def listing_data(html: str) -> dict[str, Any]:
    """A listing page's `data` (DECISIONS.md #494: a Yad2 post's `raw`): the `"item"` query's."""
    data = query_data(html, LISTING_QUERY)
    if not isinstance(data, dict) or not isinstance(data.get("token"), str):
        raise PageShapeError(f"the {LISTING_QUERY!r} query holds no listing")
    return data
