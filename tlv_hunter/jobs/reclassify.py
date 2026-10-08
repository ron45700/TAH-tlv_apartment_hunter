"""Reclassify, stage 1 (task 2.9; DECISIONS.md #144, #217–#222). Selects the stored `Listing`s that
are not the current ones, and with `--run` asks the model again and writes the diff report.

    uv run python -m tlv_hunter.jobs.reclassify                                  # free: the plan
    uv run --env-file .env python -m tlv_hunter.jobs.reclassify --run --cap 0.02 --limit 10   # PAID
    uv run --env-file .env python -m tlv_hunter.jobs.reclassify --run --cap 0.10 --allow 2bac260c

**It never writes the store:** it opens it read-only. Its output is the folder
`<store_root>/reclassify/<run_id>/` (`proposals.jsonl`, `diff.html`, `summary.json` and the two
`--allow-file` lists). Replacing a `Listing` is `apply_reclassify`'s job, free, after Ron has read
the page. With no flag it prints the plan and calls nothing; `--run` needs `--cap` (no default)
and `--limit` or `--allow`. The third command that reads `OPENAI_API_KEY` (#220); it is never
logged. It shares `classify_pending`'s attempts table and stops (#182). Never run it beside
`run_once` (#140).

Exit codes: 0, every selected post attempted (a plan included); 2, stopped early with the store
untouched (the cap, the spend limit, the quota, a refused key or request, an unknown model); 1,
refused or failed."""

import argparse
import logging
import os
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.classification_run import tokens_by_kind
from tlv_hunter.classify.cost import CostMeter, worst_case
from tlv_hunter.classify.instructions import MODEL_NAME, PROMPT_FINGERPRINT, PROMPT_VERSION
from tlv_hunter.classify.openai_classifier import OpenAIClassifier
from tlv_hunter.classify.transport import ModelTransport, OpenAITransport
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.listing import LISTING_SCHEMA_VERSION
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, job_logging, log_failure
from tlv_hunter.labeling.corrections import CORRECTIONS_FILE, read_corrections
from tlv_hunter.labeling.regression_set import LABELING_DIR
from tlv_hunter.postmodel.reclassify import (
    PROPOSALS_FILE,
    RECLASSIFY_DIRECTORY,
    Candidate,
    ReclassifyPlan,
    narrow,
    select,
    status_text,
)
from tlv_hunter.postmodel.reclassify_report import (
    Summary,
    TripleCount,
    append_proposal,
    write_run_files,
)
from tlv_hunter.postmodel.rejects import other_city_ruling
from tlv_hunter.reclassification_run import propose
from tlv_hunter.store.sqlite import SqliteRepository

KEY_VARIABLE = "OPENAI_API_KEY"
_QUIET_LOGGERS = ("openai", "httpx", "httpx2", "httpcore", "httpcore2")
EXIT_DONE, EXIT_FAILED, EXIT_STOPPED = 0, 1, 2

# Run 2.8, version 3, effort `none`: $0.042574 over 194 classified posts (PHASE_2.md 2.9, 8).
MEASURED_COST_PER_POST = 0.000219

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    make_transport: Callable[[str], ModelTransport] = OpenAITransport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
    stream: TextIO | None = None,
    log_stream: TextIO | None = None,
) -> int:
    """`stream` takes the plan and the result; `log_stream` the JSON log lines (stderr)."""
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.reclassify")
    parser.add_argument("--run", action="store_true", help="PAID: ask the model, write the report")
    parser.add_argument("--cap", type=_positive_float, help="this run's cap in USD; no default")
    parser.add_argument(
        "--limit", type=_positive_int, help="at most this many posts, by listing_id"
    )
    parser.add_argument("--allow", default="", help="comma-separated id prefixes (8 or more)")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream

    with job_logging(log_stream) as run_id:
        for name in _QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
        try:
            return _run(
                args, run_id, environ, config_root, repo_root, make_transport, clock, sleep, out
            )
        except Exception as error:
            log_failure(logger, error)
            return EXIT_FAILED


