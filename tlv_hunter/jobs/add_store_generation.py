"""Installs the store generation counter in an existing store, once (DECISIONS.md #301, #316).
Free: no model, no network.

    uv run python -m tlv_hunter.jobs.add_store_generation

The one-time migration of a file laid out before the counter: `store`, `store.listings` and
`userdata` at layout version 1. It copies the store to a dated backup beside it, then in one
transaction creates the `store_generation` table and the counter triggers on `raw_posts`,
`post_lifecycle`, `listings` and `corrections`, and sets those layout rows to version 2; the
statements are the ones a new file gets (`STORE_GENERATION_STATEMENTS` and the others). A module
whose layout row is absent is left alone: its seam lays it out at version 2 when it first opens
the file. It writes no record: it checks after that every stored `RawPost` is identical to the
backup's (invariant 14), and prints the counter.

It refuses a file already migrated, or one at any other version. The seventh store writer, like the
job commands **never run beside them** (#140); the site is not running before it (#331).

Exit codes: 0, migrated; 1, refused or failed.
"""

import argparse
import sqlite3
import sys
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    backup_store,
    describe,
    raw_post_rows,
)
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.store import sqlite as store_sqlite
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata import sqlite as userdata_sqlite

EXIT_DONE, EXIT_FAILED = 0, 1
FROM_VERSION = 1

# (module, the version it migrates to, what that version adds), in the order they run: `store`
# first, since its statements create the counter's table.
MIGRATIONS: tuple[tuple[str, int, tuple[str, ...]], ...] = (
    (
        store_sqlite.LAYOUT_MODULE,
        store_sqlite.LAYOUT_VERSION,
        store_sqlite.STORE_GENERATION_STATEMENTS,
    ),
    (
        store_sqlite.LISTINGS_LAYOUT_MODULE,
        store_sqlite.LISTINGS_LAYOUT_VERSION,
        store_sqlite.LISTINGS_GENERATION_STATEMENTS,
    ),
    (
        userdata_sqlite.LAYOUT_MODULE,
        userdata_sqlite.LAYOUT_VERSION,
        userdata_sqlite.USERDATA_GENERATION_STATEMENTS,
    ),
)


class Refused(Exception):
    """The file is not one this command migrates; nothing was written."""


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.add_store_generation").parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        return _run(config_root, repo_root, clock, out)
    except Refused as refusal:
        print(f"refused: {refusal}; nothing was written", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def _run(config_root: Path, repo_root: Path, clock: Callable[[], datetime], out: TextIO) -> int:
    config = YamlConfig(config_root).collection()
    database = repo_root / config.store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    return migrate(database, clock(), out)


def migrate(database: Path, now: datetime, out: TextIO) -> int:
    """The migration of the file at `database`, after a backup dated `now`; `Refused` before
    anything is written. Tests call it on temporary files; the command on the configured store."""
    before = _layout_rows_read_only(database)
    to_migrate = _plan(before)
    print(f"layout before: {before}", file=out)
    backup = backup_store(database, now)
    print(f"backup: {backup}", file=out)

    connection = sqlite3.connect(database, autocommit=True, timeout=BUSY_TIMEOUT_SECONDS)
    with closing(connection):
        connection.execute("BEGIN IMMEDIATE")
        try:
            # Read again inside the write transaction: nothing may have changed since the plan.
            if _layout_rows(connection) != before:
                raise Refused("the layout changed since it was read")
            for module, version, statements in MIGRATIONS:
                if module not in to_migrate:
                    continue
                for statement in statements:
                    connection.execute(statement)
                connection.execute(
                    "UPDATE layout_version SET version = ? WHERE module = ?", (version, module)
                )
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        connection.execute("COMMIT")
    print(f"migrated: {', '.join(to_migrate)}", file=out)
    print(f"layout after: {_layout_rows_read_only(database)}", file=out)

    identical = raw_post_rows(backup) == raw_post_rows(database)
    print(f"stored RawPost documents identical to the backup's: {identical}", file=out)
    if not identical:
        print("failed: a RawPost differs from the backup; restore the backup", file=out)
        return EXIT_FAILED
    generation = SqliteRepository(database, read_only=True).store_generation()
    print(f"store generation: {generation}", file=out)
    return EXIT_DONE


def _plan(rows: dict[str, int]) -> tuple[str, ...]:
    """The modules to migrate; `Refused` for a file this command does not migrate."""
    store_module = store_sqlite.LAYOUT_MODULE
    if store_module not in rows:
        raise Refused(f"no layout row for module {store_module!r}: not a store")
    if rows[store_module] == store_sqlite.LAYOUT_VERSION:
        raise Refused("the store is already migrated (its generation counter is installed)")
    wrong = {
        module: rows[module]
        for module, _, _ in MIGRATIONS
        if module in rows and rows[module] != FROM_VERSION
    }
    if wrong:
        raise Refused(f"expected layout version {FROM_VERSION}, found {wrong}")
    return tuple(module for module, _, _ in MIGRATIONS if module in rows)


def _layout_rows(connection: sqlite3.Connection) -> dict[str, int]:
    return dict(connection.execute("SELECT module, version FROM layout_version").fetchall())


def _layout_rows_read_only(database: Path) -> dict[str, int]:
    connection = sqlite3.connect(
        f"file:{database.resolve().as_posix()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
    )
    with closing(connection):
        return _layout_rows(connection)


if __name__ == "__main__":
    sys.exit(main())
