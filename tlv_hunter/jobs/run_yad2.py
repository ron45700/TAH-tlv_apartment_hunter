"""The Yad2 run command (`PHASE_6.md` build step 5; DECISIONS.md #506, #529). Free of any
key: it calls no model and no Apify; the posts it stores are classified by the `classify_pending`
that follows it. It loads Yad2's pages in a headed browser, so it runs in the browser image, under
Xvfb:

    xvfb-run -a -s '-screen 0 1920x1080x24' python -m tlv_hunter.jobs.run_yad2 [--trigger scheduled]

**The first run is the bootstrap, by itself** (#529): with no `yad2-tel-aviv` record it reads 3
list pages and checks no bump (#493). It writes the store (`yad2_run.run_yad2`: one transaction at
the end, only on success) and its `RunRecord`, `source` `"yad2"`, when it starts and when it ends
(Gate G): the listings on the list pages read (`rows_fetched`), the listing pages that failed
(`rows_skipped`), or the failure, a block's own reason ("blocked: …"). The Apify fields stay `None`
(Gate G). A record still `running` is closed as abandoned first: one run at a time across both
sources (#140).

The browser's profile is `data/yad2-profile/`, Yad2's own visitor cookies only (invariant 13,
#499): on the server its own folder, outside git and the image. Logs are JSON lines on stderr with
the run's `run_id`, as `run_once`'s.
"""

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from datetime import UTC, datetime
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
from tlv_hunter.jobs.run_once import FAILURE_KIND_LIMIT, TRIGGERS, close_abandoned
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.yad2.browser import PlaywrightBrowser
from tlv_hunter.yad2.collector import Browser, Yad2Blocked, Yad2Collector
from tlv_hunter.yad2.mapping import GROUP_ID
from tlv_hunter.yad2_run import Yad2RunResult, run_yad2

PROFILE_DIRECTORY = Path("data") / "yad2-profile"

# The browser for one run, opened and closed around it (`PlaywrightBrowser`).
BrowserFactory = Callable[[Path], AbstractContextManager[Browser]]

logger = logging.getLogger(__name__)


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    browser_factory: BrowserFactory = PlaywrightBrowser,
    image_transport: ImageTransport = urllib_image_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] | None = None,
    stream: TextIO | None = None,
) -> int:
    """Returns the exit code: 0 after a successful run, 1 otherwise."""
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.run_yad2")
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
                args.trigger,
                run_id,
                config_root,
                repo_root,
                browser_factory,
                image_transport,
                clock,
                sleep,
            )
        except Exception as error:
            log_failure(logger, error)
            return 1


def _run(
    trigger: Trigger,
    run_id: str,
    config_root: Path,
    repo_root: Path,
    browser_factory: BrowserFactory,
    image_transport: ImageTransport,
    clock: Callable[[], datetime],
    sleep: Callable[[float], None] | None,
) -> int:
    store_root = repo_root / YamlConfig(config_root).collection().store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        # Checked before any constructor runs: SQLite would create an empty file.
        logger.error("no store at %s; Facebook's bootstrap creates it", database)
        return 1

    watermarks = SqliteWatermarkStore(database)
    bootstrap = watermarks.get(GROUP_ID) is None
    if bootstrap:
        logger.info("no %s record: this run is Yad2's bootstrap", GROUP_ID)

    runs = SqliteRunStore(database)
    started_at = require_utc(clock())
    close_abandoned(runs, started_at)
    record = runs.add_run(
        RunRecord(
            schema_version=RUN_RECORD_SCHEMA_VERSION,
            source="yad2",
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
    try:
        with browser_factory(repo_root / PROFILE_DIRECTORY) as browser:
            result = run_yad2(
                collector=Yad2Collector(browser, clock=clock, sleep=sleep),
                repository=SqliteRepository(database),
                watermarks=watermarks,
                store_root=store_root,
                clock=clock,
                bootstrap=bootstrap,
                image_transport=image_transport,
                image_sleep=sleep,
            )
    except Yad2Blocked as blocked:
        _finish(runs, record, require_utc(clock()), None, blocked.reason)
        raise
    except Exception as error:
        _finish(runs, record, require_utc(clock()), None, describe(error))
        raise
    _finish(runs, record, require_utc(clock()), result, None)
    return 0


def _finish(
    runs: SqliteRunStore,
    record: RunRecord,
    now: datetime,
    result: Yad2RunResult | None,
    failure: str | None,
) -> None:
    collection = None if result is None else result.collection
    ended = RunRecord.model_validate(
        {
            **record.model_dump(),
            "finished_at": max(now, record.started_at),
            "status": "succeeded" if failure is None else "failed",
            "failure_kind": None if failure is None else failure[:FAILURE_KIND_LIMIT],
            "rows_fetched": None if collection is None else collection.listings_read,
            "rows_skipped": None if collection is None else len(collection.skipped),
        }
    )
    runs.save_run(ended, expected=record)


if __name__ == "__main__":
    sys.exit(main())
