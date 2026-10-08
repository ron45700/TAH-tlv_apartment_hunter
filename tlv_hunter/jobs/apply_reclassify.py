"""Reclassify, stage 2 (task 2.9; DECISIONS.md #217–#222). Replaces the `Listing`s of the posts Ron
names, from a finished `reclassify --run`. Free: no model, no key, no network.

    uv run python -m tlv_hunter.jobs.apply_reclassify <run_id>                 # dry run
    uv run python -m tlv_hunter.jobs.apply_reclassify <run_id> --apply --allow 2bac260c,26e8a28b
    uv run python -m tlv_hunter.jobs.apply_reclassify <run_id> --apply --allow-file <path> [...]

There is no "apply all": `--apply` needs `--allow` (id prefixes of 8 characters or more) and/or
`--allow-file` (the lists `reclassify --run` wrote, or Ron's own: one id or prefix per line, `#`
lines and blank lines ignored). Every entry must match a post of that run that has a new
`Listing`.

It refuses a run whose report is not complete, and one made for another prompt than the code's.
Then it copies the store to a dated backup beside it (its path and SHA-256 are printed, and the
copy must hash the same), reads each post again right before its write, and writes `Listing` and
record in one transaction. A post that is no longer what the run saw is not written and is listed.
Afterwards it checks that every stored `RawPost` is identical to the backup's (invariant 14).

This is the fourth command that writes the production store (#220). **It takes no lock** (#140):
never run it beside `run_once`. The names #162 and #180 dropped go to
`<store_root>/classify_runs/<apply run id>.jsonl`, for the applied posts only.

Exit codes: 0, done (a dry run included); 2, done, but at least one named post was not written; 1,
refused or failed."""

import argparse
import logging
import re
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.classify.instructions import MODEL_NAME, PROMPT_FINGERPRINT, PROMPT_VERSION
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.listing import LISTING_SCHEMA_VERSION
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    append_dropped_names,
    backup_store,
    describe,
    job_logging,
    raw_post_rows,
    sha256_file,
)
from tlv_hunter.postmodel.reclassify import (
    MIN_PREFIX,
    RECLASSIFY_DIRECTORY,
    Proposal,
    select,
    status_text,
)
from tlv_hunter.postmodel.reclassify_report import RunRefused, read_allow_file, read_finished_run
from tlv_hunter.reclassification_run import apply_proposals
from tlv_hunter.store.sqlite import SqliteRepository

EXIT_DONE, EXIT_FAILED, EXIT_NOT_ALL = 0, 1, 2
RUNS_DIRECTORY = "classify_runs"
_RUN_ID = re.compile(r"[0-9a-f]{12}")

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
    log_stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.apply_reclassify")
    parser.add_argument("run_id", help="a folder under <store_root>/reclassify/")
    parser.add_argument("--apply", action="store_true", help="write the store (needs --allow)")
    parser.add_argument("--allow", default="", help="comma-separated id prefixes (8 or more)")
    parser.add_argument(
        "--allow-file", nargs="+", default=[], type=Path, help="list files, one id per line"
    )
    args = parser.parse_args(argv)
    if stream is None:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    out = sys.stdout if stream is None else stream
    with job_logging(log_stream) as apply_run_id:
        try:
            return _run(args, apply_run_id, config_root, repo_root, clock, out)
        except Exception as error:
            print(f"failed: {describe(error)}", file=out)
            return EXIT_FAILED


