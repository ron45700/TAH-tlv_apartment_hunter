import hashlib
from datetime import UTC, date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pytest

from tlv_hunter.parsing.datetimes import nearest_occurrence, parse_rfc2822_utc, require_utc
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.parsing.prices import (
    NATIVE_PRICE_FLOOR,
    ParsedPrice,
    native_price_fallback,
    parse_native_price,
)

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


def test_require_utc_accepts_utc_and_returns_it_unchanged() -> None:
    value = datetime(2026, 10, 4, 9, 0, tzinfo=UTC)
    assert require_utc(value) is value
    assert require_utc(datetime(2026, 10, 4, 9, 0, tzinfo=timezone(timedelta(0)))).tzinfo


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 4, 9, 0),
        datetime(2026, 10, 4, 12, 0, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_require_utc_rejects_naive_and_non_utc(value: datetime) -> None:
    with pytest.raises(ValueError, match="tz-aware UTC"):
        require_utc(value)


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


@pytest.mark.parametrize(("native", "expected"), [(None, None), (0, None), (499, None), (500, 500)])
def test_native_price_fallback_ignores_a_price_below_500(native, expected) -> None:
    """DECISIONS.md #114: a constant, not config."""
    assert NATIVE_PRICE_FLOOR == 500
    assert native_price_fallback(native) == expected


@pytest.mark.parametrize(
    ("day", "month", "reference", "expected"),
    [
        (1, 10, date(2026, 10, 5), date(2026, 10, 1)),  # #115: "1.10" in a post of 5.10
        (1, 11, date(2026, 10, 5), date(2026, 11, 1)),
        (15, 12, date(2027, 1, 10), date(2026, 12, 15)),  # December in a post of January
        (1, 2, date(2026, 12, 20), date(2027, 2, 1)),
        (28, 2, date(2026, 10, 5), date(2027, 2, 28)),
        (29, 2, date(2027, 10, 5), date(2028, 2, 29)),
    ],
)
def test_nearest_occurrence(day, month, reference, expected) -> None:
    assert nearest_occurrence(day, month, reference) == expected


def test_nearest_occurrence_tie_goes_to_the_later_year() -> None:
    """DECISIONS.md #179: 31.8.2027 is 183 days after 1.3.2027 and 183 days before 1.3.2028."""
    reference = date(2027, 8, 31)
    assert reference - date(2027, 3, 1) == date(2028, 3, 1) - reference
    assert nearest_occurrence(1, 3, reference) == date(2028, 3, 1)


def test_nearest_occurrence_of_a_day_that_does_not_exist_is_none() -> None:
    assert nearest_occurrence(31, 11, date(2026, 10, 5)) is None
    assert nearest_occurrence(29, 2, date(2026, 10, 5)) is None  # no 29.2 in 2025-2027
