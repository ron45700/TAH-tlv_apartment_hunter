"""Task 3.6 (d)–(f), test groups 5 to 8: the evaluation of a post against a profile, the area's
colour, the order of a user's list, and that the derivation writes nothing (`policy/`;
`BASELINE.md` §7, §8; DECISIONS.md #245–#247, #250, #253, #269–#275, #288 R2, #295, #298, #299,
#302, #317, #320)."""

import ast
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import REPO_ROOT, SQLITE_FILENAME, make_correction, make_listing
from tests.test_dedup_stage_b import FIELDS, inputs, key_post
from tests.test_gate_d import PHONE_A, T0, add, make_member
from tlv_hunter.contracts.profile import (
    DateRangeCriterion,
    Profile,
    RangeCriterion,
    new_profile,
)
from tlv_hunter.dedup.stage_b import Card, PhotoHashes, derive_cards, load_key_posts
from tlv_hunter.policy.base import CATEGORIES, Evaluation
from tlv_hunter.policy.evaluate import evaluate, months_on
from tlv_hunter.policy.order import card_viewed, ordered
from tlv_hunter.postmodel.seen import SeenListing, seen_listing
from tlv_hunter.store.base import Repository
from tlv_hunter.store.sqlite import SqliteRepository

NOW = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
USER_ID = "1" * 32
LISTING_ID = "e" * 64


def written(value: Any) -> dict[str, Any]:
    return {"state": "written", "value": value}


UNCLEAR: dict[str, Any] = {"state": "unclear", "value": None}
NOT_WRITTEN: dict[str, Any] = {"state": "not_written", "value": None}
ROOM = written("room")
WHOLE = written("whole_apartment")


def seen(**changes: Any) -> SeenListing:
    """A written price unless `price` is given: no written price sends a post to the bottom
    (#302), which only the tests that name it should meet."""
    fields: dict[str, Any] = {"apartment_kind": WHOLE, "price": written([5000]), **changes}
    fields["price_source"] = None if fields["price"]["state"] == "not_written" else "text"
    return seen_listing(make_listing(LISTING_ID, **fields), [])


def profile(
    room: dict[str, Any] | None = None,
    whole: dict[str, Any] | None = None,
    *,
    sublets: bool = False,
) -> Profile:
    base = new_profile(USER_ID, NOW)
    return base.model_copy(
        update={
            "room": base.room.model_copy(update=room or {}),
            "whole_apartment": base.whole_apartment.model_copy(update=whole or {}),
            "include_sublets": sublets,
        }
    )


def span(low: Any, high: Any, level: str = "preference") -> RangeCriterion[Any]:
    return RangeCriterion[Any](min=low, max=high, level=level)


def dates(low: date | None, high: date | None, level: str = "preference") -> DateRangeCriterion:
    return DateRangeCriterion(earliest=low, latest=high, immediate=False, level=level)


# --- 5. the evaluation ---


def test_the_option_is_the_one_the_kind_names() -> None:
    p = profile(room={"price_max": 3000}, whole={"price_min": 6000})
    room = evaluate(seen(apartment_kind=ROOM, price=written([2500])), p, NOW)
    assert (room.option, room.shown, room.kind_marked) == ("room", True, False)
    whole = evaluate(seen(price=written([2500])), p, NOW)
    assert (whole.option, whole.shown) == (None, False)  # under its option's minimum


def test_an_option_switched_off_shows_nothing() -> None:
    p = profile(room={"enabled": False})
    assert not evaluate(seen(apartment_kind=ROOM), p, NOW).shown
    assert evaluate(seen(), p, NOW).shown


