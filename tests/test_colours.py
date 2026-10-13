"""Task 3.7, test group 9: the card's colours, the glow and the tier's reasons (`policy/colours.py`;
`PHASE_3.md` 3.7 (d); DECISIONS.md #308, #309, #320–#323, #330 points 4–6, 8, 18), every row of
(d)'s table; and the WhatsApp number (`textnorm.phones.whatsapp_number`, #311, #330 point 22)."""

from datetime import date
from typing import Any

import pytest

from tests.test_policy import (
    NOT_WRITTEN,
    NOW,
    ROOM,
    UNCLEAR,
    dates,
    profile,
    seen,
    span,
    written,
)
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.policy.colours import (
    COLOURED,
    field_colours,
    glow,
    holds_a_preference,
    tier_reasons,
)
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.postmodel.seen import SeenListing
from tlv_hunter.textnorm.phones import whatsapp_number

FROM = date(2026, 10, 1)


def colours(post: SeenListing, p: Profile | None = None) -> dict[str, str]:
    evaluation = evaluate(post, p or profile(), NOW)
    assert evaluation.shown
    return dict(field_colours(post.listing, evaluation))


# --- a profile category, from its FieldState ---


def test_match_is_green_and_mismatch_red() -> None:
    p = profile(whole={"rooms": span(3.0, 4.0), "balcony": "preference"})
    assert colours(seen(rooms=written(3.5), balcony=written(True)), p)["rooms"] == "green"
    mismatched = colours(seen(rooms=written(2.0), balcony=written(False)), p)
    assert (mismatched["rooms"], mismatched["balcony"]) == ("red", "red")


def test_a_category_not_written_is_grey_and_unclear_orange() -> None:
    p = profile(whole={"parking": "preference", "floor": span(1, 5)})
    found = colours(seen(parking=NOT_WRITTEN, floor=UNCLEAR), p)
    assert (found["parking"], found["floor"]) == ("grey", "orange")


def test_a_price_in_the_range_is_green() -> None:
    p = profile(whole={"price_max": 6000})
    assert colours(seen(price=written([5000])), p)["price"] == "green"


# --- not applied, and every field that is not a category: the post's own value (#309) ---


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("broker", False),
        ("balcony", True),
        ("parking", True),
        ("elevator", True),
        ("air_conditioning", True),
    ],
)
def test_a_known_positive_is_green_with_no_preference(field: str, value: bool) -> None:
    assert colours(seen(**{field: written(value)}))[field] == "green"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("broker", True),
        ("balcony", False),
        ("parking", False),
        ("elevator", False),
        ("air_conditioning", False),
    ],
)
def test_a_known_negative_is_plain_with_no_preference(field: str, value: bool) -> None:
    assert colours(seen(**{field: written(value)}))[field] == "plain"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("rooms", 3.0),
        ("floor", 2),
        ("building_floors", 5),
        ("size_sqm", 70.0),
        ("room_size_sqm", 12.0),
        ("furnished", "yes"),  # "yes" is plain (#330 point 8)
        ("furnished", "partial"),
        ("arnona", 450),
        ("house_committee", "included"),
    ],
)
def test_a_field_with_no_positive_or_negative_is_plain(field: str, value: Any) -> None:
    assert colours(seen(**{field: written(value)}))[field] == "plain"


@pytest.mark.parametrize("field", ["elevator", "furnished", "arnona", "rooms", "room_size_sqm"])
def test_an_own_value_not_written_is_grey_and_unclear_orange(field: str) -> None:
    assert colours(seen(**{field: NOT_WRITTEN}))[field] == "grey"
    assert colours(seen(**{field: UNCLEAR}))[field] == "orange"


def test_a_written_price_or_entry_date_with_no_range_is_plain() -> None:
    found = colours(seen(entry_date=written("immediate")))
    assert (found["price"], found["entry_date"]) == ("plain", "plain")


# --- price and entry date not written: the important-missing badge (#330 point 6) ---


def test_price_and_entry_date_not_written_are_missing_not_grey() -> None:
    found = colours(seen(price=NOT_WRITTEN, entry_date=NOT_WRITTEN))
    assert (found["price"], found["entry_date"]) == ("missing", "missing")
    # Also when the option holds a range for them: the badge, not grey.
    p = profile(whole={"price_max": 9000, "entry_date": dates(FROM, None, "critical")})
    found = colours(seen(price=NOT_WRITTEN, entry_date=NOT_WRITTEN), p)
    assert (found["price"], found["entry_date"]) == ("missing", "missing")


# --- the area ---


def test_the_area_is_orange_when_the_location_is_orange() -> None:
    assert colours(seen(areas=[30, 31]))["areas"] == "orange"  # #250, #275: none chosen
    assert colours(seen(areas=[30, 31]), profile(whole={"areas": [30]}))["areas"] == "orange"
    assert colours(seen(areas=[], streets=["סנפיר"]))["areas"] == "orange"  # #110, #320
    assert colours(seen(areas=[], stated_area_names=["בצפון"]))["areas"] == "orange"