def _run(
    args: argparse.Namespace,
    run_id: str,
    environ: Mapping[str, str],
    config_root: Path,
    repo_root: Path,
    make_transport: Callable[[str], ModelTransport],
    clock: Callable[[], datetime],
    sleep: Callable[[float], None],
    out: TextIO,
) -> int:
    allow = [part.strip() for part in args.allow.split(",") if part.strip()]
    refusal = _flag_refusal(args, allow)
    if refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    key = environ.get(KEY_VARIABLE, "").strip()
    if args.run and not key:
        print(f"refused: {KEY_VARIABLE} is not set", file=out)
        return EXIT_FAILED

    config = YamlConfig(config_root).collection()
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        # Checked before any constructor runs: SQLite would create an empty file.
        print(f"refused: no store at {database}", file=out)
        return EXIT_FAILED
    repository = SqliteRepository(database, read_only=True)

    current = (PROMPT_VERSION, LISTING_SCHEMA_VERSION, MODEL_NAME)
    plan = select(repository, current)
    try:
        candidates = narrow(plan.selected, limit=args.limit, allow=allow)
    except ValueError as error:
        print(f"refused: {error}", file=out)
        return EXIT_FAILED
    corrections = _reviewed_corrections(repo_root)

    meter = CostMeter(cap=args.cap or 1.0)
    classifier = OpenAIClassifier(
        make_transport(key) if args.run else _NoTransport(), meter, clock=clock
    )
    if not args.run:
        _print_plan(plan, candidates, corrections, repository, classifier, out)
        return EXIT_DONE
    if not candidates:
        print("nothing selected: nothing to ask the model", file=out)
        return EXIT_DONE

    folder = store_root / RECLASSIFY_DIRECTORY / run_id
    started = clock()
    logger.info(
        "reclassify start: %d to ask about, current %s, cap $%.2f, fingerprint %s",
        len(candidates),
        current,
        meter.cap,
        PROMPT_FINGERPRINT[:8],
    )
    result = propose(
        repository=repository,
        classifier=classifier,
        meter=meter,
        sleep=sleep,
        candidates=candidates,
        corrections=corrections,
        on_proposal=lambda proposal: append_proposal(folder / PROPOSALS_FILE, proposal),
    )
    proposals = result.proposals
    triples = Counter(c.triple for c in candidates)
    summary = Summary(
        format_version=1,
        run_id=run_id,
        started_at=started,
        finished_at=clock(),
        current_prompt_version=current[0],
        current_schema_version=current[1],
        current_model_name=current[2],
        prompt_fingerprint=PROMPT_FINGERPRINT,
        cap=meter.cap,
        spent=meter.spent,
        calls=len(meter.calls),
        tokens=tokens_by_kind(meter.calls),
        reported_models=sorted({str(call.reported_model) for call in meter.calls}),
        selected_by_triple=[
            TripleCount(prompt_version=t[0], schema_version=t[1], model_name=t[2], count=n)
            for t, n in sorted(triples.items())
        ],
        selected=len(candidates),
        attempted=len(proposals),
        proposed=sum(p.new is not None for p in proposals),
        failed=sum(p.new is None for p in proposals),
        not_attempted=len(result.not_attempted),
        state_changes=sum(p.status_changed for p in proposals),
        unchanged_apart_from_provenance=sum(
            p.new is not None and not p.status_changed and not p.fields_changed for p in proposals
        ),
        stopped=result.stopped,
        complete=True,
    )
    folder.mkdir(parents=True, exist_ok=True)
    texts = {}
    cities = {}
    for proposal in proposals:
        post = repository.get(proposal.listing_id)
        texts[proposal.listing_id] = "" if post is None else post.text
        if post is not None and proposal.new is not None:
            cities[proposal.listing_id] = (
                other_city_ruling(post, proposal.old.listing),
                other_city_ruling(post, proposal.new.listing),
            )
    write_run_files(folder, summary, proposals, texts, cities)
    _print_result(summary, folder, out)
    return EXIT_STOPPED if result.stopped else EXIT_DONE


