"""The scheduler (DECISIONS.md #454, #61; `PHASE_5.md` points 1, 6, 8): the settings read from the
store at every pass (the first row written from the `.env`), the rolling rhythm, "run now", run_once
then classify_pending then settle_costs serially (#140), retention once a night inside the quiet
hours (a dry run unless `RETENTION_APPLY=yes`), 3 failed collections logged, a stop that lets the
running command finish, and the log in `measure_day.sh`'s form. A fake run store, runner, clock and
stop: no process starts, nothing sleeps. The fake `run_once` writes its run's record, as the real
one does.
"""

import io
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tests.conftest import CONFIG_ROOT, SQLITE_FILENAME
from tests.test_gate_g import run_record, settings
from tlv_hunter.contracts.run_record import RunRecord
from tlv_hunter.contracts.schedule_settings import ScheduleSettings
from tlv_hunter.jobs import scheduler
from tlv_hunter.jobs.scheduler import (
    CLASSIFY_CAP,
    Refused,
    Scheduler,
    read_settings,
    retention_applies,
)
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.store.base import StaleRecordError

ZONE = ZoneInfo("Asia/Jerusalem")


def israel(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=ZONE).astimezone(UTC)


class FakeRuns:
    """Gate G's store in memory: the runs newest first, the one settings row."""

    def __init__(self, stored: ScheduleSettings | None = None) -> None:
        self.runs: list[RunRecord] = []
        self.stored = stored

    def recent_runs(self, limit: int | None = None) -> list[RunRecord]:
        return self.runs[:limit] if limit is not None else list(self.runs)

    def get_settings(self) -> ScheduleSettings | None:
        return self.stored

    def save_settings(
        self, record: ScheduleSettings, *, expected: ScheduleSettings | None
    ) -> ScheduleSettings:
        if self.stored != expected:
            raise StaleRecordError("schedule")
        self.stored = record
        return record


class World:
    """A clock that a wait and each command move on, a stop that a test sets after so many
    commands, the commands run, and the run records the fake `run_once` writes."""

    def __init__(self, start: datetime, runs: FakeRuns, *, command_minutes: float = 3) -> None:
        self.now = start
        self.runs = runs
        self.ran: list[tuple[str, tuple[str, ...], datetime]] = []
        self.codes: dict[str, list[int]] = {}
        self.stop_after: int | None = None
        self.stop_during: str | None = None
        self.on_run: Callable[[int], None] | None = None
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
        started = self.now
        self.ran.append((name, tuple(args), started))
        write(f'{{"msg": "{name} says hello"}}')
        if self.stop_during == name:
            self.stopped = True  # SIGTERM arrives while the command runs: it still finishes
        self.now += timedelta(minutes=self.minutes)
        codes = self.codes.get(name)
        code = codes.pop(0) if codes else 0
        if name == "run_once":
            self.runs.runs.insert(
                0,
                run_record(
                    run_id=f"run{len(self.ran)}",
                    trigger=args[1],
                    started_at=started,
                    finished_at=self.now,
                    status="succeeded" if code == 0 else "failed",
                    failure_kind=None if code == 0 else "boom",
                ),
            )
            if self.on_run is not None:
                self.on_run(len(self.started("run_once")))
        if self.stop_after is not None and len(self.ran) >= self.stop_after:
            self.stopped = True
        return code

    def started(self, name: str) -> list[datetime]:
        return [at for command, _, at in self.ran if command == name]


def run(world: World, tmp_path: Path, *, retention_apply: bool = False) -> str:
    out = io.StringIO()
    Scheduler(
        world.runs,
        settings(),
        tmp_path / "measure",
        retention_apply=retention_apply,
        runner=world.runner,
        clock=world.clock,
        stdout=out,
        zone=ZONE,
    ).run(world)
    return out.getvalue()


# --- settings ---


def test_the_first_settings_default_to_30_minutes_and_00_00_to_07_00() -> None:
    first = read_settings({}, israel(18, 10))
    assert (first.interval_minutes, first.quiet_from, first.quiet_until) == (30, "00:00", "07:00")
    assert first.updated_by is None and first.run_now_requested_at is None
    environ = {"RUN_INTERVAL_MINUTES": "60", "QUIET_FROM": "23:30", "QUIET_UNTIL": "6:00"}
    other = read_settings(environ, israel(18, 10))
    assert (other.interval_minutes, other.quiet_from, other.quiet_until) == (60, "23:30", "06:00")


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
        read_settings(environ, israel(18, 10))


def test_retention_applies_only_when_set_to_yes() -> None:
    assert retention_applies({}) is False
    assert retention_applies({"RETENTION_APPLY": "no"}) is False
    assert retention_applies({"RETENTION_APPLY": "YES"}) is True
    with pytest.raises(Refused):
        retention_applies({"RETENTION_APPLY": "maybe"})


