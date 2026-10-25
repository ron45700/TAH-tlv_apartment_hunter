"""The Yad2 seam (DECISIONS.md #507, #513; `PHASE_6.md` §6.5, §6.6, §6.8): the only code that knows
Yad2's pages. `Yad2Collector.collect(known, *, bootstrap)` reads the list, opens the pages of the
tokens never seen and the bump checks, and returns what it found. It reads no store and writes
nothing: `known` (every stored Yad2 post's `listing_id` → `last_published_at`) is passed in, and
the run stores the collection at the end, only when it succeeded (#502 point 18, invariant 2).

The browser is behind `Browser` (`browser.py` is Playwright's, the only part not run in tests).
No phone request, ever (#497): only the list and listing pages are loaded, and nothing is clicked.

The rules (#492, #493, #504, #514):
- **Paging:** from page 1 by the page's own links, at least `MIN_LIST_PAGES` and at most
  `MAX_LIST_PAGES`; after the minimum, the next page only while the page just read held a private
  token never seen (agency listings are not in date order, spike §S2.3). **Bootstrap:** exactly
  `BOOTSTRAP_LIST_PAGES`, every token new to the store opened, no bump check.
- **New tokens:** each listing page opened once; one that fails to load or to map is skipped and
  so tried again at the next run (its token is not stored, so not seen).
- **Bumps:** a known token on the pages read whose stored `last_published_at` is older than
  `BUMP_AGE` at the run's start has its page opened, private tokens first, at most
  `MAX_BUMP_CHECKS` a run; a later `updatedAt` is a bump.
- **A pause** of `PAUSE_SECONDS` plus a random part up to `PAUSE_JITTER_SECONDS` before every page
  load after the run's first, list and listing pages alike (§6.8).
- **A block** (`block.py`) on any page raises `Yad2Blocked`: the run fails and stores nothing.
"""

import logging
import random
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol

from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.datetimes import parse_israel_local_utc, require_utc
from tlv_hunter.parsing.ids import YAD2_SOURCE, compute_listing_id
from tlv_hunter.yad2.block import PageLoad, PageLoadError, blocked_reason
from tlv_hunter.yad2.feed import FeedItem, feed_items, page_link
from tlv_hunter.yad2.mapping import PERMALINK, form_fields, to_raw_post
from tlv_hunter.yad2.pages import PageShapeError, listing_data

logger = logging.getLogger(__name__)

# The page's own city link: Tel Aviv-Yafo (#491; spike 2 §S2.2), sorted by date, Yad2's default.
LIST_URL = "https://www.yad2.co.il/realestate/rent/tel-aviv-area?area=1&city=5000"
MIN_LIST_PAGES = 3
MAX_LIST_PAGES = 10
BOOTSTRAP_LIST_PAGES = 3
BUMP_AGE = timedelta(hours=3)
MAX_BUMP_CHECKS = 10
PAUSE_SECONDS = 4.0
PAUSE_JITTER_SECONDS = 2.0


class Browser(Protocol):
    def load(self, url: str) -> PageLoad:
        """Load one page in the run's one browser; `PageLoadError` when it does not load."""
        ...


class Yad2Blocked(RuntimeError):
    """Yad2 blocked a page (`block.py`): the run fails, stores nothing, marks no token seen."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class NewListing:
    post: RawPost
    """A token never seen, from its listing page (Gate A for Yad2)."""
    form: Mapping[str, Any]
    """The form's part of its `Listing` (`mapping.form_fields`, Gate B for Yad2)."""


@dataclass(frozen=True)
class Bump:
    listing_id: str
    updated_at: datetime
    """The listing page's `updatedAt` as UTC, later than the stored `last_published_at`."""


@dataclass(frozen=True)
class Yad2Collection:
    listings: tuple[NewListing, ...]
    bumps: tuple[Bump, ...]
    list_pages: int
    """The list pages read."""
    listings_read: int
    """The listings on the list pages read, repeats included (the `RunRecord`'s `rows_fetched`)."""
    skipped: tuple[str, ...]
    """The tokens whose listing page failed to load or to map (`rows_skipped`), in order."""


