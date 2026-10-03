import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.contracts.group_watermark import GROUP_WATERMARK_SCHEMA_VERSION, GroupWatermark
from tlv_hunter.state.base import WatermarkStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / SQLITE_FILENAME


def _mark(group_id: str, **changes) -> GroupWatermark:
    fields = {
        "schema_version": GROUP_WATERMARK_SCHEMA_VERSION,
        "group_id": group_id,
        "watermark": datetime(2026, 10, 4, 6, 15, tzinfo=UTC),
        "last_success_at": datetime(2026, 10, 4, 6, 30, 0, 250000, tzinfo=UTC),
        "consecutive_failures": 0,
    }
    return GroupWatermark(**{**fields, **changes})


def test_satisfies_the_protocol(db_path: Path) -> None:
    assert isinstance(SqliteWatermarkStore(db_path), WatermarkStore)


def test_empty_store(db_path: Path) -> None:
    store = SqliteWatermarkStore(db_path)
    assert store.get("g1") is None
    assert store.get_all() == []


def test_save_all_round_trips_through_a_fresh_instance(db_path: Path) -> None:
    first_run = _mark("g2", watermark=None, last_success_at=None, consecutive_failures=3)
    records = [_mark("g1"), first_run]
    SqliteWatermarkStore(db_path).save_all(records)

    fresh = SqliteWatermarkStore(db_path)
    assert fresh.get_all() == records
    assert fresh.get("g2") == first_run
    assert fresh.get("g1").watermark.utcoffset() == timedelta(0)
    assert fresh.get("g1").last_success_at.utcoffset() == timedelta(0)


def test_save_all_replaces_existing_groups_and_keeps_the_others(db_path: Path) -> None:
    store = SqliteWatermarkStore(db_path)
    store.save_all([_mark("g1"), _mark("g2")])
    later = _mark("g1", watermark=datetime(2026, 10, 4, 7, 0, tzinfo=UTC))
    store.save_all([later])
    assert store.get_all() == [later, _mark("g2")]


def test_save_all_is_one_transaction(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SqliteWatermarkStore(db_path)
    original = GroupWatermark.model_dump_json
    calls = []

    def fail_on_second(self, *args, **kwargs):
        calls.append(self.group_id)
        if len(calls) == 2:
            raise RuntimeError("crash mid-save")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(GroupWatermark, "model_dump_json", fail_on_second)
    with pytest.raises(RuntimeError):
        store.save_all([_mark("g1"), _mark("g2")])
    monkeypatch.undo()

    assert store.get_all() == []


def test_save_all_refuses_a_duplicate_group(db_path: Path) -> None:
    store = SqliteWatermarkStore(db_path)
    with pytest.raises(ValueError):
        store.save_all([_mark("g1"), _mark("g1")])
    assert store.get_all() == []


def test_shares_one_file_with_the_store(db_path: Path, posts) -> None:
    SqliteRepository(db_path).upsert(posts[0])
    SqliteWatermarkStore(db_path).save_all([_mark("g1")])

    assert SqliteRepository(db_path).query() == [posts[0]]
    assert SqliteWatermarkStore(db_path).get_all() == [_mark("g1")]
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute("SELECT module, version FROM layout_version ORDER BY module").fetchall()
    assert rows == [("state", 1), ("store", 1)]


def test_refuses_a_sqlite_older_than_the_minimum(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 23, 1))
    with pytest.raises(RuntimeError, match=r"'state' needs 3\.24\.0"):
        SqliteWatermarkStore(db_path)
    assert not db_path.exists()


@pytest.mark.parametrize("found", [0, 2])
def test_refuses_a_layout_version_mismatch(db_path: Path, found: int) -> None:
    SqliteWatermarkStore(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("UPDATE layout_version SET version = ? WHERE module = 'state'", (found,))
    with pytest.raises(RuntimeError, match=rf"'state' expects layout version 1, found {found}"):
        SqliteWatermarkStore(db_path)


def test_a_store_layout_mismatch_does_not_block_state(db_path: Path) -> None:
    SqliteRepository(db_path)
    with closing(sqlite3.connect(db_path)) as conn, conn:
        conn.execute("UPDATE layout_version SET version = 2 WHERE module = 'store'")
    SqliteWatermarkStore(db_path).save_all([_mark("g1")])
    with pytest.raises(RuntimeError, match="'store'"):
        SqliteRepository(db_path)
