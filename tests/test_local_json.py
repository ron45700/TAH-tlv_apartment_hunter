from pathlib import Path

from tlv_hunter.store.local_json import RAW_POSTS_COLLECTION, LocalJsonRepository

# The behaviour shared with SQLite is in test_repository_contract.py. This file holds only what is
# specific to the one-file-per-record layout.


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