def test_the_area_is_grey_with_no_location_green_on_match_else_plain() -> None:
    assert colours(seen(areas=[]))["areas"] == "grey"
    assert colours(seen(areas=[30]), profile(whole={"areas": [30, 31]}))["areas"] == "green"
    assert colours(seen(areas=[30, 31]), profile(whole={"areas": [30, 31]}))["areas"] == "green"
    assert colours(seen(areas=[30]))["areas"] == "plain"


def test_with_no_evaluation_every_field_takes_its_own_colour() -> None:
    post = seen(balcony=written(True), areas=[30, 31], price=NOT_WRITTEN, floor=UNCLEAR)
    found = field_colours(post.listing, None)
    assert set(found) == {*COLOURED, "areas"}
    assert (found["balcony"], found["price"], found["floor"]) == ("green", "missing", "orange")
    assert found["areas"] == "plain"  # area_orange is per user: not known without a profile


# --- the glow (#308, #322) ---


def test_the_glow_follows_the_tier() -> None:
    p = profile(whole={"balcony": "preference"})
    met = evaluate(seen(balcony=written(True)), p, NOW)
    assert (met.tier, glow(met, p)) == ("preferences_met", "green")
    middle = evaluate(seen(balcony=written(False)), p, NOW)
    assert (middle.tier, glow(middle, p)) == ("critical_met", "orange")
    bottom = evaluate(seen(price=NOT_WRITTEN), p, NOW)  # #302
    assert (bottom.tier, glow(bottom, p)) == ("unknown", "red")


def test_no_green_glow_while_the_option_holds_no_preference() -> None:
    """#322: every category None or critical; orange and red unchanged."""
    p = profile(whole={"price_max": 9000, "rooms": span(2.0, None, "critical")})
    assert not holds_a_preference(p.whole_apartment)
    met = evaluate(seen(rooms=written(3.0)), p, NOW)
    assert (met.tier, glow(met, p)) == ("preferences_met", None)
    guest = profile()
    capped = evaluate(seen(areas=[30, 31]), guest, NOW)  # #320: an orange location
    assert (capped.tier, glow(capped, guest)) == ("critical_met", "orange")
    bottom = evaluate(seen(price=NOT_WRITTEN), guest, NOW)
    assert glow(bottom, guest) == "red"


def test_the_glow_reads_the_option_that_admits_the_post() -> None:
    p = profile(room={"balcony": "preference"})  # the whole-apartment option holds none
    room = evaluate(seen(apartment_kind=ROOM, balcony=written(True)), p, NOW)
    assert glow(room, p) == "green"
    whole = evaluate(seen(balcony=written(True)), p, NOW)
    assert glow(whole, p) is None


def test_each_levelled_category_can_hold_a_preference() -> None:
    assert holds_a_preference(profile(whole={"size_sqm": span(50.0, None)}).whole_apartment)
    assert holds_a_preference(profile(whole={"entry_date": dates(FROM, None)}).whole_apartment)
    assert not holds_a_preference(profile(whole={"areas": [30]}).whole_apartment)


# --- the tier's reasons (#323, #332 point 29) ---


def test_the_reasons_for_the_bottom() -> None:
    p = profile(whole={"areas": [30], "entry_date": dates(FROM, None, "critical")})
    post = seen(price=NOT_WRITTEN, areas=[], streets=["סנפיר"], entry_date=NOT_WRITTEN)
    evaluation = evaluate(post, p, NOW)
    assert evaluation.tier == "unknown"
    assert tier_reasons(post.listing, evaluation, p) == ("price", "areas", "entry_date")
    unclear_kind = seen(apartment_kind=NOT_WRITTEN)
    evaluation = evaluate(unclear_kind, profile(), NOW)
    assert tier_reasons(unclear_kind.listing, evaluation, profile()) == ("kind",)


def test_the_reasons_for_the_middle() -> None:
    p = profile(whole={"balcony": "preference", "parking": "preference", "rooms": span(3.0, 4.0)})
    post = seen(balcony=written(False), parking=NOT_WRITTEN, rooms=written(3.0), areas=[30, 31])
    evaluation = evaluate(post, p, NOW)
    assert evaluation.tier == "critical_met"
    assert tier_reasons(post.listing, evaluation, p) == ("parking", "balcony", "location")


def test_the_first_tier_has_no_reason() -> None:
    p = profile(whole={"balcony": "preference"})
    post = seen(balcony=written(True))
    assert tier_reasons(post.listing, evaluate(post, p, NOW), p) == ()


# --- the WhatsApp number (#311, #330 point 22) ---


@pytest.mark.parametrize(
    ("phone", "number"),
    [
        ("0541234567", "972541234567"),
        ("054-123-4567", "972541234567"),
        ("+972 54 123 4567", "972541234567"),
        ("0501234567", "972501234567"),
        ("036123456", None),  # a landline
        ("0771234567", None),  # 10 digits, not a mobile
        ("05412345", None),  # too short
    ],
)
def test_whatsapp_takes_a_mobile_in_international_form(phone: str, number: str | None) -> None:
    assert whatsapp_number(phone) == number
