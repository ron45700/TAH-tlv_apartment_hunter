"""Task 1.11: pre-model rejects (DECISIONS.md #67, #72.1, #73). Pure functions, no storage."""

import copy
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import pytest

from tests.conftest import FETCHED_AT, load_spike_1_1a
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.premodel.rejects import initial_lifecycle, pre_model_reason, recheck
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.textnorm.annotate import annotate

LISTING_TEXT = "דירת 3 חדרים להשכרה בפלורנטין, כניסה מיידית"
MODEL_REASONS = ["other_city", "seeking", "for_sale", "not_listing"]
FLAG = {"flagged_by": "ron", "flagged_at": datetime(2026, 10, 4, 9, 0, tzinfo=UTC)}


def _map(items: list[dict[str, Any]]) -> list[RawPost]:
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in items]


@pytest.fixture
def spike_posts(spike_items) -> list[RawPost]:
    return _map(spike_items)


@pytest.fixture
def control_posts() -> list[RawPost]:
    return _map(load_spike_1_1a("_control"))


def _with_text(post: RawPost, text: str) -> RawPost:
    """The same post re-fetched with other text. Only for posts whose own text is used."""
    assert post.text_source != "shared_post"
    return annotate(
        post.with_changes(
            text=text,
            text_source="text" if text.strip() else "none",
            no_text=None,
            text_hash=None,
            phones=None,
        )
    )


def _media_types(post: RawPost) -> set[str]:
    return {media.type for media in post.media}


def _no_media(posts: list[RawPost]) -> RawPost:
    return next(post for post in posts if not post.media and post.text_source == "text")


def _with_photos(posts: list[RawPost]) -> RawPost:
    return next(
        post for post in posts if _media_types(post) == {"Photo"} and post.text_source == "text"
    )


def _no_text(posts: list[RawPost]) -> RawPost:
    return next(post for post in posts if post.no_text)


def _record(post: RawPost, **changes: Any) -> PostLifecycle:
    return PostLifecycle(**{**dict(initial_lifecycle(post)), **changes})


# --- pre_model_reason ---


def test_spike_posts_with_no_media_are_rejected_as_no_images(spike_posts) -> None:
    reasons = Counter(pre_model_reason(post) for post in spike_posts)
    assert reasons == {None: 97, "no_images": 8}
    assert all(pre_model_reason(post) == "no_images" for post in spike_posts if not post.media)


def test_control_run_has_one_real_no_text_post(control_posts) -> None:
    reasons = Counter(pre_model_reason(post) for post in control_posts)
    assert reasons == {None: 157, "no_images": 22, "no_text": 1}
    post = _no_text(control_posts)
    assert post.text_source == "none"
    assert _media_types(post) == {"Photo"}


def test_reel_only_post_is_not_rejected(spike_posts, control_posts) -> None:
    reel_only = [post for post in spike_posts + control_posts if _media_types(post) == {"Reel"}]
    assert len(reel_only) == 6
    assert all(pre_model_reason(post) is None for post in reel_only)


def test_video_only_post_is_not_rejected(spike_posts) -> None:
    post = next(post for post in spike_posts if _media_types(post) == {"Photo", "Video"})
    video_only = post.with_changes(media=[media for media in post.media if media.type == "Video"])
    assert _media_types(video_only) == {"Video"}
    assert pre_model_reason(video_only) is None


def test_no_text_comes_before_no_images(spike_posts) -> None:
    post = _with_text(_no_media(spike_posts), "")
    assert post.no_text and not post.media
    assert pre_model_reason(post) == "no_text"


def test_emoji_only_text_is_no_text(spike_posts) -> None:
    post = _with_text(_with_photos(spike_posts), "🏠🔑✨")
    assert pre_model_reason(post) == "no_text"


def test_shared_post_with_media_only_in_shared_post_is_not_rejected(spike_items) -> None:
    shared = [item for item in spike_items if item["sharedPost"] is not None]
    assert shared and all(not item["media"] for item in shared)
    assert all(pre_model_reason(post) is None for post in _map(shared))


def test_shared_post_rejected_only_when_shared_post_has_no_media_either(spike_items) -> None:
    item = copy.deepcopy(next(item for item in spike_items if item["sharedPost"] is not None))
    item["media"] = []
    item["sharedPost"]["media"] = []
    (post,) = _map([item])
    assert pre_model_reason(post) == "no_images"


def test_unannotated_post_raises(spike_items) -> None:
    post = to_raw_post(spike_items[0], FETCHED_AT)
    with pytest.raises(ValueError, match="textnorm"):
        pre_model_reason(post)
    with pytest.raises(ValueError, match="textnorm"):
        initial_lifecycle(post)


# --- initial_lifecycle ---


def test_initial_lifecycle_of_a_passing_post(spike_posts) -> None:
    post = _with_photos(spike_posts)
    assert initial_lifecycle(post) == PostLifecycle(
        schema_version=1,
        listing_id=post.listing_id,
        state="pending",
        rejection_reason=None,
        flagged_by=None,
        flagged_at=None,
        flag_note=None,
        last_published_at=post.posted_at,
        images=[],
    )


