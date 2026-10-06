"""The regression set's run (`PHASE_2.md` 2.6). PAID: two passes over the set, one call a post each.

    uv run --env-file .env python -m tlv_hunter.jobs.regression_run            # PAID, cap $0.10
    uv run --env-file .env python -m tlv_hunter.jobs.regression_run --effort low   # PAID
    uv run python -m tlv_hunter.jobs.regression_run --check                    # free: refusals only

Before any call it refuses to start without a complete, current `labels.json` (with
`label_overrides.json` on top, DECISIONS.md #196), and names every reason. `--check` stops there:
no key read, no call. The store is opened read-only and nothing is written to it: a regression run
is a test, not the classification of record. The report goes to `data/labeling/runs/<run>/`.

Reads `OPENAI_API_KEY`, as every command that calls the model may (#188); it is never logged.
Never run it beside `run_once` or `classify_pending`. Exit codes: 0, both passes ran (whatever the
verdict); 2, stopped early by the cap or a failure every post would share, with a partial report;
1, refused or failed, with nothing called.
"""

import argparse
import logging
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.classification_run import ERROR_TEXT_LIMIT, RunStop, attempt_post
from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.cost import CostMeter
from tlv_hunter.classify.instructions import PROMPT_VERSION, REASONING_EFFORT, build_prompt
from tlv_hunter.classify.openai_classifier import OpenAIClassifier
from tlv_hunter.classify.transport import ModelTransport, OpenAITransport
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, job_logging, log_failure
from tlv_hunter.labeling.compare import judge
from tlv_hunter.labeling.corrections import RUNS_DIR
from tlv_hunter.labeling.regression import prepare
from tlv_hunter.labeling.regression_set import LABELING_DIR
from tlv_hunter.labeling.run_report import PostRun, RunMeta, write_run
from tlv_hunter.store.sqlite import SqliteRepository

KEY_VARIABLE = "OPENAI_API_KEY"
DEFAULT_CAP = 0.10  # DECISIONS.md #194
PASSES = 2  # #157, O12
EFFORTS = ("none", "low")
_QUIET_LOGGERS = ("openai", "httpx", "httpx2", "httpcore", "httpcore2")

EXIT_DONE, EXIT_FAILED, EXIT_STOPPED = 0, 1, 2

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
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.regression_run")
    parser.add_argument(
        "--cap", type=_positive_float, default=DEFAULT_CAP, help="this run's cap in USD"
    )
    parser.add_argument(
        "--check", action="store_true", help="check the inputs and stop: no key, no call"
    )
    parser.add_argument(
        "--effort",
        choices=EFFORTS,
        default=REASONING_EFFORT,
        help="the reasoning effort of this run; production stays `none` (#157, #201)",
    )
    args = parser.parse_args(argv)

    with job_logging(stream) as run_id:
        for name in _QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
        try:
            return _run(
                args.cap,
                args.check,
                args.effort,
                run_id,
                environ,
                config_root,
                repo_root,
                make_transport,
                clock,
                sleep,
            )
        except Exception as error:
            log_failure(logger, error)
            return EXIT_FAILED


