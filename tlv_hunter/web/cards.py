"""The JSON of a card and of an opened post (`PHASE_3.md` 3.7 (c), (g)). Pure: from the held cards
and an evaluation to plain dicts; it reads no store and writes nothing.

Every value is the post as users see it (`SeenListing`, the admin's corrections applied, #256),
never re-derived here: the rules stay in `policy/` and `postmodel/`. Datetimes are ISO-8601 UTC
(invariant 9; the page shows them in Israel time). The poster's text is sent whole and unchanged
(invariant 11; #312). A photo's address names its post and file only; the file is found again from
the stored record when it is asked for (`routes.py`), never from the address.
"""

from collections.abc import Mapping
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Any

from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.dedup.stage_b import Card, KeyPost
from tlv_hunter.policy.base import Evaluation

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


def card_payload(card: Card, evaluation: Evaluation, area_names: Mapping[int, str]) -> dict:
    """A closed card (3.7 (c)): the shown post's summary and its evaluation."""
    shown = card.shown
    return {
        "id": card.shown_id,
        "post_ids": sorted(card.post_ids),
        "evaluation": _evaluation(evaluation),
        **_listing(shown.seen.listing, area_names),
        "text": shown.post.text,
        "permalink": shown.post.permalink,
        "photos": photo_urls(shown),
        "videos": video_links(shown),
        "last_published_at": card.last_published_at.isoformat(),
        "publications": len(card.publications),
    }


def post_payload(card: Card, area_names: Mapping[int, str]) -> dict:
    """An opened post (3.7 (c)): everything of the card's shown post, its phones with the names the
    post gave, and every publication, earliest first. No evaluation: it follows the bar, which the
    page already holds from the list."""
    shown = card.shown
    listing = shown.seen.listing
    names = {entry.phone: entry.name for entry in listing.phone_names}
    return {
        "id": card.shown_id,
        "post_ids": sorted(card.post_ids),
        **_listing(listing, area_names),
        "corrected": sorted(shown.seen.corrected),
        "text": shown.post.text,
        "permalink": shown.post.permalink,
        "photos": photo_urls(shown),
        "videos": video_links(shown),
        "phones": [
            {"phone": phone, "name": names.get(phone)} for phone in (shown.post.phones or [])
        ],
        "last_published_at": card.last_published_at.isoformat(),
        "publications": [
            {"id": publication.listing_id, "posted_at": publication.posted_at.isoformat()}
            for publication in card.publications
        ],
    }


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
