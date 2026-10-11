"""A collection run's change merged into a record another writer changed (task 3.4 (d);
DECISIONS.md #260, #289 point 2). Pure: no store."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from tlv_hunter.contracts.post_lifecycle import (
    POST_LIFECYCLE_SCHEMA_VERSION,
    PostImage,
    PostLifecycle,
)
from tlv_hunter.run_merge import merge_run_record
from tlv_hunter.store.base import StaleRecordError

LISTING_ID = "a" * 64
PUBLISHED = datetime(2026, 10, 9, 8, 0, tzinfo=UTC)
FLAGGED_AT = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)
USER = "f" * 32


def record(**changes: Any) -> PostLifecycle:
    fields: dict[str, Any] = {
        "schema_version": POST_LIFECYCLE_SCHEMA_VERSION,
        "listing_id": LISTING_ID,
        "state": "active",
        "rejection_reason": None,
        "flagged_by": None,
        "flagged_at": None,
        "flag_note": None,
        "last_published_at": PUBLISHED,
        "images": [],
        "classification_failures": 0,
        "last_classification_error": None,
    }
    return PostLifecycle(**{**fields, **changes})


FLAG = {
    "state": "rejected",
    "rejection_reason": "flagged",
    "flagged_by": USER,
    "flagged_at": FLAGGED_AT,
    "flag_note": "Netanya",
}
LATER = PUBLISHED + timedelta(hours=5)
PHOTO = PostImage(listing_id=LISTING_ID, media_id="m1", local_path="images/a/m1.jpg", error=None)


def test_a_flag_made_during_the_run_stays_and_the_run_keeps_its_publication_and_photos() -> None:
    read = record()
    run = record(last_published_at=LATER, images=[PHOTO])
    fresh = record(**FLAG)
    merged = merge_run_record(read, run, fresh)
    assert merged == record(**FLAG, last_published_at=LATER, images=[PHOTO])


def test_a_report_made_during_the_run_wins_over_the_runs_state_change() -> None:
    read = record(state="archived")
    run = record(state="active", last_published_at=LATER)  # a repost brought it back (#74)
    reported = {**FLAG, "rejection_reason": "misclassified", "flag_note": None}
    fresh = record(state="archived", **{k: v for k, v in reported.items() if k != "state"})
    merged = merge_run_record(read, run, fresh)
    assert (merged.state, merged.rejection_reason) == ("archived", "misclassified")
    assert merged.flagged_by == USER and merged.last_published_at == LATER


def test_the_runs_state_change_stays_when_the_site_changed_only_its_own_fields() -> None:
    read = record(state="archived", classification_failures=3, last_classification_error="x")
    run = record(state="active", classification_failures=3, last_classification_error="x")
    fresh = record(state="archived", classification_failures=0, last_classification_error="x")
    merged = merge_run_record(read, run, fresh)
    assert merged.state == "active"
    assert merged.classification_failures == 0  # the admin's retry (#139)


def test_a_restore_made_during_the_run_stays_when_the_run_did_not_change_the_state() -> None:
    read = record(**FLAG)
    run = record(**FLAG, last_published_at=LATER)
    fresh = record()  # restored: the flag cleared, active again
    merged = merge_run_record(read, run, fresh)
    assert merged == record(last_published_at=LATER)


def test_two_state_changes_with_no_flag_cannot_be_merged() -> None:
    """The run and the site both changed the state, and the fresh record carries no flag or
    report: the run fails and moves no watermark; the next run reads the new record."""
    read = record(state="archived", **{k: v for k, v in FLAG.items() if k != "state"})
    run = record(state="rejected", **{k: v for k, v in FLAG.items() if k != "state"})
    fresh = record(state="archived")  # restored while archived (#283)
    with pytest.raises(StaleRecordError):
        merge_run_record(read, run, fresh)


def test_three_records_of_different_posts_are_refused() -> None:
    with pytest.raises(ValueError, match="different posts"):
        merge_run_record(record(), record(), record(listing_id="b" * 64))
