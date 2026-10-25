"""The Yad2 seam's rules (`PHASE_6.md` §6.5, §6.6, §6.8; DECISIONS.md #492, #493, #497, #504, #514)
on synthetic pages in the saved pages' shapes (`tests/yad2_synthetic.py`). The saved pages
themselves are read in `test_yad2_list_pages.py`. No browser, no network."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.yad2_synthetic import (
    FakeBrowser,
    fixed_clock,
    lid,
    listing_data,
    listing_html,
    page_url,
    site,
    token,
)
from tlv_hunter.parsing.datetimes import parse_israel_local_utc
from tlv_hunter.yad2 import collector as collector_module
from tlv_hunter.yad2.block import PageLoad, PageLoadError
from tlv_hunter.yad2.collector import (
    BUMP_AGE,
    LIST_URL,
    MAX_BUMP_CHECKS,
    MAX_LIST_PAGES,
    PAUSE_SECONDS,
    Yad2Blocked,
    Yad2Collector,
)
from tlv_hunter.yad2.mapping import PERMALINK
from tlv_hunter.yad2.pages import PageShapeError

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)
OLD = NOW - BUMP_AGE - timedelta(minutes=1)
RECENT = NOW - BUMP_AGE + timedelta(minutes=1)


def _pages(count: int, start: int = 0, per_page: int = 4) -> dict[int, list[str]]:
    """`count` list pages, each with `per_page` private and 2 agency tokens, all different."""
    pages = {}
    for number in range(1, count + 1):
        base = start + (number - 1) * per_page
        pages[number] = [token(base + i) for i in range(per_page)] + [
            token((number - 1) * 2 + i, "a") for i in range(2)
        ]
    return pages


def _collector(pages, sleeps=None) -> tuple[Yad2Collector, FakeBrowser]:
    browser = FakeBrowser(pages)
    sleep = sleeps.append if sleeps is not None else lambda seconds: None
    return Yad2Collector(browser, clock=fixed_clock(NOW), sleep=sleep, jitter=lambda: 1.5), browser


def _known(tokens, at=RECENT) -> dict[str, datetime]:
    return {lid(value): at for value in tokens}


def _list_pages_asked(browser: FakeBrowser) -> list[str]:
    return [url for url in browser.asked if url.startswith(LIST_URL)]


def _opened(browser: FakeBrowser) -> list[str]:
    return [url.rsplit("/", 1)[1] for url in browser.asked if "/item/" in url]


def test_bootstrap_reads_exactly_three_pages_and_opens_every_token() -> None:
    pages = _pages(5)
    collector, browser = _collector(site(pages))
    collection = collector.collect({}, bootstrap=True)
    assert _list_pages_asked(browser) == [page_url(1), page_url(2), page_url(3)]
    expected = [value for number in (1, 2, 3) for value in pages[number]]
    assert sorted(listing.post.source_post_id for listing in collection.listings) == sorted(
        expected
    )
    assert collection.list_pages == 3
    assert collection.listings_read == 18
    assert collection.bumps == () and collection.skipped == ()


def test_bootstrap_checks_no_bump() -> None:
    pages = _pages(3)
    collector, browser = _collector(site(pages))
    collection = collector.collect(_known(pages[1], at=OLD), bootstrap=True)
    assert collection.bumps == ()
    assert not set(_opened(browser)) & set(pages[1])


def test_at_least_three_pages_when_nothing_is_new() -> None:
    pages = _pages(6)
    known = _known([value for tokens in pages.values() for value in tokens])
    collector, browser = _collector(site(pages))
    collection = collector.collect(known, bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(1), page_url(2), page_url(3)]
    assert collection.listings == ()


def test_paging_stops_after_the_first_page_past_the_minimum_with_nothing_new() -> None:
    pages = _pages(8)
    new = {pages[3][0], *pages[5]}
    seen = [value for tokens in pages.values() for value in tokens if value not in new]
    collector, browser = _collector(site(pages))
    collector.collect(_known(seen), bootstrap=False)
    # Page 3 holds a new token, so page 4 is read; it holds none: page 5's are not reached.
    assert _list_pages_asked(browser) == [page_url(n) for n in (1, 2, 3, 4)]


def test_new_private_tokens_on_pages_3_and_4_take_the_run_to_page_5() -> None:
    pages = _pages(8)
    new = [pages[3][0], pages[4][0]]
    seen = [value for tokens in pages.values() for value in tokens if value not in new]
    collector, browser = _collector(site(pages))
    collection = collector.collect(_known(seen), bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(n) for n in (1, 2, 3, 4, 5)]
    assert [listing.post.source_post_id for listing in collection.listings] == new


def test_a_new_agency_token_alone_does_not_page_on_but_is_collected() -> None:
    """#514: only private listings decide; an unseen agency token is still opened."""
    pages = _pages(6)
    agency = pages[3][-1]
    assert agency.startswith("a")
    seen = [value for tokens in pages.values() for value in tokens if value != agency]
    collector, browser = _collector(site(pages))
    collection = collector.collect(_known(seen), bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(n) for n in (1, 2, 3)]
    assert [listing.post.source_post_id for listing in collection.listings] == [agency]


