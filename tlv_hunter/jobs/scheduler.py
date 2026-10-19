"""Continuous collection on the server (DECISIONS.md #454, #61; `PHASE_5.md` points 1, 6, 8, 11).
**PAID**: every run calls Apify and OpenAI.

    python -m tlv_hunter.jobs.scheduler      # what the stack's `scheduler` service runs

**The settings are the site's** (`ScheduleSettings`, Gate G, #472), read from the store at every
pass, so the admin's change applies at once. On its first start, when the store has no settings row
yet, it writes one from its `.env` values (`RUN_INTERVAL_MINUTES`, `QUIET_FROM`, `QUIET_UNTIL`;
default 30, 00:00, 07:00); from then on those lines are not read and can leave the `.env`.

**The rhythm is rolling (#61, `tlv_hunter/schedule.py`):** the next scheduled run starts one
interval after the start of the last run that was scheduled, or manual and succeeded; a run due in
the quiet hours (Israel time, #442) waits for their end. **"Run now"**: a request the admin made on
the site (`run_now_requested_at`) in the last `RUN_NOW_FRESH` and not yet followed by a manual run
starts one, also in the quiet hours. Each run, scheduled or manual: `run_once --trigger …`, then
`classify_pending --cap 0.05`, then `settle_costs` (free), one after the other, **never in
parallel** (#140). **Once a night**, at the first pass inside the quiet hours: `retention`, a dry
run that only logs, **unless `RETENTION_APPLY=yes`** in the stack's `.env` (read at start), which
Ron sets only after reading a dry run over a dated copy of the server's store (#471 C).

Each command's output, and the scheduler's lines, go to stdout (`docker logs`) and to
`data/measure/scheduler.<date>.log`, in `measure_day.sh`'s form. 3 failed collection runs in a row
are logged and it goes on (the bot's failure alert reads the run records, point 10). **A stop
(SIGTERM) lets the running command finish** (the commands run in their own session), then it starts
nothing more. The rule for Ron: stop the scheduler before any manual job command (#140).

Exit codes: 0, stopped; 1, refused (a setting, no store, or no time zone data).
"""

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.run_record import RunRecord, Trigger
from tlv_hunter.contracts.schedule_settings import (
    INTERVAL_MINUTES,
    SCHEDULE_SETTINGS_SCHEMA_VERSION,
    ScheduleSettings,
)
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME
from tlv_hunter.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_QUIET,
    ZONE,
    in_quiet_hours,
    next_run,
    parse_hh_mm,
    quiet_end,
    rhythm_of,
    run_now_pending,
    timer_base,
)
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.store.base import StaleRecordError

INTERVAL_VARIABLE = "RUN_INTERVAL_MINUTES"
QUIET_FROM_VARIABLE = "QUIET_FROM"
QUIET_UNTIL_VARIABLE = "QUIET_UNTIL"
RETENTION_VARIABLE = "RETENTION_APPLY"
CLASSIFY_CAP = "0.05"
MAX_FAILED_COLLECTIONS = 3
POLL_SECONDS = 5.0
RECENT_RUNS = 50
LOG_DIRECTORY = Path("data") / "measure"
EXIT_STOPPED, EXIT_REFUSED = 0, 1

# A job command: its name and arguments, and where its output lines go -> its exit code.
Runner = Callable[[str, Sequence[str], Callable[[str], None]], int]


class Stop(Protocol):
    """`threading.Event`'s two methods the loop uses."""

    def is_set(self) -> bool: ...

    def wait(self, timeout: float | None = None) -> bool: ...


class Runs(Protocol):
    """What the scheduler reads and writes of Gate G (`SqliteRunStore`)."""

    def recent_runs(self, limit: int | None = None) -> list[RunRecord]: ...

    def get_settings(self) -> ScheduleSettings | None: ...

    def save_settings(
        self, record: ScheduleSettings, *, expected: ScheduleSettings | None
    ) -> ScheduleSettings: ...


class Refused(Exception):
    pass


