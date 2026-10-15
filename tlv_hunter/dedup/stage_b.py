"""The same-listing grouping, derived by the Gate D key (DECISIONS.md #230, rule 1 amended by #232;
#231, #287, #295, #297, #300): which active posts are one listing, and the cards they make.

A plain module, like `stage_a.py`: it reads a Repository and image files, and **writes nothing**.
The grouping is never written onto a post (#231): it is a fact about the posts, the same for every
user, derived from the stored records (how the site holds it is 3.7's, #301).

The key compares the posts the 2.10 rules compare (#226, #230): canonical, with a stored text hash,
`"active"`, with a `Listing`, read as users see them (the corrections in force applied, #287). The
fields rule, the agent numbers and the 72-hour window are `gate_d/candidates.py`'s, the one
implementation (#295, point 7).
"""

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Literal

from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.gate_d.candidates import MATCHABLE, WINDOW, Member, agent_numbers, matched_fields
from tlv_hunter.postmodel.seen import SeenListing, seen_listing
from tlv_hunter.store.base import Repository

Rule = Literal["phone_and_fields", "photo"]
PHONE_AND_FIELDS: Rule = "phone_and_fields"  # rule 1 (#230, #232)
PHOTO: Rule = "photo"  # rule 2 (#230)


@dataclass(frozen=True)
class KeyPost:
    """A post the key compares, as users see it."""

    post: RawPost
    lifecycle: PostLifecycle
    seen: SeenListing
    photo_hashes: frozenset[str]

    @property
    def listing_id(self) -> str:
        return self.post.listing_id


@dataclass(frozen=True)
class OtherPost:
    """A canonical post the key does not compare (rejected, pending, archived, or active with no
    `Listing`), read in the same pass for the admin's lists (3.8 (b), #397). `seen` is `None` for a
    post with no `Listing` (pending, or rejected before the model)."""

    post: RawPost
    lifecycle: PostLifecycle
    seen: SeenListing | None

    @property
    def listing_id(self) -> str:
        return self.post.listing_id


@dataclass(frozen=True)
class KeyInputs:
    members: tuple[KeyPost, ...]
    """The compared posts, by `listing_id`."""
    duplicates: Mapping[str, tuple[RawPost, ...]]
    """Every stored dedup A duplicate, by its `duplicate_of`."""
    others: tuple[OtherPost, ...] = ()
    """Every other canonical post with a lifecycle record, by `listing_id` (#397)."""


@dataclass(frozen=True)
class TiedPair:
    first_id: str
    second_id: str
    """The two ids, the smaller first."""
    rules: tuple[Rule, ...]
    """Which rules tie them: rule 1, rule 2, or both."""


@dataclass(frozen=True)
class Publication:
    listing_id: str
    posted_at: datetime


@dataclass(frozen=True)
class Card:
    """One listing: tied members and their dedup A duplicates (#231; `SCHEMA.md` `ViewedPost`).

    For the writes of 3.7 and 3.8 (#300): a "lied" flag is written on every one of
    `canonical_ids`; a "wrong classification" report on `shown_id` only. A viewed mark is written
    on `shown_id`; "mark as not viewed" removes the user's marks on every one of `post_ids`."""

    shown: KeyPost
    """The post the card shows and evaluates: the earliest `posted_at`, then the smaller
    `listing_id` (#297)."""
    canonical_ids: tuple[str, ...]
    """The members, by `posted_at` then `listing_id`; the first is `shown_id`."""
    post_ids: frozenset[str]
    """The members and their dedup A duplicates."""
    last_published_at: datetime
    """The latest of the members' `last_published_at`: the card's main time (#122)."""
    publications: tuple[Publication, ...]
    """Every post of the card, earliest `posted_at` first: the repost log's input (#75 A)."""

    @property
    def shown_id(self) -> str:
        return self.shown.listing_id


