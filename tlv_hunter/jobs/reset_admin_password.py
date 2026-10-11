"""Sets a new password for the admin, on the machine (DECISIONS.md #294). Free: no model, no
network.

    uv run python -m tlv_hunter.jobs.reset_admin_password

The fallback for a forgotten admin password: the site's reset needs a signed-in admin, and
`create_admin` refuses once an admin exists. It refuses when there is no admin, before asking
anything. Then it asks for the new password twice with `getpass` (never on the command line, never
printed or logged) and refuses two passwords that differ or one that breaks Gate C's rules. Then it
copies the store to a dated backup beside it, sets the new password through
`actions.reset_admin_password` (final: no change asked at the next sign-in; the failure count back
to 0), ends every session of the admin, and checks that every stored `RawPost` is identical to the
backup's (invariant 14).

It writes the production file, but only the admin's `User` and `Session` records in the `userdata`
tables: a store writer like the job commands, which **never runs beside them**. It reads no key.

Exit codes: 0, the password set; 1, refused or failed.
"""

import argparse
import getpass
import sqlite3
import sys
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from argon2 import PasswordHasher

from tlv_hunter.accounts import actions
from tlv_hunter.accounts.passwords import PRODUCTION_HASHER
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
from tlv_hunter.userdata.sqlite import LAYOUT_MODULE, SqliteUserDataStore

EXIT_DONE, EXIT_FAILED = 0, 1


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> int:
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.reset_admin_password").parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        return _run(config_root, repo_root, clock, out, hasher)
    except actions.Refused as refusal:
        print(f"refused: {refusal.reason}; no password was changed", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def _run(
    config_root: Path,
    repo_root: Path,
    clock: Callable[[], datetime],
    out: TextIO,
    hasher: PasswordHasher,
) -> int:
    config = YamlConfig(config_root).collection()
    database = repo_root / config.store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    # Opening `SqliteUserDataStore` on a store with no userdata tables would create them: a write
    # before the backup, so their absence is read first, read-only, and is "no admin".
    if not _has_userdata_tables(database):
        raise actions.Refused("no_admin")
    store = SqliteUserDataStore(database)
    admin = actions.find_admin(store)
    if admin is None:
        raise actions.Refused("no_admin")
    print(f"admin: {admin.username} (user {admin.user_id})", file=out)

    password = getpass.getpass("New password: ")
    if getpass.getpass("New password again: ") != password:
        print("refused: the two passwords differ; nothing was written", file=out)
        return EXIT_FAILED
    actions.require_new_password(password)

    backup = backup_store(database, clock())
    print(f"backup: {backup}", file=out)
    actions.reset_admin_password(store, password, clock(), hasher=hasher)
    print("password set; every session of the admin ended", file=out)

    identical = raw_post_rows(backup) == raw_post_rows(database)
    print(f"stored RawPost documents identical to the backup's: {identical}", file=out)
    if not identical:
        print("failed: a RawPost differs from the backup; restore the backup", file=out)
        return EXIT_FAILED
    return EXIT_DONE


def _has_userdata_tables(database: Path) -> bool:
    """Whether the `userdata` layout row exists, read-only (`mode=ro`): nothing is created."""
    connection = sqlite3.connect(
        f"file:{database.resolve().as_posix()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
    )
    with closing(connection):
        has_layout = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'layout_version'"
        ).fetchone()
        if has_layout is None:
            return False
        row = connection.execute(
            "SELECT 1 FROM layout_version WHERE module = ?", (LAYOUT_MODULE,)
        ).fetchone()
    return row is not None


if __name__ == "__main__":
    sys.exit(main())
