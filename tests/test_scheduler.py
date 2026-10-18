"""The scheduler (DECISIONS.md #454; `PHASE_4.md` point 12, replaced): its settings, the quiet hours
in Israel time (#442), the slots on the interval's multiples, run_once then classify_pending
serially (#140), 3 failed collections logged with no exit, a stop that lets the running command
finish, and the log in `measure_day.sh`'s form. A fake runner, clock and stop: no process starts,
nothing sleeps.
"""

import io
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from datetime import time as day_time
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tlv_hunter.jobs import scheduler
from tlv_hunter.jobs.scheduler import (
    CLASSIFY_CAP,
    Refused,
    Scheduler,
    Settings,
    in_quiet_hours,
    next_slot,
    read_settings,
)

ZONE = ZoneInfo("Asia/Jerusalem")
DEFAULT = Settings(timedelta(minutes=30), day_time(0, 0), day_time(7, 0))


def israel(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=ZONE).astimezone(UTC)


class World:
    """A clock that a wait and each command move on, a stop that a test sets after so many
    commands, and the commands run."""

    def __init__(self, start: datetime, *, command_minutes: float = 3) -> None:
        self.now = start
        self.ran: list[tuple[str, tuple[str, ...], datetime]] = []
        self.codes: dict[str, list[int]] = {}
        self.stop_after: int | None = None
        self.stop_during: str | None = None
        self.minutes = command_minutes
        self.stopped = False

    def clock(self) -> datetime:
        return self.now

    def is_set(self) -> bool:
        return self.stopped

    def wait(self, timeout: float | None = None) -> bool:
        if self.stopped:
            return True
        self.now += timedelta(seconds=timeout or 0)
        return False

    def runner(self, name: str, args: Sequence[str], write: Callable[[str], None]) -> int:
        self.ran.append((name, tuple(args), self.now))
        write(f'{{"msg": "{name} says hello"}}')
        if self.stop_during == name:
            self.stopped = True  # SIGTERM arrives while the command runs: it still finishes
        self.now += timedelta(minutes=self.minutes)
        codes = self.codes.get(name)
        code = codes.pop(0) if codes else 0
        if self.stop_after is not None and len(self.ran) >= self.stop_after:
            self.stopped = True
        return code


def run(world: World, tmp_path: Path, settings: Settings = DEFAULT) -> str:
    out = io.StringIO()
    Scheduler(
        settings,
        tmp_path / "measure",
        runner=world.runner,
        clock=world.clock,
        stdout=out,
        zone=ZONE,
    ).run(world)
    return out.getvalue()


# --- settings ---


def test_the_settings_default_to_30_minutes_and_00_00_to_07_00() -> None:
    assert read_settings({}) == DEFAULT
    environ = {"RUN_INTERVAL_MINUTES": "60", "QUIET_FROM": "23:30", "QUIET_UNTIL": "06:00"}
    assert read_settings(environ) == Settings(
        timedelta(minutes=60), day_time(23, 30), day_time(6, 0)
    )


@pytest.mark.parametrize(
    "environ",
    [
        {"RUN_INTERVAL_MINUTES": "half"},
        {"RUN_INTERVAL_MINUTES": "2"},
        {"RUN_INTERVAL_MINUTES": "2000"},
        {"QUIET_FROM": "7am"},
        {"QUIET_UNTIL": "25:00"},
    ],
)
def test_a_wrong_setting_is_refused(environ: dict[str, str]) -> None:
    with pytest.raises(Refused):
        read_settings(environ)


def test_main_refuses_arguments_and_wrong_settings_and_names_them() -> None:
    out = io.StringIO()
    assert scheduler.main(["--now"], stdout=out) == 1 and "no arguments" in out.getvalue()
    out = io.StringIO()
    assert scheduler.main([], environ={"QUIET_FROM": "x"}, stdout=out) == 1
    assert out.getvalue() == "refused: QUIET_FROM must be HH:MM, got 'x'\n"


def test_main_runs_until_stopped(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7))
    world.stopped = True
    out = io.StringIO()
    code = scheduler.main(
        [], environ={}, repo_root=tmp_path, runner=world.runner, clock=world.clock, stdout=out,
        stop=world,
    )  # fmt: skip
    assert code == 0 and (tmp_path / "data" / "measure" / "scheduler.2026-10-18.log").is_file()


# --- the quiet hours, in Israel time (#442) ---


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
def test_no_slot_starts_from_00_00_until_07_00_israel_time(moment: datetime, quiet: bool) -> None:
    assert in_quiet_hours(moment, DEFAULT, ZONE) is quiet


def test_quiet_hours_across_midnight_and_none() -> None:
    late = Settings(timedelta(minutes=30), day_time(23, 0), day_time(6, 0))
    assert in_quiet_hours(israel(18, 23, 30), late, ZONE)
    assert in_quiet_hours(israel(19, 5, 59), late, ZONE)
    assert not in_quiet_hours(israel(19, 6, 0), late, ZONE)
    none = Settings(timedelta(minutes=30), day_time(0, 0), day_time(0, 0))
    assert not in_quiet_hours(israel(19, 3, 0), none, ZONE)