def read_settings(environ: Mapping[str, str], now: datetime) -> ScheduleSettings:
    """The first row, from the `.env`'s three values (each may be empty: the default)."""
    raw = environ.get(INTERVAL_VARIABLE, "").strip() or str(DEFAULT_INTERVAL_MINUTES)
    try:
        minutes = int(raw)
    except ValueError:
        raise Refused(f"{INTERVAL_VARIABLE} must be whole minutes, got {raw!r}") from None
    if minutes not in INTERVAL_MINUTES:
        raise Refused(
            f"{INTERVAL_VARIABLE} must be from {INTERVAL_MINUTES.start} to {INTERVAL_MINUTES[-1]}"
        )
    quiet = []
    names = (QUIET_FROM_VARIABLE, QUIET_UNTIL_VARIABLE)
    for name, default in zip(names, DEFAULT_QUIET, strict=True):
        value = environ.get(name, "").strip() or default
        try:
            quiet.append(parse_hh_mm(value).strftime("%H:%M"))
        except ValueError:
            raise Refused(f"{name} must be HH:MM, got {value!r}") from None
    return ScheduleSettings(
        schema_version=SCHEDULE_SETTINGS_SCHEMA_VERSION,
        interval_minutes=minutes,
        quiet_from=quiet[0],
        quiet_until=quiet[1],
        run_now_requested_at=None,
        last_digest_at=None,
        updated_by=None,
        updated_at=now,
    )


def retention_applies(environ: Mapping[str, str]) -> bool:
    value = environ.get(RETENTION_VARIABLE, "").strip().lower()
    if value in ("", "no"):
        return False
    if value == "yes":
        return True
    raise Refused(f"{RETENTION_VARIABLE} must be yes or no, got {value!r}")