def test_a_sublet_needs_the_profiles_one_switch_and_its_kinds_option() -> None:
    """#246, #274, #317: one switch per profile; the option of the post's kind must be on."""
    sublet = seen(post_nature="sublet_offer")
    assert not evaluate(sublet, profile(), NOW).shown
    shown = evaluate(sublet, profile(sublets=True), NOW)
    assert (shown.shown, shown.option) == (True, "whole_apartment")
    assert not evaluate(sublet, profile(whole={"enabled": False}, sublets=True), NOW).shown
    room_sublet = seen(apartment_kind=ROOM, post_nature="sublet_offer")
    assert evaluate(room_sublet, profile(sublets=True), NOW).option == "room"
    assert not evaluate(room_sublet, profile(room={"enabled": False}, sublets=True), NOW).shown
    assert evaluate(seen(post_nature="rental_offer"), profile(), NOW).shown


def test_a_sublet_is_evaluated_with_its_options_values() -> None:
    """#246, #317: the option of its kind decides, as for a rental."""
    sublet = seen(post_nature="sublet_offer", price=written([5000]))
    assert not evaluate(sublet, profile(whole={"price_max": 4000}, sublets=True), NOW).shown
    room_cap = profile(room={"price_max": 4000}, sublets=True)
    assert evaluate(sublet, room_cap, NOW).tier == "preferences_met"
    balcony = profile(whole={"balcony": "preference"}, sublets=True)
    assert evaluate(sublet, balcony, NOW).tier == "critical_met"
    assert not evaluate(seen(post_nature="rental_offer"), profile(sublets=True), NOW).kind_marked


@pytest.mark.parametrize("kind", [UNCLEAR, NOT_WRITTEN])
def test_a_post_of_unclear_kind_is_evaluated_under_every_enabled_option_at_the_bottom(
    kind: dict[str, Any],
) -> None:
    """#273, #295 point 11."""
    post = seen(apartment_kind=kind, price=written([4000]))
    both = evaluate(post, profile(), NOW)
    assert (both.shown, both.tier, both.kind_marked, both.option) == (True, "unknown", True, "room")
    assert evaluate(post, profile(room={"price_max": 3000}), NOW).option == "whole_apartment"
    assert evaluate(post, profile(room={"enabled": False}), NOW).option == "whole_apartment"
    better = profile(room={"balcony": "preference"})  # the room option: a preference not met
    assert evaluate(post, better, NOW).option == "whole_apartment"
    neither = profile(room={"price_max": 3000}, whole={"price_max": 3000})
    assert not evaluate(post, neither, NOW).shown
    sublet = seen(apartment_kind=kind, post_nature="sublet_offer")
    assert not evaluate(sublet, profile(), NOW).shown  # #273 with the one switch (#317)
    switched = evaluate(sublet, profile(sublets=True), NOW)
    assert (switched.shown, switched.tier, switched.option) == (True, "unknown", "room")
    room_off = profile(room={"enabled": False}, sublets=True)
    assert evaluate(sublet, room_off, NOW).option == "whole_apartment"


@pytest.mark.parametrize(
    ("option", "post"),
    [
        ({"areas": [30]}, {"areas": [52]}),
        ({"price_min": 5000}, {"price": written([4000, 6000])}),  # the lowest is compared (#95)
        ({"price_max": 5000}, {"price": written([5500])}),
        ({"hide_women_only": True}, {"gender": "women_only"}),
        ({"rooms": span(3.0, None, "critical")}, {"rooms": written(2.5)}),
        ({"floor": span(None, 3, "critical")}, {"floor": written(4)}),
        ({"size_sqm": span(60.0, None, "critical")}, {"size_sqm": written(55.0)}),
        ({"broker": "critical"}, {"broker": written(True)}),
        ({"parking": "critical"}, {"parking": written(False)}),
        ({"balcony": "critical"}, {"balcony": written(False)}),
        (
            {"entry_date": dates(date(2026, 11, 1), None, "critical")},
            {"entry_date": written("immediate")},
        ),
    ],
)
def test_a_failed_critical_category_hides_the_post(option: dict, post: dict) -> None:
    assert evaluate(seen(**post), profile(whole=option), NOW).shown is False


