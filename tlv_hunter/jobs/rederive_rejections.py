"""Re-derives the stored rejections with the native-location rule (DECISIONS.md #214). Free: no
model, no network.

    uv run python -m tlv_hunter.jobs.rederive_rejections              # dry run: writes nothing
    uv run python -m tlv_hunter.jobs.rederive_rejections --apply --allow 2bac260c,26e8a28b,7d467bbe

The dry run lists every post whose state or reason would change, and the counts before and after.
`--apply` needs `--allow`, the id prefixes (at least 8 characters) of exactly the posts the dry run
shows: any other difference refuses it, with nothing written. Then it copies the store to a dated
backup beside it (its path and SHA-256 are printed, and the copy must hash the same), re-reads each
record right before writing it, writes only `state` and `rejection_reason` through
`save_lifecycle`, and checks that every stored `RawPost` is identical to the backup's
(invariant 14).

This is the third command that writes the production store, with `run_once` and `classify_pending`.
**It does not check that they are not running** (none of them takes a lock, DECISIONS.md #79 O9,
#140): never start it beside either. What it does instead is the optimistic check above: a record
that no longer holds the status the plan saw is not written, and the command fails.

Exit codes: 0, done (a dry run included); 1, refused or failed.
"""

import argparse
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
    raw_post_rows,
    sha256_file,
)
from tlv_hunter.postmodel.rederive import Plan, plan_rederivation, rederived_lifecycle
from tlv_hunter.store.sqlite import SqliteRepository

EXIT_DONE, EXIT_FAILED = 0, 1
MIN_PREFIX = 8


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.rederive_rejections")
    parser.add_argument("--apply", action="store_true", help="write the changes (needs --allow)")
    parser.add_argument(
        "--allow", default="", help="comma-separated id prefixes of the posts to change"
    )
    args = parser.parse_args(argv)
    if stream is None:
        # A city name is Hebrew: a Windows console's code page cannot print it.
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    out = sys.stdout if stream is None else stream
    try:
        return _run(args.apply, args.allow, config_root, repo_root, clock, out)
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def _run(
    apply: bool,
    allow: str,
    config_root: Path,
    repo_root: Path,
    clock: Callable[[], datetime],
    out: TextIO,
) -> int:
    config = YamlConfig(config_root).collection()
    database = repo_root / config.store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    plan = plan_rederivation(SqliteRepository(database, read_only=True))
    _print_plan(plan, out)
    if not apply:
        print("dry run: nothing written", file=out)
        return EXIT_DONE

    prefixes = [part.strip() for part in allow.split(",") if part.strip()]
    if not prefixes:
        print("refused: --apply needs --allow", file=out)
        return EXIT_FAILED
    if any(len(prefix) < MIN_PREFIX for prefix in prefixes):
        print(f"refused: an --allow prefix needs at least {MIN_PREFIX} characters", file=out)
        return EXIT_FAILED
    allowed = {
        change.listing_id for change in plan.changes if _matches(change.listing_id, prefixes)
    }
    unmatched = [p for p in prefixes if not any(c.listing_id.startswith(p) for c in plan.changes)]
    beyond = sorted(c.listing_id[:12] for c in plan.changes if c.listing_id not in allowed)
    if unmatched or beyond:
        print(
            f"refused: the plan and --allow differ. Not in the plan: {unmatched or 'none'}. "
            f"Not allowed: {beyond or 'none'}. Nothing was written.",
            file=out,
        )
        return EXIT_FAILED
    if not plan.changes:
        print("nothing to change", file=out)
        return EXIT_DONE

    backup = backup_store(database, clock())
    print(f"backup: {backup}", file=out)
    print(f"backup SHA-256: {sha256_file(backup)} (the store's, before: the same)", file=out)

    repository = SqliteRepository(database)
    for change in plan.changes:
        record = repository.get_lifecycle(change.listing_id)
        post = repository.get(change.listing_id)
        listing = repository.get_listing(change.listing_id)
        if record is None or post is None or listing is None:
            raise RuntimeError(f"{change.listing_id}: record, post or Listing vanished")
        if (record.state, record.rejection_reason) != change.old:
            raise RuntimeError(
                f"{change.listing_id}: the record changed since the plan; not written"
            )
        repository.save_lifecycle(rederived_lifecycle(record, listing, post))
        print(
            f"written: {change.listing_id[:12]} {_status(change.old)} -> {_status(change.new)}",
            file=out,
        )

    identical = raw_post_rows(backup) == raw_post_rows(database)
    print(f"stored RawPost documents identical to the backup's: {identical}", file=out)
    print(f"store SHA-256 after: {sha256_file(database)}", file=out)
    if not identical:
        print("failed: a RawPost differs from the backup; restore the backup", file=out)
        return EXIT_FAILED
    _print_plan(
        plan_rederivation(SqliteRepository(database, read_only=True)), out, after_write=True
    )
    return EXIT_DONE


def _matches(listing_id: str, prefixes: Sequence[str]) -> bool:
    return any(listing_id.startswith(prefix) for prefix in prefixes)


def _status(status: tuple[str, str | None]) -> str:
    return status[0] if status[1] is None else f"{status[0]}: {status[1]}"


def _print_plan(plan: Plan, out: TextIO, *, after_write: bool = False) -> None:
    label = "after the write" if after_write else "plan"
    print(
        f"{label}: {plan.considered} model-classified posts considered, "
        f"{plan.native_present} with a usable native locality, {len(plan.changes)} change",
        file=out,
    )
    for change in plan.changes:
        city = f" (locality: {change.locality})" if change.locality else ""
        print(
            f"  {change.listing_id[:12]}: {_status(change.old)} -> {_status(change.new)}{city}",
            file=out,
        )
    keys = sorted(set(plan.before) | set(plan.after), key=str)
    for key in keys:
        print(
            f"  {_status(key):22} {plan.before.get(key, 0):4} -> {plan.after.get(key, 0):4}",
            file=out,
        )


if __name__ == "__main__":
    sys.exit(main())
