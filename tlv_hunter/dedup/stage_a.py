"""Dedup stage A (task 1.3): layers 1 and 2, and the lifecycle changes a repost makes.

Reads the Repository and writes nothing (DECISIONS.md #75 F1); the store step is task 1.14.
Layer 3, the phone, produces nothing here (#75 C).
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.premodel.rejects import initial_lifecycle, recheck
from tlv_hunter.store.base import Repository

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DedupResult:
    posts: tuple[RawPost, ...]
    """The batch, one row per post, with `is_canonical` and `duplicate_of` set."""
    lifecycles: tuple[PostLifecycle, ...]
    """One record per batch post, then every stored canonical outside the batch whose record
    changed."""


def dedup_a(batch: Sequence[RawPost], repository: Repository) -> DedupResult:
    reader = _Reader(repository)
    posts = _collapse_repeats(batch)
    stored = {post.listing_id: reader.get(post.listing_id) for post in posts}

    # A re-fetched post keeps its stored result (sticky), also after a text edit. A stored post
    # that was `no_text` has no result to keep and goes through dedup as new (#72.2).
    assigned: dict[str, RawPost] = {}
    fresh: list[RawPost] = []
    for post in posts:
        before = stored[post.listing_id]
        if before is not None and before.text_hash is not None:
            assigned[post.listing_id] = post.with_changes(
                is_canonical=before.is_canonical, duplicate_of=before.duplicate_of
            )
        elif post.no_text:
            assigned[post.listing_id] = post.with_changes(is_canonical=True, duplicate_of=None)
        else:
            fresh.append(post)

    for text_hash in sorted({post.text_hash for post in fresh}):
        members = [post for post in fresh if post.text_hash == text_hash]
        known = [reader.checked(post) for post in reader.find_by_hash(text_hash)]
        known += [post for post in assigned.values() if post.text_hash == text_hash]
        canonicals = {
            canonical.listing_id: canonical
            for canonical in (reader.canonical_of(post) for post in known)
        }
        if canonicals:
            # A stored canonical never changes; with more than one, the earliest (#75 A, D4).
            canonical_id = min(canonicals.values(), key=_age).listing_id
        else:
            canonical_id = min(members, key=_age).listing_id
        for post in members:
            is_canonical = post.listing_id == canonical_id
            assigned[post.listing_id] = post.with_changes(
                is_canonical=is_canonical, duplicate_of=None if is_canonical else canonical_id
            )

    result = tuple(assigned[post.listing_id] for post in posts)
    return DedupResult(posts=result, lifecycles=_lifecycles(result, stored, reader))


def _collapse_repeats(batch: Sequence[RawPost]) -> list[RawPost]:
    """Layer 1 within the batch: the same post twice is kept once, the first in provider order."""
    seen: dict[str, RawPost] = {}
    for post in batch:
        seen.setdefault(post.listing_id, post)
    repeats = len(batch) - len(seen)
    if repeats:
        logger.warning("dedup: %d repeated posts in the batch, kept the first of each", repeats)
    return list(seen.values())


def _lifecycles(
    posts: tuple[RawPost, ...], stored: dict[str, RawPost | None], reader: "_Reader"
) -> tuple[PostLifecycle, ...]:
    # Base record: initial for a new post (or a stored one with no record, #75 F4), else the
    # 1.11 re-check. Then, per canonical: #74, #70, `last_published_at` (#75 F2).
    records: dict[str, PostLifecycle] = {}
    for post in posts:
        existing = reader.get_lifecycle(post.listing_id)
        records[post.listing_id] = (
            initial_lifecycle(post) if existing is None else recheck(existing, post)
        )

    in_batch = {post.listing_id: post for post in posts}
    canonical_ids = sorted(
        {post.listing_id if post.is_canonical else post.duplicate_of for post in posts}
    )
    changed: list[PostLifecycle] = []
    for canonical_id in canonical_ids:
        canonical = in_batch.get(canonical_id) or reader.get(canonical_id)
        if canonical is None or not canonical.is_canonical:
            raise ValueError(f"{canonical_id} is pointed at as a canonical but is not one")
        if canonical_id in records:
            before = records[canonical_id]
        else:
            existing = reader.get_lifecycle(canonical_id)
            before = initial_lifecycle(canonical) if existing is None else existing
        duplicates = _duplicates(canonical, posts, reader)
        new_reposts = [
            post
            for post in duplicates
            if post.listing_id in in_batch and stored[post.listing_id] is None
        ]
        record = _returned_from_archive(before, new_reposts)
        record = _media_through_repost(record, duplicates)
        latest = max([record.last_published_at, *(post.posted_at for post in duplicates)])
        record = _replace(record, last_published_at=latest)
        if canonical_id in records:
            records[canonical_id] = record
        elif record != reader.get_lifecycle(canonical_id):
            changed.append(record)

    return tuple(records[post.listing_id] for post in posts) + tuple(changed)


def _duplicates(canonical: RawPost, batch: tuple[RawPost, ...], reader: "_Reader") -> list[RawPost]:
    """The canonical's duplicates in the batch, and the stored ones reached through the hashes of
    the canonical and of its batch duplicates (#75 D1). The batch copy wins over the stored one."""
    found = {post.listing_id: post for post in batch if post.duplicate_of == canonical.listing_id}
    hashes = {canonical.text_hash, *(post.text_hash for post in found.values())}
    for text_hash in sorted(hash_ for hash_ in hashes if hash_ is not None):
        for post in reader.find_by_hash(text_hash):
            if reader.checked(post).duplicate_of == canonical.listing_id:
                found.setdefault(post.listing_id, post)
    return list(found.values())


def _returned_from_archive(record: PostLifecycle, new_reposts: list[RawPost]) -> PostLifecycle:
    """#74: a repost of an archived post returns it to the state it had. Only a duplicate new to
    the store and published after the archived clock counts (#75 E1, E2). Phase 1 has no
    classified post, so no reason means never classified (#74)."""
    if record.state != "archived":
        return record
    if not any(post.posted_at > record.last_published_at for post in new_reposts):
        return record
    if record.rejection_reason is None:
        return _replace(record, state="pending")
    # A model reason, a flag, or a pre-model one: `"rejected"` with the same reason. A
    # `no_images` post goes on to #70, which returns it to `"pending"` when a repost has media
    # (#72.5); without media it stays rejected (#75 E3).
    return _replace(record, state="rejected")


def _media_through_repost(record: PostLifecycle, duplicates: list[RawPost]) -> PostLifecycle:
    """#70, #72.4: a canonical rejected as `no_images` returns to `"pending"` when a duplicate has
    media of any kind, stored duplicates included (#75 D1)."""
    if record.state == "rejected" and record.rejection_reason == "no_images":
        if any(post.media for post in duplicates):
            return _replace(record, state="pending", rejection_reason=None)
    return record


class _Reader:
    """Repository reads, cached for one call. Every stored post read must carry a dedup result."""

    def __init__(self, repository: Repository) -> None:
        self._repository = repository
        self._posts: dict[str, RawPost | None] = {}
        self._hashes: dict[str, list[RawPost]] = {}
        self._lifecycles: dict[str, PostLifecycle | None] = {}

    def get(self, listing_id: str) -> RawPost | None:
        if listing_id not in self._posts:
            post = self._repository.get(listing_id)
            self._posts[listing_id] = None if post is None else self.checked(post)
        return self._posts[listing_id]

    def find_by_hash(self, text_hash: str) -> list[RawPost]:
        if text_hash not in self._hashes:
            self._hashes[text_hash] = self._repository.find_by_hash(text_hash)
        return self._hashes[text_hash]

    def get_lifecycle(self, listing_id: str) -> PostLifecycle | None:
        if listing_id not in self._lifecycles:
            self._lifecycles[listing_id] = self._repository.get_lifecycle(listing_id)
        return self._lifecycles[listing_id]

    def canonical_of(self, post: RawPost) -> RawPost:
        if post.is_canonical:
            return post
        canonical = self.get(post.duplicate_of) if post.duplicate_of is not None else None
        if canonical is None or not canonical.is_canonical:
            raise ValueError(
                f"stored post {post.listing_id} points at {post.duplicate_of}, "
                "which is not a stored canonical"
            )
        return canonical

    @staticmethod
    def checked(post: RawPost) -> RawPost:
        if post.is_canonical is None:
            raise ValueError(f"stored post {post.listing_id} has no dedup result (#75 D5)")
        return post


def _age(post: RawPost) -> tuple[datetime, str]:
    """The canonical rule: earliest `posted_at`, then the smaller `listing_id` (#75 D2)."""
    return (post.posted_at, post.listing_id)


def _replace(record: PostLifecycle, **changes: Any) -> PostLifecycle:
    return PostLifecycle(**{**dict(record), **changes})
