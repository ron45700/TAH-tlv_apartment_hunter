"""The real Apify cost of each run (`PHASE_5.md` point 6 A; DECISIONS.md #450, #471). **Free:** it
only reads Apify's run objects (`GET /v2/actor-runs/{id}`), which costs nothing.

    python -m tlv_hunter.jobs.settle_costs                 # what the scheduler runs after each slot
    python -m tlv_hunter.jobs.settle_costs --show <id>     # one Apify run, printed; writes nothing

For every `RunRecord` that ended `SETTLE_AFTER` (15 minutes) ago or more, has an Apify run id and no
settled cost: the run object is read again, its cost computed as Σ `chargedEventCounts` × each
event's `eventPriceUsd` (`providers.thedoor.run_charges`), and stored in `cost_usd` with the settled
`charged_events`, by compare and set. The settled `usageTotalUsd` is compared and a difference of
more than half a cent is logged (not stored), a check of the formula. A run Apify still reports as
running, or with an event that has no flat price, is left for the next pass.

`--show` is the read #449's two open points wait for: the run's status, events, prices, the cost by
the events and `usageTotalUsd`, printed. Reads `APIFY_TOKEN`, never logged. Exit codes: 0, done
(nothing to settle included); 1, refused or failed.
"""

import argparse
import json
import logging
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.run_record import RunRecord
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    describe,
    job_logging,
    log_failure,
)
from tlv_hunter.providers.thedoor import (
    TRANSITIONAL_STATUSES,
    Transport,
    UnpricedEvent,
    get_run,
    run_charges,
    urllib_transport,
)
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.store.base import StaleRecordError

TOKEN_VARIABLE = "APIFY_TOKEN"
SETTLE_AFTER = timedelta(minutes=15)
CHECK_TOLERANCE_USD = 0.005
EXIT_DONE, EXIT_FAILED = 0, 1

logger = logging.getLogger(__name__)


def due(runs: Sequence[RunRecord], now: datetime) -> list[RunRecord]:
    """The records to settle now, oldest first."""
    return sorted(
        (
            run
            for run in runs
            if run.cost_usd is None
            and run.apify_run_id is not None
            and run.finished_at is not None
            and now - run.finished_at >= SETTLE_AFTER
        ),
        key=lambda run: run.started_at,
    )


def settle(
    store: SqliteRunStore,
    token: str,
    now: datetime,
    transport: Transport | None = None,
) -> tuple[int, int]:
    """(settled, left) for the records due now."""
    settled = left = 0
    for record in due(store.recent_runs(), now):
        assert record.apify_run_id is not None
        try:
            run = get_run(token, record.apify_run_id, transport)
            if run.get("status") in TRANSITIONAL_STATUSES:
                logger.info("apify_run %s is still %s", record.apify_run_id, run.get("status"))
                left += 1
                continue
            charges = run_charges(run)
        except UnpricedEvent as error:
            logger.warning("apify_run %s not settled: %s", record.apify_run_id, error)
            left += 1
            continue
        except Exception as error:
            logger.warning("apify_run %s not read: %s", record.apify_run_id, describe(error))
            left += 1
            continue
        if (
            charges.usage_total_usd is not None
            and abs(charges.usage_total_usd - charges.cost_usd) > CHECK_TOLERANCE_USD
        ):
            logger.warning(
                "apify_run %s: the events' cost $%.4f differs from usageTotalUsd $%.4f",
                record.apify_run_id,
                charges.cost_usd,
                charges.usage_total_usd,
            )
        updated = RunRecord.model_validate(
            {
                **record.model_dump(),
                "charged_events": charges.charged_events,
                "cost_usd": charges.cost_usd,
                "cost_settled_at": now,
            }
        )
        try:
            store.save_run(updated, expected=record)
        except StaleRecordError:
            logger.warning("run %s changed while it was settled; left", record.run_id)
            left += 1
            continue
        logger.info(
            "run %s settled: $%.4f, events %s",
            record.run_id,
            charges.cost_usd,
            json.dumps(charges.charged_events, sort_keys=True),
        )
        settled += 1
    return settled, left


def show(token: str, apify_run_id: str, out: TextIO, transport: Transport | None = None) -> None:
    run = get_run(token, apify_run_id, transport)
    print(f"apify run {apify_run_id}: {run.get('status')}", file=out)
    print(f"  started {run.get('startedAt')}, finished {run.get('finishedAt')}", file=out)
    pricing = run.get("pricingInfo") or {}
    print(f"  pricingModel {pricing.get('pricingModel')}", file=out)
    print(f"  platformUsageBillingModel {run.get('platformUsageBillingModel')}", file=out)
    print(f"  chargedEventCounts {json.dumps(run.get('chargedEventCounts'))}", file=out)
    try:
        charges = run_charges(run)
    except UnpricedEvent as error:
        print(f"  the cost by the events: not computed ({error})", file=out)
    else:
        print(f"  eventPriceUsd {json.dumps(charges.prices)}", file=out)
        print(f"  the cost by the events: ${charges.cost_usd:.4f}", file=out)
    print(f"  usageTotalUsd {run.get('usageTotalUsd')}", file=out)
    print(f"  usageUsd {json.dumps(run.get('usageUsd'))}", file=out)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    transport: Transport = urllib_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.settle_costs")
    parser.add_argument("--show", metavar="APIFY_RUN_ID", help="print one run; write nothing")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    token = environ.get(TOKEN_VARIABLE, "").strip()
    if not token:
        print(f"refused: {TOKEN_VARIABLE} is not set", file=out)
        return EXIT_FAILED
    if args.show:
        try:
            show(token, args.show, out, transport)
            return EXIT_DONE
        except Exception as error:
            print(f"failed: {describe(error)}", file=out)
            return EXIT_FAILED
    with job_logging(stream):
        try:
            config = YamlConfig(config_root).collection()
            database = repo_root / config.store_root / SQLITE_FILENAME
            if not database.is_file():
                logger.error("no store at %s", database)
                return EXIT_FAILED
            settled, left = settle(SqliteRunStore(database), token, clock(), transport)
            logger.info("settle_costs: %d settled, %d left for a later pass", settled, left)
            return EXIT_DONE
        except Exception as error:
            log_failure(logger, error)
            return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
