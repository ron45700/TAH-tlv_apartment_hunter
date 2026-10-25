"""The Yad2 seam on the spikes' saved pages, read in place from `data/raw/` (gitignored; copied in
round 47 with dated names, `PHASE_6.md` §6.10): the list pages in both shapes, pages 2 and 3,
Radware's challenge page and its check page, and a bootstrap over the saved pages. No value of a
page is written here: tokens are compared with what the pages themselves hold."""

import dataclasses
from datetime import UTC, datetime

import pytest

from tests.test_yad2_mapping import _page
from tests.yad2_synthetic import FakeBrowser, fixed_clock
from tlv_hunter.yad2 import mapping
from tlv_hunter.yad2.block import PageLoad, blocked_reason
from tlv_hunter.yad2.collector import LIST_URL, Yad2Collector
from tlv_hunter.yad2.feed import PROMOTED_LISTS, feed_items, page_link
from tlv_hunter.yad2.pages import PageShapeError, listing_data, query_data

pytestmark = pytest.mark.raw_fixtures

# Spike 2's list run at 11:36 UTC (laptop: `private` 20 + `agency` 20) and its server run
# (one `yad2` list, 28 private and 12 agency).
LAPTOP = {n: f"yad2_list_page{n}_2026-10-24.html" for n in (1, 2, 3)}
MIXED = "yad2_list_mixed_page1_2026-10-24.html"
CHALLENGE = "yad2_challenge_2026-10-22.html"  # spike 1's run 4, headless
CHECK_PAGE = "yad2_radware_interstitial_2026-10-24.html"  # the server run's first document
PRIVATE = [f"yad2_listing_private_{n}_2026-10-24.html" for n in (1, 2, 3)]
# The hosts that answered spike 1's blocked load (its manifest): no gw.yad2.co.il.
CHALLENGE_HOSTS = frozenset({"www.yad2.co.il", "validate.perfdrive.com", "newassets.hcaptcha.com"})
SERVED = frozenset({"www.yad2.co.il", "gw.yad2.co.il", "www.google.com"})
NOW = datetime(2026, 10, 24, 11, 40, tzinfo=UTC)


def _feed(name: str) -> dict:
    return query_data(_page(name), "realestate-rent-feed")


def test_the_laptops_shape_private_then_agency() -> None:
    for name in LAPTOP.values():
        items = feed_items(_page(name))
        assert [item.private for item in items] == [True] * 20 + [False] * 20
        feed = _feed(name)
        assert [item.token for item in items] == [
            ad["token"] for ad in feed["private"] + feed["agency"]
        ]


def test_the_servers_mixed_shape() -> None:
    items = feed_items(_page(MIXED))
    feed = _feed(MIXED)
    assert "private" not in feed and "agency" not in feed
    assert [item.token for item in items] == [ad["token"] for ad in feed["yad2"]]
    assert (len(items), sum(item.private for item in items)) == (40, 28)


@pytest.mark.parametrize("name", [*LAPTOP.values(), MIXED])
def test_the_promoted_lists_are_left_out(name: str) -> None:
    feed = _feed(name)
    promoted = {
        ad.get("token") for list_name in PROMOTED_LISTS for ad in feed.get(list_name, [])
    } - {None}
    assert promoted
    assert promoted.isdisjoint({item.token for item in feed_items(_page(name))})


def test_pages_1_to_3_share_no_listing() -> None:
    """Spike §S2.2: stable between pages."""
    tokens = [{item.token for item in feed_items(_page(name))} for name in LAPTOP.values()]
    assert len(tokens[0] | tokens[1] | tokens[2]) == 120


@pytest.mark.parametrize("number", [1, 2, 3])
def test_each_page_links_to_the_next(number: int) -> None:
    base = LIST_URL if number == 1 else f"{LIST_URL}&page={number}"
    assert page_link(_page(LAPTOP[number]), number + 1, base=base) == (
        f"{LIST_URL}&page={number + 1}"
    )


def test_the_mixed_page_links_to_page_2() -> None:
    assert page_link(_page(MIXED), 2, base=LIST_URL) == f"{LIST_URL}&page=2"


def test_the_challenge_page_is_a_block() -> None:
    load = PageLoad(
        url=LIST_URL,
        final_url="https://validate.perfdrive.com/ccb4768f5e2ea98586d13473d71efc83/?ssa=x",
        html=_page(CHALLENGE),
        hosts=CHALLENGE_HOSTS,
    )
    assert blocked_reason(load) == "blocked: the page moved to validate.perfdrive.com"
    # The second sign alone also tells it: no call reached Yad2's API.
    on_yad2 = dataclasses.replace(load, final_url=LIST_URL)
    assert blocked_reason(on_yad2) == "blocked: no request reached gw.yad2.co.il"
    with pytest.raises(PageShapeError):
        feed_items(load.html or "")


@pytest.mark.parametrize("name", [*LAPTOP.values(), MIXED, *PRIVATE])
def test_a_served_page_is_not_a_block(name: str) -> None:
    load = PageLoad(url=LIST_URL, final_url=LIST_URL, html=_page(name), hosts=SERVED)
    assert blocked_reason(load) is None


def test_radwares_check_page_holds_no_data() -> None:
    """Served on www.yad2.co.il before the real page to a new profile: never read as a list."""
    with pytest.raises(PageShapeError):
        feed_items(_page(CHECK_PAGE))
    with pytest.raises(PageShapeError):
        listing_data(_page(CHECK_PAGE))


def test_a_bootstrap_over_the_saved_pages() -> None:
    """Pages 1-3 by their own links; the three saved listing pages mapped, every other listing
    page missing (skipped, not stored, tried at the next run)."""
    pages: dict[str, PageLoad | str | Exception] = {LIST_URL: _page(LAPTOP[1])}
    for number in (2, 3):
        pages[f"{LIST_URL}&page={number}"] = _page(LAPTOP[number])
    saved = {}
    for name in PRIVATE:
        d = listing_data(_page(name))
        saved[d["token"]] = d
        pages[mapping.PERMALINK.format(token=d["token"])] = _page(name)
    browser = FakeBrowser(pages)
    collector = Yad2Collector(browser, clock=fixed_clock(NOW), sleep=lambda s: None)
    collection = collector.collect({}, bootstrap=True)
    assert collection.list_pages == 3 and collection.listings_read == 120
    assert {listing.post.source_post_id for listing in collection.listings} == set(saved)
    for listing in collection.listings:
        d = saved[listing.post.source_post_id]
        assert listing.post == mapping.to_raw_post(d, fetched_at=NOW)
        assert listing.form == mapping.form_fields(d)
    assert len(collection.skipped) == 117
    assert len(browser.asked) == 3 + 120
