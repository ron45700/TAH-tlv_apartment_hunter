"""The collection run command (task 1.14). Paid: every run starts an Apify run.

    uv run --env-file .env python -m tlv_hunter.jobs.run_once --bootstrap   # first run
    uv run --env-file .env python -m tlv_hunter.jobs.run_once               # every run after it

The only code that reads `APIFY_TOKEN` and the only code that constructs the production store
(DECISIONS.md #79). Logs are JSON lines on stderr, each carrying this run's `run_id`.
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
from tlv_hunter.images.download import ImageTransport, urllib_image_transport
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, job_logging, log_failure
from tlv_hunter.pipeline import run_once
from tlv_hunter.providers.thedoor import ThedoorProvider, Transport, urllib_transport
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository

# How far back a `--bootstrap` run asks (#79 D1).
BOOTSTRAP_WINDOW = timedelta(hours=24)
TOKEN_VARIABLE = "APIFY_TOKEN"

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
    args = parser.parse_args(argv)

    with job_logging(stream):
        try:
            return _run(
                args.bootstrap, environ, config_root, repo_root, transport, image_transport, clock
            )
        except Exception as error:
            log_failure(logger, error)
            return 1


def _run(
    bootstrap: bool,
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

    run_once(
        provider=ThedoorProvider(config, token, transport=transport, clock=clock),
        repository=SqliteRepository(database),
        watermarks=SqliteWatermarkStore(database),
        group_ids=config.group_ids,
        max_posts=config.max_posts,
        store_root=store_root,
        clock=clock,
        bootstrap_window=BOOTSTRAP_WINDOW if bootstrap else None,
        image_transport=image_transport,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
