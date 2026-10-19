"""The retention job (`PHASE_5.md` points 1–4; DECISIONS.md #471; invariant 3). Free: no key.

    python -m tlv_hunter.jobs.retention                            # dry run over the store
    python -m tlv_hunter.jobs.retention --as-of 2026-11-30         # dry run, as if on that day
    python -m tlv_hunter.jobs.retention --database <copy.sqlite3>  # dry run over a dated copy
    python -m tlv_hunter.jobs.retention --apply                    # WRITES, after a dated backup

The rule is `tlv_hunter/retention.py`. **A dry run writes nothing** (the store is opened read-only;
the user-data tables only to read the open reports) and prints what `--apply` would do: the posts
to archive and the photo files that go with them, the posts to delete, the posts kept past 40 days
by an exemption, the orphan photo files. `--apply` takes a dated backup (`backup_store`), then:
1. **archive**, by compare and set (#260): each record as planned, else skipped and counted; the
   photo files after the record is written (a crash leaves orphans, which the sweep finds), never
   a file another record still names;
2. **delete**, each post with its lifecycle record and Listing (`Repository.delete_post`), by
   compare and set, then the users' marks on the deleted posts
   (`UserDataStore.delete_for_listings`) and the post's photo folder;
3. **the orphan sweep**, over the records as they are after 1 and 2.

The photos are read beside the database: `<folder of the database>/images/`. On the server the
scheduler runs this once a night inside the quiet hours: **a dry run until Ron sets
`RETENTION_APPLY=yes`** in the stack's `.env` (#471 C). Never beside another job command (#140).
Exit codes: 0, done; 1, refused or failed.
"""

import argparse
import logging
import shutil
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    backup_store,
    describe,
    job_logging,
    log_failure,
)
from tlv_hunter.retention import (
    IMAGES_DIR,
    Plan,
    archived,
    orphan_files,
    photo_paths,
    plan,
)
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

EXIT_DONE, EXIT_FAILED = 0, 1
LISTED = 40  # posts listed by name in each part of the dry run

logger = logging.getLogger(__name__)


class Refused(Exception):
    pass


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.retention")
    parser.add_argument("--apply", action="store_true", help="write (after a dated backup)")
    parser.add_argument("--database", type=Path, help="plan over this file (a dated copy)")
    parser.add_argument(
        "--as-of", type=date.fromisoformat, metavar="YYYY-MM-DD", help="dry run as if on that day"
    )
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    with job_logging(stream):
        try:
            if args.apply and args.as_of is not None:
                raise Refused("--as-of is for a dry run only")
            database = args.database or (
                repo_root / YamlConfig(config_root).collection().store_root / SQLITE_FILENAME
            )
            if not database.is_file():
                raise Refused(f"no store at {database}")
            now = clock()
            if args.as_of is not None:
                now = datetime.combine(args.as_of, time(12), UTC)
            if args.apply:
                backup = backup_store(database, now)
                logger.info("retention: backup %s", backup.name)
            return run(database, now, apply=args.apply, out=out)
        except Refused as refusal:
            print(f"refused: {refusal}", file=out)
            return EXIT_FAILED
        except Exception as error:
            log_failure(logger, error)
            print(f"failed: {describe(error)}", file=out)
            return EXIT_FAILED


