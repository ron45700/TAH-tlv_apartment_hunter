"""The rejection derived from the answer and from Facebook's own location, the lifecycle record
after a classification attempt, and the record a restore leaves (DECISIONS.md #92, #139, #152, #214,
#251, #281–#283, #296). Plain functions, like `premodel/rejects.py`: no storage, no model call. The
`Listing` (the model's answer) is never edited and the `RawPost` never written (invariant 14).

**The one place that rules on the city.** It takes the model's `Listing`, or a `SeenListing` (the
post as users see it, `postmodel/seen.py`): with a correction of `other_city` in force, the
correction decides, before Facebook's location field (#296); otherwise #214's order stands.
"""

import re
import unicodedata
from typing import Literal, NamedTuple

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.seen import SeenListing

ModelReason = Literal["other_city", "seeking", "for_sale", "not_listing"]
CitySource = Literal["correction", "native_location", "model"]

# The locality of a Tel Aviv-Yafo location after `_key`: "תל אביב - יפו", and a bare "תל אביב"
# (DECISIONS.md #214: a wrong active post stays visible, a wrong rejection disappears). Exact match,
# never a substring: the part after the comma is the district and reads "תל אביב" for Holon.
TEL_AVIV_KEYS = frozenset({"תל אביב יפו", "תל אביב"})
_HEBREW_LETTER = re.compile("[א-ת]")


class CityRuling(NamedTuple):
    name: str | None
    """The city to show, or None when the post is in Tel Aviv-Yafo (or names none)."""
    source: CitySource | None
    """`correction` when the admin's correction of `other_city` decided (#296), `native_location`
    when Facebook's location field did, `model` when the model did, None when there is no city."""


def native_locality(native_location: str | None) -> str | None:
    """The locality of Facebook's location field: the part before the first comma, trimmed, with no
    format characters (U+200E and the like) and one space for any run of whitespace. None when the
    field is absent, the locality is empty, or it has no Hebrew letter (the model decides then,
    #214). Hebrew is never folded: this is shown to the user."""
    if native_location is None:
        return None
    text = "".join(c for c in native_location if unicodedata.category(c) != "Cf")
    locality = " ".join(text.split(",", 1)[0].split())
    if not _HEBREW_LETTER.search(locality):
        return None
    return locality


def _key(locality: str) -> str:
    """The comparison key: every dash-like character (category Pd, the minus sign) read as a space,
    whitespace collapsed. "תל אביב - יפו", "תל אביב-יפו" and OSM's "תל־אביב–יפו" give one key."""
    spaced = "".join(" " if unicodedata.category(c) == "Pd" or c == "−" else c for c in locality)
    return " ".join(spaced.split())


def other_city_ruling(post: RawPost, listing: Listing | SeenListing) -> CityRuling:
    """A correction of `other_city` in force decides first, its value or its null (#296); then
    Facebook's location when it has a usable locality (#214); otherwise the model."""
    if isinstance(listing, SeenListing):
        if "other_city" in listing.corrected:
            city = listing.listing.other_city
            return CityRuling(None, None) if city is None else CityRuling(city, "correction")
        listing = listing.listing
    locality = native_locality(post.native_location)
    if locality is not None:
        if _key(locality) in TEL_AVIV_KEYS:
            return CityRuling(None, None)
        return CityRuling(locality, "native_location")
    if listing.other_city is not None:
        return CityRuling(listing.other_city, "model")
    return CityRuling(None, None)


def other_city_name(post: RawPost, listing: Listing | SeenListing) -> str | None:
    """The city a card shows for an other-city post: the corrected city, the native locality, or
    the model's city. The card and the rejected list pass the `SeenListing`."""
    return other_city_ruling(post, listing).name


def model_reason(post: RawPost, listing: Listing | SeenListing) -> ModelReason | None:
    """The first model-derived reason that applies, in Gate E order: `other_city`, then the post's
    nature. `no_text` and `no_images` come earlier but never reach the model; `flagged` is a
    user's. A rental or a sublet offer has none (#93)."""
    if other_city_ruling(post, listing).name is not None:
        return "other_city"
    nature = (listing.listing if isinstance(listing, SeenListing) else listing).post_nature
    if nature in ("seeking", "for_sale", "not_listing"):
        return nature
    return None


def classified_lifecycle(existing: PostLifecycle, listing: Listing, post: RawPost) -> PostLifecycle:
    """The record of a pending post after a successful classification. The failure fields are
    left as they are (#152)."""
    _check(existing, listing.listing_id)
    if post.listing_id != listing.listing_id:
        raise ValueError(f"post {post.listing_id} does not belong to {listing.listing_id}")
    reason = model_reason(post, listing)
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


def restored_lifecycle(existing: PostLifecycle, post: RawPost, seen: SeenListing) -> PostLifecycle:
    """The record a restore leaves (#251, #281–#283; the write and the reports are 3.8's): the
    flag fields cleared and the state derived from the post as users see it, by `model_reason`,
    the rule a classification uses. An archived post stays archived, its reason re-derived (#283);
    otherwise `"active"`, or `"rejected"` with the derived reason. Every other field is kept.
    Refuses a record with no flag and no report (`flagged_by` is set by both, #280)."""
    if existing.listing_id != post.listing_id or seen.listing.listing_id != post.listing_id:
        raise ValueError(f"lifecycle record {existing.listing_id} does not belong to the post")
    if existing.flagged_by is None:
        raise ValueError(f"post {existing.listing_id} has no flag and no report to restore")
    reason = model_reason(post, seen)
    if existing.state == "archived":
        state = "archived"
    else:
        state = "active" if reason is None else "rejected"
    return PostLifecycle(
        **{
            **dict(existing),
            "state": state,
            "rejection_reason": reason,
            "flagged_by": None,
            "flagged_at": None,
            "flag_note": None,
        }
    )


def _check(existing: PostLifecycle, listing_id: str) -> None:
    if existing.listing_id != listing_id:
        raise ValueError(f"lifecycle record {existing.listing_id} does not belong to {listing_id}")
    if existing.state != "pending":
        raise ValueError(f"only a pending record is classified, not {existing.state!r}")
