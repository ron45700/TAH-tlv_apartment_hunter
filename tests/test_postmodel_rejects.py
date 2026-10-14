"""The rejection derived from the answer and from Facebook's own location, and the record after a
classification attempt, the record a restore leaves (DECISIONS.md #92, #93, #139, #152, #214,
#251, #281-#283), a correction of the city (#296), and the records a user's flag and report leave
(#279, #280, #300)."""

from datetime import UTC, datetime

import pytest

from tests.conftest import make_correction, make_listing
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rejects import (
    classified_lifecycle,
    failed_lifecycle,
    flagged_lifecycle,
    model_reason,
    native_locality,
    other_city_name,
    other_city_ruling,
    reported_lifecycle,
    restored_lifecycle,
)
from tlv_hunter.postmodel.seen import SeenListing, seen_listing

TLV = "תל אביב - יפו, תל אביב"


def record(post: RawPost, **changes) -> PostLifecycle:
    fields = {
        "schema_version": POST_LIFECYCLE_SCHEMA_VERSION,
        "listing_id": post.listing_id,
        "state": "pending",
        "rejection_reason": None,
        "flagged_by": None,
        "flagged_at": None,
        "flag_note": None,
        "last_published_at": datetime(2026, 10, 5, tzinfo=UTC),
        "images": [],
        "classification_failures": 0,
        "last_classification_error": None,
    }
    return PostLifecycle(**{**fields, **changes})


def located(post: RawPost, location: str | None) -> RawPost:
    return post.with_changes(native_location=location)


def listing_of(post: RawPost, **changes) -> Listing:
    return make_listing(post.listing_id, **changes)


@pytest.fixture
def post(posts: list[RawPost]) -> RawPost:
    return located(posts[0], None)


@pytest.mark.parametrize(
    ("nature", "reason"),
    [
        ("rental_offer", None),
        ("sublet_offer", None),  # a sublet is not a rejection (#93)
        ("seeking", "seeking"),
        ("for_sale", "for_sale"),
        ("not_listing", "not_listing"),
    ],
)
def test_the_reason_from_the_post_nature(post: RawPost, nature: str, reason: str | None) -> None:
    assert model_reason(post, listing_of(post, post_nature=nature)) == reason


def test_other_city_comes_first_in_gate_e_order(post: RawPost) -> None:
    answer = listing_of(post, post_nature="seeking", other_city="רמת גן")
    assert model_reason(post, answer) == "other_city"
    assert model_reason(post, listing_of(post, other_city="רמת גן")) == "other_city"


def test_classified_lifecycle_active_and_rejected_keep_the_failure_fields(post: RawPost) -> None:
    """#152: the failure fields are left as they are after a later success."""
    existing = record(post, classification_failures=2, last_classification_error="timeout")
    active = classified_lifecycle(existing, listing_of(post), post)
    assert (active.state, active.rejection_reason) == ("active", None)
    assert (active.classification_failures, active.last_classification_error) == (2, "timeout")
    rejected = classified_lifecycle(existing, listing_of(post, post_nature="for_sale"), post)
    assert (rejected.state, rejected.rejection_reason) == ("rejected", "for_sale")
    assert rejected.images == existing.images
    assert rejected.last_published_at == existing.last_published_at


def test_failed_lifecycle_counts_and_keeps_the_state(post: RawPost) -> None:
    once = failed_lifecycle(record(post), "timeout")
    twice = failed_lifecycle(once, "refusal")
    assert (twice.state, twice.classification_failures) == ("pending", 2)
    assert twice.last_classification_error == "refusal"


@pytest.mark.parametrize("state", ["active", "archived"])
def test_only_a_pending_record_is_classified_or_failed(post: RawPost, state: str) -> None:
    with pytest.raises(ValueError, match="pending"):
        classified_lifecycle(record(post, state=state), listing_of(post), post)
    with pytest.raises(ValueError, match="pending"):
        failed_lifecycle(record(post, state=state), "timeout")


def test_a_listing_of_another_post_is_refused(post: RawPost) -> None:
    with pytest.raises(ValueError, match="does not belong"):
        classified_lifecycle(record(post), make_listing("b" * 64), post)


