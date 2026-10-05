"""The rejection derived from the answer, and the record after a classification attempt
(DECISIONS.md #92, #93, #139, #152)."""

from datetime import UTC, datetime

import pytest

from tests.conftest import make_listing
from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.postmodel.rejects import classified_lifecycle, failed_lifecycle, model_reason

ID = "a" * 64


def record(**changes) -> PostLifecycle:
    fields = {
        "schema_version": POST_LIFECYCLE_SCHEMA_VERSION,
        "listing_id": ID,
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
def test_the_reason_from_the_post_nature(nature: str, reason: str | None) -> None:
    assert model_reason(make_listing(ID, post_nature=nature)) == reason


def test_other_city_comes_first_in_gate_e_order() -> None:
    assert (
        model_reason(make_listing(ID, post_nature="seeking", other_city="רמת גן")) == "other_city"
    )
    assert model_reason(make_listing(ID, other_city="רמת גן")) == "other_city"


def test_classified_lifecycle_active_and_rejected_keep_the_failure_fields() -> None:
    """#152: the failure fields are left as they are after a later success."""
    existing = record(classification_failures=2, last_classification_error="timeout")
    active = classified_lifecycle(existing, make_listing(ID))
    assert (active.state, active.rejection_reason) == ("active", None)
    assert (active.classification_failures, active.last_classification_error) == (2, "timeout")
    rejected = classified_lifecycle(existing, make_listing(ID, post_nature="for_sale"))
    assert (rejected.state, rejected.rejection_reason) == ("rejected", "for_sale")
    assert rejected.images == existing.images
    assert rejected.last_published_at == existing.last_published_at


def test_failed_lifecycle_counts_and_keeps_the_state() -> None:
    once = failed_lifecycle(record(), "timeout")
    twice = failed_lifecycle(once, "refusal")
    assert (twice.state, twice.classification_failures) == ("pending", 2)
    assert twice.last_classification_error == "refusal"


@pytest.mark.parametrize("state", ["active", "archived"])
def test_only_a_pending_record_is_classified_or_failed(state: str) -> None:
    with pytest.raises(ValueError, match="pending"):
        classified_lifecycle(record(state=state), make_listing(ID))
    with pytest.raises(ValueError, match="pending"):
        failed_lifecycle(record(state=state), "timeout")


def test_a_listing_of_another_post_is_refused() -> None:
    with pytest.raises(ValueError, match="does not belong"):
        classified_lifecycle(record(), make_listing("b" * 64))