def store_at(repo_root: Path) -> Path:
    database = repo_root / "data" / "store" / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    SqliteRunStore(database)
    return database


def test_main_refuses_arguments_wrong_settings_and_no_store(tmp_path: Path) -> None:
    out = io.StringIO()
    assert scheduler.main(["--now"], stdout=out) == 1 and "no arguments" in out.getvalue()
    out = io.StringIO()
    assert scheduler.main([], environ={"QUIET_FROM": "x"}, stdout=out) == 1
    assert out.getvalue() == "refused: QUIET_FROM must be HH:MM, got 'x'\n"
    out = io.StringIO()
    code = scheduler.main([], environ={}, config_root=CONFIG_ROOT, repo_root=tmp_path, stdout=out)
    assert code == 1 and out.getvalue().startswith("refused: no store at")


def test_main_writes_the_first_row_from_the_env_and_runs_until_stopped(tmp_path: Path) -> None:
    database = store_at(tmp_path)
    world = World(israel(18, 10, 7), FakeRuns())
    world.stopped = True
    out = io.StringIO()
    code = scheduler.main(
        [],
        environ={"RUN_INTERVAL_MINUTES": "45"},
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        runner=world.runner,
        clock=world.clock,
        stdout=out,
        stop=world,
    )
    assert code == 0 and (tmp_path / "data" / "measure" / "scheduler.2026-10-18.log").is_file()
    stored = SqliteRunStore(database).get_settings()
    assert stored is not None and stored.interval_minutes == 45 and stored.updated_by is None
    assert "retention dry run only" in out.getvalue()


# --- the rolling rhythm (#61) ---


def test_each_run_is_run_once_then_classify_pending_then_settle_costs_serially(
    tmp_path: Path,
) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()))
    world.stop_after = 6
    run(world, tmp_path)
    assert [(name, args) for name, args, _ in world.ran] == [
        ("run_once", ("--trigger", "scheduled")),
        ("classify_pending", ("--cap", CLASSIFY_CAP)),
        ("settle_costs", ()),
    ] * 2
    # No record: the first run starts at once; the next one interval after its start.
    assert world.started("run_once") == [israel(18, 10, 7), israel(18, 10, 37)]
    times = [at for _, _, at in world.ran]
    assert all(later - earlier >= timedelta(minutes=3) for earlier, later in pairwise(times))


def test_the_next_run_follows_the_stored_records_after_a_restart(tmp_path: Path) -> None:
    runs = FakeRuns(settings())
    runs.runs = [run_record(started_at=israel(18, 10, 0), finished_at=israel(18, 10, 3))]
    world = World(israel(18, 10, 7), runs)
    world.stop_after = 3
    run(world, tmp_path)
    assert world.started("run_once") == [israel(18, 10, 30)]


def test_a_run_that_lasts_past_the_interval_is_followed_at_once(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()), command_minutes=12)
    world.stop_after = 6
    run(world, tmp_path)
    assert world.started("run_once") == [israel(18, 10, 7), israel(18, 10, 43)]


def test_a_new_interval_applies_at_the_next_pass(tmp_path: Path) -> None:
    runs = FakeRuns(settings())
    world = World(israel(18, 10, 7), runs)

    def change(count: int) -> None:
        if count == 1:
            runs.stored = settings(interval_minutes=60)

    world.on_run = change
    world.stop_after = 6
    run(world, tmp_path)
    assert world.started("run_once") == [israel(18, 10, 7), israel(18, 11, 7)]


def test_no_run_in_the_quiet_hours_and_retention_once_a_night(tmp_path: Path) -> None:
    runs = FakeRuns(settings())
    runs.runs = [run_record(started_at=israel(18, 23, 40), finished_at=israel(18, 23, 43))]
    world = World(israel(18, 23, 45), runs)
    world.stop_after = 4
    out = run(world, tmp_path)
    assert [name for name, _, _ in world.ran] == [
        "retention",
        "run_once",
        "classify_pending",
        "settle_costs",
    ]
    assert world.ran[0][1] == ()  # a dry run
    assert world.started("retention") == [israel(19, 0, 0)]
    assert world.started("run_once") == [israel(19, 7, 0)]
    assert out.count("===== quiet hours from") == 1


def test_retention_applies_when_ron_set_it(tmp_path: Path) -> None:
    world = World(israel(19, 2, 0), FakeRuns(settings()))
    world.stop_after = 1
    out = run(world, tmp_path, retention_apply=True)
    assert world.ran[0][:2] == ("retention", ("--apply",))
    assert "retention APPLIES" in out


# --- run now (#61) ---


