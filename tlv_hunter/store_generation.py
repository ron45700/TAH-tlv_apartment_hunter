"""The store generation counter (DECISIONS.md #301, #316): one number that every change of a post,
in any process, moves.

A one-row table, `store_generation`, and `AFTER INSERT`, `AFTER UPDATE` and `AFTER DELETE`
triggers that add 1, on `raw_posts`, `post_lifecycle`, `listings` (`store/`) and `corrections`
(`userdata/`). Triggers are part of the database schema, so every writer, in every process, moves
it; the site reads the number to know whether the same-listing grouping must be computed again.
SQLite triggers are row triggers: a write of several rows adds several; only a change of the
number counts.

A plain module like `sqlite_busy.py`, not a seam: the DDL both seams run, for a new file and for
the migration (`jobs/add_store_generation.py`), and the read. The table belongs to neither seam's
records: whichever of `store/` and `userdata/` lays out a file first creates it.
"""

import sqlite3

TABLE = "store_generation"
MIGRATION_COMMAND = "uv run python -m tlv_hunter.jobs.add_store_generation"

CREATE_TABLE = (
    f"CREATE TABLE IF NOT EXISTS {TABLE} ("
    "id INTEGER PRIMARY KEY CHECK (id = 1), generation INTEGER NOT NULL)",
    f"INSERT OR IGNORE INTO {TABLE} (id, generation) VALUES (1, 0)",
)


def triggers(table: str) -> tuple[str, ...]:
    """The three triggers that move the counter on any row change of `table`."""
    return tuple(
        f"CREATE TRIGGER {table}_generation_{event.lower()} AFTER {event} ON {table} "
        f"BEGIN UPDATE {TABLE} SET generation = generation + 1 WHERE id = 1; END"
        for event in ("INSERT", "UPDATE", "DELETE")
    )


def read_generation(conn: sqlite3.Connection) -> int:
    row = conn.execute(f"SELECT generation FROM {TABLE} WHERE id = 1").fetchone()
    if row is None:
        raise RuntimeError(f"no {TABLE} row: migrate with `{MIGRATION_COMMAND}`")
    return int(row[0])


def not_migrated(path: object, module: str, version: int, found: int) -> str:
    """The refusal of a file at the layout before the counter, naming the migration command."""
    return (
        f"{path}: module {module!r} expects layout version {version}, found {found}; the store "
        f"generation counter is not installed: run `{MIGRATION_COMMAND}` (it makes a dated "
        "backup first)"
    )
