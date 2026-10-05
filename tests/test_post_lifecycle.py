"""Gate E records: the approved field sets and rules (SCHEMA.md, Gate E)."""

import json
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle

NAIVE = datetime(2026, 10, 4, 9, 0)
ISRAEL = datetime(2026, 10, 4, 12, 0, tzinfo=timezone(timedelta(hours=3)))
REASONS = ["no_text", "no_images", "other_city", "seeking", "for_sale", "not_listing", "flagged"]
FLAG = {"flagged_by": "ron", "flagged_at": datetime(2026, 10, 4, 9, 0, tzinfo=UTC)}


def _lifecycle(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "schema_version": 2,
        "listing_id": "a" * 64,
        "state": "pending",
        "rejection_reason": None,
        "flagged_by": None,
        "flagged_at": None,
        "flag_note": None,
        "last_published_at": datetime(2026, 10, 4, 8, 0, tzinfo=UTC),
        "images": [],
        "classification_failures": 0,
        "last_classification_error": None,
    }
    return {**fields, **overrides}


def _watermark(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "schema_version": 1,
        "group_id": "g1",
        "watermark": None,
        "last_success_at": None,
        "consecutive_failures": 0,
    }
    return {**fields, **overrides}


def test_field_sets_are_exactly_approved() -> None:
    assert set(PostLifecycle.model_fields) == {
        "schema_version", "listing_id", "state", "rejection_reason", "flagged_by", "flagged_at",
        "flag_note", "last_published_at", "images", "classification_failures",
        "last_classification_error",
    }  # fmt: skip
    assert set(PostImage.model_fields) == {"listing_id", "media_id", "local_path", "error"}
    assert set(GroupWatermark.model_fields) == {
        "schema_version", "group_id", "watermark", "last_success_at", "consecutive_failures",
    }  # fmt: skip


def test_unapproved_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(repost_log=[]))
    with pytest.raises(ValidationError):
        GroupWatermark(**_watermark(run_id="r1"))


def test_unknown_state_and_reason_are_rejected() -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(state="deleted"))
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(state="rejected", rejection_reason="duplicate"))


@pytest.mark.parametrize("state", ["pending", "active"])
@pytest.mark.parametrize("reason", REASONS)
def test_reason_must_be_none_when_pending_or_active(state: str, reason: str) -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(state=state, rejection_reason=reason, **FLAG))


@pytest.mark.parametrize("state", ["pending", "active"])
def test_pending_and_active_without_reason_are_valid(state: str) -> None:
    assert PostLifecycle(**_lifecycle(state=state)).rejection_reason is None


def test_rejected_requires_a_reason() -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(state="rejected"))


@pytest.mark.parametrize("reason", REASONS)
def test_rejected_accepts_every_reason(reason: str) -> None:
    flag = FLAG if reason == "flagged" else {}
    assert PostLifecycle(**_lifecycle(state="rejected", rejection_reason=reason, **flag))


def test_archived_reason_is_optional() -> None:
    assert PostLifecycle(**_lifecycle(state="archived")).rejection_reason is None
    archived = PostLifecycle(**_lifecycle(state="archived", rejection_reason="seeking"))
    assert archived.rejection_reason == "seeking"


@pytest.mark.parametrize("half", [{"flagged_by": "ron"}, {"flagged_at": FLAG["flagged_at"]}])
def test_flagged_by_and_flagged_at_are_set_together(half: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(**half))


def test_flagged_reason_requires_the_flag() -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(state="rejected", rejection_reason="flagged"))
    assert PostLifecycle(**_lifecycle(state="rejected", rejection_reason="flagged", **FLAG))


def test_a_flag_without_the_flagged_reason_is_allowed() -> None:
    """Gate E requires the flag for the "flagged" reason, not the reverse."""
    assert PostLifecycle(**_lifecycle(state="active", flag_note="note", **FLAG))


@pytest.mark.parametrize(
    ("local_path", "error", "valid"),
    [("a/1.jpg", None, True), (None, "HTTP 403", True), (None, None, False), ("a", "b", False)],
)
def test_image_has_exactly_one_of_local_path_and_error(
    local_path: str | None, error: str | None, valid: bool
) -> None:
    fields = {"listing_id": "a" * 64, "media_id": "m1", "local_path": local_path, "error": error}
    if valid:
        assert PostImage(**fields)
    else:
        with pytest.raises(ValidationError):
            PostImage(**fields)


@pytest.mark.parametrize("value", [NAIVE, ISRAEL])
def test_lifecycle_datetimes_must_be_utc(value: datetime) -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(last_published_at=value))
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle(flagged_by="ron", flagged_at=value))


@pytest.mark.parametrize("value", [NAIVE, ISRAEL])
@pytest.mark.parametrize("field", ["watermark", "last_success_at"])
def test_watermark_datetimes_must_be_utc(field: str, value: datetime) -> None:
    with pytest.raises(ValidationError):
        GroupWatermark(**_watermark(**{field: value}))


def test_records_are_frozen() -> None:
    with pytest.raises(ValidationError):
        PostLifecycle(**_lifecycle()).state = "active"
    with pytest.raises(ValidationError):
        GroupWatermark(**_watermark()).consecutive_failures = 1


# --- Gate E amendment: classification failures, schema_version 2 (DECISIONS.md #139, #152) ---


def _version_1_doc(**overrides: Any) -> str:
    """A lifecycle document as phase 1 stored it: schema_version 1, no failure fields."""
    doc = PostLifecycle.model_validate(_lifecycle()).model_dump(mode="json")
    del doc["classification_failures"], doc["last_classification_error"]
    return json.dumps({**doc, "schema_version": 1, **overrides})


def test_a_stored_version_1_record_reads_as_version_2_with_no_failures() -> None:
    record = PostLifecycle.from_stored_json(_version_1_doc())
    assert record.schema_version == 2
    assert record.classification_failures == 0
    assert record.last_classification_error is None
    assert record.last_published_at == datetime(2026, 10, 4, 8, 0, tzinfo=UTC)


def test_a_stored_version_2_record_reads_unchanged() -> None:
    record = PostLifecycle.model_validate(
        _lifecycle(classification_failures=3, last_classification_error="timeout")
    )
    assert PostLifecycle.from_stored_json(record.model_dump_json()) == record


def test_a_stored_version_1_record_cannot_carry_version_2_fields() -> None:
    with pytest.raises(ValueError, match="version-1 record"):
        PostLifecycle.from_stored_json(_version_1_doc(classification_failures=0))


def test_a_version_2_record_needs_both_new_fields() -> None:
    fields = _lifecycle()
    del fields["classification_failures"]
    with pytest.raises(ValidationError):
        PostLifecycle.model_validate(fields)


@pytest.mark.parametrize("version", [0, 1, 3])
def test_a_record_built_at_another_version_is_refused(version) -> None:
    with pytest.raises(ValidationError, match="schema_version"):
        PostLifecycle.model_validate(_lifecycle(schema_version=version))


def test_classification_failures_cannot_be_negative() -> None:
    with pytest.raises(ValidationError, match="negative"):
        PostLifecycle.model_validate(_lifecycle(classification_failures=-1))
