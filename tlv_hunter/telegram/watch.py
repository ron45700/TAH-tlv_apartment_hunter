"""The bot's watch over collection (`PHASE_5.md` points 7, 9, 10; DECISIONS.md #471): wiring, like
`pipeline.py`. It reads the run records and the schedule (Gate G), the watermarks' silence counters,
the grouping's snapshot (the posts as the site holds them) and the user data, and hands them to the
pure `health.py` and `digest.py`. It writes nothing: the bot sends, and records `last_digest_at`.
"""

from collections import defaultdict
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tlv_hunter.accounts.actions import find_admin
from tlv_hunter.contracts.schedule_settings import ScheduleSettings
from tlv_hunter.contracts.user import User
from tlv_hunter.schedule import (
    DEFAULT_INTERVAL_MINUTES,
    DEFAULT_QUIET,
    Rhythm,
    parse_hh_mm,
    rhythm_of,
)
from tlv_hunter.state.base import WatermarkStore
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.telegram.digest import Digest, build_digest
from tlv_hunter.telegram.health import GroupSilence, Problem, problems, silences
from tlv_hunter.userdata.base import UserDataStore
from tlv_hunter.web.grouping import Grouping, Snapshot

RECENT_RUNS = 50
THRESHOLDS_FOR = timedelta(hours=1)  # the silence thresholds are measured again at most hourly

DEFAULT_RHYTHM = Rhythm(
    timedelta(minutes=DEFAULT_INTERVAL_MINUTES),
    parse_hh_mm(DEFAULT_QUIET[0]),
    parse_hh_mm(DEFAULT_QUIET[1]),
)


class Watch:
    def __init__(
        self,
        runs: SqliteRunStore,
        watermarks: WatermarkStore,
        grouping: Grouping,
        userdata: UserDataStore,
        *,
        clock: Callable[[], datetime],
        zone: ZoneInfo,
        group_names: Mapping[str, str] | None = None,
    ) -> None:
        self.runs = runs
        self.group_names = dict(group_names or {})
        self._watermarks = watermarks
        self._grouping = grouping
        self._userdata = userdata
        self._clock = clock
        self.zone = zone
        self._silences: tuple[datetime, list[GroupSilence]] | None = None

    def settings(self) -> ScheduleSettings | None:
        return self.runs.get_settings()

    def rhythm(self) -> Rhythm:
        settings = self.settings()
        return DEFAULT_RHYTHM if settings is None else rhythm_of(settings)

    def admin_chat(self) -> int | None:
        """The admin's chat, when linked and enabled (the digest and the failure alert are the
        admin's only)."""
        admin: User | None = find_admin(self._userdata)
        if admin is None or admin.disabled_at is not None:
            return None
        return admin.telegram_chat_id

    def silences(self, snapshot: Snapshot, now: datetime) -> list[GroupSilence]:
        """Point 9 B; the thresholds measured again at most hourly, the counters read each time."""
        rhythm = self.rhythm()
        held = self._silences
        if held is None or now - held[0] >= THRESHOLDS_FOR:
            posted: dict[str, list[datetime]] = defaultdict(list)
            for post in _posts(snapshot):
                posted[post.group_id].append(post.posted_at)
            measured = silences(
                self._watermarks.get_all(), posted, rhythm, self.zone, self.group_names
            )
            self._silences = (now, measured)
            return measured
        counters = {
            record.group_id: record.consecutive_failures for record in self._watermarks.get_all()
        }
        return [
            GroupSilence(
                group.group_id,
                counters.get(group.group_id, group.runs),
                group.threshold,
                group.name,
            )
            for group in held[1]
        ]

    def problems(self, now: datetime | None = None) -> list[Problem]:
        now = self._clock() if now is None else now
        snapshot = self._grouping.current().snapshot
        pending = [
            other.post.fetched_at
            for other in snapshot.others.values()
            if other.lifecycle.state == "pending"
        ]
        return problems(
            self.runs.recent_runs(RECENT_RUNS),
            self.rhythm(),
            self.zone,
            now,
            pending,
            self.silences(snapshot, now),
        )

    def digest(self, start: datetime, end: datetime) -> Digest:
        snapshot = self._grouping.current().snapshot
        admin = find_admin(self._userdata)
        profile = None if admin is None else self._userdata.get_profile(admin.user_id)
        return build_digest(
            snapshot,
            self.runs.recent_runs(),
            self._userdata.list_sent_alerts(),
            profile,
            self.silences(snapshot, end),
            self.problems(end),
            start,
            end,
            group_names=self.group_names,
        )


def _posts(snapshot: Snapshot):
    for member in snapshot.members.values():
        yield member.post
    for other in snapshot.others.values():
        yield other.post
    for duplicates in snapshot.duplicates.values():
        yield from duplicates
