"""One Yad2 collection run (`PHASE_6.md` §6.5, build step 4): wiring, like `pipeline.py`, holding
no business logic. The steps and what a failure at each leaves behind:

1. `known`: every stored Yad2 post's `listing_id` → `last_published_at`, read from the store.
2. `collect`: the seam reads Yad2's pages (`yad2/collector.py`); a block raises `Yad2Blocked`.
   Nothing is written before this step ends, so a blocked or failed run stores nothing and marks
   no token as seen (invariant 2, #492).
3. `annotate`, `dedup` (dedup A within Yad2, never for an agency listing, #500, #508), the bumps
   (`dedup.stage_a.bumped_lifecycle`, #520, #524), the photos (the existing download, §6.9; a
   bump that returns an archived listing downloads its photos again from its stored `RawPost`).
   Photo files may be written; a failed run leaves them to retention's orphan sweep (#471).
4. `store`: the new posts, their records and every changed record **in one transaction**
   (`Repository.save_batch`, #502 point 18), by compare and set (#260): a record another writer
   changed is merged (`run_merge.py`) and the whole write tried again, at most
   `pipeline.STORE_ATTEMPTS` in all.
5. `save watermark`: the `yad2-tel-aviv` record (#496) last, as Facebook's: its rows are the new
   listings and the bumps. A failure between steps 4 and 5 leaves the posts stored and the record
   unmoved; nothing is missed, since what was stored was read whole.

The run's `RunRecord` (`source` `"yad2"`) is written by the Yad2 run command (build step 5) from
the result's counts, or from `Yad2Blocked`'s reason.
"""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_a import DedupResult, bumped_lifecycle, dedup_a
from tlv_hunter.images.download import ImageTransport, download_images, urllib_image_transport
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.parsing.ids import YAD2_SOURCE
from tlv_hunter.pipeline import STORE_ATTEMPTS
from tlv_hunter.run_merge import merge_run_record
from tlv_hunter.state.base import WatermarkStore
from tlv_hunter.store.base import Repository, StaleRecordError
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.watermark.window import advance_group, run_since
from tlv_hunter.yad2.collector import Bump, Yad2Collection, Yad2Collector
from tlv_hunter.yad2.mapping import GROUP_ID

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Yad2RunResult:
    run_started_at: datetime
    collection: Yad2Collection
    posts: tuple[RawPost, ...]
    """The new listings as stored, with `is_canonical` and `duplicate_of` set."""
    lifecycles: tuple[PostLifecycle, ...]
    """Every record written: one per new listing, then the stored ones changed."""
    bumped: tuple[str, ...]
    """The `listing_id`s whose `last_published_at` a bump moved."""
    watermark: GroupWatermark


def run_yad2(
    *,
    collector: Yad2Collector,
    repository: Repository,
    watermarks: WatermarkStore,
    store_root: Path,
    clock: Callable[[], datetime],
    bootstrap: bool,
    image_transport: ImageTransport = urllib_image_transport,
    image_sleep: Callable[[float], None] | None = None,
) -> Yad2RunResult:
    """One run. `bootstrap`: the first run, 3 list pages, no bump check (#493); outside it the
    `yad2-tel-aviv` record must exist (`MissingWatermarkError`, as a Facebook group's)."""
    step = "since"
    try:
        run_started_at = require_utc(clock())
        records = watermarks.get_all()
        if not bootstrap:
            run_since(records, [GROUP_ID])
        elif any(record.group_id == GROUP_ID for record in records):
            logger.warning("yad2 bootstrap run on a store that has the %s record", GROUP_ID)
        logger.info("yad2 run start: bootstrap %s", bootstrap)

        step = "known"
        known = _known(repository)

        step = "collect"
        collection = collector.collect(known, bootstrap=bootstrap)

        step = "annotate"
        annotated = [annotate(listing.post) for listing in collection.listings]

        step = "dedup"
        result = dedup_a(annotated, repository)

        step = "bumps"
        result, returned, bumped = _with_bumps(result, collection.bumps, repository)

        step = "images"
        downloaded = download_images(
            DedupResult(
                posts=result.posts + returned, lifecycles=result.lifecycles, read=result.read
            ),
            repository,
            Path(store_root),
            image_transport,
            sleep=image_sleep,
            now=run_started_at,
        )

        step = "store"
        lifecycles = _store(result.posts, downloaded, repository)

        step = "save watermark"
        # Re-read: a run that saved since this one started makes `advance_group` refuse.
        before = next((r for r in watermarks.get_all() if r.group_id == GROUP_ID), None)
        published = [post.posted_at for post in result.posts]
        published += [bump.updated_at for bump in collection.bumps if bump.listing_id in bumped]
        watermark = advance_group(before, GROUP_ID, published, run_started_at=run_started_at)
        watermarks.save_all([watermark])
    except BaseException as error:
        logger.error("yad2 run failed at step %s (%s)", step, type(error).__name__)
        raise

    logger.info(
        "yad2 run done: %d new listings stored, %d bumps, %d listing pages skipped, %.0f s",
        len(result.posts),
        len(bumped),
        len(collection.skipped),
        (require_utc(clock()) - run_started_at).total_seconds(),
    )
    return Yad2RunResult(
        run_started_at=run_started_at,
        collection=collection,
        posts=result.posts,
        lifecycles=lifecycles,
        bumped=tuple(bumped),
        watermark=watermark,
    )


