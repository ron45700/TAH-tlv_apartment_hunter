"""The rejection derived from the answer and from Facebook's own location, and the record after a
classification attempt (DECISIONS.md #92, #93, #139, #152, #214)."""

from datetime import UTC, datetime

import pytest

from tests.conftest import make_listing
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rejects import (
    classified_lifecycle,
    failed_lifecycle,
    model_reason,
    native_locality,
    other_city_name,
    other_city_ruling,
)

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
