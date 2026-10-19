"""Collection health: the silent-group thresholds and the failure alert's problems (`PHASE_5.md`
points 9 B and 10 A; DECISIONS.md #78 W5b, #471). Pure: records in, problems out; nothing written.
The bot sends what this finds (`telegram/bot.py`); the digest lists it (`telegram/digest.py`).

**Silent groups (point 9 B).** A group's alert threshold, in counted runs (successful runs in which
it returned zero rows, `GroupWatermark.consecutive_failures`; the quiet hours run nothing and count
nothing): its longest silence in the stored posts (the gap between two consecutive `posted_at`,
outside the quiet hours) in intervals, times `SILENCE_FACTOR`, never below `MIN_SILENT_RUNS`. A
group is *suspect* from half its threshold (the digest names it) and *silent* at it (an alert).

**Problems (point 10 A)**, each with a key: one alert per episode, again only when it clears and
comes back (the bot keeps the keys).
- `failed_runs`: the newest `MAX_FAILED` finished runs all failed;
- `no_run`: no run started for two intervals of active time (the scheduler dead or stuck), or
  `stuck:<run_id>`: a record `running` for longer than `STUCK_AFTER`;
- `pending`: a canonical post pending classification for more than `PENDING_AFTER`;
- `silent:<group_id>`: a group at its threshold.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.contracts.run_record import RunRecord
from tlv_hunter.schedule import Rhythm, active_time

MIN_SILENT_RUNS = 48  # about a day of active hours at 30 minutes
SILENCE_FACTOR = 1.5
MAX_FAILED = 3
STUCK_AFTER = timedelta(minutes=90)  # a run's deadline (5 min) and its photos (30 min), and more
PENDING_AFTER = timedelta(hours=2)
LONGEST_GAPS = 5  # the longest raw gaps measured in active time


@dataclass(frozen=True)
class Problem:
    key: str
    text: str


@dataclass(frozen=True)
class GroupSilence:
    group_id: str
    runs: int
    threshold: int

    @property
    def silent(self) -> bool:
        return self.runs >= self.threshold

    @property
    def suspect(self) -> bool:
        return self.runs * 2 >= self.threshold


def silent_threshold(posted: Iterable[datetime], rhythm: Rhythm, zone: ZoneInfo) -> int:
    """Point 9 B for one group, from its stored publications."""
    times = sorted(posted)
    gaps = sorted((b - a, a, b) for a, b in zip(times, times[1:], strict=False))
    longest = max(
        (active_time(a, b, rhythm, zone) for _, a, b in gaps[-LONGEST_GAPS:]),
        default=timedelta(0),
    )
    runs = math.ceil(longest / rhythm.interval * SILENCE_FACTOR)
    return max(MIN_SILENT_RUNS, runs)


def silences(
    watermarks: Sequence[GroupWatermark],
    posted_by_group: Mapping[str, Sequence[datetime]],
    rhythm: Rhythm,
    zone: ZoneInfo,
) -> list[GroupSilence]:
    return [
        GroupSilence(
            group_id=record.group_id,
            runs=record.consecutive_failures,
            threshold=silent_threshold(posted_by_group.get(record.group_id, ()), rhythm, zone),
        )
        for record in sorted(watermarks, key=lambda r: r.group_id)
    ]


def problems(
    runs: Sequence[RunRecord],
    rhythm: Rhythm,
    zone: ZoneInfo,
    now: datetime,
    pending_since: Iterable[datetime],
    groups: Sequence[GroupSilence],
) -> list[Problem]:
    """`runs` newest first. What stands now, each with its episode's key."""
    found: list[Problem] = []
    finished = [run for run in runs if run.status != "running"]
    newest = finished[:MAX_FAILED]
    if len(newest) == MAX_FAILED and all(run.status == "failed" for run in newest):
        found.append(
            Problem(
                "failed_runs",
                f"{MAX_FAILED} ריצות איסוף אחרונות נכשלו. האחרונה: {newest[0].failure_kind or ''}",
            )
        )
    if runs:
        last = runs[0]
        if last.status == "running":
            if now - last.started_at > STUCK_AFTER:
                minutes = int((now - last.started_at).total_seconds() // 60)
                found.append(Problem(f"stuck:{last.run_id}", f"ריצת איסוף רצה כבר {minutes} דקות."))
        elif active_time(last.started_at, now, rhythm, zone) > 2 * rhythm.interval:
            found.append(Problem("no_run", "לא התחילה ריצת איסוף כבר שני מרווחים: המתזמן לא רץ?"))
    waiting = [moment for moment in pending_since if now - moment > PENDING_AFTER]
    if waiting:
        found.append(
            Problem(
                "pending",
                f"{len(waiting)} מודעות ממתינות לסיווג יותר משעתיים: הסיווג נכשל?",
            )
        )
    for group in groups:
        if group.silent:
            found.append(
                Problem(
                    f"silent:{group.group_id}",
                    f"הקבוצה {group.group_id} לא החזירה אף פוסט ב-{group.runs} ריצות "
                    f"(הסף {group.threshold}).",
                )
            )
    return found