def run(database: Path, now: datetime, *, apply: bool, out: TextIO) -> int:
    store_root = database.parent
    reader = SqliteRepository(database, read_only=True)
    userdata = SqliteUserDataStore(database)
    posts = reader.query()
    lifecycles = {
        post.listing_id: record
        for post in posts
        if (record := reader.get_lifecycle(post.listing_id)) is not None
    }
    open_reports = {report.listing_id for report in userdata.find_reports(status="open")}
    the_plan = plan(posts, lifecycles, open_reports, now)
    if not apply:
        orphans = orphan_files(store_root, photo_paths(lifecycles.values()), now)
        report(the_plan, lifecycles, store_root, orphans, len(posts), database, out)
        return EXIT_DONE
    writer = SqliteRepository(database)
    counts = Counter[str]()
    named = photo_paths(lifecycles.values())
    for group in the_plan.archive:
        for listing_id in (group.canonical, *group.duplicates):
            read = lifecycles[listing_id]
            try:
                writer.save_lifecycle(
                    archived(read, canonical=listing_id == group.canonical), expected=read
                )
            except StaleRecordError:
                counts["archive skipped: changed"] += 1
                continue
            counts["archived" if listing_id == group.canonical else "duplicates cleared"] += 1
            lifecycles[listing_id] = archived(read, canonical=listing_id == group.canonical)
            still_named = photo_paths(lifecycles.values())
            for path in photo_paths([read]) - still_named:
                counts["photo files deleted"] += _unlink(store_root / path)
            named = still_named
    deleted: list[str] = []
    for group in the_plan.delete:
        for listing_id in (*group.duplicates, group.canonical):
            try:
                writer.delete_post(listing_id, expected=lifecycles[listing_id])
            except (StaleRecordError, KeyError):
                counts["delete skipped: changed"] += 1
                continue
            deleted.append(listing_id)
            del lifecycles[listing_id]
            folder = store_root / IMAGES_DIR / listing_id
            if len(listing_id) == 64 and folder.is_dir():
                shutil.rmtree(folder)
    counts["posts deleted"] = len(deleted)
    if deleted:
        counts["user marks deleted"] = userdata.delete_for_listings(deleted)
    named = photo_paths(lifecycles.values())
    for path in orphan_files(store_root, named, now):
        counts["orphan files deleted"] += _unlink(path)
    _remove_empty_folders(store_root / IMAGES_DIR)
    summary = ", ".join(f"{name} {count}" for name, count in sorted(counts.items())) or "nothing"
    logger.info("retention applied: %s", summary)
    print(f"retention applied at {now.isoformat()}: {summary}", file=out)
    return EXIT_DONE


def report(
    the_plan: Plan,
    lifecycles: dict[str, PostLifecycle],
    store_root: Path,
    orphans: list[Path],
    stored: int,
    database: Path,
    out: TextIO,
) -> None:
    """The dry run's text, for Ron to read before any `--apply` (#471 C)."""

    def line(text: str) -> None:
        print(text, file=out)

    named_files = [
        store_root / path
        for listing_id in the_plan.to_clear
        for path in photo_paths([lifecycles[listing_id]])
    ]
    present = [path for path in named_files if path.is_file()]
    line(f"retention DRY RUN over {database} as of {the_plan.now.isoformat()}: writes nothing")
    line(f"{stored} posts stored; the rule: archive at 25 days, delete at 40, from the last")
    line("publication; flagged, reported and open-report posts are never deleted")
    states = Counter(group.state for group in the_plan.archive)
    line(
        f"ARCHIVE: {len(the_plan.archive)} posts (by state now: {dict(sorted(states.items()))}),"
        f" {len(the_plan.to_clear) - len(the_plan.archive)} duplicates with them;"
        f" {len(named_files)} photo entries removed, {len(present)} files on disk,"
        f" {_bytes(present)}"
    )
    _list(the_plan.archive, the_plan.now, line)
    line(
        f"DELETE: {len(the_plan.delete)} posts and {len(the_plan.to_delete) - len(the_plan.delete)}"
        " duplicates, each with its lifecycle record, its Listing and the users' marks on it"
    )
    _list(the_plan.delete, the_plan.now, line)
    reasons = Counter(group.exempt_because for group in the_plan.kept)
    line(f"KEPT past 40 days by an exemption: {len(the_plan.kept)} {dict(sorted(reasons.items()))}")
    _list(the_plan.kept, the_plan.now, line)
    line(f"ORPHAN photo files (no record names them, older than 24 hours): {len(orphans)},")
    line(f"  {_bytes(orphans)}")
    for path in orphans[:LISTED]:
        line(f"  {path.relative_to(store_root).as_posix()}")


def _list(groups, now: datetime, line: Callable[[str], None]) -> None:
    for group in groups[:LISTED]:
        days = (now - group.last_published_at).days
        extra = f", {len(group.duplicates)} duplicates" if group.duplicates else ""
        kept = f", kept: {group.exempt_because}" if group.exempt_because else ""
        line(
            f"  {group.canonical[:12]}  {group.state:<8}  last published "
            f"{group.last_published_at.date().isoformat()} ({days} days){extra}{kept}"
        )
    if len(groups) > LISTED:
        line(f"  … and {len(groups) - LISTED} more")


def _bytes(paths: Sequence[Path]) -> str:
    total = sum(path.stat().st_size for path in paths if path.is_file())
    return f"{total / 1_000_000:.1f} MB"


def _unlink(path: Path) -> int:
    if path.is_file():
        path.unlink()
        return 1
    return 0


def _remove_empty_folders(folder: Path) -> None:
    if not folder.is_dir():
        return
    for child in folder.iterdir():
        if child.is_dir() and not any(child.iterdir()):
            child.rmdir()


if __name__ == "__main__":
    sys.exit(main())
