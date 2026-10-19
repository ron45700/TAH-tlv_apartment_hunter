"""Gate G's records (DECISIONS.md #472; `PHASE_5.md` point 5): `RunRecord` and `ScheduleSettings`,
in the same SQLite file as `store/`, `state/` and `userdata/`, with their own tables and their own
layout row `store.runs` (version 1), created when absent, as Gate F's `userdata.telegram`: no
migration command, and an older image still opens the file (every opener reads only its own rows).

Writers, each by compare and set where two could meet (#260): `run_once` (a run's record),
`settle_costs` (its cost), the site (the settings, "run now"), the bot (`last_digest_at` only), the
scheduler (the settings' first row, from its `.env`). They move no store generation counter: the
site groups on none of them. Records of runs are never deleted (a few dozen a day).
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from tlv_hunter.contracts.run_record import RunRecord
from tlv_hunter.contracts.schedule_settings import ScheduleSettings
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS, begin_immediate
from tlv_hunter.store.base import StaleRecordError

MIN_SQLITE_VERSION = (3, 24, 0)
LAYOUT_MODULE = "store.runs"
LAYOUT_VERSION = 1
SETTINGS_ID = "schedule"

_CREATE_LAYOUT_VERSION = (
    "CREATE TABLE IF NOT EXISTS layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)"
)
_CREATE_TABLES = (
    "CREATE TABLE run_records (run_id TEXT PRIMARY KEY, doc TEXT NOT NULL)",
    "CREATE TABLE schedule_settings (id TEXT PRIMARY KEY, doc TEXT NOT NULL)",
)


class SqliteRunStore:
    """One connection per operation; every write in `BEGIN IMMEDIATE`. Datetimes live inside the
    documents; none is passed to sqlite3 as a parameter. Runs are listed in insertion order
    (`rowid`), which is the order they started: one run at a time (#140)."""

    def __init__(self, path: Path) -> None:
        if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
            raise RuntimeError(
                f"SQLite {sqlite3.sqlite_version} is too old; module {LAYOUT_MODULE!r} needs "
                f"{'.'.join(map(str, MIN_SQLITE_VERSION))} or later"
            )
        self._path = Path(path)
        with self._transaction() as conn:
            conn.execute(_CREATE_LAYOUT_VERSION)
            row = conn.execute(
                "SELECT version FROM layout_version WHERE module = ?", (LAYOUT_MODULE,)
            ).fetchone()
            if row is None:
                for statement in _CREATE_TABLES:
                    conn.execute(statement)
                conn.execute(
                    "INSERT INTO layout_version (module, version) VALUES (?, ?)",
                    (LAYOUT_MODULE, LAYOUT_VERSION),
                )
            elif row[0] != LAYOUT_VERSION:
                raise RuntimeError(
                    f"{self._path}: module {LAYOUT_MODULE!r} expects layout version "
                    f"{LAYOUT_VERSION}, found {row[0]}; no automatic migration"
                )

    # --- runs ---

    def add_run(self, record: RunRecord) -> RunRecord:
        """A new run's record; a `run_id` already stored raises `sqlite3.IntegrityError`."""
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO run_records (run_id, doc) VALUES (?, ?)",
                (record.run_id, record.model_dump_json()),
            )
        return record

    def save_run(self, record: RunRecord, *, expected: RunRecord) -> RunRecord:
        """Compare and set against the record the writer read; `StaleRecordError` otherwise."""
        if record.run_id != expected.run_id:
            raise ValueError("a run's id never changes")
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM run_records WHERE run_id = ?", (record.run_id,)
            ).fetchone()
            if row is None or RunRecord.model_validate_json(row[0]) != expected:
                raise StaleRecordError(record.run_id)
            conn.execute(
                "UPDATE run_records SET doc = ? WHERE run_id = ?",
                (record.model_dump_json(), record.run_id),
            )
        return record

    def get_run(self, run_id: str) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT doc FROM run_records WHERE run_id = ?", (run_id,)).fetchone()
        return None if row is None else RunRecord.model_validate_json(row[0])

    def recent_runs(self, limit: int | None = None) -> list[RunRecord]:
        """The newest first; all of them when `limit` is `None`."""
        sql = "SELECT doc FROM run_records ORDER BY rowid DESC"
        params: tuple[int, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (limit,)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [RunRecord.model_validate_json(doc) for (doc,) in rows]

    # --- the schedule ---

    def get_settings(self) -> ScheduleSettings | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc FROM schedule_settings WHERE id = ?", (SETTINGS_ID,)
            ).fetchone()
        return None if row is None else ScheduleSettings.model_validate_json(row[0])

    def save_settings(
        self, record: ScheduleSettings, *, expected: ScheduleSettings | None
    ) -> ScheduleSettings:
        """Compare and set; `expected=None` writes only when there is no row yet."""
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM schedule_settings WHERE id = ?", (SETTINGS_ID,)
            ).fetchone()
            stored = None if row is None else ScheduleSettings.model_validate_json(row[0])
            if stored != expected:
                raise StaleRecordError(SETTINGS_ID)
            conn.execute(
                "INSERT INTO schedule_settings (id, doc) VALUES (?, ?) "
                "ON CONFLICT (id) DO UPDATE SET doc = excluded.doc",
                (SETTINGS_ID, record.model_dump_json()),
            )
        return record

    def set_last_digest(self, at: datetime) -> bool:
        """The bot's one write: `last_digest_at` on the stored row, in one transaction, whatever
        else changed meanwhile. `False` when there is no row (nothing written)."""
        with self._transaction() as conn:
            row = conn.execute(
                "SELECT doc FROM schedule_settings WHERE id = ?", (SETTINGS_ID,)
            ).fetchone()
            if row is None:
                return False
            stored = ScheduleSettings.model_validate_json(row[0])
            updated = ScheduleSettings.model_validate({**stored.model_dump(), "last_digest_at": at})
            conn.execute(
                "UPDATE schedule_settings SET doc = ? WHERE id = ?",
                (updated.model_dump_json(), SETTINGS_ID),
            )
        return True

    # --- plumbing ---

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, autocommit=True, timeout=BUSY_TIMEOUT_SECONDS)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            begin_immediate(conn, LAYOUT_MODULE)
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
