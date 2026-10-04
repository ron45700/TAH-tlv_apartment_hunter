"""One collection run (task 1.14): wires the modules together and holds no business logic.

The steps, their order, and what a failure at each one leaves behind: DECISIONS.md #79. Only
`WatermarkStore.save_all`, the last write, moves a watermark (invariant 2).
"""

import logging
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_a import DedupResult, dedup_a
from tlv_hunter.images.download import ImageTransport, download_images, urllib_image_transport
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.providers.base import Provider
from tlv_hunter.state.base import WatermarkStore
from tlv_hunter.store.base import Repository
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.watermark.window import CutOff, advance, run_since

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunResult:
    run_started_at: datetime
    since: datetime
    posts: tuple[RawPost, ...]
    """The batch as handed to the store step, with `is_canonical` and `duplicate_of` set."""
    lifecycles: tuple[PostLifecycle, ...]
    """The records the store step saved: one per batch post, then stored canonicals outside it."""
    watermarks: tuple[GroupWatermark, ...]
    cut_off: tuple[CutOff, ...]
    repaired: tuple[str, ...]
    """The listing_ids of stored posts that had no lifecycle record at the start of the run."""


def run_once(
    *,
    provider: Provider,
    repository: Repository,
    watermarks: WatermarkStore,
    group_ids: Sequence[str],
    max_posts: int,
    store_root: Path,
    clock: Callable[[], datetime],
    bootstrap_window: timedelta | None = None,
    image_transport: ImageTransport = urllib_image_transport,
) -> RunResult:
    """One run. `bootstrap_window` set means a bootstrap run: the window is that long, back from
    `run_started_at`, and configured groups with no watermark record get one."""
    step = "repair"
    try:
        repaired = _repair_missing_lifecycles(repository)

        step = "since"
        run_started_at = require_utc(clock())
        if bootstrap_window is None:
            since = run_since(watermarks.get_all(), group_ids)
        else:
            since = run_started_at - bootstrap_window
            _warn_existing_records(watermarks.get_all(), group_ids)
        logger.info(
            "run start: bootstrap %s, since %s, %d groups",
            bootstrap_window is not None,
            since.isoformat(),
            len(group_ids),
        )

        step = "fetch"
        fetched = provider.fetch(group_ids, since)

        step = "annotate"
        annotated = [annotate(post) for post in fetched]

        step = "dedup"
        result = dedup_a(annotated, repository)

        step = "images"
        result = download_images(result, repository, Path(store_root), image_transport)

        step = "store"
        _store(result, repository)

        step = "advance"
        # Re-read: a run that saved since this one started makes `advance` refuse (#79 O9).
        advanced = advance(
            watermarks.get_all(),
            group_ids,
            fetched,
            run_started_at=run_started_at,
            since=since,
            max_posts=max_posts,
        )

        step = "save watermarks"
        watermarks.save_all(advanced.records)
    except BaseException as error:
        logger.error("run failed at step %s (%s)", step, type(error).__name__)
        raise

    for gap in advanced.cut_off:
        logger.warning(
            "group %s cut off: %d rows, window start %s, oldest post %s",
            gap.group_id,
            gap.rows,
            gap.window_start.isoformat(),
            gap.oldest_posted_at.isoformat(),
        )
    states = Counter(record.state for record in result.lifecycles[: len(result.posts)])
    canonicals = sum(1 for post in result.posts if post.is_canonical)
    logger.info(
        "run done: %d rows fetched, %d posts stored (%d canonical, %d duplicate), states %s, "
        "%d stored canonicals outside the batch updated, %d groups cut off, %.0f s",
        len(fetched),
        len(result.posts),
        canonicals,
        len(result.posts) - canonicals,
        dict(sorted(states.items())),
        len(result.lifecycles) - len(result.posts),
        len(advanced.cut_off),
        (require_utc(clock()) - run_started_at).total_seconds(),
    )
    return RunResult(
        run_started_at=run_started_at,
        since=since,
        posts=result.posts,
        lifecycles=result.lifecycles,
        watermarks=advanced.records,
        cut_off=advanced.cut_off,
        repaired=repaired,
    )


def _repair_missing_lifecycles(repository: Repository) -> tuple[str, ...]:
    """#79 O3: a stored post with no lifecycle record gets its initial one. It should not happen:
    in SQLite `upsert_with_lifecycle` writes both in one transaction."""
    missing = repository.find_without_lifecycle()
    for post in missing:
        repository.save_lifecycle(initial_lifecycle(post))
    listing_ids = tuple(post.listing_id for post in missing)
    if listing_ids:
        logger.error(
            "repaired %d stored posts with no lifecycle record: %s",
            len(listing_ids),
            ", ".join(listing_ids),
        )
    return listing_ids


def _warn_existing_records(records: Sequence[GroupWatermark], group_ids: Sequence[str]) -> None:
    """#79 O4: a bootstrap run on a store that already has records is allowed, and named."""
    existing = sorted({record.group_id for record in records} & set(group_ids))
    if existing:
        logger.warning(
            "bootstrap run on groups that already have a watermark record: %s",
            ", ".join(existing),
        )


def _store(result: DedupResult, repository: Repository) -> None:
    """The store step (#79). Each write is its own transaction, so the order decides what a crash
    between two writes leaves behind:

    1. Stored canonicals outside the batch, before the new duplicates that changed them. Saved
       after the duplicate, a crash between the two leaves the duplicate stored and the canonical
       archived for good: only a duplicate new to the store brings it back (#74, #75 E1).
    2. Batch canonicals, then batch duplicates. The provider returns newest first, so a duplicate
       usually comes before its canonical; a duplicate stored without its canonical makes every
       later `dedup_a` raise.

    Every post goes through `upsert_with_lifecycle`, which creates a record only, then
    `save_lifecycle`, which replaces it: a re-fetched post's record has changed.
    """
    records = {record.listing_id: record for record in result.lifecycles}
    in_batch = {post.listing_id for post in result.posts}
    for record in result.lifecycles:
        if record.listing_id not in in_batch:
            repository.save_lifecycle(record)
    canonicals = [post for post in result.posts if post.is_canonical]
    duplicates = [post for post in result.posts if not post.is_canonical]
    for post in canonicals + duplicates:
        record = records[post.listing_id]
        repository.upsert_with_lifecycle(post, record)
        repository.save_lifecycle(record)
