"""Continuous collection on the server (DECISIONS.md #454; `PHASE_4.md` point 12, replaced): a
simple bridge to Phase 5's scheduler. **PAID**: every slot calls Apify and OpenAI.

    python -m tlv_hunter.jobs.scheduler      # what the stack's `scheduler` service runs

Every `RUN_INTERVAL_MINUTES` (default 30), on the multiples of the interval (:00 and :30 by
default), except slots starting from `QUIET_FROM` until `QUIET_UNTIL` Israel time (default
00:00-07:00, #442): `run_once`, then `classify_pending --cap 0.05` (the cap per run of
`measure_day.sh`, #445), one after the other, **never in parallel** (#140). A slot that runs past
the next starts that one at once. The three settings come from the stack's `.env` and are read at
start: a change needs a restart of the service. The job keys come from `jobs.env` and reach the two
commands only; this command reads none.

Each command's output, and the slot lines, go to stdout (`docker logs`) and to
`data/measure/scheduler.<date>.log` (the stack's `appdata/measure/`), in `measure_day.sh`'s form,
so `bash measure_day.sh totals appdata/measure/scheduler.<date>.log` reads them. 3 failed
collection runs in a row are logged, and it waits for the next slot (no silent exit). **A stop
(SIGTERM) lets the running command finish**: the commands run in their own session, so a stop
reaches this process only; it then classifies nothing more and exits. The rule for Ron: stop the
scheduler before any manual job command (#140). The admin-set interval, "run now" and retention stay
Phase 5's.

Exit codes: 0, stopped; 1, refused (a setting, or no time zone data).
"""

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import time as day_time
from pathlib import Path
from typing import Protocol, TextIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from tlv_hunter.jobs.common import REPO_ROOT

ZONE = "Asia/Jerusalem"
INTERVAL_VARIABLE = "RUN_INTERVAL_MINUTES"
QUIET_FROM_VARIABLE = "QUIET_FROM"
QUIET_UNTIL_VARIABLE = "QUIET_UNTIL"
DEFAULT_INTERVAL = 30
DEFAULT_QUIET = ("00:00", "07:00")
INTERVALS = range(5, 24 * 60 + 1)  # minutes
CLASSIFY_CAP = "0.05"
MAX_FAILED_COLLECTIONS = 3
LOG_DIRECTORY = Path("data") / "measure"
EXIT_STOPPED, EXIT_REFUSED = 0, 1

# A job command: its name and arguments, and where its output lines go -> its exit code.
Runner = Callable[[str, Sequence[str], Callable[[str], None]], int]


class Stop(Protocol):
    """`threading.Event`'s two methods the loop uses."""

    def is_set(self) -> bool: ...

    def wait(self, timeout: float | None = None) -> bool: ...


@dataclass(frozen=True)
class Settings:
    interval: timedelta
    quiet_from: day_time
    quiet_until: day_time


class Refused(Exception):
    pass


def read_settings(environ: Mapping[str, str]) -> Settings:
    raw = environ.get(INTERVAL_VARIABLE, "").strip() or str(DEFAULT_INTERVAL)
    try:
        minutes = int(raw)
    except ValueError:
        raise Refused(f"{INTERVAL_VARIABLE} must be whole minutes, got {raw!r}") from None
    if minutes not in INTERVALS:
        raise Refused(f"{INTERVAL_VARIABLE} must be from {INTERVALS.start} to {INTERVALS[-1]}")
    quiet = []
    names = (QUIET_FROM_VARIABLE, QUIET_UNTIL_VARIABLE)
    for name, default in zip(names, DEFAULT_QUIET, strict=True):
        value = environ.get(name, "").strip() or default
        try:
            quiet.append(datetime.strptime(value, "%H:%M").time())
        except ValueError:
            raise Refused(f"{name} must be HH:MM, got {value!r}") from None
    return Settings(timedelta(minutes=minutes), quiet[0], quiet[1])