@pytest.mark.parametrize(
    ("option", "post"),
    [
        ({"areas": [30]}, {"areas": [], "streets": ["דיזנגוף"]}),
        ({"price_max": 5000}, {"price": UNCLEAR}),
        ({"price_min": 3000}, {"price": NOT_WRITTEN}),
        ({"rooms": span(3.0, None, "critical")}, {"rooms": UNCLEAR}),
        ({"parking": "critical"}, {}),  # parking not written: unknown, not "no parking" (#299)
        ({"entry_date": dates(date(2026, 11, 1), None, "critical")}, {}),
    ],
)
def test_an_unknown_critical_category_sends_the_post_to_the_bottom(
    option: dict, post: dict
) -> None:
    evaluation = evaluate(seen(**post), profile(whole=option), NOW)
    assert (evaluation.shown, evaluation.tier) == (True, "unknown")


@pytest.mark.parametrize(
    "option",
    [
        {},  # nothing set (#268)
        {"balcony": "preference"},
        {"areas": [30]},
        {"rooms": span(2.0, 4.0, "critical")},
    ],
)
def test_a_post_with_no_written_price_is_always_at_the_bottom(option: dict) -> None:
    """#302: also when the user set no price range; every other category met."""
    post = {"price": NOT_WRITTEN, "areas": [30], "rooms": written(3.0), "balcony": written(True)}
    evaluation = evaluate(seen(**post), profile(whole=option), NOW)
    assert (evaluation.shown, evaluation.tier) == (True, "unknown")
    assert evaluation.fields["price"] == "not_applied" and "price" in evaluation.missing_important
    priced = evaluate(seen(**{**post, "price": written([5000])}), profile(whole=option), NOW)
    assert priced.tier == "preferences_met"


def test_no_written_price_does_not_bring_back_a_post_a_critical_category_hides() -> None:
    """#302 changes the tier only: a failed critical category still hides the post."""
    post = seen(price=NOT_WRITTEN, areas=[52])
    assert not evaluate(post, profile(whole={"areas": [30]}), NOW).shown


def test_an_unclear_price_with_no_price_range_is_not_sent_to_the_bottom() -> None:
    """#302 names a price that is not written; an unclear one counts only against a set range."""
    post = seen(price=UNCLEAR)
    assert evaluate(post, profile(), NOW).tier == "preferences_met"
    assert evaluate(post, profile(whole={"price_max": 6000}), NOW).tier == "unknown"


def test_women_only_is_shown_with_the_icon_when_the_switch_is_off() -> None:
    post = seen(gender="women_only")
    assert not evaluate(post, profile(whole={"hide_women_only": True}), NOW).shown
    icon = evaluate(post, profile(whole={"hide_women_only": False}), NOW)
    assert (icon.shown, icon.women_only_icon) == (True, True)
    assert icon.fields["women_only"] == "not_applied"
    assert not evaluate(seen(gender="women_preferred"), profile(), NOW).women_only_icon


@pytest.mark.parametrize(
    ("post", "tier", "state"),
    [
        ({"balcony": written(True)}, "preferences_met", "match"),
        ({"balcony": written(False)}, "critical_met", "mismatch"),
        ({}, "critical_met", "not_written"),  # an unknown preference is not met (#298)
        ({"balcony": UNCLEAR}, "critical_met", "unclear"),
    ],
)
def test_a_preference_orders_and_never_hides(post: dict, tier: str, state: str) -> None:
    evaluation = evaluate(seen(**post), profile(whole={"balcony": "preference"}), NOW)
    assert (evaluation.shown, evaluation.tier) == (True, tier)
    assert evaluation.fields["balcony"] == state


