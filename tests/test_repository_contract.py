"""The Repository contract. Every test runs against local_json and SQLite (make_repository)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import FETCHED_AT
from tlv_hunter.contracts.post_lifecycle import (
    POST_LIFECYCLE_SCHEMA_VERSION,
    PostImage,
    PostLifecycle,
)
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.store.base import Repository

MakeRepository = Callable[[], Repository]


def _pending(post: RawPost, **changes) -> PostLifecycle:
    fields = {
        "schema_version": POST_LIFECYCLE_SCHEMA_VERSION,
        "listing_id": post.listing_id,
        "state": "pending",
        "rejection_reason": None,
        "flagged_by": None,
        "flagged_at": None,
        "flag_note": None,
        "last_published_at": post.posted_at,
        "images": [],
    }
    return PostLifecycle(**{**fields, **changes})


def test_all_20_round_trip_identical_through_a_fresh_instance(
    make_repository: MakeRepository, thedoor_items, posts
) -> None:
    writer = make_repository()
    for post in posts:
        writer.upsert(post)

    stored = {post.listing_id: post for post in make_repository().query()}
    assert len(stored) == 20
    items_by_id = {item["post_id"]: item for item in thedoor_items}
    for post in posts:
        back = stored[post.listing_id]
        assert back == post
        assert back.model_dump(mode="json") == post.model_dump(mode="json")
        assert back.raw == items_by_id[post.source_post_id]
        assert back.posted_at.utcoffset() == timedelta(0)
        assert back.fetched_at.utcoffset() == timedelta(0)


def test_upsert_overwrites_record_but_keeps_first_fetched_at(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    first = posts[0]
    repo.upsert(first)
    refetched = first.with_changes(fetched_at=FETCHED_AT + timedelta(minutes=30), reactions_count=5)

    returned = repo.upsert(refetched)

    stored = make_repository().query()
    assert len(stored) == 1
    assert stored[0] == returned
    assert stored[0].reactions_count == 5
    assert stored[0].fetched_at == FETCHED_AT


def test_get_returns_the_stored_post_or_none(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    first = posts[0]
    assert repo.get(first.listing_id) is None
    repo.upsert(first)
    repo.upsert(
        first.with_changes(fetched_at=FETCHED_AT + timedelta(minutes=30), reactions_count=5)
    )

    back = make_repository().get(first.listing_id)
    assert back == first.with_changes(reactions_count=5)
    assert back.fetched_at == FETCHED_AT
    assert repo.get(posts[1].listing_id) is None


def test_find_by_hash(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    for post in posts:
        repo.upsert(post)
    by_id = {post.source_post_id: post for post in posts}
    pair = by_id["2178092279420962"]
    found = {p.source_post_id for p in repo.find_by_hash(pair.text_hash)}
    assert found == {"2178092279420962", "2177447349485455"}
    assert repo.find_by_hash(None) == []
    assert repo.find_by_hash("0" * 64) == []


def test_find_by_phone_matches_across_formats(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    for post in posts:
        repo.upsert(post)
    assert {p.source_post_id for p in repo.find_by_phone("054-800-8244")} == {
        "10163683432542695",
        "10163683412257695",
    }
    assert {p.source_post_id for p in repo.find_by_phone("+972509184537")} == {
        "2178554076041449",
        "2178430789387111",
    }
    assert repo.find_by_phone("0500000000") == []


def test_query_on_empty_store_returns_nothing(make_repository: MakeRepository) -> None:
    assert make_repository().query() == []


# --- post lifecycle record -------------------------------------------------------------------


def test_get_lifecycle_of_unknown_post_is_none(make_repository: MakeRepository) -> None:
    assert make_repository().get_lifecycle("0" * 64) is None


def test_save_and_get_lifecycle_round_trip_through_a_fresh_instance(
    make_repository: MakeRepository, posts
) -> None:
    post = posts[0]
    make_repository().upsert(post)
    record = _pending(
        post,
        state="rejected",
        rejection_reason="flagged",
        flagged_by="ron",
        flagged_at=datetime(2026, 10, 4, 9, 30, 0, 123456, tzinfo=UTC),
        flag_note="נתניה, לא תל אביב",
        images=[
            PostImage(listing_id=post.listing_id, media_id="m1", local_path="a/1.jpg", error=None),
            PostImage(listing_id=post.listing_id, media_id="m2", local_path=None, error="HTTP 403"),
        ],
    )

    assert make_repository().save_lifecycle(record) == record

    back = make_repository().get_lifecycle(post.listing_id)
    assert back == record
    assert back.flagged_at.utcoffset() == timedelta(0)
    assert back.last_published_at.utcoffset() == timedelta(0)


def test_save_lifecycle_requires_a_stored_post(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    with pytest.raises(KeyError):
        repo.save_lifecycle(_pending(posts[0]))
    assert repo.get_lifecycle(posts[0].listing_id) is None


def test_save_lifecycle_is_whole_record_replace_and_last_write_wins(
    make_repository: MakeRepository, posts
) -> None:
    """Pins a known limit (BACKLOG.md, open technical choices): two writers that both read the
    same record lose the first writer's change. Phase 1 has one writer."""
    post = posts[0]
    repo = make_repository()
    repo.upsert(post)
    repo.save_lifecycle(_pending(post))

    read_by_a = repo.get_lifecycle(post.listing_id)
    read_by_b = repo.get_lifecycle(post.listing_id)
    repo.save_lifecycle(
        read_by_a.model_copy(update={"flagged_by": "ron", "flagged_at": FETCHED_AT})
    )
    repo.save_lifecycle(
        read_by_b.model_copy(update={"state": "rejected", "rejection_reason": "seeking"})
    )

    final = make_repository().get_lifecycle(post.listing_id)
    assert final.state == "rejected" and final.rejection_reason == "seeking"
    assert final.flagged_by is None and final.flagged_at is None


