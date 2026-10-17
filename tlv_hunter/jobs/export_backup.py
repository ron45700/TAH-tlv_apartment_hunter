"""Exports a dated backup of the store out of the Docker volume (`PHASE_3.md` 3.9 (g); DECISIONS.md
#424, point 93). Free: no model, no network.

    docker compose run --rm jobs python -m tlv_hunter.jobs.export_backup               # the laptop
    docker compose run --rm jobs python -m tlv_hunter.jobs.export_backup --no-photos  # the server

Run by hand after each working session, until Phase 5's scheduler: the volume can be deleted by
`docker compose down -v` or by Docker Desktop's "Purge data", and the export is the copy that
lives outside it. It takes a fresh dated backup beside the store (`jobs.common.backup_store`:
SQLite's online backup, checked for integrity and for the same `RawPost` rows, so the site may run
beside it), then copies that file into `data/store_exports/` (a folder of the machine, bind-mounted
into the `jobs` container) and checks the export hashes like the backup. It overwrites nothing:
an export of the same name refuses, and the backup stays in the volume. Then the photos
(DECISIONS.md #427, point 99): every file under `<store_root>/images/` that is not yet in
`data/store_exports/images/` is copied there and checked by its hash. A photo never changes once
written, so one already exported is left as it is: the export never overwrites and never deletes a
photo. **`--no-photos`** (the server, DECISIONS.md #446, amending #427 point 99) exports none: the
server's backups hold the database only. **The 7 newest exports are kept** (DECISIONS.md #447): once
the new export is checked, older dated exports in `data/store_exports/` are deleted, as
`backup_store` does for the backups beside the store; no other file there is touched.

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
    BACKUPS_KEPT,
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    backup_store,
    describe,
    prune_backups,
    sha256_file,
)

EXIT_DONE, EXIT_FAILED = 0, 1
EXPORTS_DIR = Path("data") / "store_exports"
IMAGES_DIR = "images"


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.export_backup")
    parser.add_argument(
        "--no-photos",
        action="store_true",
        help="export the database only (the server, DECISIONS.md #446)",
    )
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        database = repo_root / YamlConfig(config_root).collection().store_root / SQLITE_FILENAME
        if not database.is_file():
            raise FileNotFoundError(f"no store at {database}")
        export(database, repo_root / EXPORTS_DIR, clock(), out, photos=not args.no_photos)
        return EXIT_DONE
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def export(
    database: Path, exports: Path, now: datetime, out: TextIO, *, photos: bool = True
) -> Path:
    """A fresh dated backup of `database`, copied into `exports`; nothing overwritten; the older
    exports beyond the 7 newest deleted once it is checked."""
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
    for old in prune_backups(target, database.stem, database.suffix):
        print(f"old export deleted ({BACKUPS_KEPT} newest kept): {old.name}", file=out)
    kept_backups = len(list(backup.parent.glob(f"{database.stem}.*.backup{database.suffix}")))
    print(f"backups beside the store: {kept_backups} (at most {BACKUPS_KEPT} kept)", file=out)
    if not photos:
        print("photos: not exported (--no-photos)", file=out)
        return target
    new, kept = export_photos(database.parent / IMAGES_DIR, exports / IMAGES_DIR)
    print(f"photos: {new} new exported, {kept} already there (left as they are)", file=out)
    return target


def export_photos(images: Path, exported: Path) -> tuple[int, int]:
    """Every photo file under `images` not yet under `exported`, copied there and checked by its
    hash; a file already exported is left as it is. Returns (new, already there)."""
    new = kept = 0
    files = sorted(path for path in images.rglob("*") if path.is_file()) if images.is_dir() else []
    for photo in files:
        target = exported / photo.relative_to(images)
        if target.exists():
            kept += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(photo, target)
        if sha256_file(target) != sha256_file(photo):
            raise RuntimeError(f"the exported photo {target} does not hash like {photo}")
        new += 1
    return new, kept


if __name__ == "__main__":
    sys.exit(main())