@dataclass
class PhotoHashes:
    """The SHA-256 of stored photo files, memoised in this process only, never written (#231).
    Keyed by the file's path, size and modification time, so a replaced file is read again."""

    _memo: dict[tuple[str, int, int], str] = field(default_factory=dict)

    def of(self, store_root: Path, lifecycle: PostLifecycle) -> frozenset[str]:
        """The hashes of the post's downloaded photos; a missing file adds nothing."""
        hashes = set()
        for image in lifecycle.images:
            if image.local_path is None:
                continue
            path = Path(store_root) / image.local_path
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            key = (str(path), stat.st_size, stat.st_mtime_ns)
            if key not in self._memo:
                self._memo[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.add(self._memo[key])
        return frozenset(hashes)


def is_compared(post: RawPost, lifecycle: PostLifecycle | None) -> bool:
    """Canonical, with a stored text hash, `"active"` (#226, #230). The `Listing` is checked by
    the caller."""
    return (
        post.is_canonical is True
        and post.text_hash is not None
        and lifecycle is not None
        and lifecycle.state == "active"
    )


def load_key_posts(
    store: Repository,
    corrections: Iterable[FieldCorrection],
    store_root: Path,
    photos: PhotoHashes,
) -> KeyInputs:
    """Read-only: the compared posts as users see them, and every dedup A duplicate; in the same
    pass, every other canonical post with a lifecycle record (`others`, the admin's lists, #397).
    `corrections` is what `UserDataStore.find_corrections()` returned (removed ones are ignored)."""
    by_post: dict[str, list[FieldCorrection]] = defaultdict(list)
    for correction in corrections:
        by_post[correction.listing_id].append(correction)
    members: list[KeyPost] = []
    others: list[OtherPost] = []
    duplicates: dict[str, list[RawPost]] = defaultdict(list)
    for post in store.query():
        if post.is_canonical is False and post.duplicate_of is not None:
            duplicates[post.duplicate_of].append(post)
            continue
        lifecycle = store.get_lifecycle(post.listing_id)
        if lifecycle is None:
            continue
        listing = store.get_listing(post.listing_id)
        if listing is None or not is_compared(post, lifecycle):
            if post.is_canonical is not False:
                seen = None if listing is None else seen_listing(listing, by_post[post.listing_id])
                others.append(OtherPost(post=post, lifecycle=lifecycle, seen=seen))
            continue
        members.append(
            KeyPost(
                post=post,
                lifecycle=lifecycle,
                seen=seen_listing(listing, by_post.get(post.listing_id, ())),
                photo_hashes=photos.of(store_root, lifecycle),
            )
        )
    return KeyInputs(
        members=tuple(sorted(members, key=lambda member: member.listing_id)),
        duplicates={key: tuple(posts) for key, posts in duplicates.items()},
        others=tuple(sorted(others, key=lambda other: other.listing_id)),
    )


def key_agent_numbers(members: Iterable[KeyPost]) -> frozenset[str]:
    """The agent numbers: found in 4 or more compared posts (#230, #232)."""
    return agent_numbers(
        Member(member.post, member.lifecycle, member.seen.listing) for member in members
    )


def pair_rules(first: KeyPost, second: KeyPost, agents: frozenset[str]) -> tuple[Rule, ...]:
    """The rules of the key that tie two compared posts; `()` when nothing ties them. Different
    text hashes, `posted_at` at most 72 hours apart; rule 1, a shared phone that is not an agent
    number and the fields rule; rule 2, a shared photo and one of those two. Nothing else ties."""
    if first.post.text_hash == second.post.text_hash:
        return ()
    if abs(first.post.posted_at - second.post.posted_at) > WINDOW:
        return ()
    shared = set(first.post.phones or []) & set(second.post.phones or [])
    phone = any(number not in agents for number in shared)
    matched = matched_fields(first.seen.listing, second.seen.listing)
    fields = all(name in matched for name in MATCHABLE)
    photo = bool(first.photo_hashes & second.photo_hashes)
    rules: list[Rule] = []
    if phone and fields:
        rules.append(PHONE_AND_FIELDS)
    if photo and (phone or fields):
        rules.append(PHOTO)
    return tuple(rules)


def tied_pairs(members: Sequence[KeyPost]) -> tuple[TiedPair, ...]:
    """Every tied pair, by ids. Both rules need a shared non-agent phone or a shared photo, so only
    the posts that share one are compared, not every pair."""
    for member in members:
        if not is_compared(member.post, member.lifecycle):
            raise ValueError(f"post {member.listing_id} is not one the key compares")
    agents = key_agent_numbers(members)
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, member in enumerate(members):
        for number in set(member.post.phones or []) - agents:
            buckets[("phone", number)].append(index)
        for digest in member.photo_hashes:
            buckets[("photo", digest)].append(index)
    candidates = {pair for indexes in buckets.values() for pair in combinations(indexes, 2)}
    pairs = []
    for first, second in candidates:
        rules = pair_rules(members[first], members[second], agents)
        if rules:
            low, high = sorted((members[first].listing_id, members[second].listing_id))
            pairs.append(TiedPair(low, high, rules))
    return tuple(sorted(pairs, key=lambda pair: (pair.first_id, pair.second_id)))


def cards(inputs: KeyInputs, pairs: Iterable[TiedPair]) -> tuple[Card, ...]:
    """Every member in exactly one card: a card is a connected group of tied members (#295,
    point 5), with their dedup A duplicates. By `shown_id`."""
    by_id = {member.listing_id: member for member in inputs.members}
    parent = {listing_id: listing_id for listing_id in by_id}

    def root(listing_id: str) -> str:
        while parent[listing_id] != listing_id:
            parent[listing_id] = parent[parent[listing_id]]
            listing_id = parent[listing_id]
        return listing_id

    for pair in pairs:
        if pair.first_id not in by_id or pair.second_id not in by_id:
            raise KeyError(f"{pair.first_id}|{pair.second_id}: not a compared post")
        parent[root(pair.first_id)] = root(pair.second_id)
    groups: dict[str, list[KeyPost]] = defaultdict(list)
    for listing_id, member in by_id.items():
        groups[root(listing_id)].append(member)
    result = [_card(group, inputs.duplicates) for group in groups.values()]
    return tuple(sorted(result, key=lambda card: card.shown_id))


def derive_cards(inputs: KeyInputs) -> tuple[Card, ...]:
    """The cards of the compared posts: `tied_pairs`, then `cards`."""
    return cards(inputs, tied_pairs(inputs.members))


def _card(group: list[KeyPost], duplicates: Mapping[str, tuple[RawPost, ...]]) -> Card:
    members = sorted(group, key=lambda member: (member.post.posted_at, member.listing_id))
    posts = [member.post for member in members]
    for member in members:
        posts.extend(duplicates.get(member.listing_id, ()))
    publications = sorted(
        (Publication(post.listing_id, post.posted_at) for post in posts),
        key=lambda publication: (publication.posted_at, publication.listing_id),
    )
    return Card(
        shown=members[0],
        canonical_ids=tuple(member.listing_id for member in members),
        post_ids=frozenset(post.listing_id for post in posts),
        last_published_at=max(member.lifecycle.last_published_at for member in members),
        publications=tuple(publications),
    )
