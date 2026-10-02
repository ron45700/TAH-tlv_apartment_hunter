import hashlib
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import pytest

from tlv_hunter.parsing.datetimes import parse_rfc2822_utc
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.parsing.prices import ParsedPrice, parse_native_price

OBSERVED_PRICES = {
    "2178554076041449": ("₪9,000", 9000),
    "2178444986052358": ("₪3,560", 3560),
    "2178430789387111": ("₪9,000", 9000),
    "2178421059388084": ("₪8,700", 8700),
    "2178206242742899": ("₪2,380", 2380),
    "2178092279420962": ("₪3,600", 3600),
    "2177677192795804": ("₪2,940", 2940),
    "2177447349485455": ("₪3,600", 3600),
}


def test_known_creation_time_parses_to_utc() -> None:
    assert parse_rfc2822_utc("Sun, 13 Sep 2026 18:47:44 GMT") == datetime(
        2026, 9, 13, 18, 47, 44, tzinfo=UTC
    )


def test_all_20_creation_times_parse_to_aware_utc(thedoor_items) -> None:
    for item in thedoor_items:
        parsed = parse_rfc2822_utc(item["creation_time"])
        assert parsed.utcoffset() == timedelta(0)
        assert parsed == parsedate_to_datetime(item["creation_time"])


def test_non_utc_offset_is_converted_to_utc() -> None:
    parsed = parse_rfc2822_utc("Sun, 13 Sep 2026 21:47:44 +0300")
    assert parsed == datetime(2026, 9, 13, 18, 47, 44, tzinfo=UTC)
    assert parsed.utcoffset() == timedelta(0)


def test_unknown_zone_minus_0000_raises_instead_of_returning_naive() -> None:
    with pytest.raises(ValueError):
        parse_rfc2822_utc("Sun, 13 Sep 2026 18:47:44 -0000")


def test_garbage_datetime_raises() -> None:
    with pytest.raises(ValueError):
        parse_rfc2822_utc("not a date")


def test_all_8_observed_sale_post_prices_parse(thedoor_items) -> None:
    sale_posts = {i["post_id"]: i["sale_post"] for i in thedoor_items if i["sale_post"] is not None}
    assert set(sale_posts) == set(OBSERVED_PRICES)
    for post_id, (raw, amount) in OBSERVED_PRICES.items():
        assert sale_posts[post_id]["price"] == raw
        assert parse_native_price(raw) == ParsedPrice(amount, "ILS")


@pytest.mark.parametrize(
    "raw", ["$3,600", "3,600", "₪", "₪3.600", "₪3,60", "3,600 ₪", "€3,600", "₪3,600/month", ""]
)
def test_unparseable_or_non_shekel_price_is_none_not_a_guess(raw: str) -> None:
    assert parse_native_price(raw) == ParsedPrice(None, None)


def test_price_without_thousands_separator() -> None:
    assert parse_native_price("₪3600") == ParsedPrice(3600, "ILS")


def test_listing_id_is_full_sha256_hex_of_post_id() -> None:
    listing_id = compute_listing_id("10163683432542695")
    assert listing_id == hashlib.sha256(b"10163683432542695").hexdigest()
    assert len(listing_id) == 64


def test_listing_ids_are_distinct_across_the_20_posts(thedoor_items) -> None:
    assert len({compute_listing_id(i["post_id"]) for i in thedoor_items}) == 20


def test_empty_source_post_id_raises() -> None:
    with pytest.raises(ValueError):
        compute_listing_id("")