@pytest.mark.parametrize(
    ("name", "wrong"), [("broker", True), ("parking", False), ("balcony", False)]
)
def test_the_fixed_wanted_values(name: str, wrong: bool) -> None:
    """#269: no broker, has parking, has a balcony."""
    wants = profile(whole={key: "preference" for key in ("broker", "parking", "balcony")})
    good = {"broker": written(False), "parking": written(True), "balcony": written(True)}
    assert evaluate(seen(**good), wants, NOW).tier == "preferences_met"
    evaluation = evaluate(seen(**{**good, name: written(wrong)}), wants, NOW)
    assert evaluation.tier == "critical_met" and evaluation.fields[name] == "mismatch"


def test_ranges_are_inclusive_with_half_rooms_and_the_basement() -> None:
    """#271."""
    p = profile(whole={"rooms": span(2.5, 3.5), "floor": span(-1, 0)})
    assert evaluate(seen(rooms=written(2.5), floor=written(-1)), p, NOW).tier == "preferences_met"
    assert evaluate(seen(rooms=written(3.5), floor=written(0)), p, NOW).tier == "preferences_met"
    assert evaluate(seen(rooms=written(4.0), floor=written(0)), p, NOW).tier == "critical_met"


def test_no_size_filter_in_the_room_option() -> None:
    """#247: the room option holds none; a room post's size is never compared."""
    dumped = profile().model_dump()
    dumped["room"]["size_sqm"] = span(60.0, None).model_dump()
    with pytest.raises(ValueError):
        Profile.model_validate(dumped)
    room = evaluate(seen(apartment_kind=ROOM, size_sqm=written(10.0)), profile(), NOW)
    assert room.fields["size_sqm"] == "not_applied"
    whole = profile(whole={"size_sqm": span(60.0, None)})
    assert evaluate(seen(size_sqm=written(70.0)), whole, NOW).fields["size_sqm"] == "match"


def test_immediate_compares_as_the_utc_date_of_the_evaluation() -> None:
    """R2: at 22:30 UTC on 2026-10-11 (01:30 on 10-12 in Israel) it is 2026-10-11."""
    late = datetime(2026, 10, 11, 22, 30, tzinfo=UTC)
    post = seen(entry_date=written("immediate"))
    on_the_day = profile(whole={"entry_date": dates(date(2026, 10, 11), date(2026, 10, 11))})
    assert evaluate(post, on_the_day, late).fields["entry_date"] == "match"
    next_day = profile(whole={"entry_date": dates(date(2026, 10, 12), None)})
    assert evaluate(post, next_day, late).fields["entry_date"] == "mismatch"
    dated = seen(entry_date=written(date(2026, 10, 12)))
    assert evaluate(dated, next_day, late).fields["entry_date"] == "match"
    with pytest.raises(ValueError):
        evaluate(post, on_the_day, datetime(2026, 10, 11, 22, 30))  # not tz-aware


def chip(level: str = "preference") -> DateRangeCriterion:
    return DateRangeCriterion(earliest=None, latest=None, immediate=True, level=level)


def test_the_chip_is_a_rolling_window_of_three_calendar_months() -> None:
    """#458: no lower bound; up to today plus 3 calendar months, today being the evaluation's UTC
    date (R2), so the window moves each day by itself."""
    wanted = profile(whole={"entry_date": chip()})
    outcome = lambda when, now=NOW: evaluate(  # noqa: E731
        seen(entry_date=written(when)), wanted, now
    ).fields["entry_date"]
    assert outcome(date(2027, 1, 11)) == "match"  # NOW is 2026-10-11
    assert outcome(date(2027, 1, 12)) == "mismatch"
    assert outcome(date(2026, 9, 1)) == "match"  # a past date in a post means "available now"
    assert outcome("immediate") == "match"
    assert outcome(date(2027, 1, 12), datetime(2026, 10, 12, 9, 0, tzinfo=UTC)) == "match"


