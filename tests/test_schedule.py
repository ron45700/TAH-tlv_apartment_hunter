"""The schedule's rhythm (`tlv_hunter/schedule.py`; DECISIONS.md #61, #442, #471 point 8 A): the
quiet hours in Israel time, their end, the timer's base, the next run, the active time between two
moments, "run now" pending, the run in progress. Pure: no store, no clock."""

from datetime import UTC, datetime, timedelta
from datetime import time as day_time
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from tests.test_gate_g import run_record, settings
from tlv_hunter.schedule import (
    RUN_NOW_FRESH,
    Rhythm,
    active_time,
    in_quiet_hours,
    next_run,
    quiet_end,
    rhythm_of,
    run_now_pending,
    running,
    timer_base,
    yad2_rhythm_of,
)

ZONE = ZoneInfo("Asia/Jerusalem")
DEFAULT = Rhythm(timedelta(minutes=30), day_time(0, 0), day_time(7, 0))


def israel(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=ZONE).astimezone(UTC)


def test_the_rhythm_of_the_stored_settings() -> None:
    rhythm = rhythm_of(settings(interval_minutes=45, quiet_from="23:30", quiet_until="06:00"))
    assert rhythm == Rhythm(timedelta(minutes=45), day_time(23, 30), day_time(6, 0))


@pytest.mark.parametrize(
    ("moment", "quiet"),
    [
        (israel(18, 23, 59), False),
        (israel(19, 0, 0), True),
        (israel(19, 6, 59), True),
        (israel(19, 7, 0), False),
        (israel(26, 0, 30), True),  # after the clocks went back (winter time, 2026-10-25)
        (israel(26, 7, 0), False),
    ],
)
def test_no_run_starts_from_00_00_until_07_00_israel_time(moment: datetime, quiet: bool) -> None:
    assert in_quiet_hours(moment, DEFAULT, ZONE) is quiet


def test_quiet_hours_across_midnight_and_none() -> None:
    late = Rhythm(timedelta(minutes=30), day_time(23, 0), day_time(6, 0))
    assert in_quiet_hours(israel(18, 23, 30), late, ZONE)
    assert in_quiet_hours(israel(19, 5, 59), late, ZONE)
    assert not in_quiet_hours(israel(19, 6, 0), late, ZONE)
    none = Rhythm(timedelta(minutes=30), day_time(0, 0), day_time(0, 0))
    assert not in_quiet_hours(israel(19, 3, 0), none, ZONE)
    assert not none.has_quiet_hours


def test_the_end_of_the_quiet_hours_is_the_next_until_in_israel_time() -> None:
    assert quiet_end(israel(19, 0, 10), DEFAULT, ZONE) == israel(19, 7, 0)
    late = Rhythm(timedelta(minutes=30), day_time(23, 0), day_time(6, 0))
    assert quiet_end(israel(18, 23, 30), late, ZONE) == israel(19, 6, 0)
    # The night the clocks go back: 07:00 Israel is 05:00 UTC, an hour later than in summer.
    assert quiet_end(israel(25, 1, 0), DEFAULT, ZONE) == datetime(2026, 10, 25, 5, 0, tzinfo=UTC)


def test_the_timer_is_reset_by_a_scheduled_run_and_by_a_manual_run_that_succeeded() -> None:
    scheduled = run_record(run_id="s", started_at=israel(18, 10, 0), trigger="scheduled")
    failed = run_record(
        run_id="f",
        started_at=israel(18, 10, 10),
        finished_at=israel(18, 10, 12),
        trigger="manual",
        status="failed",
        failure_kind="boom",
    )
    assert timer_base([failed, scheduled]) == israel(18, 10, 0)  # a failed manual run: no reset
    manual = run_record(
        run_id="m", started_at=israel(18, 10, 20), finished_at=israel(18, 10, 22), trigger="manual"
    )
    assert timer_base([manual, failed, scheduled]) == israel(18, 10, 20)
    assert timer_base([]) is None


def test_the_next_run_is_one_interval_after_the_base_and_never_in_the_quiet_hours() -> None:
    now = israel(18, 10, 5)
    assert next_run(None, DEFAULT, ZONE, now) == now
    assert next_run(israel(18, 10, 0), DEFAULT, ZONE, now) == israel(18, 10, 30)
    assert next_run(israel(18, 23, 45), DEFAULT, ZONE, now) == israel(19, 7, 0)
    hourly = Rhythm(timedelta(minutes=60), day_time(0, 0), day_time(7, 0))
    assert next_run(israel(18, 10, 0), hourly, ZONE, now) == israel(18, 11, 0)


def test_the_active_time_leaves_out_the_quiet_hours() -> None:
    assert active_time(israel(18, 22, 0), israel(19, 8, 0), DEFAULT, ZONE) == timedelta(hours=3)
    none = Rhythm(timedelta(minutes=30), day_time(0, 0), day_time(0, 0))
    assert active_time(israel(18, 22, 0), israel(19, 8, 0), none, ZONE) == timedelta(hours=10)
    assert active_time(israel(19, 8, 0), israel(18, 22, 0), DEFAULT, ZONE) == timedelta(0)


def test_run_now_is_pending_until_a_manual_run_follows_it_and_while_fresh() -> None:
    asked = israel(18, 10, 0)
    wanted = settings(run_now_requested_at=asked)
    now = asked + timedelta(minutes=1)
    assert run_now_pending(wanted, [], None, now)
    assert not run_now_pending(wanted, [], asked, now)  # this process started it
    started: Any = run_record(trigger="manual", started_at=asked + timedelta(seconds=5))
    assert not run_now_pending(wanted, [started], None, now)  # started before a restart
    stale = asked + RUN_NOW_FRESH + timedelta(seconds=1)
    assert not run_now_pending(wanted, [], None, stale)
    assert not run_now_pending(settings(), [], None, now)


def test_the_run_in_progress_is_the_newest_record_while_running() -> None:
    live = run_record(run_id="live", status="running", finished_at=None)
    done = run_record(run_id="done")
    assert running([live, done]) == live
    assert running([done, live]) is None
    assert running([]) is None


# --- two sources (PHASE_6.md §6.7, DECISIONS.md #527-#530) ---


def test_yad2s_rhythm_is_its_interval_and_the_complement_of_its_hours() -> None:
    assert yad2_rhythm_of(settings()) is None  # off
    on = settings(yad2_interval_minutes=60, yad2_hours_from="06:00", yad2_hours_until="23:00")
    assert yad2_rhythm_of(on) == Rhythm(timedelta(minutes=60), day_time(23, 0), day_time(6, 0))


def test_each_sources_timer_reads_its_own_runs() -> None:
    start = datetime(2026, 10, 25, 8, 0, tzinfo=UTC)
    facebook = run_record(run_id="f", started_at=start, finished_at=start + timedelta(minutes=5))
    yad2 = run_record(
        run_id="y",
        source="yad2",
        started_at=start + timedelta(minutes=20),
        finished_at=start + timedelta(minutes=40),
        apify_run_id=None,
        charged_events=None,
        window_since=None,
    )
    assert timer_base([yad2, facebook]) == start
    assert timer_base([yad2, facebook], "yad2") == start + timedelta(minutes=20)
