"""Retention's rule (`BASELINE.md` §5, invariant 3; DECISIONS.md #46, #63, #77 D4b, #255, #471
points 1–4): what to archive, what to delete, what is kept. A plain module: the plan is pure; the
two helpers at the end read the photo folder. `jobs/retention.py` applies it.

- **A group** is a canonical post and its dedup A duplicates; a duplicate follows its canonical's
  clock (point 3 A): a repost already moves the canonical's `last_published_at`. A duplicate whose
  canonical is not stored keeps its own clock.
- **Archive** at `ARCHIVE_AFTER` (25 days, 25 × 24 hours from the stored UTC instant) since the
  canonical's last publication, from `active`, `rejected` or `pending`: the canonical becomes
  `archived` (its reason kept), its photo files are deleted and its `PostImage` entries removed;
  the duplicates' photo files and entries go with it, their records otherwise unchanged.
- **Delete** at `DELETE_AFTER` (40 days): the duplicates first, then the canonical (`dedup_a` raises
  on a duplicate whose canonical is gone), each `RawPost`, `PostLifecycle` and `Listing` together,
  with the users' marks on them.
- **Exempt from deletion, not from the archive's photo deletion:** a canonical flagged "lied" or
  reported as wrongly classified (`rejection_reason` `flagged` or `misclassified`), or with an open
  report. A left-out post keeps `misclassified` and stays exempt (decided by the build: deletion
  cannot be undone). Once restored, a post follows the rule again.
- **Orphan photos** (point 4): a file under `images/` that no `PostImage` names, older than
  `ORPHAN_MIN_AGE`.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tlv_hunter.contracts.post_lifecycle import USER_REASONS, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost

ARCHIVE_AFTER = timedelta(days=25)
DELETE_AFTER = timedelta(days=40)
ORPHAN_MIN_AGE = timedelta(hours=24)
IMAGES_DIR = "images"


@dataclass(frozen=True)
class Group:
    canonical: str
    duplicates: tuple[str, ...]
    last_published_at: datetime
    state: str
    exempt_because: str | None


@dataclass(frozen=True)
class Plan:
    now: datetime
    archive: tuple[Group, ...]
    """Groups whose canonical is archived now (its duplicates' photos go with it)."""
    delete: tuple[Group, ...]
    """Groups deleted now, duplicates first."""
    kept: tuple[Group, ...]
    """Groups past `DELETE_AFTER` kept by an exemption."""

    @property
    def to_clear(self) -> tuple[str, ...]:
        """The posts whose photos the archive deletes: each archived canonical and its
        duplicates."""
        return tuple(i for group in self.archive for i in (group.canonical, *group.duplicates))

    @property
    def to_delete(self) -> tuple[str, ...]:
        """The delete order: each group's duplicates, then its canonical."""
        return tuple(i for group in self.delete for i in (*group.duplicates, group.canonical))


def exemption(lifecycle: PostLifecycle, open_report_ids: set[str]) -> str | None:
    """Why a canonical is never deleted (invariant 3, #255), or `None`."""
    if lifecycle.rejection_reason in USER_REASONS:
        return lifecycle.rejection_reason
    if lifecycle.listing_id in open_report_ids:
        return "open_report"
    return None


def groups(posts: Sequence[RawPost], lifecycles: Mapping[str, PostLifecycle]) -> list[Group]:
    """Every stored canonical with its stored duplicates; posts with no lifecycle record are left
    out (the next collection run gives them one, #79 O3)."""
    stored = {post.listing_id for post in posts}
    duplicates: dict[str, list[str]] = defaultdict(list)
    heads: list[str] = []
    for post in sorted(posts, key=lambda p: p.listing_id):
        if post.listing_id not in lifecycles:
            continue
        if post.is_canonical is False and post.duplicate_of in stored:
            duplicates[post.duplicate_of].append(post.listing_id)
        else:
            heads.append(post.listing_id)
    found = []
    for listing_id in heads:
        record = lifecycles[listing_id]
        found.append(
            Group(
                canonical=listing_id,
                duplicates=tuple(i for i in duplicates[listing_id] if i in lifecycles),
                last_published_at=record.last_published_at,
                state=record.state,
                exempt_because=None,
            )
        )
    return found


def plan(
    posts: Sequence[RawPost],
    lifecycles: Mapping[str, PostLifecycle],
    open_report_ids: set[str],
    now: datetime,
) -> Plan:
    archive, delete, kept = [], [], []
    for group in groups(posts, lifecycles):
        age = now - group.last_published_at
        if age < ARCHIVE_AFTER:
            continue
        reason = exemption(lifecycles[group.canonical], open_report_ids)
        group = Group(**{**group.__dict__, "exempt_because": reason})
        if age >= DELETE_AFTER and reason is None:
            delete.append(group)
            continue
        if age >= DELETE_AFTER:
            kept.append(group)
        if group.state != "archived" or _has_photos(group, lifecycles):
            archive.append(group)
    return Plan(now=now, archive=tuple(archive), delete=tuple(delete), kept=tuple(kept))


def archived(record: PostLifecycle, *, canonical: bool) -> PostLifecycle:
    """The record after the archive: no photo entries; a canonical also `archived`, its reason
    kept (`BASELINE.md` §5)."""
    changes: dict[str, object] = {"images": []}
    if canonical:
        changes["state"] = "archived"
    return PostLifecycle.model_validate({**record.model_dump(), **changes})


def photo_paths(records: Iterable[PostLifecycle]) -> set[str]:
    """The relative paths every given record names (`images/<listing_id>/<file>`)."""
    return {
        image.local_path
        for record in records
        for image in record.images
        if image.local_path is not None
    }


def orphan_files(store_root: Path, named: set[str], now: datetime) -> list[Path]:
    """Files under `<store_root>/images/` no record names, last changed `ORPHAN_MIN_AGE` or more
    before `now` (a second guard beside the scheduler's one run at a time)."""
    folder = Path(store_root) / IMAGES_DIR
    if not folder.is_dir():
        return []
    found = []
    cutoff = now.timestamp() - ORPHAN_MIN_AGE.total_seconds()
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(store_root).as_posix()
        if relative not in named and path.stat().st_mtime <= cutoff:
            found.append(path)
    return found


def _has_photos(group: Group, lifecycles: Mapping[str, PostLifecycle]) -> bool:
    return any(
        image.local_path is not None
        for listing_id in (group.canonical, *group.duplicates)
        for image in lifecycles[listing_id].images
    )
