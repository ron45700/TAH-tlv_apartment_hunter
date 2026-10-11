"""The post as a user sees it (SCHEMA.md, Gate C, "The post a user sees"; DECISIONS.md #256, #281,
#287, #295): the model's `Listing` with the admin's corrections in force applied over a copy.

A plain module, like `rejects.py`: pure functions, no storage, no model call. The stored `Listing`
is never edited (#256): the caller reads the corrections (`UserDataStore.find_corrections`) and
passes them in. Every reader of a post for a user reads `SeenListing`: the evaluation (`policy/`),
the card, the restore's derived state (`rejects.restored_lifecycle`) and the Gate D key
(`dedup/stage_b.py`).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.field_correction import FieldCorrection, listing_field_type
from tlv_hunter.contracts.listing import Listing


@dataclass(frozen=True)
class SeenListing:
    listing: Listing
    """The post as users see it: a valid Gate B `Listing`, the corrected fields replaced."""
    corrected: frozenset[ReportableField]
    """The fields a correction in force replaced: the card's "corrected by hand" marks (#256)."""


def seen_listing(listing: Listing, corrections: Iterable[FieldCorrection]) -> SeenListing:
    """Applies every correction in force of the post over a copy of its `Listing`; a removed one is
    ignored. Raises `ValueError` for a correction of another post, or two in force on one field.

    `price_source` follows a corrected `price` (#295, point 3): `None` when the corrected price is
    not written, `"text"` when the model's was `None` and the corrected one is not (the admin read
    it in the post's text); otherwise it is kept. Gate B ties the two together."""
    replaced: dict[str, Any] = {}
    for correction in corrections:
        if correction.listing_id != listing.listing_id:
            raise ValueError(
                f"correction {correction.correction_id} is of post {correction.listing_id}, "
                f"not {listing.listing_id}"
            )
        if not correction.in_force:
            continue
        if correction.field in replaced:
            raise ValueError(f"two corrections in force on {correction.field} (#284)")
        replaced[correction.field] = listing_field_type(correction.field).dump_python(
            correction.corrected_value
        )
    if not replaced:
        return SeenListing(listing, frozenset())
    data = {**listing.model_dump(), **replaced}
    if "price" in replaced:
        if replaced["price"]["state"] == "not_written":
            data["price_source"] = None
        elif listing.price_source is None:
            data["price_source"] = "text"
    return SeenListing(Listing.model_validate(data), frozenset(replaced))
