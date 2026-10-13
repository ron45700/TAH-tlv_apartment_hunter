"""The same-listing grouping held in the site's memory (DECISIONS.md #231, #301, #316;
`PHASE_3.md` 3.7 (h)).

The grouping is a fact about the posts, the same for every user: it is computed once, held, and
computed again only when the store generation counter moved, that is when a post, a lifecycle, a
classification or a correction changed, in any process (`store_generation.py`). One recompute at
a time: a request that finds the counter moved waits for the lock, then reads the counter again, so
two requests never compute the same generation twice. Reads only; writes nothing.
"""

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.dedup.stage_b import (
    Card,
    KeyInputs,
    KeyPost,
    PhotoHashes,
    derive_cards,
    load_key_posts,
)
from tlv_hunter.store.sqlite import SqliteRepository


@dataclass(frozen=True)
class Snapshot:
    """The grouping at one store generation."""

    generation: int
    cards: tuple[Card, ...]
    members: Mapping[str, KeyPost]
    """Every compared post (the cards' members), by `listing_id`: whose photos are served."""
    card_of: Mapping[str, Card]
    """Every post of every card, its dedup A duplicates included, to the card that holds it."""


@dataclass(frozen=True)
class Held:
    snapshot: Snapshot
    generation_ms: float
    """The read of the counter."""
    group_ms: float | None
    """The recompute, when this request ran one; `None` when the held grouping was current."""


class Grouping:
    def __init__(
        self,
        repository: SqliteRepository,
        corrections: Callable[[], Iterable[FieldCorrection]],
        store_root: Path,
        *,
        derive: Callable[[KeyInputs], tuple[Card, ...]] = derive_cards,
    ) -> None:
        self._repository = repository
        self._corrections = corrections
        self._store_root = Path(store_root)
        self._derive = derive
        self._photos = PhotoHashes()  # kept across recomputes: only changed files are hashed again
        self._lock = threading.Lock()
        self._snapshot: Snapshot | None = None
        self.recomputes = 0

    def current(self) -> Held:
        started = time.perf_counter()
        generation = self._repository.store_generation()
        generation_ms = _ms_since(started)
        held = self._snapshot
        if held is not None and held.generation == generation:
            return Held(held, generation_ms, None)
        with self._lock:
            # The counter is read before the posts: a write during the load leaves this snapshot
            # labelled with the older number, so the next request computes again.
            generation = self._repository.store_generation()
            held = self._snapshot
            if held is not None and held.generation == generation:
                return Held(held, generation_ms, None)
            started = time.perf_counter()
            inputs = load_key_posts(
                self._repository, self._corrections(), self._store_root, self._photos
            )
            cards = self._derive(inputs)
            snapshot = Snapshot(
                generation=generation,
                cards=cards,
                members={member.listing_id: member for member in inputs.members},
                card_of={listing_id: card for card in cards for listing_id in card.post_ids},
            )
            self._snapshot = snapshot
            self.recomputes += 1
            return Held(snapshot, generation_ms, _ms_since(started))


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000
