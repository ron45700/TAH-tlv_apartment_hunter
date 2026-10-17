"""`jobs.common.backup_store` by SQLite's online backup (`PHASE_3.md` 3.9 (k) 4; DECISIONS.md #424,
point 89), against temporary stores only: never the production store."""

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.jobs import common
from tlv_hunter.jobs.common import backup_store, integrity_ok, online_copy, raw_post_rows
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.store.sqlite import SqliteRepository

NOW = datetime(2026, 10, 16, 9, 0, tzinfo=UTC)


@pytest.fixture
def database(tmp_path: Path, posts) -> Path:
    path = tmp_path / "store" / SQLITE_FILENAME
    path.parent.mkdir()
    repository = SqliteRepository(path)
    for post in posts[:3]:
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE scratch (x TEXT)")  # a table for the writer below
    return path


def test_the_backup_is_dated_checked_and_holds_the_same_rows(database: Path) -> None:
    backup = backup_store(database, NOW)
    assert backup.name == "tlv_hunter.2026-10-16.backup.sqlite3"
    assert integrity_ok(backup)
    assert raw_post_rows(backup) == raw_post_rows(database)
    assert len(raw_post_rows(backup)) == 3


def test_a_writer_beside_it_neither_blocks_nor_breaks_the_backup(database: Path) -> None:
    """The site writes beside the job commands (#260): a write transaction open on another
    connection during the backup. The copy holds what was committed and passes its checks."""
    writer = sqlite3.connect(database, autocommit=True)
    with closing(writer):
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO scratch VALUES ('not yet committed')")
        backup = backup_store(database, NOW)  # while the writer holds its RESERVED lock
        writer.execute("COMMIT")
    assert integrity_ok(backup)
    with closing(sqlite3.connect(backup)) as copy:
        assert copy.execute("SELECT count(*) FROM scratch").fetchone() == (0,)
    with closing(sqlite3.connect(database)) as store:
        assert store.execute("SELECT count(*) FROM scratch").fetchone() == (1,)


def test_the_store_is_only_read(database: Path) -> None:
    before = database.read_bytes()
    backup_store(database, NOW)
    assert database.read_bytes() == before


def test_a_second_backup_the_same_day_gets_the_time_and_nothing_is_overwritten(
    database: Path,
) -> None:
    first = backup_store(database, NOW)
    second = backup_store(database, NOW)
    assert second.name == "tlv_hunter.2026-10-16T090000.backup.sqlite3"
    assert first.is_file() and second.is_file()
    with pytest.raises(FileExistsError):
        backup_store(database, NOW)


def test_a_backup_whose_raw_posts_differ_fails(
    database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = iter([[("a", "{}", None)], [("b", "{}", None)]])
    monkeypatch.setattr(common, "raw_post_rows", lambda path: next(rows))
    with pytest.raises(RuntimeError, match="RawPost rows differ"):
        backup_store(database, NOW)


def test_online_copy_refuses_a_missing_store_and_an_existing_target(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no store"):
        online_copy(tmp_path / "absent.sqlite3", tmp_path / "copy.sqlite3")
    source = tmp_path / "source.sqlite3"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("CREATE TABLE t (x)")
    target = tmp_path / "copy.sqlite3"
    target.write_bytes(b"earlier")
    with pytest.raises(FileExistsError):
        online_copy(source, target)
    assert target.read_bytes() == b"earlier"
