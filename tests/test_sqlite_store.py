"""What is specific to SqliteRepository. The shared contract is in test_repository_contract.py."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.contracts.post_lifecycle import POST_LIFECYCLE_SCHEMA_VERSION, PostLifecycle
from tlv_hunter.store import sqlite as store_sqlite
from tlv_hunter.store.sqlite import SqliteRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / SQLITE_FILENAME


def _rows(path: Path, sql: str) -> list[tuple]:
    with closing(sqlite3.connect(path)) as conn:
        return conn.execute(sql).fetchall()


def _pending(post) -> PostLifecycle:
    return PostLifecycle(
        schema_version=POST_LIFECYCLE_SCHEMA_VERSION,
        listing_id=post.listing_id,
        state="pending",
        rejection_reason=None,
        flagged_by=None,
        flagged_at=None,
        flag_note=None,
        last_published_at=post.posted_at,
        images=[],
    )


def test_creates_its_tables_and_its_layout_row(db_path: Path) -> None:
    SqliteRepository(db_path)
    tables = {name for (name,) in _rows(db_path, "SELECT name FROM sqlite_master")}
    assert {"layout_version", "raw_posts", "post_lifecycle", "raw_posts_text_hash"} <= tables
    assert _rows(db_path, "SELECT module, version FROM layout_version") == [("store", 1)]


def test_reopening_an_existing_file_keeps_the_data(db_path: Path, posts) -> None:
    SqliteRepository(db_path).upsert(posts[0])
    assert SqliteRepository(db_path).query() == [posts[0]]


def test_text_hash_column_matches_the_document(db_path: Path, posts) -> None:
    repo = SqliteRepository(db_path)
    for post in posts:
        repo.upsert(post)
    columns = dict(_rows(db_path, "SELECT listing_id, text_hash FROM raw_posts"))
    assert columns == {post.listing_id: post.text_hash for post in posts}


def test_failure_inside_upsert_with_lifecycle_rolls_back_the_post(
    db_path: Path, posts, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = SqliteRepository(db_path)

    def fail(*args, **kwargs):
        raise RuntimeError("crash between the two writes")

    monkeypatch.setattr(PostLifecycle, "model_dump_json", fail)
    with pytest.raises(RuntimeError):
        repo.upsert_with_lifecycle(posts[0], _pending(posts[0]))
    monkeypatch.undo()

    assert repo.query() == []
    assert repo.get_lifecycle(posts[0].listing_id) is None


def test_foreign_key_refuses_an_orphan_lifecycle_row(db_path: Path) -> None:
    repo = SqliteRepository(db_path)
    with pytest.raises(sqlite3.IntegrityError), repo._connect() as conn:
        conn.execute("INSERT INTO post_lifecycle (listing_id, doc) VALUES ('x', '{}')")


def test_no_connection_is_left_open(db_path: Path, posts) -> None:
    repo = SqliteRepository(db_path)
    repo.upsert_with_lifecycle(posts[0], _pending(posts[0]))
    repo.query()
    repo.get_lifecycle(posts[0].listing_id)
    db_path.unlink()  # On Windows this fails while any connection holds the file open.
    assert not db_path.exists()


def test_refuses_a_sqlite_older_than_the_minimum(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # 3.38.0: the JSON functions built in by default (DECISIONS.md #80).
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 37, 2))
    with pytest.raises(RuntimeError, match=r"'store' needs 3\.38\.0"):
        SqliteRepository(db_path)
    assert not db_path.exists()


def test_minimum_version_is_met_by_this_interpreter() -> None:
    assert sqlite3.sqlite_version_info >= store_sqlite.MIN_SQLITE_VERSION


@pytest.mark.parametrize("found", [0, 2])
def test_refuses_a_layout_version_mismatch(db_path: Path, found: int) -> None:
    SqliteRepository(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("UPDATE layout_version SET version = ? WHERE module = 'store'", (found,))
    with pytest.raises(RuntimeError, match=rf"'store' expects layout version 1, found {found}"):
        SqliteRepository(db_path)
