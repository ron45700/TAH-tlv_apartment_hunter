"""The collection run command (task 1.14). Paid: every run starts an Apify run.

    uv run --env-file .env python -m tlv_hunter.jobs.run_once --bootstrap   # first run
    ... run_once --bootstrap --max-posts 30   # the server's first run, 30 posts a group (DEPLOY.md)
    uv run --env-file .env python -m tlv_hunter.jobs.run_once               # every run after it
    ... run_once --trigger scheduled          # what the scheduler runs (manual by default)

Reads `APIFY_TOKEN` (with `settle_costs`, which only reads runs) and constructs the production store
(DECISIONS.md #79). Logs are JSON lines on stderr, each carrying this run's `run_id`.

**Gate G (#472):** the run's `RunRecord` is written when it starts (`running`) and when it ends
(`succeeded`, or `failed` with the reason), with what the provider learned of its Apify run: the
Apify run id, the rows returned and skipped, the end-of-run charged events (preliminary, P19; the
cost is settled later by `settle_costs`). A record still `running` when a run starts is closed as
failed, "abandoned": one run at a time (#140), so it can only be one that died.
"""

import argparse
import logging
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.run_record import RUN_RECORD_SCHEMA_VERSION, RunRecord, Trigger
from tlv_hunter.images.download import ImageTransport, urllib_image_transport
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    describe,
    job_logging,
    log_failure,
)
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.pipeline import run_once
from tlv_hunter.providers.thedoor import ApifyRun, ThedoorProvider, Transport, urllib_transport
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository

# How far back a `--bootstrap` run asks (#79 D1).
BOOTSTRAP_WINDOW = timedelta(hours=24)
TOKEN_VARIABLE = "APIFY_TOKEN"
TRIGGERS: tuple[Trigger, ...] = ("scheduled", "manual")
FAILURE_KIND_LIMIT = 300
ABANDONED = "abandoned: the run ended with no record of its end"

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    transport: Transport = urllib_transport,
    image_transport: ImageTransport = urllib_image_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    """Returns the exit code: 0 after a successful run, 1 otherwise."""
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.run_once")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help=(
            "first run: create the store and ask "
            f"{BOOTSTRAP_WINDOW // timedelta(hours=1)} hours back"
        ),
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        metavar="N",
        help=(
            "this run only: ask at most N posts per group, from 1 up to the configured max_posts "
            "(the server's bootstrap, DEPLOY.md)"
        ),
    )
    parser.add_argument(
        "--trigger",
        choices=TRIGGERS,
        default="manual",
        help="what started the run, for its record: the scheduler passes 'scheduled'",
    )
    args = parser.parse_args(argv)

    with job_logging(stream) as run_id:
        try:
            return _run(
                args.bootstrap,
                args.max_posts,
                args.trigger,
                run_id,
                environ,
                config_root,
                repo_root,
                transport,
                image_transport,
                clock,
            )
        except Exception as error:
            log_failure(logger, error)
            return 1


def _run(
    bootstrap: bool,
    max_posts: int | None,
    trigger: Trigger,
    run_id: str,
    environ: Mapping[str, str],
    config_root: Path,
    repo_root: Path,
    transport: Transport,
    image_transport: ImageTransport,
    clock: Callable[[], datetime],
) -> int:
    config = YamlConfig(config_root).collection()
    if config.provider != "thedoor":
        logger.error("provider %s is not built", config.provider)
        return 1
    if max_posts is not None:
        # Only lower: the configured value is what keeps groups × max_posts under the charge cap's
        # maxItems (#78 W3). The provider and the watermark logic read the same copy.
        if not 1 <= max_posts <= config.max_posts:
            logger.error("--max-posts must be from 1 to %d, got %d", config.max_posts, max_posts)
            return 1
        logger.info("max_posts %d for this run (configured %d)", max_posts, config.max_posts)
        config = config.model_copy(update={"max_posts": max_posts})
    token = environ.get(TOKEN_VARIABLE, "").strip()
    if not token:
        logger.error("%s is not set", TOKEN_VARIABLE)
        return 1

    # A relative store_root resolves against the repo root, not the working directory (#79 O6).
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if bootstrap:
        store_root.mkdir(parents=True, exist_ok=True)
    elif not database.is_file():
        # Checked before any constructor runs: SQLite would create an empty file.
        logger.error("no store at %s; the first run needs --bootstrap", database)
        return 1

    runs = SqliteRunStore(database)
    started_at = require_utc(clock())
    close_abandoned(runs, started_at)
    record = runs.add_run(
        RunRecord(
            schema_version=RUN_RECORD_SCHEMA_VERSION,
            run_id=run_id,
            trigger=trigger,
            started_at=started_at,
            finished_at=None,
            status="running",
            failure_kind=None,
            rows_fetched=None,
            rows_skipped=None,
            window_since=None,
            window_capped=False,
            apify_run_id=None,
            charged_events=None,
            cost_usd=None,
            cost_settled_at=None,
        )
    )
    provider = ThedoorProvider(config, token, transport=transport, clock=clock)
    try:
        result = run_once(
            provider=provider,
            repository=SqliteRepository(database),
            watermarks=SqliteWatermarkStore(database),
            group_ids=config.group_ids,
            max_posts=config.max_posts,
            store_root=store_root,
            clock=clock,
            bootstrap_window=BOOTSTRAP_WINDOW if bootstrap else None,
            image_transport=image_transport,
        )
    except Exception as error:
        _finish(runs, record, provider.last_run, require_utc(clock()), None, describe(error))
        raise
    _finish(runs, record, provider.last_run, require_utc(clock()), result.since, None)
    return 0


def close_abandoned(runs: SqliteRunStore, now: datetime) -> list[RunRecord]:
    """Every record still `running` becomes `failed`, "abandoned", at `now`: one run at a time
    (#140), so a record left running belongs to a run that died before writing its end."""
    closed = []
    for found in runs.recent_runs():
        if found.status != "running":
            continue
        ended = RunRecord.model_validate(
            {
                **found.model_dump(),
                "status": "failed",
                "finished_at": max(now, found.started_at),
                "failure_kind": ABANDONED,
            }
        )
        runs.save_run(ended, expected=found)
        logger.warning("run %s was left running; closed as abandoned", found.run_id)
        closed.append(ended)
    return closed


def _finish(
    runs: SqliteRunStore,
    record: RunRecord,
    apify: ApifyRun | None,
    now: datetime,
    since: datetime | None,
    failure: str | None,
) -> None:
    ended = RunRecord.model_validate(
        {
            **record.model_dump(),
            "finished_at": max(now, record.started_at),
            "status": "succeeded" if failure is None else "failed",
            "failure_kind": None if failure is None else failure[:FAILURE_KIND_LIMIT],
            "rows_fetched": None if apify is None else apify.rows,
            "rows_skipped": None if apify is None else apify.skipped,
            "window_since": since,
            "apify_run_id": None if apify is None else apify.apify_run_id,
            "charged_events": None if apify is None else apify.charged_events,
        }
    )
    runs.save_run(ended, expected=record)


if __name__ == "__main__":
    sys.exit(main())
