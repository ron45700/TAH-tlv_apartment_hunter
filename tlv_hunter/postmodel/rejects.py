"""The rejection derived from the model's answer, and the lifecycle record after a classification
attempt (DECISIONS.md #92, #139, #152). Plain functions, like `premodel/rejects.py`: no storage.
"""

from typing import Literal

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle

ModelReason = Literal["other_city", "seeking", "for_sale", "not_listing"]


def model_reason(listing: Listing) -> ModelReason | None:
    """The first model-derived reason that applies, in Gate E order: `other_city`, then the post's
    nature. `no_text` and `no_images` come earlier but never reach the model; `flagged` is a
    user's. A rental or a sublet offer has none (#93)."""
    if listing.other_city is not None:
        return "other_city"
    if listing.post_nature in ("seeking", "for_sale", "not_listing"):
        return listing.post_nature
    return None


def classified_lifecycle(existing: PostLifecycle, listing: Listing) -> PostLifecycle:
    """The record of a pending post after a successful classification. The failure fields are
    left as they are (#152)."""
    _check(existing, listing.listing_id)
    reason = model_reason(listing)
    return PostLifecycle(
        **{
            **dict(existing),
            "state": "active" if reason is None else "rejected",
            "rejection_reason": reason,
        }
    )


def failed_lifecycle(existing: PostLifecycle, error: str) -> PostLifecycle:
    """The record of a pending post after a classification run in which it failed (#139)."""
    _check(existing, existing.listing_id)
    return PostLifecycle(
        **{
            **dict(existing),
            "classification_failures": existing.classification_failures + 1,
            "last_classification_error": error,
        }
    )


def _check(existing: PostLifecycle, listing_id: str) -> None:
    if existing.listing_id != listing_id:
        raise ValueError(f"lifecycle record {existing.listing_id} does not belong to {listing_id}")
    if existing.state != "pending":
        raise ValueError(f"only a pending record is classified, not {existing.state!r}")
