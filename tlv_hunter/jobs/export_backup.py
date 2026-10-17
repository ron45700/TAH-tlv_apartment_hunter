"""Exports a dated backup of the store out of the Docker volume (`PHASE_3.md` 3.9 (g); DECISIONS.md
#424, point 93). Free: no model, no network.

    docker compose run --rm jobs python -m tlv_hunter.jobs.export_backup

Run by hand after each working session, until Phase 5's scheduler: the volume can be deleted by
`docker compose down -v` or by Docker Desktop's "Purge data", and the export is the copy that
lives outside it. It takes a fresh dated backup beside the store (`jobs.common.backup_store`:
SQLite's online backup, checked for integrity and for the same `RawPost` rows, so the site may run
beside it), then copies that file into `data/store_exports/` (a folder of the machine, bind-mounted
into the `jobs` container) and checks the export hashes like the backup. It overwrites nothing:
an export of the same name refuses, and the backup stays in the volume. The database only: the
photos stay in the volume.

Exit codes: 0, exported; 1, refused or failed.
"""

import argparse
import shutil
import sys
from collections.abc import Callable, Sequence
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
    sha256_file,
)

EXIT_DONE, EXIT_FAILED = 0, 1
EXPORTS_DIR = Path("data") / "store_exports"


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.export_backup").parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        database = repo_root / YamlConfig(config_root).collection().store_root / SQLITE_FILENAME
        if not database.is_file():
            raise FileNotFoundError(f"no store at {database}")
        export(database, repo_root / EXPORTS_DIR, clock(), out)
        return EXIT_DONE
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def export(database: Path, exports: Path, now: datetime, out: TextIO) -> Path:
    """A fresh dated backup of `database`, copied into `exports`; nothing overwritten."""
    backup = backup_store(database, now)
    backup_sha = sha256_file(backup)
    print(f"backup: {backup} (SHA-256 {backup_sha})", file=out)
    exports.mkdir(parents=True, exist_ok=True)
    target = exports / backup.name
    if target.exists():
        raise FileExistsError(f"{target} exists: not overwritten (the backup stays in the volume)")
    shutil.copy2(backup, target)
    if sha256_file(target) != backup_sha:
        raise RuntimeError(f"the export {target} does not hash like the backup")
    print(f"exported: {target} (SHA-256 {backup_sha}, the backup's)", file=out)
    return target


if __name__ == "__main__":
    sys.exit(main())