def _known(repository: Repository) -> dict[str, datetime]:
    known = {}
    for post in repository.query():
        if post.source != YAD2_SOURCE:
            continue
        record = repository.get_lifecycle(post.listing_id)
        known[post.listing_id] = post.posted_at if record is None else record.last_published_at
    return known


def _with_bumps(
    result: DedupResult, bumps: Sequence[Bump], repository: Repository
) -> tuple[DedupResult, tuple[RawPost, ...], list[str]]:
    """The bumps' records added to dedup's. A bump moves the listing's own record and, for a
    duplicate, its canonical's (the card's time, as a repost moves it, #75 F2). Returns the
    result, the stored canonicals a bump brought back from archive (their photos to download
    again), and the bumped `listing_id`s."""
    records = {record.listing_id: record for record in result.lifecycles}
    order = [record.listing_id for record in result.lifecycles]
    read: dict[str, PostLifecycle | None] = dict(result.read)
    returned: dict[str, RawPost] = {}
    bumped: list[str] = []

    def has_listing(listing_id: str) -> bool:
        return repository.get_listing(listing_id) is not None

    for bump in bumps:
        post = repository.get(bump.listing_id)
        if post is None:
            continue
        targets = [post.listing_id]
        if not post.is_canonical and post.duplicate_of is not None:
            targets.append(post.duplicate_of)
        for listing_id in targets:
            current = records.get(listing_id)
            if current is None:
                current = repository.get_lifecycle(listing_id)
                if current is None:
                    continue
                read[listing_id] = current
            moved = bumped_lifecycle(current, bump.updated_at, has_listing)
            if moved is None:
                continue
            if listing_id not in records:
                order.append(listing_id)
            records[listing_id] = moved
            if listing_id == post.listing_id:
                bumped.append(listing_id)
            if current.state == "archived" and moved.state != "archived":
                stored = post if listing_id == post.listing_id else repository.get(listing_id)
                if stored is not None and stored.is_canonical:
                    returned[listing_id] = stored
    lifecycles = tuple(records[listing_id] for listing_id in order)
    return (
        DedupResult(posts=result.posts, lifecycles=lifecycles, read=read),
        tuple(returned.values()),
        bumped,
    )


def _store(
    posts: tuple[RawPost, ...], result: DedupResult, repository: Repository
) -> tuple[PostLifecycle, ...]:
    """The one transaction, tried again on a record another writer changed (#260, #289)."""
    records = {record.listing_id: record for record in result.lifecycles}
    new_ids = {post.listing_id for post in posts}
    new = [(post, records[post.listing_id]) for post in posts]
    expected: dict[str, PostLifecycle | None] = dict(result.read)
    # A new listing's record is created with its post; any other changed record, by compare and
    # set against the record as the run read it.
    to_write = {
        listing_id: record
        for listing_id, record in records.items()
        if listing_id not in new_ids or expected.get(listing_id) is not None
    }
    stale = ""
    for _ in range(STORE_ATTEMPTS):
        try:
            repository.save_batch(
                new, [(record, expected[lid]) for lid, record in to_write.items()]
            )
            return tuple({**records, **to_write}.values())
        except StaleRecordError as error:
            stale = error.listing_id
            fresh = repository.get_lifecycle(stale)
            read = result.read.get(stale)
            if fresh is None or read is None or stale not in to_write:
                raise
            logger.warning("store: %s changed during the run; merged", stale)
            to_write[stale] = merge_run_record(read, records[stale], fresh)
            expected[stale] = fresh
    raise StaleRecordError(stale)