def _run(
    args: argparse.Namespace,
    apply_run_id: str,
    config_root: Path,
    repo_root: Path,
    clock: Callable[[], datetime],
    out: TextIO,
) -> int:
    if not _RUN_ID.fullmatch(args.run_id):
        print("refused: a run id is 12 hexadecimal characters", file=out)
        return EXIT_FAILED
    config = YamlConfig(config_root).collection()
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        print(f"refused: no store at {database}", file=out)
        return EXIT_FAILED
    try:
        run = read_finished_run(store_root / RECLASSIFY_DIRECTORY / args.run_id)
    except RunRefused as error:
        print(f"refused: {error}", file=out)
        return EXIT_FAILED
    if run.summary.prompt_fingerprint != PROMPT_FINGERPRINT:
        print(
            "refused: the run was made for another prompt than the code's "
            f"({run.summary.prompt_fingerprint[:8]} against {PROMPT_FINGERPRINT[:8]})",
            file=out,
        )
        return EXIT_FAILED

    entries = [part.strip() for part in args.allow.split(",") if part.strip()]
    try:
        for path in args.allow_file:
            entries.extend(read_allow_file(path))
    except OSError as error:
        print(f"refused: {error}", file=out)
        return EXIT_FAILED
    chosen = _choose(run.proposals, entries, out)
    if chosen is None:
        return EXIT_FAILED

    _print_run(run.summary.run_id, run.proposals, chosen if entries else None, out)
    if not args.apply:
        print("dry run: nothing written", file=out)
        return EXIT_DONE
    if not entries:
        print("refused: --apply needs --allow or --allow-file", file=out)
        return EXIT_FAILED

    backup = backup_store(database, clock())
    logger.info(
        "apply start: reclassify run %s, %d posts named, backup %s",
        args.run_id,
        len(chosen),
        backup,
    )
    print(f"backup: {backup}", file=out)
    print(f"backup SHA-256: {sha256_file(backup)} (the store's, before: the same)", file=out)

    names_path = store_root / RUNS_DIRECTORY / f"{apply_run_id}.jsonl"
    repository = SqliteRepository(database)
    outcomes = apply_proposals(
        repository=repository,
        proposals=chosen,
        on_written=lambda p: append_dropped_names(
            names_path,
            listing_id=p.listing_id,
            prompt_version=p.new.listing.prompt_version,  # type: ignore[union-attr]
            streets=p.dropped.streets,
            area_names=p.dropped.area_names,
            other_city=p.dropped.other_city,
        ),
    )
    not_written = 0
    for outcome in outcomes:
        if outcome.result == "written":
            print(
                f"written: {outcome.listing_id[:12]} {status_text(outcome.old_status)} -> "
                f"{status_text(outcome.new_status)}",
                file=out,
            )
        elif outcome.result == "already applied":
            print(f"already applied: {outcome.listing_id[:12]}", file=out)
        else:
            not_written += 1
            print(f"NOT written: {outcome.listing_id[:12]}: {outcome.reason}", file=out)

    logger.info(
        "apply done: %d written, %d already applied, %d not written",
        sum(o.result == "written" for o in outcomes),
        sum(o.result == "already applied" for o in outcomes),
        not_written,
    )
    identical = raw_post_rows(backup) == raw_post_rows(database)
    print(f"stored RawPost documents identical to the backup's: {identical}", file=out)
    print(f"store SHA-256 after: {sha256_file(database)}", file=out)
    if not identical:
        print("failed: a RawPost differs from the backup; restore the backup", file=out)
        return EXIT_FAILED
    current = (PROMPT_VERSION, LISTING_SCHEMA_VERSION, MODEL_NAME)
    left = len(select(SqliteRepository(database, read_only=True), current).selected)
    print(f"still selected for reclassify, any run: {left}", file=out)
    return EXIT_NOT_ALL if not_written else EXIT_DONE


def _choose(
    proposals: Sequence[Proposal], entries: Sequence[str], out: TextIO
) -> list[Proposal] | None:
    """The proposals named by `entries`: every entry must match a proposal that has a new
    `Listing`. None, after printing why, when one does not (nothing is written then)."""
    problems = []
    chosen: dict[str, Proposal] = {}
    for entry in dict.fromkeys(entries):
        if len(entry) < MIN_PREFIX:
            problems.append(f"{entry!r}: a prefix needs at least {MIN_PREFIX} characters")
            continue
        matches = [p for p in proposals if p.listing_id.startswith(entry)]
        if not matches:
            problems.append(f"{entry}: matches no post of this run")
        elif all(p.new is None for p in matches):
            problems.append(f"{entry}: the run has no new Listing for it (it failed)")
        for p in matches:
            if p.new is not None:
                chosen[p.listing_id] = p
    if problems:
        print("refused: " + "; ".join(problems) + ". Nothing was written.", file=out)
        return None
    return sorted(chosen.values(), key=lambda p: p.listing_id)


def _print_run(
    run_id: str, proposals: Sequence[Proposal], chosen: Sequence[Proposal] | None, out: TextIO
) -> None:
    shown = proposals if chosen is None else chosen
    scope = "all the proposals (no --allow)" if chosen is None else f"{len(shown)} named"
    print(f"run {run_id}: {len(proposals)} proposals; showing {scope}", file=out)
    for p in sorted(shown, key=lambda p: p.listing_id):
        if p.new is None:
            print(f"  {p.listing_id[:12]}: failed ({p.error})", file=out)
            continue
        flag = "  [flagged: record kept]" if p.old.flagged else ""
        reviewed = "  [reviewed by Ron]" if p.reviewed else ""
        print(
            f"  {p.listing_id[:12]}: {status_text(p.old_status)} -> {status_text(p.new_status)}; "
            f"{len(p.fields_changed)} fields changed{flag}{reviewed}",
            file=out,
        )


if __name__ == "__main__":
    sys.exit(main())
