"""The candidate pairs of Gate D's evidence (`PHASE_2.md` 2.10; DECISIONS.md #145, #226): two stored
posts with different text hashes that one of two rules puts side by side for Ron to judge.

A plain module, not a seam: pure functions over the posts, their lifecycle records and their
`Listing`s, and one reader of a Repository. It decides no Gate D key and no dedup B rule, marks no
post as a duplicate and writes nothing. The page and the measurement are in `page.py` and
`verdicts.py`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.store.base import Repository

RULES_VERSION = "1"
# "A few days" (#226, point 4): the gap between the two posts' own `posted_at`.
WINDOW = timedelta(hours=72)
# A number found in this many compared posts or more is an agent's: it lists no pairs one by one,
# only a labelled sample (#226, point 2). Today's data has numbers in 7, 7, 3 and 2 posts.
AGENT_NUMBER_POSTS = 4
AGENT_SAMPLE_SIZE = 3

FIELDS, PHONE, AGENT_PHONE_SAMPLE = "fields", "phone", "agent_phone_sample"
SIGNALS = (FIELDS, PHONE, AGENT_PHONE_SAMPLE)
PRICE, ROOMS, AREAS = "price", "rooms", "areas"
MATCHABLE = (PRICE, ROOMS, AREAS)


@dataclass(frozen=True)
class Member:
    """A post the rules compare: canonical, active, classified."""

    post: RawPost
    lifecycle: PostLifecycle
    listing: Listing

    @property
    def listing_id(self) -> str:
        return self.post.listing_id


@dataclass(frozen=True)
class Population:
    members: tuple[Member, ...]
    total_posts: int
    duplicates: int
    first_posted_at: datetime | None
    last_posted_at: datetime | None

    @property
    def span_hours(self) -> float:
        if self.first_posted_at is None or self.last_posted_at is None:
            return 0.0
        return (self.last_posted_at - self.first_posted_at).total_seconds() / 3600


@dataclass(frozen=True)
class CandidatePair:
    first_id: str
    second_id: str
    found_by: tuple[str, ...]
    matched: tuple[str, ...]
    """Which of `price`, `rooms`, `areas` match, whichever rule found the pair."""
    shared_phones: tuple[str, ...]
    gap_hours: float
    same_group: bool

    @property
    def key(self) -> str:
        return pair_key(self.first_id, self.second_id)


@dataclass(frozen=True)
class Candidates:
    members: int
    pairs: tuple[CandidatePair, ...]
    agent_numbers: int
    agent_pairs: int
    """Every compared pair whose only shared numbers are agent numbers, listed or not."""

    def count(self, signal: str) -> int:
        return sum(1 for pair in self.pairs if signal in pair.found_by)


def pair_key(first_id: str, second_id: str) -> str:
    """`<smaller listing_id>|<larger>`: the pair's key in the export (`PHASE_2.md` 2.10)."""
    low, high = sorted((first_id, second_id))
    return f"{low}|{high}"


def load_population(store: Repository) -> Population:
    """The compared posts, ordered by listing_id, and the figures the measurement is read against.
    Reads only; a post with no lifecycle record, no `Listing` or no stored hash is not a member."""
    posts = store.query()
    members = []
    for post in posts:
        if post.is_canonical is not True or post.text_hash is None:
            continue
        lifecycle = store.get_lifecycle(post.listing_id)
        if lifecycle is None or lifecycle.state != "active":
            continue
        listing = store.get_listing(post.listing_id)
        if listing is None:
            continue
        members.append(Member(post, lifecycle, listing))
    times = [post.posted_at for post in posts]
    return Population(
        members=tuple(sorted(members, key=lambda member: member.listing_id)),
        total_posts=len(posts),
        duplicates=sum(1 for post in posts if post.is_canonical is False),
        first_posted_at=min(times, default=None),
        last_posted_at=max(times, default=None),
    )


def _prices(listing: Listing) -> frozenset[int] | None:
    marked = listing.price
    return frozenset(marked.value) if marked.state == "written" and marked.value else None


def _rooms(listing: Listing) -> float | None:
    return listing.rooms.value if listing.rooms.state == "written" else None


def matched_fields(first: Listing, second: Listing) -> tuple[str, ...]:
    """The fields of the fields rule that match: both prices written and equal as sets, both rooms
    written and equal, both `areas` non-empty with a number in common (#226, point 3)."""
    matched = []
    prices = (_prices(first), _prices(second))
    if prices[0] is not None and prices[0] == prices[1]:
        matched.append(PRICE)
    rooms = (_rooms(first), _rooms(second))
    if rooms[0] is not None and rooms[0] == rooms[1]:
        matched.append(ROOMS)
    if set(first.areas) & set(second.areas):
        matched.append(AREAS)
    return tuple(matched)


def agent_numbers(members: Iterable[Member]) -> frozenset[str]:
    """The numbers found in `AGENT_NUMBER_POSTS` or more of the compared posts."""
    counts: dict[str, int] = {}
    for member in members:
        for phone in set(member.post.phones or []):
            counts[phone] = counts.get(phone, 0) + 1
    return frozenset(phone for phone, n in counts.items() if n >= AGENT_NUMBER_POSTS)


def find_candidates(members: Sequence[Member]) -> Candidates:
    """The pairs of the two rules, in the order of the page: found by both rules, the fields rule,
    the phone rule, then the labelled sample of agent-number pairs; by `listing_id` within each."""
    ordered = sorted(members, key=lambda member: member.listing_id)
    agents = agent_numbers(ordered)
    listed: list[CandidatePair] = []
    agent_only: list[CandidatePair] = []
    agent_pairs = 0
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            if first.post.text_hash == second.post.text_hash:
                continue
            gap = abs(first.post.posted_at - second.post.posted_at)
            if gap > WINDOW:
                continue
            shared = tuple(sorted(set(first.post.phones or []) & set(second.post.phones or [])))
            matched = matched_fields(first.listing, second.listing)
            fields = all(name in matched for name in MATCHABLE)
            phone = any(number not in agents for number in shared)
            agent_phone = bool(shared) and not phone
            agent_pairs += agent_phone
            found_by = tuple(name for name, found in ((FIELDS, fields), (PHONE, phone)) if found)
            if (
                not found_by
                and agent_phone
                and (PRICE in matched or {ROOMS, AREAS} <= set(matched))
            ):
                found_by = (AGENT_PHONE_SAMPLE,)
            if not found_by:
                continue
            pair = CandidatePair(
                first_id=first.listing_id,
                second_id=second.listing_id,
                found_by=found_by,
                matched=matched,
                shared_phones=shared,
                gap_hours=gap.total_seconds() / 3600,
                same_group=first.post.group_id == second.post.group_id,
            )
            (agent_only if found_by == (AGENT_PHONE_SAMPLE,) else listed).append(pair)
    sample = sorted(agent_only, key=lambda pair: (pair.gap_hours, pair.key))[:AGENT_SAMPLE_SIZE]
    listed.sort(key=lambda pair: (_rank(pair), pair.key))
    sample.sort(key=lambda pair: pair.key)
    return Candidates(
        members=len(ordered),
        pairs=tuple(listed + sample),
        agent_numbers=len(agents),
        agent_pairs=agent_pairs,
    )


def _rank(pair: CandidatePair) -> int:
    if FIELDS in pair.found_by and PHONE in pair.found_by:
        return 0
    return 1 if FIELDS in pair.found_by else 2