def test_upsert_alone_creates_no_lifecycle_record(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    repo.upsert(posts[0])
    assert repo.get_lifecycle(posts[0].listing_id) is None
    assert repo.find_without_lifecycle() == [posts[0]]


def test_upsert_with_lifecycle_stores_both(make_repository: MakeRepository, posts) -> None:
    post = posts[0]
    initial = _pending(post)

    assert make_repository().upsert_with_lifecycle(post, initial) == post

    fresh = make_repository()
    assert fresh.query() == [post]
    assert fresh.get_lifecycle(post.listing_id) == initial
    assert fresh.find_without_lifecycle() == []


def test_upsert_with_lifecycle_never_overwrites_an_existing_record(
    make_repository: MakeRepository, posts
) -> None:
    post = posts[0]
    repo = make_repository()
    existing = _pending(post, state="rejected", rejection_reason="other_city")
    repo.upsert(post)
    repo.save_lifecycle(existing)
    refetched = post.with_changes(fetched_at=FETCHED_AT + timedelta(minutes=30), reactions_count=7)

    returned = repo.upsert_with_lifecycle(refetched, _pending(post))

    assert returned.fetched_at == FETCHED_AT
    fresh = make_repository()
    assert fresh.query() == [returned]
    assert fresh.query()[0].reactions_count == 7
    assert fresh.get_lifecycle(post.listing_id) == existing


def test_upsert_with_lifecycle_rejects_a_record_of_another_post(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    with pytest.raises(ValueError):
        repo.upsert_with_lifecycle(posts[0], _pending(posts[1]))
    assert repo.query() == []
    assert repo.get_lifecycle(posts[0].listing_id) is None
    assert repo.get_lifecycle(posts[1].listing_id) is None


def test_upsert_keeps_the_lifecycle_record(make_repository: MakeRepository, posts) -> None:
    post = posts[0]
    repo = make_repository()
    repo.upsert_with_lifecycle(post, _pending(post))
    repo.upsert(post.with_changes(reactions_count=3))
    assert make_repository().get_lifecycle(post.listing_id) == _pending(post)


def test_find_without_lifecycle_returns_exactly_the_posts_without_a_record(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    with_record = posts[:5]
    for post in with_record:
        repo.upsert_with_lifecycle(post, _pending(post))
    for post in posts[5:]:
        repo.upsert(post)

    missing = {post.listing_id for post in make_repository().find_without_lifecycle()}
    assert missing == {post.listing_id for post in posts[5:]}
