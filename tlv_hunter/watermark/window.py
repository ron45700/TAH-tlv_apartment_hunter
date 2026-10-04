"""The per-group watermark logic (task 1.13): the run's window, and the records after a run.

A plain module with no storage of its own (DECISIONS.md #78). It returns the records unsaved;
task 1.14 writes them through `WatermarkStore.save_all` after a successful run, and writes
nothing after a failed one (invariant 2).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from tlv_hunter.contracts.group_watermark import GROUP_WATERMARK_SCHEMA_VERSION, GroupWatermark
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.parsing.datetimes import require_utc

# The overlap subtracted from the last successful run's start (#78 W2).
BUFFER = timedelta(minutes=15)


class MissingWatermarkError(LookupError):
    """A configured group has no record outside bootstrap (#78 W7)."""

    def __init__(self, group_ids: Sequence[str]) -> None:
        self.group_ids = tuple(group_ids)
        super().__init__(
            f"no watermark record for configured group(s) {', '.join(self.group_ids)}; "
            "a group without a record needs a bootstrap run"
        )


@dataclass(frozen=True)
class CutOff:
    """A group that returned `max_posts` posts or more without reaching its window start: the
    posts published between `window_start` and `oldest_posted_at` may never have been returned."""

    group_id: str
    rows: int
    window_start: datetime
    oldest_posted_at: datetime


@dataclass(frozen=True)
class WatermarkAdvance:
    records: tuple[GroupWatermark, ...]
    """One record per configured group, in configured order. Groups no longer configured are not
    included, so `save_all` leaves their records untouched."""
    cut_off: tuple[CutOff, ...]
    """For task 1.14 to log with the run_id. The group still advances (#78 W3)."""


def run_since(records: Sequence[GroupWatermark], group_ids: Sequence[str]) -> datetime:
    """The run's window start: the configured groups' earliest `last_success_at`, minus the
    buffer (#78 W1). Records of groups no longer configured do not count."""
    by_group = _by_group(records)
    configured = _configured(group_ids)
    missing = [
        group_id
        for group_id in configured
        if group_id not in by_group or by_group[group_id].last_success_at is None
    ]
    if missing:
        raise MissingWatermarkError(missing)
    return min(require_utc(by_group[group_id].last_success_at) for group_id in configured) - BUFFER


def advance(
    records: Sequence[GroupWatermark],
    group_ids: Sequence[str],
    posts: Sequence[RawPost],
    *,
    run_started_at: datetime,
    since: datetime,
    max_posts: int,
) -> WatermarkAdvance:
    """The records after a successful run, from every post `fetch()` returned (#78 W6).

    `run_started_at` is our clock before `fetch()` (#78 W5a); `since` is the window the run
    asked for, from `run_since` or, in a bootstrap run, the bootstrap window. A configured group
    with no record gets a new one here; refusing it outside bootstrap is `run_since`'s job.
    """
    require_utc(run_started_at)
    require_utc(since)
    if since >= run_started_at:
        raise ValueError(f"since {since.isoformat()} is not before {run_started_at.isoformat()}")
    if max_posts <= 0:
        raise ValueError(f"max_posts must be positive, got {max_posts}")
    by_group = _by_group(records)
    configured = _configured(group_ids)

    posts_by_group: dict[str, list[RawPost]] = {group_id: [] for group_id in configured}
    for post in posts:
        if post.group_id not in posts_by_group:
            raise ValueError(
                f"post {post.listing_id} is from group {post.group_id}, not configured"
            )
        posts_by_group[post.group_id].append(post)

    updated: list[GroupWatermark] = []
    cut_off: list[CutOff] = []
    for group_id in configured:
        before = by_group.get(group_id)
        group_posts = posts_by_group[group_id]
        if (
            before is not None
            and before.last_success_at is not None
            and run_started_at < before.last_success_at
        ):
            raise ValueError(
                f"group {group_id}: run started {run_started_at.isoformat()}, before its last "
                f"success {before.last_success_at.isoformat()}"
            )
        watermark = before.watermark if before is not None else None
        failures = before.consecutive_failures if before is not None else 0
        if group_posts:
            newest = max(post.posted_at for post in group_posts)
            # The highest posted_at seen; it never moves backwards.
            watermark = newest if watermark is None else max(watermark, newest)
            failures = 0
        else:
            # A successful run in which the group returned zero rows (#78 W5b).
            failures += 1

        gap = _cut_off(group_id, group_posts, before, since, max_posts)
        if gap is not None:
            cut_off.append(gap)

        updated.append(
            GroupWatermark(
                schema_version=GROUP_WATERMARK_SCHEMA_VERSION,
                group_id=group_id,
                watermark=watermark,
                last_success_at=run_started_at,
                consecutive_failures=failures,
            )
        )
    return WatermarkAdvance(records=tuple(updated), cut_off=tuple(cut_off))


def _cut_off(
    group_id: str,
    group_posts: Sequence[RawPost],
    before: GroupWatermark | None,
    since: datetime,
    max_posts: int,
) -> CutOff | None:
    # Posts arrive newest first, so a group at max_posts may have stopped before its window start.
    # The count is of the posts fetch() returned, after its since filter: a row it dropped there
    # was older than `since`, so that group reached its window. A row skipped under #71 D lowers
    # the count, and such a group can go unreported.
    if len(group_posts) < max_posts:
        return None
    window_start = since
    if before is not None and before.watermark is not None:
        window_start = max(since, before.watermark - BUFFER)
    oldest = min(post.posted_at for post in group_posts)
    if oldest <= window_start:
        return None
    return CutOff(
        group_id=group_id,
        rows=len(group_posts),
        window_start=window_start,
        oldest_posted_at=oldest,
    )


def _by_group(records: Sequence[GroupWatermark]) -> dict[str, GroupWatermark]:
    by_group: dict[str, GroupWatermark] = {}
    for record in records:
        if record.group_id in by_group:
            raise ValueError(f"duplicate watermark record for group {record.group_id}")
        by_group[record.group_id] = record
    return by_group


def _configured(group_ids: Sequence[str]) -> list[str]:
    if not group_ids:
        raise ValueError("group_ids is empty")
    if len(set(group_ids)) != len(group_ids):
        raise ValueError("group_ids contains duplicates")
    return list(group_ids)
