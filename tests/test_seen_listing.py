"""Task 3.6 (a), test group 1: the post as a user sees it (`postmodel/seen.py`; DECISIONS.md #256,
#281, #284, #287, #295 point 3)."""

from datetime import date
from typing import Any

import pytest

from tests.conftest import make_correction, make_listing
from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.postmodel.seen import seen_listing

LISTING_ID = "c" * 64

# One corrected value per reportable field, each different from `base()`'s.
CORRECTED: dict[str, Any] = {
    "post_nature": "sublet_offer",
    "apartment_kind": {"state": "written", "value": "room"},
    "price": {"state": "written", "value": [6500]},
    "entry_date": {"state": "written", "value": "immediate"},
    "rooms": {"state": "written", "value": 3.5},
    "floor": {"state": "written", "value": -1},
    "building_floors": {"state": "written", "value": 4},
    "size_sqm": {"state": "written", "value": 70.5},
    "room_size_sqm": {"state": "written", "value": 12.0},
    "broker": {"state": "written", "value": False},
    "balcony": {"state": "written", "value": True},
    "parking": {"state": "unclear", "value": None},
    "elevator": {"state": "written", "value": True},
    "air_conditioning": {"state": "written", "value": False},
    "furnished": {"state": "written", "value": "partial"},
    "arnona": {"state": "written", "value": "included"},
    "house_committee": {"state": "written", "value": 250},
    "gender": "women_only",
    "areas": [42, 52],
    "streets": ["הרצל"],
    "other_city": "רמת גן",
    "phone_names": [{"phone": "0541234567", "name": "דני"}],
}


def base() -> Listing:
    return make_listing(
        LISTING_ID,
        price={"state": "written", "value": [7000]},
        price_source="text",
        entry_date={"state": "written", "value": date(2026, 11, 1)},
        areas=[52],
    )


def test_every_reportable_field_has_a_case() -> None:
    assert set(CORRECTED) == set(ReportableField.__args__)  # type: ignore[attr-defined]


@pytest.mark.parametrize("field", sorted(CORRECTED))
def test_each_reportable_field_is_corrected_on_a_copy(field: str) -> None:
    listing = base()
    before = listing.model_dump()
    correction = make_correction(listing, field, CORRECTED[field])
    seen = seen_listing(listing, [correction])
    assert getattr(seen.listing, field) == correction.corrected_value
    assert seen.corrected == {field}
    assert listing.model_dump() == before  # the stored Listing is never edited (#256)
    untouched = {name for name in Listing.model_fields if name not in (field, "price_source")}
    assert {name: getattr(seen.listing, name) for name in untouched} == {
        name: getattr(listing, name) for name in untouched
    }
    assert Listing.model_validate(seen.listing.model_dump()) == seen.listing


def test_no_correction_returns_the_listing_itself() -> None:
    listing = base()
    seen = seen_listing(listing, [])
    assert seen.listing is listing and seen.corrected == frozenset()


def test_a_removed_correction_is_ignored_and_two_fields_are_both_applied() -> None:
    listing = base()
    removed = make_correction(listing, "areas", [40], removed=True, n=1)
    rooms = make_correction(listing, "rooms", {"state": "written", "value": 2.0}, n=2)
    areas = make_correction(listing, "areas", [30, 31], n=3)
    seen = seen_listing(listing, [removed, rooms, areas])
    assert (seen.listing.areas, seen.listing.rooms.value) == ([30, 31], 2.0)
    assert seen.corrected == {"areas", "rooms"}
    only_removed = seen_listing(listing, [removed])
    assert only_removed.listing == listing and only_removed.corrected == frozenset()


def test_a_correction_of_another_post_or_two_in_force_on_a_field_raise() -> None:
    listing = base()
    other = make_correction(make_listing("d" * 64), "areas", [40])
    with pytest.raises(ValueError, match="is of post"):
        seen_listing(listing, [other])
    first = make_correction(listing, "areas", [40], n=1)
    second = make_correction(listing, "areas", [41], n=2)
    with pytest.raises(ValueError, match="two corrections in force"):
        seen_listing(listing, [first, second])


def test_price_source_follows_a_price_corrected_across_not_written() -> None:
    """#295, point 3."""
    priced = base()
    to_nothing = make_correction(priced, "price", {"state": "not_written", "value": None})
    assert seen_listing(priced, [to_nothing]).listing.price_source is None
    to_unclear = make_correction(priced, "price", {"state": "unclear", "value": None})
    assert seen_listing(priced, [to_unclear]).listing.price_source == "text"
    native = make_listing(
        LISTING_ID, price={"state": "written", "value": [1000]}, price_source="native"
    )
    changed = make_correction(native, "price", {"state": "written", "value": [7200]})
    assert seen_listing(native, [changed]).listing.price_source == "native"  # kept
    unpriced = make_listing(LISTING_ID)
    assert unpriced.price_source is None
    found = make_correction(unpriced, "price", {"state": "written", "value": [5000]})
    seen = seen_listing(unpriced, [found])
    assert (seen.listing.price.value, seen.listing.price_source) == ([5000], "text")
