"""Gate G (DECISIONS.md #472; `PHASE_5.md` point 5): the `RunRecord` and `ScheduleSettings`
contracts, their store (`state/runs.py`: its own layout row, created when absent; compare and set),
the Repository's one delete (`delete_post`, both stores), the users' marks deleted with a post
(`delete_for_listings`), and the timed write lock of point 13 (`sqlite_busy.begin_immediate`).
Temporary stores only."""

import logging
import sqlite3
import threading
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import SQLITE_FILENAME, make_listing, overwrite_classification
from tests.test_gate_d import make_post
from tests.test_userdata_store import ADMIN_ID, admin
from tlv_hunter import sqlite_busy
from tlv_hunter.contracts.profile import new_profile
from tlv_hunter.contracts.run_record import RUN_RECORD_SCHEMA_VERSION, RunRecord
from tlv_hunter.contracts.schedule_settings import (
    SCHEDULE_SETTINGS_SCHEMA_VERSION,
    ScheduleSettings,
)
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.state.runs import LAYOUT_MODULE, SqliteRunStore
from tlv_hunter.store.base import Repository, StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

NOW = datetime(2026, 10, 20, 7, 0, tzinfo=UTC)


def run_record(**changes: Any) -> RunRecord:
    fields: dict[str, Any] = {
        "schema_version": RUN_RECORD_SCHEMA_VERSION,
        "run_id": "abc123def456",
        "trigger": "scheduled",
        "started_at": NOW,
        "finished_at": NOW + timedelta(minutes=2),
        "status": "succeeded",
        "failure_kind": None,
        "rows_fetched": 12,
        "rows_skipped": 0,
        "window_since": NOW - timedelta(minutes=45),
        "window_capped": False,
        "apify_run_id": "AbCdEf",
        "charged_events": {"apify-default-dataset-item": 12, "apify-actor-start": 1},
        "cost_usd": None,
        "cost_settled_at": None,
    }
    return RunRecord(**{**fields, **changes})


def settings(**changes: Any) -> ScheduleSettings:
    fields: dict[str, Any] = {
        "schema_version": SCHEDULE_SETTINGS_SCHEMA_VERSION,
        "interval_minutes": 30,
        "quiet_from": "00:00",
        "quiet_until": "07:00",
        "run_now_requested_at": None,
        "last_digest_at": None,
        "updated_by": None,
        "updated_at": NOW,
    }
    return ScheduleSettings(**{**fields, **changes})


# --- the contracts ---


