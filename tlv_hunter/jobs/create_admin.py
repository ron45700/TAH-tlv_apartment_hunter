"""Creates the one admin, on the machine (DECISIONS.md #244, #290). Free: no model, no network.

    uv run python -m tlv_hunter.jobs.create_admin

Asks for the username, then the password twice with `getpass` (never on the command line, never
printed or logged). It refuses a username or password that breaks Gate C's rules, two passwords
that differ, and an existing admin. Then it copies the store to a dated backup beside it, writes
the admin and their profile through `UserDataStore.create_admin`, and checks that every stored
`RawPost` is identical to the backup's (invariant 14).

It writes the production file, but only the `userdata` tables (created on its first open): a store
writer like the job commands, which **never runs beside them**. It reads no key.

Exit codes: 0, the admin created; 1, refused or failed.
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence
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
from tlv_hunter.userdata.base import AdminExists
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

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
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.create_admin").parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        return _run(config_root, repo_root, clock, out, hasher)
    except actions.Refused as refusal:
        print(f"refused: {refusal.reason}; no user was written", file=out)
        return EXIT_FAILED
    except AdminExists:
        print("refused: there is already an admin (#244); no user was written", file=out)
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

    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")
    if getpass.getpass("Password again: ") != password:
        print("refused: the two passwords differ; nothing was written", file=out)
        return EXIT_FAILED
    actions.require_new_credentials(username, password)

    backup = backup_store(database, clock())
    print(f"backup: {backup}", file=out)
    store = SqliteUserDataStore(database)
    admin = actions.create_admin(store, username, password, clock(), hasher=hasher)
    print(f"admin created: {admin.username} (user {admin.user_id})", file=out)

    identical = raw_post_rows(backup) == raw_post_rows(database)
    print(f"stored RawPost documents identical to the backup's: {identical}", file=out)
    if not identical:
        print("failed: a RawPost differs from the backup; restore the backup", file=out)
        return EXIT_FAILED
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