def test_run_now_starts_a_manual_run_at_once_even_in_the_quiet_hours_and_once(
    tmp_path: Path,
) -> None:
    asked = israel(19, 2, 0)
    runs = FakeRuns(settings(run_now_requested_at=asked))
    world = World(asked + timedelta(seconds=30), runs)
    world.stop_after = 4
    out = run(world, tmp_path)
    assert [(name, args) for name, args, _ in world.ran][:3] == [
        ("run_once", ("--trigger", "manual")),
        ("classify_pending", ("--cap", CLASSIFY_CAP)),
        ("settle_costs", ()),
    ]
    assert world.ran[3][0] == "retention"  # then the night goes on: no second manual run
    assert "===== run now, asked" in out


def test_a_stale_or_already_followed_run_now_is_not_started(tmp_path: Path) -> None:
    asked = israel(18, 10, 0)
    runs = FakeRuns(settings(run_now_requested_at=asked))
    runs.runs = [
        run_record(trigger="scheduled", started_at=asked - timedelta(minutes=5), finished_at=asked)
    ]
    world = World(asked + timedelta(minutes=16), runs)  # older than 15 minutes
    world.stop_after = 1
    run(world, tmp_path)
    assert world.ran[0][1] == ("--trigger", "scheduled")
    runs = FakeRuns(settings(run_now_requested_at=asked))
    runs.runs = [
        run_record(
            trigger="manual",
            started_at=asked + timedelta(seconds=3),
            finished_at=asked + timedelta(minutes=1),
        )
    ]
    world = World(asked + timedelta(minutes=2), runs)
    world.stop_after = 1
    run(world, tmp_path)
    assert world.ran[0][1] == ("--trigger", "scheduled")
    assert world.ran[0][2] == asked + timedelta(minutes=30, seconds=3)


def test_a_manual_run_that_fails_does_not_reset_the_timer(tmp_path: Path) -> None:
    asked = israel(18, 10, 10)
    runs = FakeRuns(settings(run_now_requested_at=asked))
    runs.runs = [run_record(started_at=israel(18, 10, 0), finished_at=israel(18, 10, 3))]
    world = World(asked, runs)
    world.codes = {"run_once": [1, 0]}
    world.stop_after = 4
    run(world, tmp_path)
    assert world.started("run_once") == [asked, israel(18, 10, 30)]
    runs = FakeRuns(settings(run_now_requested_at=asked))
    runs.runs = [run_record(started_at=israel(18, 10, 0), finished_at=israel(18, 10, 3))]
    world = World(asked, runs)
    world.stop_after = 4
    run(world, tmp_path)
    assert world.started("run_once") == [asked, israel(18, 10, 40)]


# --- failures, stops, the log ---


def test_three_failed_collections_are_logged_and_it_goes_on(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()))
    world.codes = {"run_once": [1, 1, 1, 0]}
    world.stop_after = 12
    out = run(world, tmp_path)
    assert len(world.started("run_once")) == 4
    assert "===== collection failed (3 in a row)" in out
    assert "===== 3 failed collection runs in a row: the next run goes on" in out
    assert out.rstrip().splitlines()[-1].startswith("===== scheduler stopped")


def test_a_stop_lets_the_running_command_finish_and_starts_nothing_more(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()))
    world.stop_during = "run_once"
    out = run(world, tmp_path)
    assert [name for name, _, _ in world.ran] == ["run_once"]
    assert "--- run_once, exit 0, ended" in out
    assert out.rstrip().splitlines()[-1].startswith("===== scheduler stopped")


def test_a_stop_while_waiting_ends_at_once(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()))
    world.stopped = True
    out = run(world, tmp_path)
    assert world.ran == [] and "===== scheduler stopped" in out


def test_the_log_is_measure_days_form_on_stdout_and_in_the_days_file(tmp_path: Path) -> None:
    world = World(israel(18, 10, 7), FakeRuns(settings()))
    world.stop_after = 2
    out = run(world, tmp_path)
    log = (tmp_path / "measure" / "scheduler.2026-10-18.log").read_text(encoding="utf-8")
    assert log == out
    lines = out.splitlines()
    assert lines[0].startswith("===== scheduler started 2026-10-18 10:07:00 IDT; every 30 minutes")
    assert "quiet 00:00-07:00 Asia/Jerusalem; classify cap $0.05" in lines[0]
    assert lines[1] == "===== run 2026-10-18 10:07 IDT, due 10:07:00"
    assert lines[2] == "--- run_once, started 2026-10-18 10:07:00 IDT"
    assert lines[3] == '{"msg": "run_once says hello"}'
    assert lines[4] == "--- run_once, exit 0, ended 2026-10-18 10:10:00 IDT"
    assert lines[5] == "--- classify_pending, started 2026-10-18 10:10:00 IDT"


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
