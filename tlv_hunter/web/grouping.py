"""The same-listing grouping held in the site's memory (DECISIONS.md #231, #301, #316;
`PHASE_3.md` 3.7 (h); D, #371, #379–#380).

The grouping is a fact about the posts, the same for every user: it is computed once, held, and
computed again only when the store generation counter moved, that is when a post, a lifecycle, a
classification or a correction changed, in any process (`store_generation.py`). One recompute at
a time. Reads only; writes nothing.

Two modes. **In the foreground** (the tests' default, and the behaviour before D) a request that
finds the counter moved computes the grouping itself, every other request waiting for it. **In the
background** (D, what `serve` runs) a request never computes: it starts a recompute in a thread when
the counter moved and none is running, and answers at once from the snapshot it holds; before the
first snapshot exists it raises `NotReady` (the API answers "loading", #380). A recompute that ends
with the counter moved again runs once more.

**The removal overlay** (#379): the posts the site itself has just made inactive (a flag, a report
that removed the post), each with the store generation after its write. A card that holds one is
left out of every answer until a snapshot at or after that generation is held, so a user's own flag
or report leaves the list at once although the snapshot is older. It only ever removes.
"""

import logging
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_b import (
    Card,
    KeyInputs,
    KeyPost,
    OtherPost,
    PhotoHashes,
    derive_cards,
    load_key_posts,
)
from tlv_hunter.store.sqlite import SqliteRepository

logger = logging.getLogger(__name__)


class NotReady(Exception):
    """No grouping has been computed yet since the site started (background mode)."""


@dataclass(frozen=True)
class Snapshot:
    """The grouping at one store generation."""

    generation: int
    cards: tuple[Card, ...]
    members: Mapping[str, KeyPost]
    """Every compared post (the cards' members), by `listing_id`: whose photos are served."""
    card_of: Mapping[str, Card]
    """Every post of every card, its dedup A duplicates included, to the card that holds it."""
    others: Mapping[str, OtherPost]
    """Every other canonical post, by `listing_id`: the admin's lists (3.8 (b), #397). Never
    reaches a non-admin: only the admin's routes read it."""
    duplicates: Mapping[str, tuple[RawPost, ...]]
    """Every dedup A duplicate, by its canonical: the admin's repost log."""


@dataclass(frozen=True)
class Held:
    snapshot: Snapshot
    """The snapshot as answers see it: the overlay's cards already left out."""
    generation_ms: float
    """The read of the counter."""
    group_ms: float | None
    """The recompute, when this request ran one; `None` otherwise."""


class Grouping:
    def __init__(
        self,
        repository: SqliteRepository,
        corrections: Callable[[], Iterable[FieldCorrection]],
        store_root: Path,
        *,
        derive: Callable[[KeyInputs], tuple[Card, ...]] = derive_cards,
        background: bool = False,
    ) -> None:
        self._repository = repository
        self._corrections = corrections
        self._store_root = Path(store_root)
        self._derive = derive
        self._background = background
        self._photos = PhotoHashes()  # kept across recomputes: only changed files are hashed again
        self._lock = threading.Lock()  # one recompute at a time
        self._state = threading.Lock()  # the snapshot, the overlay, the running flag
        self._snapshot: Snapshot | None = None
        # a post the site made inactive -> the store generation after the write
        self._removed: dict[str, int] = {}
        # the last view: (the snapshot's id, the overlay's version, the view)
        self._seen: tuple[int, int, Snapshot] | None = None
        self._overlay_version = 0
        self._running = False
        self._idle = threading.Event()  # set while no background recompute runs
        self._idle.set()
        self.recomputes = 0

    # --- the answers' view ---

    def current(self) -> Held:
        started = time.perf_counter()
        generation = self._repository.store_generation()
        generation_ms = _ms_since(started)
        held = self._snapshot
        if held is not None and held.generation == generation:
            return Held(self._view(held), generation_ms, None)
        if self._background:
            self._start_recompute()
            if held is None:
                raise NotReady
            return Held(self._view(held), generation_ms, None)
        started = time.perf_counter()
        snapshot = self._recompute_if_moved()
        return Held(self._view(snapshot), generation_ms, _ms_since(started))

    def start(self) -> None:
        """Background mode: the first grouping, begun at once, before any visitor (#380)."""
        if self._background:
            self._start_recompute()

    def remove(self, listing_ids: Iterable[str]) -> None:
        """The overlay (#379): posts this site has just made inactive. Call it after the write."""
        generation = self._repository.store_generation()
        with self._state:
            for listing_id in listing_ids:
                self._removed[listing_id] = generation
            self._overlay_version += 1

    @property
    def computing(self) -> bool:
        return self._running

    def wait(self, timeout: float) -> bool:
        """Until no background recompute runs (or the timeout): False when one still runs."""
        return self._idle.wait(timeout)

    # --- the recompute ---

    def _recompute_if_moved(self) -> Snapshot:
        with self._lock:
            # The counter is read before the posts: a write during the load leaves this snapshot
            # labelled with the older number, so the next look computes again.
            generation = self._repository.store_generation()
            held = self._snapshot
            if held is not None and held.generation == generation:
                return held
            inputs = load_key_posts(
                self._repository, self._corrections(), self._store_root, self._photos
            )
            cards = self._derive(inputs)
            snapshot = Snapshot(
                generation=generation,
                cards=cards,
                members={member.listing_id: member for member in inputs.members},
                card_of={listing_id: card for card in cards for listing_id in card.post_ids},
                others={other.listing_id: other for other in inputs.others},
                duplicates=inputs.duplicates,
            )
            with self._state:
                self._snapshot = snapshot
                stale = [i for i, g in self._removed.items() if g <= snapshot.generation]
                for listing_id in stale:
                    del self._removed[listing_id]
                if stale:
                    self._overlay_version += 1
            self.recomputes += 1
            return snapshot

    def _start_recompute(self) -> None:
        with self._state:
            if self._running:
                return
            self._running = True
            self._idle.clear()
        threading.Thread(target=self._run, name="grouping", daemon=True).start()

    def _run(self) -> None:
        try:
            while True:
                snapshot = self._recompute_if_moved()
                if self._repository.store_generation() == snapshot.generation:
                    break
        except Exception:
            # The next request starts another; the held snapshot keeps answering meanwhile.
            logger.exception("the grouping's recompute failed")
        finally:
            with self._state:
                self._running = False
                self._idle.set()

    # --- the overlay applied ---

    def _view(self, snapshot: Snapshot) -> Snapshot:
        with self._state:
            removed = dict(self._removed)
            version = self._overlay_version
            seen = self._seen
        if not removed:
            return snapshot
        if seen is not None and seen[0] == id(snapshot) and seen[1] == version:
            return seen[2]
        cards = tuple(c for c in snapshot.cards if not removed.keys() & set(c.canonical_ids))
        kept = {id(c) for c in cards}
        view = Snapshot(
            generation=snapshot.generation,
            cards=cards,
            members={i: m for i, m in snapshot.members.items() if id(snapshot.card_of[i]) in kept},
            card_of={i: c for i, c in snapshot.card_of.items() if id(c) in kept},
            others=snapshot.others,
            duplicates=snapshot.duplicates,
        )
        with self._state:
            self._seen = (id(snapshot), version, view)
        return view


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000