def test_a_run_record_round_trips_through_json() -> None:
    record = run_record(cost_usd=0.023, cost_settled_at=NOW + timedelta(minutes=20))
    assert RunRecord.model_validate_json(record.model_dump_json()) == record


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "running"},  # running with an end
        {"status": "failed"},  # failed with no reason
        {"failure_kind": "boom"},  # a reason on a success
        {"finished_at": NOW - timedelta(seconds=1)},
        {"rows_fetched": -1},
        {"charged_events": {"x": -1}},
        {"cost_usd": 0.1},  # a cost with no settling time
        {"started_at": datetime(2026, 10, 20, 7, 0)},  # naive
        {"schema_version": 2},
        {"run_id": ""},
    ],
)
def test_a_run_record_refuses_what_does_not_hold_together(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        run_record(**changes)


def test_a_running_record_has_no_end_and_no_cost() -> None:
    running = run_record(status="running", finished_at=None)
    assert running.finished_at is None
    with pytest.raises(ValueError):
        run_record(status="running", finished_at=None, cost_usd=0.1, cost_settled_at=NOW)


@pytest.mark.parametrize(
    "changes",
    [
        {"interval_minutes": 4},
        {"interval_minutes": 1441},
        {"quiet_from": "7:00"},
        {"quiet_until": "24:00"},
        {"updated_by": "ron"},  # a user id is opaque, never a name
        {"updated_at": datetime(2026, 10, 20, 7, 0)},
    ],
)
def test_schedule_settings_refuse_a_value_out_of_range(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        settings(**changes)


def test_schedule_settings_accept_the_bounds_and_equal_quiet_times() -> None:
    assert settings(interval_minutes=5, quiet_from="00:00", quiet_until="00:00")
    assert settings(interval_minutes=1440, updated_by=ADMIN_ID).updated_by == ADMIN_ID


# --- the store ---


def layout_rows(path: Path) -> dict[str, int]:
    with closing(sqlite3.connect(path)) as conn:
        return dict(conn.execute("SELECT module, version FROM layout_version").fetchall())


def test_the_layout_row_is_created_when_absent_and_left_alone_after(tmp_path: Path) -> None:
    database = tmp_path / SQLITE_FILENAME
    SqliteRepository(database)
    assert LAYOUT_MODULE not in layout_rows(database)
    SqliteRunStore(database)
    assert layout_rows(database)[LAYOUT_MODULE] == 1
    before = layout_rows(database)
    SqliteRunStore(database).recent_runs()
    assert layout_rows(database) == before
    SqliteRepository(database, read_only=True).query()  # an older opener reads its own rows only


def test_another_layout_version_is_refused(tmp_path: Path) -> None:
    database = tmp_path / SQLITE_FILENAME
    SqliteRunStore(database)
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("UPDATE layout_version SET version = 2 WHERE module = ?", (LAYOUT_MODULE,))
        conn.commit()
    with pytest.raises(RuntimeError, match="no automatic migration"):
        SqliteRunStore(database)


def test_runs_are_listed_newest_first_and_written_by_compare_and_set(tmp_path: Path) -> None:
    store = SqliteRunStore(tmp_path / SQLITE_FILENAME)
    first = store.add_run(run_record(run_id="first"))
    second = store.add_run(run_record(run_id="second", status="running", finished_at=None))
    assert [r.run_id for r in store.recent_runs()] == ["second", "first"]
    assert [r.run_id for r in store.recent_runs(1)] == ["second"]
    with pytest.raises(sqlite3.IntegrityError):
        store.add_run(run_record(run_id="first"))
    ended = run_record(run_id="second", finished_at=NOW + timedelta(minutes=3))
    store.save_run(ended, expected=second)
    assert store.get_run("second") == ended
    with pytest.raises(StaleRecordError):
        store.save_run(run_record(run_id="second", rows_fetched=1), expected=second)
    assert store.get_run("first") == first
    assert store.get_run("nothing") is None


def test_the_settings_are_one_row_written_by_compare_and_set(tmp_path: Path) -> None:
    store = SqliteRunStore(tmp_path / SQLITE_FILENAME)
    assert store.get_settings() is None
    assert store.set_last_digest(NOW) is False  # no row: nothing written
    first = store.save_settings(settings(), expected=None)
    with pytest.raises(StaleRecordError):
        store.save_settings(settings(interval_minutes=10), expected=None)
    changed = store.save_settings(settings(interval_minutes=10), expected=first)
    assert store.get_settings() == changed
    with pytest.raises(StaleRecordError):
        store.save_settings(settings(interval_minutes=20), expected=first)
    assert store.set_last_digest(NOW + timedelta(hours=1)) is True
    stored = store.get_settings()
    assert stored is not None and stored.interval_minutes == 10
    assert stored.last_digest_at == NOW + timedelta(hours=1)


# --- the Repository's one delete (both stores) ---


def test_delete_post_removes_the_post_its_record_and_its_listing_by_compare_and_set(
    make_repository: Callable[[], Repository],
) -> None:
    repository = make_repository()
    kept, gone = make_post(1, "flat one words"), make_post(2, "flat two words")
    for post in (kept, gone):
        repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    listing = make_listing(gone.listing_id)
    record = repository.get_lifecycle(gone.listing_id)
    assert record is not None
    overwrite_classification(repository, listing, record)
    read = repository.get_lifecycle(gone.listing_id)
    assert read is not None
    with pytest.raises(StaleRecordError):
        repository.delete_post(gone.listing_id, expected=initial_lifecycle(kept))
    assert repository.get(gone.listing_id) is not None  # nothing deleted
    fresh = make_repository()
    fresh.delete_post(gone.listing_id, expected=read)
    assert fresh.get(gone.listing_id) is None
    assert fresh.get_lifecycle(gone.listing_id) is None
    assert fresh.get_listing(gone.listing_id) is None
    assert fresh.get(kept.listing_id) is not None
    with pytest.raises(KeyError):
        fresh.delete_post(gone.listing_id, expected=read)


def test_delete_post_moves_the_store_generation(tmp_path: Path) -> None:
    repository = SqliteRepository(tmp_path / SQLITE_FILENAME)
    post = make_post(1, "flat one words")
    repository.upsert_with_lifecycle(post, initial_lifecycle(post))
    before = repository.store_generation()
    repository.delete_post(post.listing_id, expected=initial_lifecycle(post))
    assert repository.store_generation() > before


# --- the users' marks deleted with their post (#62) ---


def test_delete_for_listings_deletes_viewed_sent_and_hidden_marks_only(tmp_path: Path) -> None:
    from tlv_hunter.contracts.sent_alert import SENT_ALERT_SCHEMA_VERSION, SentAlert

    userdata = SqliteUserDataStore(tmp_path / SQLITE_FILENAME)
    userdata.create_admin(admin(), new_profile(ADMIN_ID, NOW))
    gone, kept = "a" * 64, "b" * 64
    for listing_id in (gone, kept):
        userdata.mark_viewed(ADMIN_ID, listing_id, NOW)
        userdata.hide(ADMIN_ID, listing_id, NOW)
        userdata.add_sent_alert(
            SentAlert(
                schema_version=SENT_ALERT_SCHEMA_VERSION,
                user_id=ADMIN_ID,
                listing_id=listing_id,
                sent_at=NOW,
            )
        )
    assert userdata.delete_for_listings([gone]) == 3
    assert userdata.viewed_listing_ids(ADMIN_ID) == {kept}
    assert userdata.hidden_listing_ids(ADMIN_ID) == {kept}
    assert userdata.sent_listing_ids(ADMIN_ID) == {kept}
    assert [a.listing_id for a in userdata.list_sent_alerts()] == [kept]
    assert userdata.delete_for_listings([]) == 0


# --- the timed write lock (point 13) ---


def test_a_write_that_waits_for_the_lock_is_logged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    database = tmp_path / SQLITE_FILENAME
    store = SqliteRunStore(database)
    holder = sqlite3.connect(database, autocommit=True, check_same_thread=False)
    holder.execute("BEGIN IMMEDIATE")
    release = threading.Timer(0.3, lambda: holder.execute("COMMIT"))
    monkeypatch.setattr(sqlite_busy, "SLOW_LOCK_SECONDS", 0.1)
    with caplog.at_level(logging.WARNING, logger="tlv_hunter.sqlite_busy"):
        release.start()
        store.add_run(run_record())
    release.join()
    holder.close()
    assert any(
        "sqlite write lock: waited" in r.message and "store.runs" in r.message
        for r in caplog.records
    )


def test_a_lock_never_obtained_is_logged_and_raised(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    database = tmp_path / SQLITE_FILENAME
    SqliteRunStore(database)
    holder = sqlite3.connect(database, autocommit=True)
    holder.execute("BEGIN IMMEDIATE")
    try:
        waiting = sqlite3.connect(database, autocommit=True, timeout=0.1)
        with caplog.at_level(logging.ERROR, logger="tlv_hunter.sqlite_busy"):
            with pytest.raises(sqlite3.OperationalError):
                sqlite_busy.begin_immediate(waiting, "test")
        waiting.close()
    finally:
        holder.execute("ROLLBACK")
        holder.close()
    assert any("database is locked" in r.message for r in caplog.records)