def test_a_post_of_another_listing_is_refused(posts: list[RawPost]) -> None:
    with pytest.raises(ValueError, match="does not belong"):
        classified_lifecycle(record(posts[0]), listing_of(posts[0]), posts[1])


# --- the locality of Facebook's location field (#214) ---


@pytest.mark.parametrize(
    ("location", "locality"),
    [
        (TLV, "תל אביב - יפו"),
        ("חולון, תל אביב", "חולון"),  # the district after the comma is never the locality
        ("רמת גן, תל אביב", "רמת גן"),
        ("באר שבע, ישראל", "באר שבע"),
        ("חולון", "חולון"),  # no comma: all of it
        ("  חולון  ,  תל אביב ", "חולון"),
        ("‎חולון‎, תל אביב", "חולון"),  # the marks this provider emits (U+200E)
        ("חו‏לון, תל אביב", "חולון"),  # inside a word too
        ("﻿חולון, תל אביב", "חולון"),
        ("רמת גן, תל אביב", "רמת גן"),  # a non-breaking space
        ("רמת   גן,x", "רמת גן"),
        ("רמת\t גן, תל אביב", "רמת גן"),
        ("‎תל אביב - יפו‎, תל אביב", "תל אביב - יפו"),
    ],
)
def test_the_locality_is_the_part_before_the_first_comma(location: str, locality: str) -> None:
    assert native_locality(location) == locality


@pytest.mark.parametrize(
    "location",
    [None, "", "   ", "‎‏", ", תל אביב", " ,תל אביב", "Holon, Tel Aviv", "Tel Aviv-Yafo", "123"],
)
def test_no_usable_locality_means_the_model_decides(location: str | None) -> None:
    """Absent, empty, or with no Hebrew letter (a provider whose language changed, #214)."""
    assert native_locality(location) is None


def test_hebrew_final_letters_are_never_folded() -> None:
    assert native_locality("חולון, תל אביב") == "חולון"
    assert native_locality("חולונ, תל אביב") == "חולונ"


# --- the rule (#214) ---


@pytest.mark.parametrize(
    "location",
    [
        TLV,
        "תל אביב-יפו, תל אביב",  # no spaces around the dash
        "תל אביב – יפו, תל אביב",  # an en dash
        "תל־אביב–יפו, תל אביב",  # a maqaf and an en dash, as OpenStreetMap writes it
        "תל אביב − יפו, תל אביב",  # the minus sign
        "‎תל אביב - יפו‎, תל אביב",
        "תל אביב - יפו",  # non-breaking spaces, no district
        "תל אביב, תל אביב",  # a bare "תל אביב" is a Tel Aviv key too (Ron's decision, #214)
        "תל אביב",
        "תל-אביב, ישראל",
    ],
)
def test_a_tel_aviv_locality_is_never_other_city_even_when_the_model_said_so(
    post: RawPost, location: str
) -> None:
    where = located(post, location)
    answer = listing_of(where, other_city="עין ורד")
    assert other_city_ruling(where, answer) == (None, None)
    assert model_reason(where, answer) is None
    assert other_city_name(where, answer) is None


@pytest.mark.parametrize(
    ("location", "city"),
    [
        ("חולון, תל אביב", "חולון"),
        ("רמת גן, תל אביב", "רמת גן"),
        ("באר שבע, ישראל", "באר שבע"),
        ("‎רמת גן‎, תל אביב", "רמת גן"),
        ("צפון תל אביב - יפו, תל אביב", "צפון תל אביב - יפו"),  # never a substring match
        ("תל אביב יפו נווה צדק, תל אביב", "תל אביב יפו נווה צדק"),
        ("גבעתיים, תל אביב - יפו", "גבעתיים"),  # a district that reads Tel Aviv-Yafo
    ],
)
def test_any_other_locality_is_other_city_even_when_the_model_said_null(
    post: RawPost, location: str, city: str
) -> None:
    where = located(post, location)
    answer = listing_of(where, other_city=None)
    assert other_city_ruling(where, answer) == (city, "native_location")
    assert model_reason(where, answer) == "other_city"
    assert other_city_name(where, answer) == city


