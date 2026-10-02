from datetime import timedelta
from pathlib import Path

import pytest

from tests.conftest import FETCHED_AT
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.store.local_json import RAW_POSTS_COLLECTION, LocalJsonRepository
from tlv_hunter.textnorm.annotate import annotate


@pytest.fixture
def posts(thedoor_items):
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in thedoor_items]


def test_all_20_round_trip_identical_through_a_fresh_instance(
    tmp_path: Path, thedoor_items, posts
) -> None:
    writer = LocalJsonRepository(tmp_path)
    for post in posts:
        writer.upsert(post)

    stored = {post.listing_id: post for post in LocalJsonRepository(tmp_path).query()}
    assert len(stored) == 20
    items_by_id = {item["post_id"]: item for item in thedoor_items}
    for post in posts:
        back = stored[post.listing_id]
        assert back == post
        assert back.model_dump(mode="json") == post.model_dump(mode="json")
        assert back.raw == items_by_id[post.source_post_id]
        assert back.posted_at.utcoffset() == timedelta(0)
        assert back.fetched_at.utcoffset() == timedelta(0)


def test_layout_is_one_file_per_record_with_nothing_else(tmp_path: Path, posts) -> None:
    repo = LocalJsonRepository(tmp_path)
    for post in posts:
        repo.upsert(post)
    assert [p.name for p in tmp_path.iterdir()] == [RAW_POSTS_COLLECTION]
    files = sorted(p.name for p in (tmp_path / RAW_POSTS_COLLECTION).iterdir())
    assert files == sorted(f"{post.listing_id}.json" for post in posts)


def test_hebrew_is_stored_unescaped(tmp_path: Path, posts) -> None:
    repo = LocalJsonRepository(tmp_path)
    repo.upsert(posts[0])
    content = (tmp_path / RAW_POSTS_COLLECTION / f"{posts[0].listing_id}.json").read_text(
        encoding="utf-8"
    )
    assert "להשכרה" in content
    assert "\\u05" not in content


def test_upsert_overwrites_record_but_keeps_first_fetched_at(tmp_path: Path, posts) -> None:
    repo = LocalJsonRepository(tmp_path)
    first = posts[0]
    repo.upsert(first)
    refetched = first.with_changes(fetched_at=FETCHED_AT + timedelta(minutes=30), reactions_count=5)

    returned = repo.upsert(refetched)

    stored = LocalJsonRepository(tmp_path).query()
    assert len(stored) == 1
    assert stored[0] == returned
    assert stored[0].reactions_count == 5
    assert stored[0].fetched_at == FETCHED_AT


def test_find_by_hash(tmp_path: Path, posts) -> None:
    repo = LocalJsonRepository(tmp_path)
    for post in posts:
        repo.upsert(post)
    by_id = {post.source_post_id: post for post in posts}
    pair = by_id["2178092279420962"]
    found = {p.source_post_id for p in repo.find_by_hash(pair.text_hash)}
    assert found == {"2178092279420962", "2177447349485455"}
    assert repo.find_by_hash(None) == []
    assert repo.find_by_hash("0" * 64) == []


def test_find_by_phone_matches_across_formats(tmp_path: Path, posts) -> None:
    repo = LocalJsonRepository(tmp_path)
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


def test_query_on_empty_store_returns_nothing(tmp_path: Path) -> None:
    assert LocalJsonRepository(tmp_path).query() == []