def test_slots_fall_on_the_intervals_multiples() -> None:
    assert next_slot(israel(18, 10, 7), timedelta(minutes=30)) == israel(18, 10, 30)
    assert next_slot(israel(18, 10, 30), timedelta(minutes=30)) == israel(18, 11, 0)
    assert next_slot(israel(18, 10, 7), timedelta(minutes=60)) == israel(18, 11, 0)


# --- the loop ---


def test_each_slot_runs_run_once_then_classify_pending_serially(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7))
    world.stop_after = 4
    run(world, tmp_path)
    assert [(name, args) for name, args, _ in world.ran] == [
        ("run_once", ()),
        ("classify_pending", ("--cap", CLASSIFY_CAP)),
        ("run_once", ()),
        ("classify_pending", ("--cap", CLASSIFY_CAP)),
    ]
    starts = [at for name, _, at in world.ran if name == "run_once"]
    assert starts == [israel(18, 10, 30), israel(18, 11, 0)]
    # Serial: each command starts after the one before it ended (3 minutes each).
    times = [at for _, _, at in world.ran]
    assert all(later - earlier >= timedelta(minutes=3) for earlier, later in pairwise(times))


def test_no_slot_in_the_quiet_hours_and_the_night_is_logged_once(tmp_path: Path) -> None:
    world = World(israel(18, 23, 40))
    world.stop_after = 4
    out = run(world, tmp_path)
    starts = [at for name, _, at in world.ran if name == "run_once"]
    assert starts == [israel(19, 7, 0), israel(19, 7, 30)]
    assert out.count("===== quiet hours from") == 1


def test_a_slot_that_runs_past_the_next_starts_it_at_once(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), command_minutes=20)
    world.stop_after = 4
    out = run(world, tmp_path)
    starts = [at for name, _, at in world.ran if name == "run_once"]
    assert starts == [israel(18, 10, 30), israel(18, 11, 10)]
    assert "===== the slot ran past 11:00: the next starts now" in out


def test_three_failed_collections_are_logged_and_it_goes_on(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7))
    world.codes = {"run_once": [1, 1, 1, 0]}
    world.stop_after = 8
    out = run(world, tmp_path)
    assert [name for name, _, _ in world.ran].count("run_once") == 4
    assert "===== collection failed (3 in a row)" in out
    assert "===== 3 failed collection runs in a row: waiting for the next slot" in out
    assert out.rstrip().splitlines()[-1].startswith("===== scheduler stopped")


def test_a_stop_lets_the_running_command_finish_and_classifies_nothing_more(
    tmp_path: Path,
) -> None:
    world = World(israel(18, 10, 7))
    world.stop_during = "run_once"
    out = run(world, tmp_path)
    assert [name for name, _, _ in world.ran] == ["run_once"]
    assert "--- run_once, exit 0, ended" in out
    assert out.rstrip().splitlines()[-1].startswith("===== scheduler stopped")


def test_a_stop_while_waiting_ends_at_once(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7))
    world.stopped = True
    out = run(world, tmp_path)
    assert world.ran == [] and "===== scheduler stopped" in out


def test_the_log_is_measure_days_form_on_stdout_and_in_the_days_file(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7))
    world.stop_after = 2
    out = run(world, tmp_path)
    log = (tmp_path / "measure" / "scheduler.2026-10-18.log").read_text(encoding="utf-8")
    assert log == out
    lines = out.splitlines()
    assert lines[0].startswith("===== scheduler started 2026-10-18 10:07:00 IDT; a slot every 30")
    assert "quiet 00:00-07:00 Asia/Jerusalem; classify cap $0.05" in lines[0]
    assert lines[1] == "===== slot 2026-10-18 10:30 IDT, started 10:30:00"
    assert lines[2] == "--- run_once, started 2026-10-18 10:30:00 IDT"
    assert lines[3] == '{"msg": "run_once says hello"}'
    assert lines[4] == "--- run_once, exit 0, ended 2026-10-18 10:33:00 IDT"
    assert lines[5] == "--- classify_pending, started 2026-10-18 10:33:00 IDT"


def test_the_real_runner_streams_a_commands_output_and_returns_its_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started: list[dict] = []

    class FakeProcess:
        def __init__(self, command: list[str], **options: object) -> None:
            started.append({"command": command, **options})
            self.stdout = io.StringIO("line one\nline two\n")

        def __enter__(self) -> "FakeProcess":
            return self

        def __exit__(self, *exc: object) -> None:
            pass

        def wait(self) -> int:
            return 2

    monkeypatch.setattr(scheduler.subprocess, "Popen", FakeProcess)
    lines: list[str] = []
    assert scheduler.subprocess_runner("classify_pending", ["--cap", "0.05"], lines.append) == 2
    assert lines == ["line one", "line two"]
    (call,) = started
    assert call["command"][1:] == ["-m", "tlv_hunter.jobs.classify_pending", "--cap", "0.05"]
    assert call["start_new_session"] is True  # a stop reaches the scheduler only