def test_the_native_city_wins_over_the_models_other_city(post: RawPost) -> None:
    where = located(post, "חולון, תל אביב")
    ruling = other_city_ruling(where, listing_of(where, other_city="בת ים"))
    assert ruling == ("חולון", "native_location")


def test_without_a_native_locality_the_model_decides_as_before(post: RawPost) -> None:
    assert other_city_ruling(post, listing_of(post, other_city="רמת גן")) == ("רמת גן", "model")
    assert other_city_ruling(post, listing_of(post)) == (None, None)
    english = located(post, "Holon, Israel")
    assert other_city_ruling(english, listing_of(english, other_city="חולון")) == ("חולון", "model")
    assert other_city_ruling(english, listing_of(english)) == (None, None)


def test_the_order_is_unchanged_other_city_first_then_the_nature(post: RawPost) -> None:
    holon = located(post, "חולון, תל אביב")
    for nature in ("for_sale", "seeking", "not_listing", "rental_offer"):
        assert model_reason(holon, listing_of(holon, post_nature=nature)) == "other_city"
    tel_aviv = located(post, TLV)
    answer = listing_of(tel_aviv, post_nature="seeking", other_city="עין ורד")
    assert model_reason(tel_aviv, answer) == "seeking"


def test_classified_lifecycle_uses_the_native_city(post: RawPost) -> None:
    ramat_gan = located(post, "רמת גן, תל אביב")
    rejected = classified_lifecycle(record(ramat_gan), listing_of(ramat_gan), ramat_gan)
    assert (rejected.state, rejected.rejection_reason) == ("rejected", "other_city")
    tel_aviv = located(post, TLV)
    answer = listing_of(tel_aviv, other_city="עין ורד")
    active = classified_lifecycle(record(tel_aviv), answer, tel_aviv)
    assert (active.state, active.rejection_reason) == ("active", None)


def test_the_rule_edits_neither_the_listing_nor_the_post(post: RawPost) -> None:
    where = located(post, "רמת גן, תל אביב")
    answer = listing_of(where, other_city="בת ים")
    before = (where.model_dump_json(), answer.model_dump_json())
    other_city_ruling(where, answer)
    model_reason(where, answer)
    classified_lifecycle(record(where), answer, where)
    assert (where.model_dump_json(), answer.model_dump_json()) == before
    assert answer.other_city == "בת ים"  # the model's answer stays as it was


# --- a correction of other_city outranks the native location (DECISIONS.md #296) ---

FLAGGER = "f" * 32
FLAGGED_AT = datetime(2026, 10, 11, 10, 0, tzinfo=UTC)


def seen_of(post: RawPost, corrections: dict[str, object] | None = None, **changes) -> SeenListing:
    listing = listing_of(post, **changes)
    made = [
        make_correction(listing, field, value, n=n)
        for n, (field, value) in enumerate((corrections or {}).items(), start=1)
    ]
    return seen_listing(listing, made)


def test_a_city_correction_outranks_the_native_location_both_ways(post: RawPost) -> None:
    holon = located(post, "חולון, תל אביב")
    rescued = seen_of(holon, {"other_city": None}, other_city="חולון")
    assert other_city_ruling(holon, rescued) == (None, None)
    assert model_reason(holon, rescued) is None
    assert other_city_name(holon, rescued) is None
    tel_aviv = located(post, TLV)
    moved = seen_of(tel_aviv, {"other_city": "רמת גן"})
    assert other_city_ruling(tel_aviv, moved) == ("רמת גן", "correction")
    assert model_reason(tel_aviv, moved) == "other_city"


def test_without_a_city_correction_the_seen_listing_follows_214(post: RawPost) -> None:
    """#214's order stands between the native location and the model."""
    holon = located(post, "חולון, תל אביב")
    seen = seen_of(holon, {"rooms": {"state": "written", "value": 3.0}}, other_city="בת ים")
    assert other_city_ruling(holon, seen) == other_city_ruling(holon, seen.listing)
    assert other_city_ruling(holon, seen) == ("חולון", "native_location")
    assert other_city_ruling(post, seen_of(post, other_city="בת ים")) == ("בת ים", "model")
    removed = make_correction(listing_of(holon), "other_city", None, removed=True)
    assert other_city_ruling(holon, seen_listing(listing_of(holon), [removed])) == (
        "חולון",
        "native_location",
    )