def in_quiet_hours(moment: datetime, settings: Settings, zone: ZoneInfo) -> bool:
    """Israel time from `quiet_from` until `quiet_until`; across midnight when `from` is later.
    The conversion is the schedule's own (invariant 9)."""
    local = moment.astimezone(zone).time()
    start, end = settings.quiet_from, settings.quiet_until
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


def next_slot(after: datetime, interval: timedelta) -> datetime:
    """The first multiple of the interval strictly after `after` (UTC, from the epoch)."""
    seconds = int(interval.total_seconds())
    stamp = int(after.timestamp())
    return datetime.fromtimestamp((stamp // seconds + 1) * seconds, UTC)


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
        settings: Settings,
        log_directory: Path,
        *,
        runner: Runner = subprocess_runner,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        stdout: TextIO | None = None,
        zone: ZoneInfo | None = None,
    ) -> None:
        self._settings = settings
        self._log_directory = Path(log_directory)
        self._runner = runner
        self._clock = clock
        self._stdout = sys.stdout if stdout is None else stdout
        self._zone = ZoneInfo(ZONE) if zone is None else zone

    def run(self, stop: Stop) -> None:
        """Until `stop` is set; a wait ends at once on a stop, a running command never does."""
        settings = self._settings
        quiet = f"{settings.quiet_from:%H:%M}-{settings.quiet_until:%H:%M} {ZONE}"
        self._line(
            f"===== scheduler started {self._israel(self._clock())}; a slot every "
            f"{int(settings.interval.total_seconds() // 60)} minutes; quiet {quiet}; "
            f"classify cap ${CLASSIFY_CAP}"
        )
        failed = 0
        quiet_logged = False
        slot = next_slot(self._clock(), settings.interval)
        while not stop.is_set():
            if stop.wait(max(0.0, (slot - self._clock()).total_seconds())):
                break
            if in_quiet_hours(slot, settings, self._zone):
                if not quiet_logged:
                    self._line(
                        f"===== quiet hours from {self._israel(slot, '%Y-%m-%d %H:%M')}: no slot "
                        f"until {settings.quiet_until:%H:%M}"
                    )
                    quiet_logged = True
                slot = next_slot(slot, settings.interval)
                continue
            quiet_logged = False
            self._line(
                f"===== slot {self._israel(slot, '%Y-%m-%d %H:%M %Z')}, started "
                f"{self._israel(self._clock(), '%H:%M:%S')}"
            )
            if self._job("run_once") == 0:
                failed = 0
            else:
                failed += 1
                self._line(f"===== collection failed ({failed} in a row)")
                if failed >= MAX_FAILED_COLLECTIONS:
                    self._line(
                        f"===== {failed} failed collection runs in a row: waiting for the next "
                        "slot (look at the log; the scheduler goes on)"
                    )
            # A stop during run_once ends it there: its posts wait for the next classify_pending.
            if not stop.is_set():
                self._job("classify_pending", "--cap", CLASSIFY_CAP)
            slot = next_slot(slot, settings.interval)
            if self._clock() >= slot:
                self._line(
                    f"===== the slot ran past {self._israel(slot, '%H:%M')}: the next starts now"
                )
                slot = self._clock()
        self._line(f"===== scheduler stopped {self._israel(self._clock())}")

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
    repo_root: Path = REPO_ROOT,
    runner: Runner = subprocess_runner,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stdout: TextIO | None = None,
    stop: Stop | None = None,
) -> int:
    out = sys.stdout if stdout is None else stdout
    if argv:
        print("refused: the scheduler takes no arguments; its settings are in the .env", file=out)
        return EXIT_REFUSED
    try:
        settings = read_settings(environ)
        zone = ZoneInfo(ZONE)
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
        settings, repo_root / LOG_DIRECTORY, runner=runner, clock=clock, stdout=out, zone=zone
    ).run(stop)
    return EXIT_STOPPED


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