@pytest.mark.parametrize("make", [_no_media, _no_text])
def test_initial_lifecycle_of_a_rejected_post(make, spike_posts, control_posts) -> None:
    post = make(spike_posts + control_posts)
    record = initial_lifecycle(post)
    assert record.state == "rejected"
    assert record.rejection_reason == pre_model_reason(post)
    assert record.last_published_at == post.posted_at
    assert record.last_published_at.tzinfo is UTC
    assert record.images == []


# --- recheck: a post rejected before the model (#72.1) ---


def test_real_refetch_with_unchanged_content_changes_nothing(spike_posts, control_posts) -> None:
    again = {post.listing_id: post for post in control_posts}
    for post in spike_posts:
        record = initial_lifecycle(post)
        assert recheck(record, again[post.listing_id]) == record


def test_no_images_refetched_with_media_returns_to_pending(spike_posts) -> None:
    post = _no_media(spike_posts)
    record = initial_lifecycle(post)
    refetched = post.with_changes(media=_with_photos(spike_posts).media)
    assert recheck(record, refetched) == _record(post, state="pending", rejection_reason=None)


def test_no_images_refetched_with_media_but_no_text_becomes_no_text(spike_posts) -> None:
    post = _no_media(spike_posts)
    refetched = _with_text(post.with_changes(media=_with_photos(spike_posts).media), "")
    assert recheck(initial_lifecycle(post), refetched).rejection_reason == "no_text"


def test_no_images_refetched_with_neither_becomes_no_text(spike_posts) -> None:
    post = _no_media(spike_posts)
    result = recheck(initial_lifecycle(post), _with_text(post, ""))
    assert (result.state, result.rejection_reason) == ("rejected", "no_text")


def test_no_text_refetched_with_text_and_media_returns_to_pending(control_posts) -> None:
    post = _no_text(control_posts)
    result = recheck(initial_lifecycle(post), _with_text(post, LISTING_TEXT))
    assert (result.state, result.rejection_reason) == ("pending", None)


def test_no_text_refetched_with_text_but_no_media_becomes_no_images(control_posts) -> None:
    post = _no_text(control_posts)
    refetched = _with_text(post, LISTING_TEXT).with_changes(media=[])
    result = recheck(initial_lifecycle(post), refetched)
    assert (result.state, result.rejection_reason) == ("rejected", "no_images")


@pytest.mark.parametrize("make", [_no_media, _no_text])
def test_still_failing_stays_rejected_unchanged(make, spike_posts, control_posts) -> None:
    post = make(spike_posts + control_posts)
    record = initial_lifecycle(post)
    assert recheck(record, post) == record


def test_recheck_keeps_every_other_field(spike_posts) -> None:
    post = _no_media(spike_posts)
    image = PostImage(listing_id="b" * 64, media_id="m1", local_path=None, error="timeout")
    later = datetime(2026, 10, 5, 8, 0, tzinfo=UTC)
    record = _record(post, images=[image], last_published_at=later, flag_note="note")
    refetched = post.with_changes(media=_with_photos(spike_posts).media)
    assert recheck(record, refetched) == _record(
        post,
        state="pending",
        rejection_reason=None,
        images=[image],
        last_published_at=later,
        flag_note="note",
    )


# --- recheck: a pending post (#73.2) ---


def test_pending_refetched_unchanged_stays_pending(spike_posts) -> None:
    post = _with_photos(spike_posts)
    record = initial_lifecycle(post)
    assert recheck(record, post) == record


def test_pending_refetched_without_media_becomes_no_images(spike_posts) -> None:
    post = _with_photos(spike_posts)
    result = recheck(initial_lifecycle(post), post.with_changes(media=[]))
    assert (result.state, result.rejection_reason) == ("rejected", "no_images")


def test_pending_refetched_without_text_becomes_no_text(spike_posts) -> None:
    post = _with_photos(spike_posts)
    result = recheck(initial_lifecycle(post), _with_text(post, ""))
    assert (result.state, result.rejection_reason) == ("rejected", "no_text")


# --- recheck: records left untouched (#73.2, #73.3) ---


UNTOUCHED = [
    {"state": "active", "rejection_reason": None},
    *({"state": "rejected", "rejection_reason": reason} for reason in MODEL_REASONS),
    {"state": "rejected", "rejection_reason": "flagged", **FLAG},
    {"state": "archived", "rejection_reason": "no_text"},
    {"state": "archived", "rejection_reason": "no_images"},
    {"state": "archived", "rejection_reason": None},
]


@pytest.mark.parametrize(
    "changes", UNTOUCHED, ids=lambda c: f"{c['state']}-{c['rejection_reason']}"
)
def test_record_with_a_verdict_or_archived_is_untouched(changes, spike_posts) -> None:
    post = _with_photos(spike_posts)
    record = _record(post, **changes)
    emptied = _with_text(post, "").with_changes(media=[])
    assert recheck(record, emptied) is record
    assert recheck(record, post) is record


def test_recheck_refuses_another_posts_record(spike_posts) -> None:
    first, second = spike_posts[:2]
    with pytest.raises(ValueError, match="does not belong"):
        recheck(initial_lifecycle(first), second)