# --- the restore's derived state (DECISIONS.md #251, #281-#283; test group 2) ---


def flagged(post: RawPost, reason: str = "flagged", state: str = "rejected") -> PostLifecycle:
    return record(
        post,
        state=state,
        rejection_reason=reason,
        flagged_by=FLAGGER,
        flagged_at=FLAGGED_AT,
        flag_note="not what it says",
        classification_failures=1,
        last_classification_error="timeout",
    )


def test_a_flagged_active_post_restores_to_active_with_every_other_field_kept(
    post: RawPost,
) -> None:
    existing = flagged(post)
    restored = restored_lifecycle(existing, post, seen_of(post))
    assert (restored.state, restored.rejection_reason) == ("active", None)
    assert (restored.flagged_by, restored.flagged_at, restored.flag_note) == (None, None, None)
    kept = {"last_published_at", "images", "classification_failures", "last_classification_error"}
    assert restored.model_dump(include=kept) == existing.model_dump(include=kept)


def test_a_reported_post_restores_from_the_corrected_values(post: RawPost) -> None:
    """#281: the corrected nature decides, not the model's."""
    seen = seen_of(post, {"post_nature": "for_sale"})
    restored = restored_lifecycle(flagged(post, "misclassified"), post, seen)
    assert (restored.state, restored.rejection_reason) == ("rejected", "for_sale")


def test_an_other_city_post_by_its_native_location_stays_rejected(post: RawPost) -> None:
    holon = located(post, "חולון, תל אביב")
    restored = restored_lifecycle(flagged(holon), holon, seen_of(holon))
    assert (restored.state, restored.rejection_reason) == ("rejected", "other_city")
    rescued = seen_of(holon, {"other_city": None})
    assert restored_lifecycle(flagged(holon), holon, rescued).state == "active"  # #296


@pytest.mark.parametrize(("nature", "reason"), [("rental_offer", None), ("seeking", "seeking")])
def test_an_archived_post_stays_archived_its_reason_re_derived(
    post: RawPost, nature: str, reason: str | None
) -> None:
    """#283."""
    existing = flagged(post, "flagged", state="archived")
    restored = restored_lifecycle(existing, post, seen_of(post, post_nature=nature))
    assert (restored.state, restored.rejection_reason) == ("archived", reason)
    assert restored.flagged_by is None


def test_a_record_with_no_flag_and_no_report_or_of_another_post_is_refused(
    post: RawPost, posts: list[RawPost]
) -> None:
    active = record(post, state="active")
    with pytest.raises(ValueError, match="no flag and no report"):
        restored_lifecycle(active, post, seen_of(post))
    other = located(posts[1], None)
    with pytest.raises(ValueError, match="does not belong"):
        restored_lifecycle(flagged(post), post, seen_of(other))


@pytest.mark.parametrize(
    ("location", "changes", "corrections"),
    [
        (None, {}, {}),
        (None, {"post_nature": "seeking"}, {}),
        (None, {}, {"post_nature": "not_listing"}),
        (None, {"other_city": "רמת גן"}, {}),
        ("חולון, תל אביב", {}, {}),
        (TLV, {"other_city": "עין ורד"}, {"post_nature": "for_sale"}),
        (None, {"post_nature": "sublet_offer"}, {"rooms": {"state": "written", "value": 2.0}}),
    ],
)
def test_the_restore_and_a_classification_derive_the_same_reason(
    post: RawPost, location: str | None, changes: dict, corrections: dict
) -> None:
    """One implementation of Gate E's order and of #214: `model_reason`."""
    where = located(post, location)
    seen = seen_of(where, corrections, **changes)
    restored = restored_lifecycle(flagged(where), where, seen)
    classified = classified_lifecycle(record(where), seen.listing, where)
    assert (restored.state, restored.rejection_reason) == (
        classified.state,
        classified.rejection_reason,
    )


# --- a user's flag and report (3.7 (i); Gate E as amended, #279, #280, #300) ---