class Yad2Collector:
    def __init__(
        self,
        browser: Browser,
        *,
        clock: Callable[[], datetime],
        sleep: Callable[[float], None] | None = None,
        jitter: Callable[[], float] | None = None,
    ) -> None:
        """`sleep` defaults to `time.sleep` and `jitter` to a uniform draw up to
        `PAUSE_JITTER_SECONDS`, both looked up at the call so that tests can refuse them."""
        self._browser = browser
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        self._loads = 0

    def collect(self, known: Mapping[str, datetime], *, bootstrap: bool) -> Yad2Collection:
        self._loads = 0
        started = require_utc(self._clock())
        items, list_pages, listings_read = self._read_list(known, bootstrap)
        skipped: list[str] = []

        listings = []
        for item in items:
            if _listing_id(item.token) in known:
                continue
            d = self._listing_page(item.token, skipped)
            if d is None:
                continue
            try:
                post = to_raw_post(d, fetched_at=require_utc(self._clock()))
                form = form_fields(d)
            except (KeyError, TypeError, ValueError) as error:
                logger.warning("yad2: listing %s did not map: %r", item.token, error)
                skipped.append(item.token)
                continue
            listings.append(NewListing(post=post, form=form))

        bumps = [] if bootstrap else self._bumps(items, known, started, skipped)
        logger.info(
            "yad2: %d list pages, %d listings read, %d new, %d bumps, %d skipped",
            list_pages,
            listings_read,
            len(listings),
            len(bumps),
            len(skipped),
        )
        return Yad2Collection(
            listings=tuple(listings),
            bumps=tuple(bumps),
            list_pages=list_pages,
            listings_read=listings_read,
            skipped=tuple(skipped),
        )

    def _read_list(
        self, known: Mapping[str, datetime], bootstrap: bool
    ) -> tuple[list[FeedItem], int, int]:
        """The run's list pages: every token once, in the order first seen."""
        seen: dict[str, FeedItem] = {}
        url: str | None = LIST_URL
        pages = listings_read = 0
        limit = BOOTSTRAP_LIST_PAGES if bootstrap else MAX_LIST_PAGES
        while url is not None:
            load = self._load(url)
            if load.html is None:
                raise PageShapeError(f"list page {pages + 1} has no document")
            page_items = feed_items(load.html)
            pages += 1
            listings_read += len(page_items)
            holds_new = False
            for item in page_items:
                if item.token in seen:
                    continue
                seen[item.token] = item
                if item.private and _listing_id(item.token) not in known:
                    holds_new = True
            if pages >= limit or (not bootstrap and pages >= MIN_LIST_PAGES and not holds_new):
                break
            url = page_link(load.html, pages + 1, base=load.final_url)
            if url is None:
                logger.warning("yad2: list page %d has no link to page %d", pages, pages + 1)
        return list(seen.values()), pages, listings_read

    def _bumps(
        self,
        items: list[FeedItem],
        known: Mapping[str, datetime],
        started: datetime,
        skipped: list[str],
    ) -> list[Bump]:
        due = [
            item
            for item in items
            if (stored := known.get(_listing_id(item.token))) is not None
            and stored < started - BUMP_AGE
        ]
        due.sort(key=lambda item: not item.private)  # stable: private first, each in page order
        bumps = []
        for item in due[:MAX_BUMP_CHECKS]:
            d = self._listing_page(item.token, skipped)
            if d is None:
                continue
            listing_id = _listing_id(item.token)
            try:
                updated_at = parse_israel_local_utc(d["dates"]["updatedAt"])
            except (KeyError, TypeError, ValueError) as error:
                logger.warning("yad2: listing %s has no updatedAt: %r", item.token, error)
                skipped.append(item.token)
                continue
            if updated_at > known[listing_id]:
                bumps.append(Bump(listing_id=listing_id, updated_at=updated_at))
        return bumps

    def _listing_page(self, token: str, skipped: list[str]) -> dict[str, Any] | None:
        """The listing page's `data`, or `None` (the token appended to `skipped`) when the page
        did not load or holds no listing with this token. A block raises."""
        try:
            load = self._load(PERMALINK.format(token=token))
        except PageLoadError as error:
            logger.warning("yad2: listing %s did not load: %s", token, error)
            skipped.append(token)
            return None
        try:
            if load.html is None:
                raise PageShapeError("no document")
            d = listing_data(load.html)
            if d["token"] != token:
                raise PageShapeError("the page holds another listing")
        except PageShapeError as error:
            logger.warning("yad2: listing %s: %s", token, error)
            skipped.append(token)
            return None
        return d

    def _load(self, url: str) -> PageLoad:
        if self._loads:
            jitter = self._jitter() if self._jitter else random.uniform(0, PAUSE_JITTER_SECONDS)
            (self._sleep or time.sleep)(PAUSE_SECONDS + jitter)
        self._loads += 1
        load = self._browser.load(url)
        reason = blocked_reason(load)
        if reason is not None:
            logger.error("yad2: %s (page %d of the run)", reason, self._loads)
            raise Yad2Blocked(reason)
        return load


def _listing_id(token: str) -> str:
    return compute_listing_id(token, source=YAD2_SOURCE)
