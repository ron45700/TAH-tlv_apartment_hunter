"""The Repository contract. Every test runs against local_json and SQLite (make_repository)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from tests.conftest import FETCHED_AT, make_listing
from tlv_hunter.contracts.post_lifecycle import (
    POST_LIFECYCLE_SCHEMA_VERSION,
    PostImage,
    PostLifecycle,
)
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.store.base import Repository

MakeRepository = Callable[[], Repository]


def written(value):
    return {"state": "written", "value": value}


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
        "classification_failures": 0,
        "last_classification_error": None,
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


# --- find_lifecycles_with_image_errors (DECISIONS.md #80) ---


def _image(post: RawPost, media_id: str, error: str | None) -> PostImage:
    local_path = None if error is not None else f"images/{post.listing_id}/{media_id}.jpg"
    return PostImage(
        listing_id=post.listing_id, media_id=media_id, local_path=local_path, error=error
    )


def test_find_lifecycles_with_image_errors_matches_the_entries_by_prefix(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    images = {
        0: [_image(posts[0], "a", None), _image(posts[0], "b", "network: gaierror")],
        1: [_image(posts[1], "a", "timeout")],
        2: [_image(posts[2], "a", "http 403"), _image(posts[2], "b", None)],
        3: [],
        4: [_image(posts[4], "a", "not attempted: time budget")],
    }
    for index, entries in images.items():
        repo.upsert_with_lifecycle(posts[index], _pending(posts[index], images=entries))

    found = make_repository().find_lifecycles_with_image_errors(("network: ", "timeout"))
    expected = sorted([posts[0].listing_id, posts[1].listing_id])
    assert [record.listing_id for record in found] == expected
    assert found[0] == make_repository().get_lifecycle(expected[0])

    every = make_repository().find_lifecycles_with_image_errors(
        ("network: ", "timeout", "not attempted: time budget", "http ")
    )
    assert len(every) == 4
    assert make_repository().find_lifecycles_with_image_errors(()) == []
    assert make_repository().find_lifecycles_with_image_errors(("too large",)) == []


def test_find_lifecycles_with_image_errors_reads_only_the_error_field_from_its_start(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    # The prefix in other fields, or inside an error, is not a match.
    noted = _pending(
        posts[0],
        state="rejected",
        rejection_reason="flagged",
        flagged_by="ron",
        flagged_at=datetime(2026, 10, 4, 9, 0, tzinfo=UTC),
        flag_note="network: gaierror",
        images=[_image(posts[0], "network: gaierror", "http 404 network: gaierror")],
    )
    repo.upsert_with_lifecycle(posts[0], noted)
    assert make_repository().find_lifecycles_with_image_errors(("network: ",)) == []


def test_find_lifecycles_with_image_errors_on_an_empty_store(
    make_repository: MakeRepository,
) -> None:
    assert make_repository().find_lifecycles_with_image_errors(("network: ",)) == []


# --- task 2.2: Listing storage (DECISIONS.md #131; invariant 14) ---


def _canonical(post: RawPost) -> RawPost:
    return post.with_changes(is_canonical=True, duplicate_of=None)


def test_get_listing_of_an_unclassified_post_is_none(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    repo.upsert_with_lifecycle(posts[0], _pending(posts[0]))
    assert repo.get_listing(posts[0].listing_id) is None


def test_save_classification_writes_both_and_round_trips_through_a_fresh_instance(
    make_repository: MakeRepository, posts
) -> None:
    post = posts[0]
    make_repository().upsert_with_lifecycle(post, _pending(post))
    listing = make_listing(
        post.listing_id, areas=[30, 31], price=written([4500]), price_source="text"
    )
    active = _pending(post, state="active")
    make_repository().save_classification(listing, active)

    fresh = make_repository()
    assert fresh.get_listing(post.listing_id) == listing
    assert fresh.get_lifecycle(post.listing_id) == active


def test_save_classification_replaces_an_earlier_listing(
    make_repository: MakeRepository, posts
) -> None:
    post = posts[0]
    repo = make_repository()
    repo.upsert_with_lifecycle(post, _pending(post))
    repo.save_classification(
        make_listing(post.listing_id, areas=[37]), _pending(post, state="active")
    )
    second = make_listing(post.listing_id, areas=[52], prompt_version="test-2")
    repo.save_classification(second, _pending(post, state="active"))
    assert make_repository().get_listing(post.listing_id) == second


def test_save_classification_requires_a_stored_post(make_repository: MakeRepository, posts) -> None:
    repo = make_repository()
    with pytest.raises(KeyError):
        repo.save_classification(make_listing(posts[0].listing_id), _pending(posts[0]))
    assert repo.get_listing(posts[0].listing_id) is None


def test_save_classification_refuses_a_pair_of_two_posts(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    for post in posts[:2]:
        repo.upsert_with_lifecycle(post, _pending(post))
    with pytest.raises(ValueError, match="different posts"):
        repo.save_classification(make_listing(posts[0].listing_id), _pending(posts[1]))
    assert repo.get_listing(posts[0].listing_id) is None


def test_save_classification_never_touches_the_stored_post(
    make_repository: MakeRepository, posts
) -> None:
    """Invariant 14: classification never touches the source text (DECISIONS.md #163)."""
    repo = make_repository()
    for post in posts:
        repo.upsert_with_lifecycle(post, _pending(post))
    before = {post.listing_id: post.model_dump_json() for post in make_repository().query()}
    for post in posts:
        repo.save_classification(make_listing(post.listing_id), _pending(post, state="active"))
    after = {post.listing_id: post.model_dump_json() for post in make_repository().query()}
    assert after == before


def test_find_pending_canonicals_returns_exactly_the_pending_canonicals(
    make_repository: MakeRepository, posts
) -> None:
    repo = make_repository()
    pending, active, archived, rejected, duplicate, canonical_no_result = posts[:6]
    for post in (pending, active, archived, rejected):
        repo.upsert_with_lifecycle(_canonical(post), _pending(post))
    repo.save_lifecycle(_pending(active, state="active"))
    repo.save_lifecycle(_pending(archived, state="archived"))
    repo.save_lifecycle(_pending(rejected, state="rejected", rejection_reason="seeking"))
    repo.upsert_with_lifecycle(
        duplicate.with_changes(is_canonical=False, duplicate_of=pending.listing_id),
        _pending(duplicate),
    )
    repo.upsert_with_lifecycle(_canonical(posts[6]), _pending(posts[6]))
    repo.upsert(_canonical(canonical_no_result))  # no lifecycle record: not pending

    found = make_repository().find_pending_canonicals()
    assert [post.listing_id for post in found] == sorted([pending.listing_id, posts[6].listing_id])


def test_find_pending_canonicals_on_an_empty_store(make_repository: MakeRepository) -> None:
    assert make_repository().find_pending_canonicals() == []
