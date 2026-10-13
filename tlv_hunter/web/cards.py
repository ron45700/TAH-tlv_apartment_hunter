"""The JSON of a card and of an opened post (`PHASE_3.md` 3.7 (c), (g)). Pure: from the held cards
and an evaluation to plain dicts; it reads no store and writes nothing.

Every value is the post as users see it (`SeenListing`, the admin's corrections applied, #256),
never re-derived here: the rules stay in `policy/` and `postmodel/`. Datetimes are ISO-8601 UTC
(invariant 9; the page shows them in Israel time). The poster's text is sent whole and unchanged
(invariant 11; #312). A photo's address names its post and file only; the file is found again from
the stored record when it is asked for (`routes.py`), never from the address.

The colours, the glow and the tier's reasons are `policy/colours.py`'s (step 3); this module only
puts them into words, so the page holds no rule (#330 point 18). A WhatsApp link is built for each
mobile number (`textnorm.phones.whatsapp_number`, #311, #330 point 22).
"""

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any

from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.dedup.stage_b import Card, KeyPost
from tlv_hunter.policy.base import Evaluation
from tlv_hunter.policy.colours import field_colours, glow, tier_reasons
from tlv_hunter.textnorm.phones import whatsapp_number

MARKED_FIELDS = (
    "apartment_kind",
    "price",
    "entry_date",
    "rooms",
    "floor",
    "building_floors",
    "size_sqm",
    "room_size_sqm",
    "broker",
    "balcony",
    "parking",
    "elevator",
    "air_conditioning",
    "furnished",
    "arnona",
    "house_committee",
)
PHOTO_TYPES = ("photo", "Photo")
WHATSAPP = "https://wa.me/{number}"

# The tier's label, in the words of 3.7 (d) (#323), and each reason's words by the field's state.
TIER_WORDS = {
    "preferences_met": "מתאים לכל ההעדפות",
    "critical_met": "מתאים חלקית",
    "unknown": "חסר מידע",
}
NO_PREFERENCE = "לא הוגדרו העדפות בחיפוש הזה"
FIELD_NAMES = {
    "rooms": "חדרים",
    "floor": "קומה",
    "size_sqm": "גודל",
    "broker": "תיווך",
    "parking": "חניה",
    "balcony": "מרפסת",
    "entry_date": "תאריך כניסה",
    "price": "מחיר",
    "areas": "אזור",
}
REASON_WORDS = {
    ("kind", None): "סוג הנכס לא ברור",
    ("location", None): "המיקום לא ודאי",
    ("price", "not_written"): "אין מחיר",
    ("price", "unclear"): "המחיר לא ברור",
    ("areas", "not_written"): "אין מיקום",
    ("areas", "unclear"): "האזור לא ברור",
    ("entry_date", "not_written"): "אין תאריך כניסה",
    ("broker", "mismatch"): "בתיווך",
    ("parking", "mismatch"): "אין חניה",
    ("balcony", "mismatch"): "אין מרפסת",
}
STATE_WORDS = {"mismatch": "מחוץ לטווח", "not_written": "לא צוין", "unclear": "לא ברור"}


def photo_name(local_path: str) -> str:
    return PurePosixPath(local_path).name


def photo_urls(member: KeyPost) -> list[str]:
    """The addresses of the post's downloaded photos, in the stored order."""
    return [
        f"/api/photos/{member.listing_id}/{photo_name(image.local_path)}"
        for image in member.lifecycle.images
        if image.local_path is not None
    ]


def video_links(member: KeyPost) -> list[str]:
    """Facebook's page of each video or reel (only photos are downloaded); a post with no photo
    shows the first in the photo's place (round 9)."""
    return [media.page_url for media in member.post.media if media.type not in PHOTO_TYPES]


def card_payload(
    card: Card, evaluation: Evaluation, profile: Profile, area_names: Mapping[int, str]
) -> dict:
    """A closed card (3.7 (c)): the shown post's summary, its evaluation, its colours and glow."""
    shown = card.shown
    listing = shown.seen.listing
    mobiles = whatsapp_links(shown)
    return {
        "id": card.shown_id,
        "post_ids": sorted(card.post_ids),
        "evaluation": _evaluation(evaluation),
        "glow": glow(evaluation, profile),
        "tier_label": tier_label(listing, evaluation, profile),
        "colours": dict(field_colours(listing, evaluation)),
        **_listing(listing, area_names),
        "text": shown.post.text,
        "permalink": shown.post.permalink,
        "photos": photo_urls(shown),
        "videos": video_links(shown),
        "whatsapp": mobiles[0] if mobiles else None,
        "last_published_at": card.last_published_at.isoformat(),
        "publications": len(card.publications),
    }


