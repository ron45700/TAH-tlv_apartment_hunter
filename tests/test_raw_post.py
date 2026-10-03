from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from pydantic import ValidationError

from tlv_hunter.contracts.raw_post import Media, RawPost
from tlv_hunter.parsing.ids import compute_listing_id

RAW_POST_FIELDS = {
    "schema_version", "source", "source_post_id", "listing_id", "group_id", "group_title",
    "permalink", "posted_at", "fetched_at", "raw",
    "text", "text_source", "post_type",
    "media",
    "native_price", "native_price_raw", "native_currency", "native_title", "native_location",
    "author_name", "author_id_raw", "author_profile_url",
    "top_comment", "reactions_count", "comments_count", "shares_count",
    "text_hash", "phones", "no_text", "is_canonical", "duplicate_of",
}  # fmt: skip
MEDIA_FIELDS = {"type", "uri", "width", "height", "media_id", "page_url"}
DERIVED_FIELDS = {"text_hash", "phones", "no_text", "is_canonical", "duplicate_of"}


def _valid(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "schema_version": 1,
        "source": "thedoor",
        "source_post_id": "123",
        "listing_id": compute_listing_id("123"),
        "group_id": "g1",
        "group_title": None,
        "permalink": "https://example.invalid/p/123",
        "posted_at": datetime(2026, 9, 13, 18, 0, tzinfo=UTC),
        "fetched_at": datetime(2026, 9, 13, 18, 5, tzinfo=UTC),
        "raw": {"post_id": "123"},
        "text": "hello",
        "text_source": "text",
        "post_type": "regular",
        "media": [],
        "native_price": None,
        "native_price_raw": None,
        "native_currency": None,
        "native_title": None,
        "native_location": None,
        "author_name": None,
        "author_id_raw": None,
        "author_profile_url": None,
        "top_comment": None,
        "reactions_count": None,
        "comments_count": None,
        "shares_count": None,
    }
    fields.update(overrides)
    return fields


def test_field_set_matches_schema_md_exactly() -> None:
    assert set(RawPost.model_fields) == RAW_POST_FIELDS
    assert len(RAW_POST_FIELDS) == 31


def test_media_field_set_matches_schema_md_exactly() -> None:
    assert set(Media.model_fields) == MEDIA_FIELDS


def test_derived_fields_default_to_not_computed() -> None:
    post = RawPost(**_valid())
    assert all(getattr(post, name) is None for name in DERIVED_FIELDS)


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(invented_field=1))


def test_media_width_and_height_accept_none() -> None:
    media = Media(type="Video", uri="u", width=None, height=None, media_id="1", page_url="p")
    assert media.width is None and media.height is None


@pytest.mark.parametrize("field", ["posted_at", "fetched_at"])
def test_naive_datetime_is_rejected(field: str) -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(**{field: datetime(2026, 9, 13, 18, 0)}))


@pytest.mark.parametrize("field", ["posted_at", "fetched_at"])
def test_non_utc_aware_datetime_is_rejected(field: str) -> None:
    israel = timezone(timedelta(hours=3))
    with pytest.raises(ValidationError):
        RawPost(**_valid(**{field: datetime(2026, 9, 13, 21, 0, tzinfo=israel)}))


def test_listing_id_must_match_source_post_id() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(listing_id=compute_listing_id("999")))


def test_text_source_text_with_blank_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(text="  \n", text_source="text"))


def test_text_source_none_with_real_text_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(text="hello", text_source="none"))


def test_hash_or_phones_before_textnorm_ran_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(text_hash="abc"))
    with pytest.raises(ValidationError):
        RawPost(**_valid(phones=[]))


def test_no_text_true_with_hash_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(text=" ", text_source="none", no_text=True, text_hash="abc", phones=[]))


def test_no_text_false_without_hash_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(no_text=False, text_hash=None, phones=[]))


def test_no_text_must_agree_with_text() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(no_text=True, text_hash=None, phones=[]))


def test_text_that_normalizes_to_nothing_is_accepted_as_no_text() -> None:
    post = RawPost(**_valid(text="🏠🏠", no_text=True, text_hash=None, phones=[]))
    assert post.text_source == "text" and post.no_text is True


def test_text_that_normalizes_to_nothing_cannot_be_no_text_false() -> None:
    with pytest.raises(ValidationError):
        RawPost(**_valid(text="🏠🏠", no_text=False, text_hash="abc", phones=[]))


def test_with_changes_revalidates() -> None:
    post = RawPost(**_valid())
    with pytest.raises(ValidationError):
        post.with_changes(text_hash="abc")


def test_model_is_frozen() -> None:
    post = RawPost(**_valid())
    with pytest.raises(ValidationError):
        post.text = "changed"
