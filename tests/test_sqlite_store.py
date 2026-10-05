"""What is specific to SqliteRepository. The shared contract is in test_repository_contract.py."""

import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing
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
        classification_failures=0,
        last_classification_error=None,
    )


def test_creates_its_tables_and_its_layout_row(db_path: Path) -> None:
    SqliteRepository(db_path)
    tables = {name for (name,) in _rows(db_path, "SELECT name FROM sqlite_master")}
    assert {
        "layout_version",
        "raw_posts",
        "post_lifecycle",
        "raw_posts_text_hash",
        "listings",
    } <= tables
    assert sorted(_rows(db_path, "SELECT module, version FROM layout_version")) == [
        ("store", 1),
        ("store.listings", 1),
    ]


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


# --- task 2.2: the listings table has its own layout row (option C); layout 1 is untouched ---

# The store's layout 1 exactly as phase 1 created it, before the listings table existed.
_LAYOUT_1 = (
    "CREATE TABLE layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)",
    "CREATE TABLE raw_posts (listing_id TEXT PRIMARY KEY, text_hash TEXT, doc TEXT NOT NULL)",
    "CREATE INDEX raw_posts_text_hash ON raw_posts (text_hash)",
    "CREATE TABLE post_lifecycle ("
    "listing_id TEXT PRIMARY KEY REFERENCES raw_posts (listing_id), doc TEXT NOT NULL)",
    "INSERT INTO layout_version (module, version) VALUES ('store', 1)",
)


def _version_1_doc(post) -> str:
    """A lifecycle document as phase 1 wrote it: schema_version 1, no failure fields."""
    doc = _pending(post).model_dump(mode="json")
    del doc["classification_failures"], doc["last_classification_error"]
    doc["schema_version"] = 1
    return json.dumps(doc)


def _layout_1_file(path: Path, posts) -> None:
    with closing(sqlite3.connect(path)) as conn:
        for statement in _LAYOUT_1:
            conn.execute(statement)
        for post in posts:
            conn.execute(
                "INSERT INTO raw_posts (listing_id, text_hash, doc) VALUES (?, ?, ?)",
                (post.listing_id, post.text_hash, post.model_dump_json()),
            )
            conn.execute(
                "INSERT INTO post_lifecycle (listing_id, doc) VALUES (?, ?)",
                (post.listing_id, _version_1_doc(post)),
            )
        conn.commit()


def test_opens_a_layout_1_store_and_leaves_its_records_untouched(db_path: Path, posts) -> None:
    _layout_1_file(db_path, posts)
    before_posts = _rows(db_path, "SELECT listing_id, text_hash, doc FROM raw_posts ORDER BY 1")
    before_records = _rows(db_path, "SELECT listing_id, doc FROM post_lifecycle ORDER BY 1")

    repo = SqliteRepository(db_path)
    SqliteRepository(db_path)  # opening again changes nothing more

    assert (
        _rows(db_path, "SELECT listing_id, text_hash, doc FROM raw_posts ORDER BY 1")
        == before_posts
    )
    assert _rows(db_path, "SELECT listing_id, doc FROM post_lifecycle ORDER BY 1") == before_records
    assert sorted(_rows(db_path, "SELECT module, version FROM layout_version")) == [
        ("store", 1),
        ("store.listings", 1),
    ]
    assert _rows(db_path, "SELECT count(*) FROM listings") == [(0,)]
    record = repo.get_lifecycle(posts[0].listing_id)
    assert (record.schema_version, record.classification_failures) == (2, 0)
    assert record.last_classification_error is None
    assert len(repo.query()) == len(posts)


def test_a_version_1_record_is_written_back_as_version_2_only_when_saved(
    db_path: Path, posts
) -> None:
    _layout_1_file(db_path, posts[:2])
    repo = SqliteRepository(db_path)
    repo.save_lifecycle(repo.get_lifecycle(posts[0].listing_id))
    versions = dict(
        _rows(db_path, "SELECT listing_id, doc ->> '$.schema_version' FROM post_lifecycle")
    )
    assert versions == {posts[0].listing_id: 2, posts[1].listing_id: 1}


@pytest.mark.parametrize("found", [0, 2])
def test_refuses_a_listings_layout_version_mismatch(db_path: Path, found: int) -> None:
    SqliteRepository(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            "UPDATE layout_version SET version = ? WHERE module = 'store.listings'", (found,)
        )
        conn.commit()
    with pytest.raises(
        RuntimeError, match=rf"'store.listings' expects layout version 1, found {found}"
    ):
        SqliteRepository(db_path)


def test_failure_inside_save_classification_rolls_back_the_listing(
    db_path: Path, posts, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = SqliteRepository(db_path)
    repo.upsert_with_lifecycle(posts[0], _pending(posts[0]))

    def fail(*args, **kwargs):
        raise RuntimeError("crash between the two writes")

    monkeypatch.setattr(PostLifecycle, "model_dump_json", fail)
    with pytest.raises(RuntimeError):
        repo.save_classification(make_listing(posts[0].listing_id), _pending(posts[0]))
    monkeypatch.undo()

    assert repo.get_listing(posts[0].listing_id) is None
    assert repo.get_lifecycle(posts[0].listing_id) == _pending(posts[0])


def test_foreign_key_refuses_an_orphan_listing_row(db_path: Path) -> None:
    SqliteRepository(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO listings (listing_id, doc) VALUES ('missing', '{}')")
