"""Moves the store into the Docker volume, once (`PHASE_3.md` 3.9 (f); DECISIONS.md #416). Free:
no model, no network.

    docker compose run --rm -v ./data/store:/import:ro jobs python -m tlv_hunter.jobs.move_store

The Windows store is mounted read-only at `/import` (`--source` names another folder); the target
is the configured store root, `/app/data/store` in the container: the volume. It refuses when the
source has no store, when the target already holds one or any of the copied folders with files in
them, and when a rollback journal lies beside the source (something may be writing it). Then:

1. the database by SQLite's online backup from a read-only connection (`jobs.common.online_copy`);
2. the folders `images/`, `classify_runs/` and `reclassify/`, file by file (the old dated backups
   and the site's copies stay where they are);
3. the checks, each printed: `PRAGMA integrity_check` is `ok`; the `RawPost` rows equal the
   source's; every table's row count equal; the store generation and the layout versions equal;
   every copied file's SHA-256 equal; the source's SHA-256 unchanged.

It writes nothing in the source, so **the source is itself the backup**. A check that fails leaves
the copy in place for inspection and says so; the next run refuses, since the target then holds a
store. The eighth store writer; like the other job commands it is **never run beside them** (#140),
and the site is not running (3.9 (f), step 1 of the move).

Exit codes: 0, moved and every check passed; 1, refused, failed, or a check failed.
"""

import argparse
import shutil
import sqlite3
import sys
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    describe,
    integrity_ok,
    online_copy,
    raw_post_rows,
    sha256_file,
)
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.store_generation import TABLE as GENERATION_TABLE

EXIT_DONE, EXIT_FAILED = 0, 1
DEFAULT_SOURCE = Path("/import")
COPIED_FOLDERS = ("images", "classify_runs", "reclassify")


class Refused(Exception):
    """Nothing to move, or a target that already holds a store; nothing was written."""


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.move_store")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        target_root = repo_root / YamlConfig(config_root).collection().store_root
        return move(args.source, target_root, out)
    except Refused as refusal:
        print(f"refused: {refusal}; nothing was written", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def move(source_root: Path, target_root: Path, out: TextIO) -> int:
    """The store under `source_root` copied into `target_root` and checked; `Refused` before
    anything is written. Tests call it on temporary folders; the command on `/import` and the
    volume."""
    source = source_root / SQLITE_FILENAME
    target = target_root / SQLITE_FILENAME
    _refuse_unless_movable(source_root, target_root)
    source_sha = sha256_file(source)
    print(f"source: {source} (SHA-256 {source_sha})", file=out)

    target_root.mkdir(parents=True, exist_ok=True)
    online_copy(source, target)
    print(f"copied the database: {target}", file=out)
    copied = 0
    for folder in COPIED_FOLDERS:
        if (source_root / folder).is_dir():
            shutil.copytree(source_root / folder, target_root / folder, dirs_exist_ok=True)
            copied += len(_files(source_root / folder))
    print(f"copied {copied} files from {', '.join(COPIED_FOLDERS)}", file=out)

    source_counts, target_counts = _row_counts(source), _row_counts(target)
    print(f"row counts: {target_counts}", file=out)
    checks = (
        ("integrity check ok", integrity_ok(target)),
        ("RawPost rows identical", raw_post_rows(target) == raw_post_rows(source)),
        ("every table's row count identical", target_counts == source_counts),
        ("store generation identical", _same_rows(source, target, GENERATION_TABLE)),
        ("layout versions identical", _same_rows(source, target, "layout_version")),
        ("every copied file identical", _file_hashes(target_root) == _file_hashes(source_root)),
        ("source unchanged", sha256_file(source) == source_sha),
    )
    for name, passed in checks:
        print(f"check: {name}: {passed}", file=out)
    if all(passed for _, passed in checks):
        print(f"moved: the store is in {target_root}; the source was not changed", file=out)
        return EXIT_DONE
    print(
        f"failed: a check did not pass; the copy is left in {target_root} for inspection, "
        "and the source was not changed",
        file=out,
    )
    return EXIT_FAILED


def _refuse_unless_movable(source_root: Path, target_root: Path) -> None:
    source = source_root / SQLITE_FILENAME
    if not source.is_file():
        raise Refused(f"no store at {source}")
    if source.with_name(source.name + "-journal").exists():
        raise Refused(f"a rollback journal lies beside {source}: is something writing it?")
    if (target_root / SQLITE_FILENAME).exists():
        raise Refused(f"{target_root} already holds a store")
    for folder in COPIED_FOLDERS:
        if _files(target_root / folder):
            raise Refused(f"{target_root / folder} already holds files")


def _files(folder: Path) -> list[Path]:
    return sorted(path for path in folder.rglob("*") if path.is_file()) if folder.is_dir() else []


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for folder in COPIED_FOLDERS
        for path in _files(root / folder)
    }


def _read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(
        f"file:{path.resolve().as_posix()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
    )


def _row_counts(path: Path) -> dict[str, int]:
    with closing(_read_only(path)) as connection:
        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        return {
            table: connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in tables
        }


def _same_rows(source: Path, target: Path, table: str) -> bool:
    return _rows(source, table) == _rows(target, table)


def _rows(path: Path, table: str) -> list[tuple] | None:
    """Every row of `table` in a fixed order, or None when the file has no such table."""
    with closing(_read_only(path)) as connection:
        present = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
        ).fetchone()
        if present is None:
            return None
        return connection.execute(f'SELECT * FROM "{table}" ORDER BY 1').fetchall()


if __name__ == "__main__":
    sys.exit(main())