FLAGGER = "a" * 32
FIRST_REPORTER = "b" * 32
SECOND_REPORTER = "c" * 32
FLAGGED_AT = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
LATER = datetime(2026, 10, 14, 9, 0, tzinfo=UTC)


def active_with_history(post: RawPost) -> PostLifecycle:
    """An active record whose other fields must survive a flag or a report untouched."""
    return record(
        post,
        state="active",
        classification_failures=1,
        last_classification_error="timeout",
        last_published_at=datetime(2026, 10, 12, 7, 30, tzinfo=UTC),
    )


def test_a_flag_rejects_an_active_post_as_flagged_and_keeps_every_other_field(
    post: RawPost,
) -> None:
    existing = active_with_history(post)
    result = flagged_lifecycle(existing, FLAGGER, FLAGGED_AT, "the photos are of another flat")
    assert (result.state, result.rejection_reason) == ("rejected", "flagged")
    assert (result.flagged_by, result.flagged_at) == (FLAGGER, FLAGGED_AT)
    assert result.flag_note == "the photos are of another flat"
    kept = ("last_published_at", "images", "classification_failures", "last_classification_error")
    assert all(getattr(result, name) == getattr(existing, name) for name in kept)
    assert flagged_lifecycle(existing, FLAGGER, FLAGGED_AT, None).flag_note is None


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "pending"},
        {"state": "rejected", "rejection_reason": "seeking"},
        {"state": "archived"},
        {
            "state": "rejected",
            "rejection_reason": "misclassified",
            "flagged_by": FIRST_REPORTER,
            "flagged_at": FLAGGED_AT,
        },
    ],
)
def test_only_an_active_post_is_flagged(post: RawPost, changes: dict) -> None:
    with pytest.raises(ValueError, match="only an active post is flagged"):
        flagged_lifecycle(record(post, **changes), FLAGGER, LATER, None)


def test_a_report_rejects_an_active_post_as_misclassified_with_the_reporter(
    post: RawPost,
) -> None:
    existing = active_with_history(post)
    result = reported_lifecycle(existing, FIRST_REPORTER, FLAGGED_AT)
    assert (result.state, result.rejection_reason) == ("rejected", "misclassified")
    assert (result.flagged_by, result.flagged_at) == (FIRST_REPORTER, FLAGGED_AT)  # #280
    assert result.flag_note is None
    kept = ("last_published_at", "images", "classification_failures", "last_classification_error")
    assert all(getattr(result, name) == getattr(existing, name) for name in kept)


def test_only_the_first_reporter_is_flagged_by(post: RawPost) -> None:
    """#280: a second reporter changes nothing on the record."""
    first = reported_lifecycle(active_with_history(post), FIRST_REPORTER, FLAGGED_AT)
    assert reported_lifecycle(first, SECOND_REPORTER, LATER) == first


def test_a_flagged_post_that_is_reported_still_shows_flagged(post: RawPost) -> None:
    """#279: "flagged" shows when both apply."""
    flagged_record = flagged_lifecycle(active_with_history(post), FLAGGER, FLAGGED_AT, "fake")
    assert reported_lifecycle(flagged_record, FIRST_REPORTER, LATER) == flagged_record


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "pending"},
        {"state": "rejected", "rejection_reason": "other_city"},
        {"state": "archived"},
    ],
)
def test_a_post_with_no_card_is_not_reported(post: RawPost, changes: dict) -> None:
    with pytest.raises(ValueError, match="only an active post is reported"):
        reported_lifecycle(record(post, **changes), FIRST_REPORTER, LATER)


def test_a_restore_undoes_a_flag_and_a_report(post: RawPost) -> None:
    """The records the site writes are the ones 3.6's restore reads (#251, #282)."""
    seen = seen_of(post)
    for user_record in (
        flagged_lifecycle(record(post, state="active"), FLAGGER, FLAGGED_AT, "fake"),
        reported_lifecycle(record(post, state="active"), FIRST_REPORTER, FLAGGED_AT),
    ):
        restored = restored_lifecycle(user_record, post, seen)
        assert (restored.state, restored.rejection_reason, restored.flagged_by) == (
            "active",
            None,
            None,
        )
