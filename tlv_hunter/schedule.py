"""The schedule's rhythm (DECISIONS.md #61, #442, #471 point 8 A): a plain module, pure, shared by
the scheduler (`jobs/scheduler.py`), the admin's schedule page (`web/admin.py`) and the bot's
health checks (`telegram/health.py`), so the three agree on when the next run is.

**Rolling, as #61 says:** the next run is the timer's base plus the interval. The base is the start
of the newest run that was scheduled, or manual and succeeded: a manual run that fails does not
reset the timer. A run due inside the quiet hours waits for their end; the first run after the
quiet hours is at their end. With no run at all, the next is now.

The quiet hours are Israel local time (`Asia/Jerusalem`); converting is the schedule's own
(invariant 9). From equal to until means none. They run across midnight when `from` is later.

**Two sources (`PHASE_6.md` §6.7; DECISIONS.md #528, #530):** each source's timer reads its own
runs only. Yad2's rhythm is a `Rhythm` too: its interval, and as its quiet hours the complement of
its daytime hours (from `yad2_hours_until` to `yad2_hours_from`), so every rule here applies to it
unchanged; `None` when its three settings are `None` (no Yad2 runs).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import time as day_time
from zoneinfo import ZoneInfo

from tlv_hunter.contracts.run_record import RunRecord, RunSource
from tlv_hunter.contracts.schedule_settings import ScheduleSettings

ZONE = "Asia/Jerusalem"
DEFAULT_INTERVAL_MINUTES = 30
DEFAULT_QUIET = ("00:00", "07:00")
# What the schedule page offers while Yad2 is off (DECISIONS.md #514, #527, #529).
YAD2_DEFAULTS = (60, "06:00", "23:00")
# A "run now" older than this is not started (the scheduler was down when it was asked).
RUN_NOW_FRESH = timedelta(minutes=15)


@dataclass(frozen=True)
class Rhythm:
    interval: timedelta
    quiet_from: day_time
    quiet_until: day_time

    @property
    def has_quiet_hours(self) -> bool:
        return self.quiet_from != self.quiet_until


def parse_hh_mm(value: str) -> day_time:
    return datetime.strptime(value, "%H:%M").time()


def rhythm_of(settings: ScheduleSettings) -> Rhythm:
    return Rhythm(
        timedelta(minutes=settings.interval_minutes),
        parse_hh_mm(settings.quiet_from),
        parse_hh_mm(settings.quiet_until),
    )


def yad2_rhythm_of(settings: ScheduleSettings) -> Rhythm | None:
    """Yad2's rhythm: runs start from `yad2_hours_from` until before `yad2_hours_until`."""
    if (
        settings.yad2_interval_minutes is None
        or settings.yad2_hours_from is None
        or settings.yad2_hours_until is None
    ):
        return None
    return Rhythm(
        timedelta(minutes=settings.yad2_interval_minutes),
        parse_hh_mm(settings.yad2_hours_until),
        parse_hh_mm(settings.yad2_hours_from),
    )


def in_quiet_hours(moment: datetime, rhythm: Rhythm, zone: ZoneInfo) -> bool:
    local = moment.astimezone(zone).time()
    start, end = rhythm.quiet_from, rhythm.quiet_until
    if start == end:
        return False
    if start < end:
        return start <= local < end
    return local >= start or local < end


def quiet_end(moment: datetime, rhythm: Rhythm, zone: ZoneInfo) -> datetime:
    """The first `quiet_until` (Israel time) after `moment`, in UTC."""
    local = moment.astimezone(zone)
    end = datetime.combine(local.date(), rhythm.quiet_until, zone)
    if end <= local:
        end = datetime.combine(local.date() + timedelta(days=1), rhythm.quiet_until, zone)
    return end.astimezone(UTC)


def timer_base(runs: Iterable[RunRecord], source: RunSource = "facebook") -> datetime | None:
    """The start of the source's newest run that resets its timer (#61): scheduled, or manual
    and succeeded."""
    starts = [
        run.started_at
        for run in runs
        if run.source == source and (run.trigger == "scheduled" or run.status == "succeeded")
    ]
    return max(starts, default=None)


def run_now_pending(
    settings: ScheduleSettings,
    runs: Iterable[RunRecord],
    handled: datetime | None,
    now: datetime,
) -> bool:
    """The admin's "run now" not yet followed by a manual run, and fresh (#61, point 8)."""
    asked = settings.run_now_requested_at
    if asked is None or asked == handled or now - asked > RUN_NOW_FRESH:
        return False
    return not any(run.trigger == "manual" and run.started_at >= asked for run in runs)


def running(runs: Iterable[RunRecord]) -> RunRecord | None:
    """The run in progress: the newest record, when it is still `running`."""
    newest = next(iter(runs), None)
    return newest if newest is not None and newest.status == "running" else None


def next_run(base: datetime | None, rhythm: Rhythm, zone: ZoneInfo, now: datetime) -> datetime:
    """When the next scheduled run starts: the base plus the interval, or now with no base; moved
    to the end of the quiet hours when it falls inside them."""
    due = now if base is None else base + rhythm.interval
    if in_quiet_hours(due, rhythm, zone):
        due = quiet_end(due, rhythm, zone)
    return due


def active_time(start: datetime, end: datetime, rhythm: Rhythm, zone: ZoneInfo) -> timedelta:
    """The time from `start` to `end` outside the quiet hours, to the minute: how long the
    scheduler had to run (the failure alert's "no run for two intervals", point 10)."""
    if end <= start:
        return timedelta(0)
    if not rhythm.has_quiet_hours:
        return end - start
    minute = timedelta(minutes=1)
    total, moment = timedelta(0), start
    while moment < end:
        step = min(minute, end - moment)
        if not in_quiet_hours(moment, rhythm, zone):
            total += step
        moment += step
    return total
