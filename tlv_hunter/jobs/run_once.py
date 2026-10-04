"""The collection run command (task 1.14). Paid: every run starts an Apify run.

    uv run --env-file .env python -m tlv_hunter.jobs.run_once --bootstrap   # first run
    uv run --env-file .env python -m tlv_hunter.jobs.run_once               # every run after it

The only code that reads `APIFY_TOKEN` and the only code that constructs the production store
(DECISIONS.md #79). Logs are JSON lines on stderr, each carrying this run's `run_id`.
"""

import argparse
import json
import logging
import os
import sys
import traceback
import uuid
from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.images.download import ImageTransport, urllib_image_transport
from tlv_hunter.pipeline import run_once
from tlv_hunter.providers.thedoor import ThedoorProvider, Transport, urllib_transport
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = REPO_ROOT / "config"
# The one SQLite file both `store` and `state` open, under `store_root` (DECISIONS.md #65).
SQLITE_FILENAME = "tlv_hunter.sqlite3"
# How far back a `--bootstrap` run asks (#79 D1).
BOOTSTRAP_WINDOW = timedelta(hours=24)
TOKEN_VARIABLE = "APIFY_TOKEN"

logger = logging.getLogger(__name__)

_run_id: ContextVar[str] = ContextVar("run_id", default="-")


class _RunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = _run_id.get()
        return True


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "run_id": getattr(record, "run_id", "-"),
                "msg": record.getMessage(),
            },
            ensure_ascii=False,
        )


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

    run_token = _run_id.set(uuid.uuid4().hex[:12])
    handler = logging.StreamHandler(sys.stderr if stream is None else stream)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RunIdFilter())
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        return _run(
            args.bootstrap, environ, config_root, repo_root, transport, image_transport, clock
        )
    except Exception as error:
        # Frames only: a message can carry a post's content, so it goes through _describe.
        logger.error(
            "run failed: %s; traceback: %s",
            _describe(error),
            " | ".join(line.strip() for line in traceback.format_tb(error.__traceback__)),
        )
        return 1
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        _run_id.reset(run_token)


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


def _describe(error: BaseException) -> str:
    """The exception without input values: pydantic puts the input in its message."""
    if isinstance(error, ValidationError):
        details = (
            f"{'.'.join(str(part) for part in entry['loc']) or '<model>'}: {entry['type']}"
            for entry in error.errors(include_input=False, include_url=False)
        )
        return f"ValidationError ({'; '.join(details)})"
    return f"{type(error).__name__}: {error}"


if __name__ == "__main__":
    sys.exit(main())