def _run(
    cap: float,
    check: bool,
    effort: str,
    run_id: str,
    environ: Mapping[str, str],
    config_root: Path,
    repo_root: Path,
    make_transport: Callable[[str], ModelTransport],
    clock: Callable[[], datetime],
    sleep: Callable[[float], None],
) -> int:
    config = YamlConfig(config_root).collection()
    database = repo_root / config.store_root / SQLITE_FILENAME
    if not database.is_file():
        logger.error("no store at %s", database)
        return EXIT_FAILED
    store = SqliteRepository(database, read_only=True)
    prepared = prepare(repo_root, store)
    if prepared.refusals:
        for reason in prepared.refusals:
            logger.error("refused: %s", reason)
        logger.error(
            "regression run refused: %d reasons; nothing was called", len(prepared.refusals)
        )
        return EXIT_FAILED
    logger.info(
        "regression set ready: %d posts, removed positions %s, ambiguous %s, overrides %s",
        len(prepared.truths),
        prepared.removed,
        prepared.ambiguous,
        "applied" if prepared.overrides is not None else "none",
    )
    if check:
        return EXIT_DONE

    key = environ.get(KEY_VARIABLE, "").strip()
    if not key:
        logger.error("%s is not set", KEY_VARIABLE)
        return EXIT_FAILED
    prompt = build_prompt(reasoning_effort=effort)
    meter = CostMeter(cap=cap)
    classifier = OpenAIClassifier(make_transport(key), meter, clock=clock, prompt=prompt)
    started = clock()
    logger.info(
        "regression run start: model %s, prompt_version %s, effort %s, temperature %s, "
        "%d passes, cap $%.2f",
        prompt.model,
        PROMPT_VERSION,
        prompt.reasoning_effort,
        prompt.temperature,
        PASSES,
        cap,
    )

    passes: list[list[PostRun]] = []
    stopped: str | None = None
    for number in range(1, PASSES + 1):
        runs: list[PostRun] = []
        passes.append(runs)
        for post in prepared.posts:
            first_call = len(meter.calls)
            try:
                result, attempts = attempt_post(post, classifier, sleep)
            except RunStop as stop:
                stopped = stop.reason
                logger.warning(
                    "regression run stopped in pass %d before %s: %s",
                    number,
                    post.listing_id,
                    stop.reason,
                )
                break
            calls = tuple(meter.calls[first_call:])
            if isinstance(result, ClassificationError):
                run = PostRun(
                    post.listing_id,
                    f"failed: {result.kind}",
                    attempts,
                    None,
                    calls,
                    str(result)[:ERROR_TEXT_LIMIT],
                )
            else:
                run = PostRun(post.listing_id, "ok", attempts, result, calls)
            runs.append(run)
            logger.info(
                "pass %d post %s: %s, %d attempts, $%.6f, reported model %s",
                number,
                post.listing_id,
                run.outcome,
                attempts,
                sum(call.cost for call in calls),
                ",".join(sorted({str(call.reported_model) for call in calls})) or "-",
            )
        if stopped is not None:
            break

    results = [
        judge(
            number,
            prepared.truths,
            {
                run.listing_id: None if run.completed is None else run.completed.listing
                for run in runs
            },
        )
        for number, runs in enumerate(passes, 1)
    ]
    meta = RunMeta(
        run_id=run_id,
        started_at=started,
        finished_at=clock(),
        model=prompt.model,
        prompt_version=PROMPT_VERSION,
        prompt_fingerprint=prompt.fingerprint(),
        reasoning_effort=prompt.reasoning_effort,
        temperature=prompt.temperature,
        cap=cap,
        spent=meter.spent,
        stopped=stopped,
    )
    folder = write_run(repo_root / LABELING_DIR / RUNS_DIR, meta, prepared, passes, results)
    for result in results:
        logger.info(
            "pass %d: %s; errors %s; areas exact %s, %.2f returned a post; filled in %d; "
            "failed positions %s",
            result.number,
            result.verdict,
            {f.field: f.errors for f in result.fields if f.errors},
            None if result.areas_exact is None else result.areas_exact.errors,
            0.0 if result.areas_exact is None else result.areas_exact.average_returned,
            len(result.filled_in),
            result.failed_posts,
        )
    logger.info(
        "regression run done: %d calls, $%.6f of $%.2f, stopped %s, report %s",
        len(meter.calls),
        meter.spent,
        cap,
        stopped or "no",
        folder,
    )
    return EXIT_STOPPED if stopped is not None else EXIT_DONE


def _positive_float(value: str) -> float:
    number = float(value)
    if not number > 0:
        raise argparse.ArgumentTypeError("must be above 0")
    return number


if __name__ == "__main__":
    sys.exit(main())
