"""Gate B: the Listing record's rules (SCHEMA.md, Gate B; DECISIONS.md #109, task 2.2)."""

from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from tests.conftest import make_listing
from tlv_hunter.contracts.listing import Listing, Marked

ID = "a" * 64


def written(value):
    return {"state": "written", "value": value}


def test_listing_fields_are_exactly_approved() -> None:
    """SCHEMA.md, Gate B, in its order."""
    assert list(Listing.model_fields) == [
        "schema_version",
        "listing_id",
        "model_name",
        "prompt_version",
        "classified_at",
        "post_nature",
        "apartment_kind",
        "price",
        "price_source",
        "entry_date_written",
        "entry_date",
        "rooms",
        "floor",
        "building_floors",
        "size_sqm",
        "room_size_sqm",
        "broker",
        "balcony",
        "parking",
        "elevator",
        "air_conditioning",
        "furnished",
        "arnona",
        "house_committee",
        "gender",
        "streets",
        "stated_area_names",
        "areas",
        "other_city",
        "phone_names",
    ]


def test_a_listing_with_nothing_written_is_valid() -> None:
    listing = make_listing(ID)
    assert listing.price.state == "not_written"
    assert listing.areas == []


def test_a_full_listing_round_trips_through_json() -> None:
    listing = make_listing(
        ID,
        apartment_kind=written("room"),
        price=written([4500, 4800]),
        price_source="text",
        entry_date_written="1.11",
        entry_date=written(date(2026, 11, 1)),
        rooms=written(3.5),
        floor=written(-1),
        size_sqm=written(52.5),
        balcony=written(False),
        furnished=written("partial"),
        arnona=written("included"),
        house_committee=written(150),
        streets=["דיזנגוף"],
        stated_area_names=["בצפון הישן"],
        areas=[30, 31],
        phone_names=[{"phone": "0541234567", "name": "דני"}],
    )
    assert Listing.model_validate_json(listing.model_dump_json()) == listing


def test_an_immediate_entry_date_round_trips() -> None:
    listing = make_listing(ID, entry_date=written("immediate"))
    assert Listing.model_validate_json(listing.model_dump_json()).entry_date.value == "immediate"


@pytest.mark.parametrize(
    "marked",
    [
        {"state": "written", "value": None},
        {"state": "not_written", "value": True},
        {"state": "unclear", "value": True},
    ],
)
def test_a_value_is_set_exactly_when_written(marked) -> None:
    with pytest.raises(ValidationError, match="exactly when state is 'written'"):
        Marked[bool].model_validate(marked)


def test_an_unclear_field_keeps_no_value() -> None:
    assert make_listing(ID, parking={"state": "unclear", "value": None}).parking.value is None


@pytest.mark.parametrize(
    ("price", "source"),
    [
        ({"state": "not_written", "value": None}, "text"),
        (written([4000]), None),
        ({"state": "unclear", "value": None}, None),
    ],
)
def test_price_source_is_none_exactly_when_price_is_not_written(price, source) -> None:
    with pytest.raises(ValidationError, match="price_source"):
        make_listing(ID, price=price, price_source=source)


def test_an_unclear_price_has_a_source() -> None:
    listing = make_listing(ID, price={"state": "unclear", "value": None}, price_source="text")
    assert listing.price_source == "text"


@pytest.mark.parametrize(("value", "match"), [([], "at least one"), ([4000, 0], "greater than 0")])
def test_a_written_price_is_a_non_empty_list_of_positive_amounts(value, match) -> None:
    with pytest.raises(ValidationError, match=match):
        make_listing(ID, price=written(value), price_source="text")


@pytest.mark.parametrize("rooms", [0.0, -1.0, 2.25, 3.3])
def test_rooms_is_a_positive_multiple_of_a_half(rooms) -> None:
    with pytest.raises(ValidationError, match="multiple of 0.5"):
        make_listing(ID, rooms=written(rooms))


@pytest.mark.parametrize(
    ("areas", "match"), [([0], "1-71"), ([72], "1-71"), ([31, 30], "sorted"), ([30, 30], "sorted")]
)
def test_areas_are_sorted_municipal_numbers_with_no_repeats(areas, match) -> None:
    with pytest.raises(ValidationError, match=match):
        make_listing(ID, areas=areas)


def test_a_phone_name_carries_the_stored_phone_format() -> None:
    with pytest.raises(ValidationError, match="stored format"):
        make_listing(ID, phone_names=[{"phone": "054-1234567", "name": "דני"}])


@pytest.mark.parametrize(
    "when",
    [
        datetime(2026, 10, 5, 12, 0),
        datetime(2026, 10, 5, 15, 0, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_classified_at_is_tz_aware_utc(when) -> None:
    with pytest.raises(ValidationError, match="UTC"):
        make_listing(ID, classified_at=when)


def test_unknown_fields_are_refused() -> None:
    with pytest.raises(ValidationError):
        make_listing(ID, confidence=0.9)


def test_a_listing_is_frozen() -> None:
    with pytest.raises(ValidationError):
        make_listing(ID).areas = [1]  # type: ignore[misc]