def tier_label(listing: Listing, evaluation: Evaluation, profile: Profile) -> str | None:
    """The "i"'s words (#323): the tier and, below the first, why. `None` for a post not shown."""
    if not evaluation.shown or evaluation.tier is None:
        return None
    if evaluation.tier == "preferences_met":
        return TIER_WORDS["preferences_met"] if glow(evaluation, profile) else NO_PREFERENCE
    reasons = [
        _reason_words(name, listing, evaluation)
        for name in tier_reasons(listing, evaluation, profile)
    ]
    head = TIER_WORDS[evaluation.tier]
    return f"{head}: {', '.join(reasons)}" if reasons else head


def _reason_words(name: str, listing: Listing, evaluation: Evaluation) -> str:
    if name in ("kind", "location"):
        return REASON_WORDS[(name, None)]
    state = evaluation.fields.get(name)
    if name == "price" and listing.price.state == "not_written":
        state = "not_written"
    words = REASON_WORDS.get((name, state))
    if words is not None:
        return words
    return f"{FIELD_NAMES.get(name, name)}: {STATE_WORDS.get(state or '', 'לא ידוע')}"


def whatsapp_links(member: KeyPost) -> list[str]:
    """A click-to-chat link for each mobile number of the post, in the post's order."""
    links = (_whatsapp(phone) for phone in (member.post.phones or []))
    return [link for link in links if link is not None]


def post_payload(card: Card, area_names: Mapping[int, str]) -> dict:
    """An opened post (3.7 (c)): everything of the card's shown post, its phones with the names the
    post gave and their WhatsApp links, and every publication, earliest first. No evaluation: it
    follows the bar, and the page takes the tier, the glow and the colours from the list's card;
    `own_colours` are the post's own, for a post the list does not hold."""
    shown = card.shown
    listing = shown.seen.listing
    names = {entry.phone: entry.name for entry in listing.phone_names}
    return {
        "id": card.shown_id,
        "post_ids": sorted(card.post_ids),
        **_listing(listing, area_names),
        "corrected": sorted(shown.seen.corrected),
        "own_colours": dict(field_colours(listing, None)),
        "text": shown.post.text,
        "permalink": shown.post.permalink,
        "photos": photo_urls(shown),
        "videos": video_links(shown),
        "phones": [
            {"phone": phone, "name": names.get(phone), "whatsapp": _whatsapp(phone)}
            for phone in (shown.post.phones or [])
        ],
        "last_published_at": card.last_published_at.isoformat(),
        "publications": [
            {"id": publication.listing_id, "posted_at": publication.posted_at.isoformat()}
            for publication in card.publications
        ],
    }


def _whatsapp(phone: str) -> str | None:
    number = whatsapp_number(phone)
    return None if number is None else WHATSAPP.format(number=number)


def _listing(listing: Listing, area_names: Mapping[int, str]) -> dict:
    return {
        "post_nature": listing.post_nature,
        **{name: _marked(getattr(listing, name)) for name in MARKED_FIELDS},
        "entry_date_written": listing.entry_date_written,
        "gender": listing.gender,
        "areas": [{"number": n, "name": area_names[n]} for n in listing.areas],
        "streets": list(listing.streets),
        "stated_area_names": list(listing.stated_area_names),
    }


def _evaluation(evaluation: Evaluation) -> dict:
    return {
        "option": evaluation.option,
        "tier": evaluation.tier,
        "kind_marked": evaluation.kind_marked,
        "fields": dict(evaluation.fields),
        "missing_important": sorted(evaluation.missing_important),
        "area_orange": evaluation.area_orange,
        "women_only_icon": evaluation.women_only_icon,
        "corrected": sorted(evaluation.corrected),
    }


def _marked(marked: Marked[Any]) -> dict:
    return {"state": marked.state, "value": _plain(marked.value)}


def _plain(value: Any) -> Any:
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value
