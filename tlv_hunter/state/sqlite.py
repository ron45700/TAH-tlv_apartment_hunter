import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from tlv_hunter.contracts.group_watermark import GroupWatermark

# UPSERT with a conflict target (INSERT ... ON CONFLICT(col) DO UPDATE), 3.24.0.
MIN_SQLITE_VERSION = (3, 24, 0)
LAYOUT_MODULE = "state"
LAYOUT_VERSION = 1

_CREATE_LAYOUT_VERSION = (
    "CREATE TABLE IF NOT EXISTS layout_version (module TEXT PRIMARY KEY, version INTEGER NOT NULL)"
)
_CREATE_TABLES = ("CREATE TABLE group_watermarks (group_id TEXT PRIMARY KEY, doc TEXT NOT NULL)",)


class SqliteWatermarkStore:
    """GroupWatermark records in the same SQLite file as the store; one JSON document per group.

    Datetimes live inside the documents, serialized and validated by the pydantic model; none is
    passed to sqlite3 as a parameter. One connection per operation.
    """

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

    def get(self, group_id: str) -> GroupWatermark | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT doc FROM group_watermarks WHERE group_id = ?", (group_id,)
            ).fetchone()
        return None if row is None else GroupWatermark.model_validate_json(row[0])

    def get_all(self) -> list[GroupWatermark]:
        with self._connect() as conn:
            rows = conn.execute("SELECT doc FROM group_watermarks ORDER BY group_id").fetchall()
        return [GroupWatermark.model_validate_json(doc) for (doc,) in rows]

    def save_all(self, records: Sequence[GroupWatermark]) -> None:
        group_ids = [record.group_id for record in records]
        if len(set(group_ids)) != len(group_ids):
            raise ValueError(f"duplicate group_id in one save: {group_ids}")
        with self._transaction() as conn:
            for record in records:
                conn.execute(
                    "INSERT INTO group_watermarks (group_id, doc) VALUES (?, ?) "
                    "ON CONFLICT (group_id) DO UPDATE SET doc = excluded.doc",
                    (record.group_id, record.model_dump_json()),
                )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path, autocommit=True)
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            conn.execute("COMMIT")
