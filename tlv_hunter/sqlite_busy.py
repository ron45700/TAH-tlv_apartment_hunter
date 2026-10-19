"""The one busy timeout every SQLite connection of the package passes (DECISIONS.md #259, #289), and
the one timed `BEGIN IMMEDIATE` every write transaction starts with (point 13 of `PHASE_5.md`,
DECISIONS.md #471).

`BUSY_TIMEOUT_SECONDS`: how many seconds a connection waits on a locked table before `sqlite3`
raises `OperationalError`; Python 3.12's default is 5.0 (docs.python.org, read 2026-10-10,
`ASSUMPTIONS.md` I14). Each module still opens its own connections (#65).

`begin_immediate` changes no behaviour: it measures. A write that waited more than
`SLOW_LOCK_SECONDS` for the lock is logged as a warning, and a lock not obtained within the busy
timeout ("database is locked") as an error before it is raised: the two numbers the WAL decision
rests on (#259, point 13 A). Nothing else is logged: no path, no statement.
"""

import logging
import sqlite3
import time

BUSY_TIMEOUT_SECONDS = 10.0
SLOW_LOCK_SECONDS = 1.0

logger = logging.getLogger(__name__)


def begin_immediate(conn: sqlite3.Connection, module: str) -> None:
    """`BEGIN IMMEDIATE`, timed; `module` names the writer's seam in the log line."""
    started = time.monotonic()
    try:
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.OperationalError as error:
        if "locked" in str(error) or "busy" in str(error):
            logger.error(
                "sqlite write lock: database is locked after %.1f s (%s)",
                time.monotonic() - started,
                module,
            )
        raise
    waited = time.monotonic() - started
    if waited > SLOW_LOCK_SECONDS:
        logger.warning("sqlite write lock: waited %.1f s (%s)", waited, module)
