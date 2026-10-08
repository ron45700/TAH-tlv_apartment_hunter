"""What the job commands share (DECISIONS.md #182): where the store lives, and the JSON-lines
log on stderr with the run's `run_id`, moved unchanged from `run_once.py`; the dated backup of the
store and the check of the stored posts that the commands writing it share (#214, #220); and the
dropped-names line (#182).
"""

import hashlib
import json
import logging
import shutil
import sqlite3
import sys
import traceback
import uuid
from collections.abc import Collection, Iterator
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def backup_store(database: Path, now: datetime) -> Path:
    """A dated copy of the store beside it; a second one on the same day gets the time in its name.
    The copy must hash like the store. Nothing is overwritten."""
    base = database.with_name(f"{database.stem}.{now.date().isoformat()}.backup{database.suffix}")
    target = (
        base
        if not base.exists()
        else base.with_name(
            f"{database.stem}.{now.strftime('%Y-%m-%dT%H%M%S')}.backup{database.suffix}"
        )
    )
    if target.exists():
        raise FileExistsError(f"{target} exists: not overwritten")
    shutil.copy2(database, target)
    if sha256_file(target) != sha256_file(database):
        raise RuntimeError("the backup does not hash like the store")
    return target


def raw_post_rows(path: Path) -> list[tuple[str, str, str | None]]:
    """Every stored `RawPost` row, read-only: invariant 14 is that these are the same before and
    after a command that writes classifications."""
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return connection.execute(
            "SELECT listing_id, doc, text_hash FROM raw_posts ORDER BY listing_id"
        ).fetchall()
    finally:
        connection.close()


def append_dropped_names(
    path: Path,
    *,
    listing_id: str,
    prompt_version: str,
    streets: Collection[str],
    area_names: Collection[str],
    other_city: str | None,
) -> None:
    """One JSON line per post written (#182 A), in the file of the run that wrote it, created with
    its first line. The review report reads these files (`labeling/review.py`)."""
    line = {
        "listing_id": listing_id,
        "prompt_version": prompt_version,
        "dropped_streets": list(streets),
        "dropped_area_names": list(area_names),
        "dropped_other_city": other_city,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")