def subprocess_runner(name: str, args: Sequence[str], write: Callable[[str], None]) -> int:
    """`python -m tlv_hunter.jobs.<name>` in its own session (a stop reaches the scheduler only),
    its output line by line to `write`, its environment this one's (the job keys)."""
    with subprocess.Popen(
        [sys.executable, "-m", f"tlv_hunter.jobs.{name}", *args],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            write(line.rstrip("\n"))
        return process.wait()


class Scheduler:
    def __init__(
        self,
        runs: Runs,
        first_settings: ScheduleSettings,
        log_directory: Path,
        *,
        retention_apply: bool = False,
        runner: Runner = subprocess_runner,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        stdout: TextIO | None = None,
        zone: ZoneInfo | None = None,
    ) -> None:
        self._runs = runs
        self._first = first_settings
        self._log_directory = Path(log_directory)
        self._retention_apply = retention_apply
        self._runner = runner
        self._clock = clock
        self._stdout = sys.stdout if stdout is None else stdout
        self._zone = ZoneInfo(ZONE) if zone is None else zone
        self._failed = 0

    def run(self, stop: Stop) -> None:
        """Until `stop` is set; a wait ends at once on a stop, a running command never does."""
        settings = self._settings()
        self._line(
            f"===== scheduler started {self._israel(self._clock())}; every "
            f"{settings.interval_minutes} minutes from the last run's start; quiet "
            f"{settings.quiet_from}-{settings.quiet_until} {ZONE}; classify cap ${CLASSIFY_CAP}; "
            f"retention {'APPLIES' if self._retention_apply else 'dry run only'}"
        )
        handled: datetime | None = None
        base: datetime | None = None  # this process's own runs, beside the records
        retention_for: datetime | None = None  # the end of the quiet hours it ran in
        quiet_logged = False
        while not stop.is_set():
            settings = self._settings()
            rhythm = rhythm_of(settings)
            now = self._clock()
            recent = self._runs.recent_runs(RECENT_RUNS)
            if run_now_pending(settings, recent, handled, now):
                handled = settings.run_now_requested_at
                assert handled is not None
                self._line(f"===== run now, asked {self._israel(handled, '%H:%M:%S')} on the site")
                if self._cycle("manual", stop) == 0:
                    base = now
                continue
            if in_quiet_hours(now, rhythm, self._zone):
                end = quiet_end(now, rhythm, self._zone)
                if not quiet_logged:
                    self._line(
                        f"===== quiet hours from {self._israel(now, '%Y-%m-%d %H:%M')}: no run "
                        f"until {settings.quiet_until}"
                    )
                    quiet_logged = True
                if retention_for != end:
                    retention_for = end
                    self._job("retention", *(("--apply",) if self._retention_apply else ()))
                    continue
                if stop.wait(min(POLL_SECONDS, (end - now).total_seconds())):
                    break
                continue
            quiet_logged = False
            last = max((t for t in (timer_base(recent), base) if t is not None), default=None)
            due = next_run(last, rhythm, self._zone, now)
            if now >= due:
                self._line(
                    f"===== run {self._israel(now, '%Y-%m-%d %H:%M %Z')}, due "
                    f"{self._israel(due, '%H:%M:%S')}"
                )
                self._cycle("scheduled", stop)
                base = now
                continue
            if stop.wait(min(POLL_SECONDS, (due - now).total_seconds())):
                break
        self._line(f"===== scheduler stopped {self._israel(self._clock())}")

    def _settings(self) -> ScheduleSettings:
        """The site's settings; on the first start the `.env`'s, written as the first row."""
        stored = self._runs.get_settings()
        if stored is not None:
            return stored
        try:
            return self._runs.save_settings(self._first, expected=None)
        except StaleRecordError:  # the site wrote one meanwhile
            found = self._runs.get_settings()
            return self._first if found is None else found

    def _cycle(self, trigger: Trigger, stop: Stop) -> int:
        code = self._job("run_once", "--trigger", trigger)
        if code == 0:
            self._failed = 0
        else:
            self._failed += 1
            self._line(f"===== collection failed ({self._failed} in a row)")
            if self._failed >= MAX_FAILED_COLLECTIONS:
                self._line(
                    f"===== {self._failed} failed collection runs in a row: the next run goes on "
                    "(look at the log; the bot alerts the admin)"
                )
        # A stop during run_once ends it there: its posts wait for the next classify_pending.
        if not stop.is_set():
            self._job("classify_pending", "--cap", CLASSIFY_CAP)
        if not stop.is_set():
            self._job("settle_costs")
        return code

    def _job(self, name: str, *args: str) -> int:
        self._line(f"--- {name}, started {self._israel(self._clock())}")
        code = self._runner(name, args, self._line)
        self._line(f"--- {name}, exit {code}, ended {self._israel(self._clock())}")
        return code

    def _line(self, text: str) -> None:
        print(text, file=self._stdout, flush=True)
        day = self._clock().astimezone(self._zone).date().isoformat()
        self._log_directory.mkdir(parents=True, exist_ok=True)
        with (self._log_directory / f"scheduler.{day}.log").open("a", encoding="utf-8") as log:
            log.write(text + "\n")

    def _israel(self, moment: datetime, form: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
        return moment.astimezone(self._zone).strftime(form)


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    runner: Runner = subprocess_runner,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stdout: TextIO | None = None,
    stop: Stop | None = None,
) -> int:
    out = sys.stdout if stdout is None else stdout
    if argv:
        print("refused: the scheduler takes no arguments; its settings are the site's", file=out)
        return EXIT_REFUSED
    try:
        first = read_settings(environ, clock())
        apply = retention_applies(environ)
        zone = ZoneInfo(ZONE)
        database = repo_root / YamlConfig(config_root).collection().store_root / SQLITE_FILENAME
        if not database.is_file():
            raise Refused(f"no store at {database}")
        runs = SqliteRunStore(database)
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_REFUSED
    except ZoneInfoNotFoundError:
        print(f"refused: no time zone data for {ZONE}", file=out)
        return EXIT_REFUSED
    if stop is None:
        stopping = threading.Event()
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: stopping.set())
        stop = stopping
    Scheduler(
        runs,
        first,
        repo_root / LOG_DIRECTORY,
        retention_apply=apply,
        runner=runner,
        clock=clock,
        stdout=out,
        zone=zone,
    ).run(stop)
    return EXIT_STOPPED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
