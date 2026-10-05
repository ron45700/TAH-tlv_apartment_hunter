"""The classification job's command (task 2.5). PAID: every post is one model call.

    uv run --env-file .env python -m tlv_hunter.jobs.classify_pending --cap 1.00
    uv run --env-file .env python -m tlv_hunter.jobs.classify_pending --cap 0.05 --limit 10

The only code that reads `OPENAI_API_KEY` (DECISIONS.md #128); it is never logged. With
`run_once`, one of the two job commands that construct the production store (#182). Never run it
beside `run_once` (#140). Logs are JSON lines on stderr, each carrying this run's `run_id`; the
names #162 and #180 dropped go to `<store_root>/classify_runs/<run_id>.jsonl` (#182).

Exit codes (#182): 0, every post attempted; 2, stopped early with the store consistent (the cap,
the spend limit, the quota, a refused key or request, an unknown model); 1, failed.
"""

import argparse
import json
import logging
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.classification_run import classify_pending
from tlv_hunter.classify.complete import Completed
from tlv_hunter.classify.cost import CostMeter
from tlv_hunter.classify.openai_classifier import OpenAIClassifier
from tlv_hunter.classify.transport import ModelTransport, OpenAITransport
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, job_logging, log_failure
from tlv_hunter.store.sqlite import SqliteRepository

KEY_VARIABLE = "OPENAI_API_KEY"
RUNS_DIRECTORY = "classify_runs"
# Their request lines carry no key, but nothing but this job's own lines goes to the log.
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
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.classify_pending")
    parser.add_argument(
        "--cap", type=_positive_float, required=True, help="this run's cap in USD; no default"
    )
    parser.add_argument(
        "--limit", type=_positive_int, help="classify at most this many posts, by listing_id"
    )
    args = parser.parse_args(argv)

    with job_logging(stream) as run_id:
        for name in _QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
        try:
            return _run(
                args.cap,
                args.limit,
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
    limit: int | None,
    run_id: str,
    environ: Mapping[str, str],
    config_root: Path,
    repo_root: Path,
    make_transport: Callable[[str], ModelTransport],
    clock: Callable[[], datetime],
    sleep: Callable[[float], None],
) -> int:
    key = environ.get(KEY_VARIABLE, "").strip()
    if not key:
        logger.error("%s is not set", KEY_VARIABLE)
        return EXIT_FAILED

    config = YamlConfig(config_root).collection()
    # A relative store_root resolves against the repo root, as in run_once (#79 O6).
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        # Checked before any constructor runs: SQLite would create an empty file.
        logger.error("no store at %s; run_once --bootstrap creates it", database)
        return EXIT_FAILED

    meter = CostMeter(cap=cap)
    classifier = OpenAIClassifier(make_transport(key), meter, clock=clock)
    names = _DroppedNames(store_root / RUNS_DIRECTORY / f"{run_id}.jsonl")
    result = classify_pending(
        repository=SqliteRepository(database),
        classifier=classifier,
        meter=meter,
        sleep=sleep,
        limit=limit,
        on_written=names.write,
    )
    return EXIT_STOPPED if result.stopped else EXIT_DONE


class _DroppedNames:
    """One JSON line per post written (#182 A), the file created with its first line."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def write(self, completed: Completed) -> None:
        line = {
            "listing_id": completed.listing.listing_id,
            "prompt_version": completed.listing.prompt_version,
            "dropped_streets": list(completed.dropped_streets),
            "dropped_area_names": list(completed.dropped_area_names),
            "dropped_other_city": completed.dropped_other_city,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(line, ensure_ascii=False) + "\n")


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
