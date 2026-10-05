"""What the two job commands share (DECISIONS.md #182): where the store lives, and the JSON-lines
log on stderr with the run's `run_id`. Moved unchanged from `run_once.py`.
"""

import json
import logging
import sys
import traceback
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_ROOT = REPO_ROOT / "config"
# The one SQLite file both `store` and `state` open, under `store_root` (DECISIONS.md #65).
SQLITE_FILENAME = "tlv_hunter.sqlite3"

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


@contextmanager
def job_logging(stream: TextIO | None = None) -> Iterator[str]:
    """JSON lines on `stream` (stderr by default) at INFO, each with a new run_id, which it
    yields. The root logger is restored on exit."""
    run_id = uuid.uuid4().hex[:12]
    run_token = _run_id.set(run_id)
    handler = logging.StreamHandler(sys.stderr if stream is None else stream)
    handler.setFormatter(_JsonFormatter())
    handler.addFilter(_RunIdFilter())
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    try:
        yield run_id
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        _run_id.reset(run_token)


def log_failure(logger: logging.Logger, error: BaseException) -> None:
    # Frames only: a message can carry a post's content, so it goes through describe.
    logger.error(
        "run failed: %s; traceback: %s",
        describe(error),
        " | ".join(line.strip() for line in traceback.format_tb(error.__traceback__)),
    )


def describe(error: BaseException) -> str:
    """The exception without input values: pydantic puts the input in its message."""
    if isinstance(error, ValidationError):
        details = (
            f"{'.'.join(str(part) for part in entry['loc']) or '<model>'}: {entry['type']}"
            for entry in error.errors(include_input=False, include_url=False)
        )
        return f"ValidationError ({'; '.join(details)})"
    return f"{type(error).__name__}: {error}"
