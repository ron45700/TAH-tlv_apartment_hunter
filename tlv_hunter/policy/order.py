"""The order of one user's list (`PHASE_3.md` 3.6 (e); `BASELINE.md` §8; DECISIONS.md #62, #253,
#276, #295 point 10). Pure: nothing written, no model call.
"""

from collections.abc import Collection, Iterable

from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.policy.base import TIER_RANK, Evaluation


def card_viewed(card: Card, viewed_ids: Collection[str]) -> bool:
    """Viewed when any post of the card has the user's mark, so a card stays viewed when a further
    publication joins it (#253; SCHEMA.md `ViewedPost`)."""
    return any(listing_id in viewed_ids for listing_id in card.post_ids)


def ordered(
    entries: Iterable[tuple[Card, Evaluation]], viewed_ids: Collection[str]
) -> list[tuple[Card, Evaluation]]:
    """Drops what is not shown; then every unviewed card before every viewed one (#62); inside
    each, the tiers of §8; inside a tier, the newest last publication first, then `shown_id`.
    Each evaluation must be of its card's shown post."""
    shown = []
    for card, evaluation in entries:
        if evaluation.listing_id != card.shown_id:
            raise ValueError(f"the evaluation of {evaluation.listing_id} is not of {card.shown_id}")
        if evaluation.shown:
            shown.append((card, evaluation))
    return sorted(
        shown,
        key=lambda entry: (
            card_viewed(entry[0], viewed_ids),
            TIER_RANK[entry[1].tier or "unknown"],
            -entry[0].last_published_at.timestamp(),
            entry[0].shown_id,
        ),
    )