def _flag_refusal(args: argparse.Namespace, allow: Sequence[str]) -> str | None:
    if not args.run:
        if args.cap is not None:
            return "--cap goes with --run"
        return None
    if args.cap is None:
        return "--run needs --cap (no default)"
    if args.limit is None and not allow:
        return "--run needs --limit or --allow: the number of posts is always chosen (#217)"
    return None


def _reviewed_corrections(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """The posts with a reviewed correction on file (#222), to the fields Ron corrected.
    Read only."""
    corrections = read_corrections(repo_root / LABELING_DIR / CORRECTIONS_FILE)
    if corrections is None:
        return {}
    return {key: tuple(c.fields) for key, c in corrections.reviewed().items()}


class _NoTransport:
    """The plan builds the requests to price them; it can never send one."""

    def send(self, request: dict) -> dict:
        raise RuntimeError("the plan makes no call")


def _print_plan(
    plan: ReclassifyPlan,
    candidates: Sequence[Candidate],
    corrections: Mapping[str, tuple[str, ...]],
    repository: SqliteRepository,
    classifier: OpenAIClassifier,
    out: TextIO,
) -> None:
    def triple(t) -> str:
        return f"prompt {t[0]} / schema {t[1]} / {t[2]}"

    print("reclassify plan: nothing written, no call", file=out)
    print(f"current: {triple(plan.current)}", file=out)
    total = sum(plan.stored.values())
    print(f"stored Listings: {total}", file=out)
    for t, count in sorted(plan.stored.items()):
        print(f"  {triple(t)}: {count}", file=out)
    print(
        f"selected: {len(plan.selected)}; to ask about with these flags: {len(candidates)}",
        file=out,
    )
    for reason, count in sorted(plan.left_out.items()):
        print(f"  left out, {reason}: {count}", file=out)
    for c in candidates:
        marks = []
        if c.flagged:
            marks.append("flagged: record kept")
        if c.listing_id in corrections:
            fields = corrections[c.listing_id]
            marks.append("reviewed by Ron" + (f", corrected {', '.join(fields)}" if fields else ""))
        print(
            f"  {c.listing_id[:12]}  {status_text(c.status):22} {triple(c.triple)}"
            + (f"  [{'; '.join(marks)}]" if marks else ""),
            file=out,
        )
    if not candidates:
        print("nothing to reclassify", file=out)
        return
    worst = [
        worst_case(classifier.request(post))
        for c in candidates
        if (post := repository.get(c.listing_id)) is not None
    ]
    n = len(candidates)
    print(
        f"estimate: {n} x ${MEASURED_COST_PER_POST} = ${n * MEASURED_COST_PER_POST:.4f} "
        "(measured on run 2.8, effort none); worst case of one call for the cap check: "
        f"${min(worst):.5f} to ${max(worst):.5f}",
        file=out,
    )
    limit = f" --limit {n}" if n else ""
    print(
        "to ask the model (PAID): uv run --env-file .env python -m tlv_hunter.jobs.reclassify "
        f"--run --cap <USD>{limit}",
        file=out,
    )


def _print_result(summary: Summary, folder: Path, out: TextIO) -> None:
    print(
        f"run {summary.run_id}: {summary.attempted} attempted, {summary.proposed} proposed, "
        f"{summary.failed} failed, {summary.not_attempted} not attempted, {summary.state_changes} "
        f"state changes; ${summary.spent:.6f} of ${summary.cap:.2f}; "
        f"stopped: {summary.stopped or 'no'}",
        file=out,
    )
    print(f"report: {folder / 'diff.html'}", file=out)
    print(
        f"lists: {folder / 'allow_unchanged.txt'}, {folder / 'allow_state_changes.txt'}", file=out
    )
    print(
        f"next: read the report, then uv run python -m tlv_hunter.jobs.apply_reclassify "
        f"{summary.run_id}  (dry run), then --apply --allow-file <list>",
        file=out,
    )
    print("the store was not written", file=out)


def _positive_float(value: str) -> float:
    number = float(value)
    if not number > 0:
        raise argparse.ArgumentTypeError("must be above 0")
    return number


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return number


if __name__ == "__main__":
    sys.exit(main())
