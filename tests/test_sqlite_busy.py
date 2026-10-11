"""The explicit busy timeout on every SQLite connection of the package (task 3.4 (e);
DECISIONS.md #259, #289 point 6)."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import SQLITE_FILENAME
from tlv_hunter.jobs.common import raw_post_rows
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore


def test_the_busy_timeout_is_ten_seconds() -> None:
    assert BUSY_TIMEOUT_SECONDS == 10.0


def test_every_connection_of_the_four_modules_passes_the_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = sqlite3.connect
    timeouts: list[Any] = []

    def recording(*args: Any, **kwargs: Any) -> sqlite3.Connection:
        timeouts.append(kwargs.get("timeout"))
        return real(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", recording)
    database = tmp_path / SQLITE_FILENAME
    repository = SqliteRepository(database)
    repository.query()
    SqliteRepository(database, read_only=True).query()
    SqliteWatermarkStore(database).get_all()
    SqliteUserDataStore(database).list_users()
    raw_post_rows(database)

    assert len(timeouts) >= 7
    assert set(timeouts) == {BUSY_TIMEOUT_SECONDS}