def test_never_more_than_ten_list_pages() -> None:
    pages = _pages(14)
    collector, browser = _collector(site(pages))
    collection = collector.collect({lid("zzzzzzzz"): RECENT}, bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(n) for n in range(1, MAX_LIST_PAGES + 1)]
    assert collection.list_pages == MAX_LIST_PAGES


def test_a_token_repeated_on_a_later_page_is_read_once_and_is_not_new_there() -> None:
    pages = _pages(6)
    pages[4] = [pages[3][0], *pages[2]]  # moved down between page loads
    seen = [value for n in (1, 2, 5, 6) for value in pages[n]] + pages[3][1:]
    collector, browser = _collector(site(pages))
    collection = collector.collect(_known(seen), bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(n) for n in (1, 2, 3, 4)]
    assert [listing.post.source_post_id for listing in collection.listings] == [pages[3][0]]
    assert collection.listings_read == 6 * 3 + 7


def test_the_list_ends_where_its_links_end() -> None:
    pages = _pages(4)
    collector, browser = _collector(site(pages))
    collection = collector.collect({}, bootstrap=False)
    assert _list_pages_asked(browser) == [page_url(n) for n in (1, 2, 3, 4)]
    assert collection.list_pages == 4


def test_the_mixed_shape_is_read_the_same() -> None:
    collector, _ = _collector(site(_pages(3), mixed=True))
    assert len(collector.collect({}, bootstrap=True).listings) == 18


def test_the_promoted_lists_are_ignored() -> None:
    collector, browser = _collector(site(_pages(3)))
    collection = collector.collect({}, bootstrap=True)
    assert "x0000001" not in {listing.post.source_post_id for listing in collection.listings}
    assert "x0000001" not in _opened(browser)


def test_a_pause_of_four_seconds_and_the_random_part_before_every_load_but_the_first() -> None:
    sleeps: list[float] = []
    collector, browser = _collector(site(_pages(3)), sleeps)
    collector.collect({}, bootstrap=True)
    assert len(browser.asked) == 3 + 18
    assert sleeps == [PAUSE_SECONDS + 1.5] * (len(browser.asked) - 1)


def test_the_random_part_is_drawn_up_to_two_seconds(monkeypatch: pytest.MonkeyPatch) -> None:
    draws: list[tuple[float, float]] = []

    def uniform(low: float, high: float) -> float:
        draws.append((low, high))
        return 0.25

    monkeypatch.setattr(collector_module.random, "uniform", uniform)
    sleeps: list[float] = []
    browser = FakeBrowser(site(_pages(3)))
    Yad2Collector(browser, clock=fixed_clock(NOW), sleep=sleeps.append).collect({}, bootstrap=True)
    assert set(draws) == {(0, 2.0)}
    assert set(sleeps) == {4.25}


def test_a_listing_page_that_fails_is_skipped_and_its_token_not_returned() -> None:
    pages = _pages(3)
    bad_load, bad_shape, other = pages[1][0], pages[1][1], pages[2][0]
    served = site(pages)
    served[PERMALINK.format(token=bad_load)] = PageLoadError("timeout")
    served[PERMALINK.format(token=bad_shape)] = "<html>the listing was removed</html>"
    served[PERMALINK.format(token=other)] = listing_html(listing_data("q0000000"))
    collector, _ = _collector(served)
    collection = collector.collect({}, bootstrap=True)
    assert collection.skipped == (bad_load, bad_shape, other)
    returned = {listing.post.source_post_id for listing in collection.listings}
    assert returned.isdisjoint(collection.skipped)
    assert len(returned) == 18 - 3


def test_a_listing_that_does_not_map_is_skipped() -> None:
    pages = _pages(3)
    broken = pages[1][0]
    d = listing_data(broken)
    del d["dates"]
    collector, _ = _collector(site(pages, {broken: d}))
    assert collector.collect({}, bootstrap=True).skipped == (broken,)


def test_a_new_listing_comes_with_its_form() -> None:
    collector, _ = _collector(site(_pages(3)))
    listing = collector.collect({}, bootstrap=True).listings[0]
    assert listing.post.source == "yad2"
    assert listing.post.fetched_at == NOW
    assert listing.form["price"] == {"state": "written", "value": [6500]}


def test_a_list_page_that_fails_fails_the_run() -> None:
    served = site(_pages(3))
    served[page_url(2)] = PageLoadError("timeout")
    with pytest.raises(PageLoadError):
        _collector(served)[0].collect({}, bootstrap=True)
    served[page_url(2)] = "<html>no data</html>"
    with pytest.raises(PageShapeError):
        _collector(served)[0].collect({}, bootstrap=True)


