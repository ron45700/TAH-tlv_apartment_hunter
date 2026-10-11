"""The one busy timeout every SQLite connection of the package passes (DECISIONS.md #259, #289).

How many seconds a connection waits on a locked table before `sqlite3` raises
`OperationalError`; Python 3.12's default is 5.0 (docs.python.org, read 2026-10-10,
`ASSUMPTIONS.md` I14). A constant, not a shared helper: each module still opens its own
connections (#65).
"""

BUSY_TIMEOUT_SECONDS = 10.0