def test_the_window_ends_on_the_months_last_day_when_it_is_shorter() -> None:
    assert months_on(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert months_on(date(2027, 11, 30), 3) == date(2028, 2, 29)
    assert months_on(date(2026, 12, 31), 3) == date(2027, 3, 31)
    wanted = profile(whole={"entry_date": chip()})
    late_month = datetime(2026, 11, 30, 9, 0, tzinfo=UTC)
    last = evaluate(seen(entry_date=written(date(2027, 2, 28))), wanted, late_month)
    assert last.fields["entry_date"] == "match"
    after = evaluate(seen(entry_date=written(date(2027, 3, 1))), wanted, late_month)
    assert after.fields["entry_date"] == "mismatch"


def test_the_chip_as_critical_hides_a_later_entry() -> None:
    wanted = profile(whole={"entry_date": chip("critical")})
    assert not evaluate(seen(entry_date=written(date(2027, 3, 1))), wanted, NOW).shown
    assert evaluate(seen(entry_date=written(date(2026, 12, 1))), wanted, NOW).shown


def test_a_corrected_field_is_read_instead_of_the_models() -> None:
    listing = make_listing(LISTING_ID, apartment_kind=WHOLE, rooms=written(5.0))
    fix = make_correction(listing, "rooms", written(3.0))
    p = profile(whole={"rooms": span(None, 3.0, "critical")})
    assert not evaluate(seen_listing(listing, []), p, NOW).shown
    corrected = evaluate(seen_listing(listing, [fix]), p, NOW)
    assert corrected.shown and corrected.corrected == {"rooms"}


def test_the_important_fields_missing_and_a_state_for_every_category() -> None:
    evaluation = evaluate(seen(price=NOT_WRITTEN), profile(), NOW)
    assert evaluation.missing_important == {"price", "entry_date"}
    assert set(evaluation.fields) == set(CATEGORIES)
    assert evaluation.fields["women_only"] == "match"  # hidden by default (#268), and met
    priced = evaluate(seen(price=written([5000])), profile(), NOW)
    assert priced.missing_important == {"entry_date"}


@pytest.mark.parametrize("nature", ["seeking", "for_sale", "not_listing"])
def test_a_post_that_is_not_an_offer_is_not_shown(nature: str) -> None:
    assert not evaluate(seen(post_nature=nature), profile(), NOW).shown


# --- 6. the area's colour ---


@pytest.mark.parametrize(
    ("areas", "chosen", "shown", "orange"),
    [
        ([52], [30], False, False),  # one area: never orange (here it fails the area)
        ([52], [], True, False),
        ([30, 31], [30, 31], True, False),  # every one chosen (#250)
        ([30, 31], [30, 31, 52], True, False),
        ([30, 31], [30], True, True),
        ([30, 31], [], True, True),  # none chosen (#275)
    ],
)
def test_the_area_is_orange_unless_every_area_is_chosen(
    areas: list[int], chosen: list[int], shown: bool, orange: bool
) -> None:
    result = evaluate(seen(areas=areas), profile(whole={"areas": chosen}), NOW)
    assert (result.shown, result.area_orange) == (shown, orange)


@pytest.mark.parametrize("chosen", [[], [30]])
def test_no_area_is_unclear_with_a_street_or_a_name_and_not_written_without(
    chosen: list[int],
) -> None:
    p = profile(whole={"areas": chosen})
    with_street = evaluate(seen(streets=["דיזנגוף"]), p, NOW)
    named = evaluate(seen(stated_area_names=["הצפון הישן"]), p, NOW)
    nothing = evaluate(seen(), p, NOW)
    assert with_street.fields["areas"] == named.fields["areas"] == "unclear"
    assert nothing.fields["areas"] == "not_written"
    assert not (with_street.area_orange or nothing.area_orange)


# --- 6b. an orange location caps the tier at the middle (#320) ---


@pytest.mark.parametrize("chosen", [[], [30], [30, 52]])
def test_several_areas_not_all_chosen_are_never_preferences_met(chosen: list[int]) -> None:
    """#320 case (b), with and without chosen areas; every other category met."""
    result = evaluate(seen(areas=[30, 31]), profile(whole={"areas": chosen}), NOW)
    assert (result.shown, result.area_orange, result.tier) == (True, True, "critical_met")


def test_several_areas_all_chosen_are_not_capped() -> None:
    result = evaluate(seen(areas=[30, 31]), profile(whole={"areas": [30, 31]}), NOW)
    assert (result.area_orange, result.tier) == (False, "preferences_met")


@pytest.mark.parametrize("post", [{"streets": ["דיזנגוף"]}, {"stated_area_names": ["הצפון הישן"]}])
def test_no_area_with_a_street_or_a_name_and_no_areas_chosen_is_capped(post: dict) -> None:
    """#320 case (a): no areas chosen; the location is unclear, so the middle, not the top."""
    result = evaluate(seen(**post), profile(), NOW)
    assert (result.shown, result.fields["areas"], result.tier) == (True, "unclear", "critical_met")


@pytest.mark.parametrize("post", [{"streets": ["דיזנגוף"]}, {"stated_area_names": ["הצפון הישן"]}])
def test_no_area_with_a_street_and_areas_chosen_stays_at_the_bottom(post: dict) -> None:
    """Unchanged by #320: with areas chosen it is an unknown critical category."""
    result = evaluate(seen(**post), profile(whole={"areas": [30]}), NOW)
    assert (result.shown, result.tier) == (True, "unknown")


def test_a_post_with_no_location_at_all_is_not_capped() -> None:
    """#320 does not cover a post that gives no location: with no areas chosen it stays top."""
    result = evaluate(seen(), profile(), NOW)
    assert (result.fields["areas"], result.area_orange, result.tier) == (
        "not_written",
        False,
        "preferences_met",
    )
    assert evaluate(seen(), profile(whole={"areas": [30]}), NOW).tier == "unknown"


def test_the_cap_never_lifts_a_post_from_the_bottom_and_needs_no_preference() -> None:
    """The cap lowers only: a post already at the bottom stays there."""
    no_price = seen(areas=[30, 31], price=NOT_WRITTEN)
    assert evaluate(no_price, profile(), NOW).tier == "unknown"
    unclear_kind = seen(areas=[30, 31], apartment_kind=UNCLEAR)
    assert evaluate(unclear_kind, profile(), NOW).tier == "unknown"


def test_the_cap_weighs_in_the_choice_between_two_options() -> None:
    """A post of unclear kind is at the bottom either way; a sublet of a written kind follows
    its own option. The capped tier is the one the option comparison sees (#295 point 11)."""
    post = seen(areas=[30, 31])
    room_all = profile(room={"areas": [30, 31]}, whole={"areas": [30]})
    assert evaluate(post, room_all, NOW).tier == "critical_met"  # whole_apartment's, capped


# --- 7. the order ---


def card_and(n: int, tier: str | None, **changes: Any) -> tuple[Card, Evaluation]:
    (card,) = derive_cards(inputs(key_post(n, **changes)))
    evaluation = Evaluation(
        listing_id=card.shown_id,
        shown=tier is not None,
        option="whole_apartment" if tier else None,
        kind_marked=False,
        tier=tier,  # type: ignore[arg-type]
        fields={},
        missing_important=frozenset(),
        area_orange=False,
        women_only_icon=False,
        corrected=frozenset(),
    )
    return card, evaluation


def test_unviewed_before_viewed_then_the_tiers_then_the_newest() -> None:
    hours = timedelta(hours=1)
    old_best = card_and(1, "preferences_met", published=T0)
    new_best = card_and(2, "preferences_met", published=T0 + hours)
    middle = card_and(3, "critical_met", published=T0 + 5 * hours)
    bottom = card_and(4, "unknown", published=T0 + 9 * hours)
    viewed_best = card_and(5, "preferences_met", published=T0 + 9 * hours)
    hidden = card_and(6, None)
    result = ordered(
        [hidden, bottom, viewed_best, old_best, middle, new_best], {viewed_best[0].shown_id}
    )
    assert [card.shown_id for card, _ in result] == [
        entry[0].shown_id for entry in (new_best, old_best, middle, bottom, viewed_best)
    ]


def test_a_card_is_viewed_through_any_of_its_posts() -> None:
    """#253: a further publication grouped into the card leaves it viewed."""
    first = key_post(1, phone=PHONE_A, at=T0, **FIELDS)
    later = key_post(2, phone=PHONE_A, at=T0 + timedelta(hours=3), **FIELDS)
    (card,) = derive_cards(inputs(first, later))
    assert card_viewed(card, {later.listing_id})
    assert card_viewed(card, {first.listing_id})
    assert not card_viewed(card, {"x" * 64})


def test_an_evaluation_of_another_post_is_refused() -> None:
    card, _ = card_and(1, "preferences_met")
    _, other = card_and(2, "preferences_met")
    with pytest.raises(ValueError, match="is not of"):
        ordered([(card, other)], set())


# --- 8. nothing is written ---

REPOSITORY_WRITES = ("upsert", "upsert_with_lifecycle", "save_lifecycle", "save_classification")
USERDATA_WRITES = (
    "create_admin",
    "create_user",
    "save_user",
    "add_key",
    "save_key",
    "add_session",
    "end_session",
    "end_sessions",
    "save_profile",
    "mark_viewed",
    "unmark_viewed",
    "add_report",
    "save_report",
    "add_correction",
    "save_correction",
)


class ReadOnly:
    """A Repository that refuses every write."""

    def __init__(self, inner: Repository) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        if name in REPOSITORY_WRITES:
            raise AssertionError(f"3.6 called the write method {name}")
        return getattr(self._inner, name)


def test_a_full_derivation_leaves_the_store_byte_identical(tmp_path: Path) -> None:
    """Invariants 12 and 14: load, key, cards, evaluation and order write nothing."""
    database = tmp_path / SQLITE_FILENAME
    repository = SqliteRepository(database)
    a = make_member(1, phone=PHONE_A, price=[5000], rooms=3.0, areas=[30])
    b = make_member(2, phone=PHONE_A, price=[5000], rooms=3.0, areas=[30])
    c = make_member(3, price=[8000], rooms=2.0, areas=[52])
    for member in (a, b, c):
        add(repository, member)
    before = database.read_bytes()
    reader: Any = ReadOnly(SqliteRepository(database, read_only=True))
    loaded = load_key_posts(reader, [], tmp_path, PhotoHashes())
    derived = derive_cards(loaded)
    p = profile(whole={"areas": [30, 52]})
    entries = [(card, evaluate(card.shown.seen, p, NOW)) for card in derived]
    result = ordered(entries, {a.listing_id})
    assert len(derived) == 2 and len(result) == 2
    assert database.read_bytes() == before


def test_the_3_6_modules_import_no_model_and_no_user_store_and_call_no_write() -> None:
    modules = [
        REPO_ROOT / "tlv_hunter" / "postmodel" / "seen.py",
        REPO_ROOT / "tlv_hunter" / "dedup" / "stage_b.py",
        *sorted((REPO_ROOT / "tlv_hunter" / "policy").glob("*.py")),
    ]
    forbidden = ("tlv_hunter.classify", "tlv_hunter.userdata", "openai", "tlv_hunter.store.sqlite")
    for path in modules:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        imported += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not [name for name in imported if name.startswith(forbidden)], path
        called = {
            n.func.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        assert not called & set(REPOSITORY_WRITES + USERDATA_WRITES), path


def test_the_evaluation_edits_neither_the_profile_nor_the_post() -> None:
    """Invariant 12: no per-user value is written; both are only read."""
    p = profile(whole={"areas": [30]})
    post = seen(areas=[30])
    before = (p.model_dump_json(), post.listing.model_dump_json())
    evaluate(post, p, NOW)
    assert (p.model_dump_json(), post.listing.model_dump_json()) == before