@pytest.mark.parametrize("where", ["list page 1", "list page 3", "a listing page"])
def test_a_challenge_page_anywhere_blocks_the_run(where: str) -> None:
    pages = _pages(3)
    served = site(pages)
    url = {
        "list page 1": page_url(1),
        "list page 3": page_url(3),
        "a listing page": PERMALINK.format(token=pages[2][1]),
    }[where]
    served[url] = PageLoad(
        url=url,
        final_url="https://validate.perfdrive.com/abc/?ssa=1",
        html="<html><title>Radware</title></html>",
        hosts=frozenset({"www.yad2.co.il", "validate.perfdrive.com"}),
    )
    collector, browser = _collector(served)
    with pytest.raises(Yad2Blocked, match="validate.perfdrive.com"):
        collector.collect({}, bootstrap=True)
    assert browser.asked[-1] == url  # nothing loaded after the block


def test_a_page_with_no_call_to_yad2s_api_blocks_the_run() -> None:
    served = site(_pages(3))
    html = served[page_url(1)]
    assert isinstance(html, str)
    served[page_url(1)] = PageLoad(
        url=page_url(1), final_url=page_url(1), html=html, hosts=frozenset({"www.yad2.co.il"})
    )
    with pytest.raises(Yad2Blocked, match="gw.yad2.co.il"):
        _collector(served)[0].collect({}, bootstrap=True)


def test_the_background_challenge_frame_is_not_a_block() -> None:
    """Every Yad2 page carries Google's background frame (spike §7, §S2.5)."""
    served = site(_pages(3))
    html = served[page_url(1)]
    assert isinstance(html, str)
    frame = '<body><iframe src="https://www.google.com/recaptcha/api2/aframe"></iframe>'
    served[page_url(1)] = PageLoad(
        url=page_url(1),
        final_url=page_url(1),
        html=html.replace("<body>", frame),
        hosts=frozenset({"www.yad2.co.il", "gw.yad2.co.il", "www.google.com"}),
    )
    assert len(_collector(served)[0].collect({}, bootstrap=True).listings) == 18


def test_bump_checks_open_known_tokens_over_three_hours_old_private_first_at_most_ten() -> None:
    pages = _pages(3, per_page=6)  # 18 private, 6 agency
    tokens = [value for number in (1, 2, 3) for value in pages[number]]
    private = [value for value in tokens if value.startswith("p")]
    known = _known(tokens, at=OLD)
    known[lid(private[0])] = RECENT  # updated within 3 hours: not checked
    collector, browser = _collector(site(pages))
    collector.collect(known, bootstrap=False)
    assert _opened(browser) == private[1 : 1 + MAX_BUMP_CHECKS]


def test_agency_tokens_are_checked_after_the_private_ones() -> None:
    pages = _pages(3, per_page=2)  # 6 private, 6 agency
    tokens = [value for number in (1, 2, 3) for value in pages[number]]
    private = [value for value in tokens if value.startswith("p")]
    agency = [value for value in tokens if value.startswith("a")]
    collector, browser = _collector(site(pages))
    collector.collect(_known(tokens, at=OLD), bootstrap=False)
    assert _opened(browser) == private + agency[:4]


def test_a_later_updated_at_is_a_bump_and_the_same_is_not() -> None:
    pages = _pages(3)
    tokens = [value for number in (1, 2, 3) for value in pages[number]]
    bumped, same = pages[1][0], pages[1][1]
    known = _known(tokens)
    known[lid(bumped)] = OLD
    known[lid(same)] = parse_israel_local_utc("2026-10-24T08:00:00")
    listings = {
        bumped: listing_data(bumped, updated_at="2026-10-24T14:30:00"),
        same: listing_data(same, updated_at="2026-10-24T08:00:00"),
    }
    collector, _ = _collector(site(pages, listings))
    collection = collector.collect(known, bootstrap=False)
    assert [(bump.listing_id, bump.updated_at) for bump in collection.bumps] == [
        (lid(bumped), parse_israel_local_utc("2026-10-24T14:30:00"))
    ]
    assert collection.listings == ()


def test_only_the_list_and_listing_pages_are_ever_asked() -> None:
    """#497: no phone request: every URL asked is a list page or a listing's permalink."""
    pages = _pages(4)
    tokens = [value for tokens in pages.values() for value in tokens]
    collector, browser = _collector(site(pages))
    collector.collect(_known(tokens[:8], at=OLD), bootstrap=False)
    for url in browser.asked:
        assert url.startswith(LIST_URL) or url.startswith(
            "https://www.yad2.co.il/realestate/item/tel-aviv-area/"
        ), url


def test_the_seam_reads_no_store_and_never_clicks() -> None:
    package = Path(collector_module.__file__).parent
    for path in package.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        for word in ("tlv_hunter.store", "tlv_hunter.state", ".click(", "sqlite3"):
            assert word not in source, (path.name, word)


def test_block_detection_never_looks_for_a_challenge_word() -> None:
    """§6.6: never the word "captcha": no Yad2 module's code holds it."""
    package = Path(collector_module.__file__).parent
    for path in package.glob("*.py"):
        assert "captcha" not in path.read_text(encoding="utf-8").lower(), path.name
