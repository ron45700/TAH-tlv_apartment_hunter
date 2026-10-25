"""The JSON of the admin's pages (`PHASE_3.md` 3.8 (c), (d)). Pure, as `cards.py`: from records read
by the caller to plain dicts; it reads no store and writes nothing.

A post's fields are `cards.listing_json`'s, the post as users see it (the corrections in force
applied, #256); the model's own answer is given beside it on the detail page. The city of an
other-city post is `postmodel.rejects`'s ruling (#214, #296). A user is named by their username,
never by `user_id` (Gate C: `user_id` is never shown). No hash of any kind is ever put in a
payload: not a password's, a key's or a session's. A photo's address names its post and file only;
the file is found again from the stored record when it is asked for (`admin.py`).
"""

from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any, get_args

from tlv_hunter.contracts.classification_report import ClassificationReport, ReportableField
from tlv_hunter.contracts.field_correction import FieldCorrection
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.contracts.signup_key import SignupKey
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import KeyPost, OtherPost
from tlv_hunter.postmodel.rejects import ReportMark, other_city_ruling
from tlv_hunter.postmodel.seen import SeenListing
from tlv_hunter.web.cards import (
    listing_json,
    photo_name,
    post_videos,
    shown_phones,
    source_of,
    whatsapp_link,
)
from tlv_hunter.web.writes import REPORT_LABELS

# Gate E's reasons and states as the admin reads them (3.8 (c)).
REASON_WORDS = {
    "no_text": "אין טקסט",
    "no_images": "אין תמונות",
    "other_city": "עיר אחרת",
    "seeking": "מחפשים דירה",
    "for_sale": "למכירה",
    "not_listing": "לא מודעת דירה",
    "flagged": "סומנה כמשקרת",
    "misclassified": "דווח סיווג שגוי",
}
STATE_WORDS = {
    "pending": "ממתינה לסיווג",
    "active": "פעילה",
    "rejected": "נדחתה",
    "archived": "בארכיון",
}
UNKNOWN_USER = "משתמש לא ידוע"

ListItem = KeyPost | OtherPost


def admin_photo_urls(listing_id: str, lifecycle: PostLifecycle) -> list[str]:
    """The admin's addresses of a post's downloaded photos, in the stored order."""
    return [
        f"/api/admin/photos/{listing_id}/{photo_name(image.local_path)}"
        for image in lifecycle.images
        if image.local_path is not None
    ]


def post_row(
    item: ListItem,
    *,
    duplicates: int,
    area_names: Mapping[int, str],
    usernames: Mapping[str, str],
) -> dict:
    """A row of the rejected, pending, archive or flags list, or a reported post's head."""
    post, lifecycle, seen = item.post, item.lifecycle, item.seen
    photos = admin_photo_urls(post.listing_id, lifecycle)
    return {
        "id": post.listing_id,
        **_state(lifecycle),
        "city": None if seen is None else other_city_ruling(post, seen).name,
        "posted_at": post.posted_at.isoformat(),
        "last_published_at": lifecycle.last_published_at.isoformat(),
        "publications": 1 + duplicates,
        "source": source_of(post),
        "text": post.text,
        "permalink": post.permalink,
        "photo": photos[0] if photos else None,
        "photo_count": len(photos),
        "videos": post_videos(post),
        "failures": lifecycle.classification_failures,
        "last_error": lifecycle.last_classification_error,
        "flag": _flag(lifecycle, usernames),
        "listing": None if seen is None else listing_json(seen.listing, area_names),
        "corrected": [] if seen is None else sorted(seen.corrected),
    }


def post_detail(
    post: RawPost,
    lifecycle: PostLifecycle,
    model: Listing | None,
    seen: SeenListing | None,
    *,
    corrections: Sequence[FieldCorrection],
    reports: Sequence[ClassificationReport],
    duplicates: Sequence[RawPost],
    marks: Iterable[ReportMark],
    preview: PostLifecycle | None,
    area_names: Mapping[int, str],
    usernames: Mapping[str, str],
) -> dict:
    """The admin's opened post (3.8 (c), "Post detail"), read fresh by the caller: the post, its
    record, the model's answer beside the seen one field by field, every correction and report, the
    city's ruling and its source, and what a restore would leave now (#406)."""
    ruling = None if seen is None else other_city_ruling(post, seen)
    names = {} if seen is None else {entry.phone: entry.name for entry in seen.listing.phone_names}
    publications = sorted([post, *duplicates], key=lambda each: (each.posted_at, each.listing_id))
    return {
        "id": post.listing_id,
        "canonical": post.is_canonical is not False,
        "lifecycle": {
            **_state(lifecycle),
            "flag": _flag(lifecycle, usernames),
            "failures": lifecycle.classification_failures,
            "last_error": lifecycle.last_classification_error,
            "last_published_at": lifecycle.last_published_at.isoformat(),
            "image_errors": [image.error for image in lifecycle.images if image.error is not None],
        },
        "source": source_of(post),
        "text": post.text,
        "permalink": post.permalink,
        "posted_at": post.posted_at.isoformat(),
        "photos": admin_photo_urls(post.listing_id, lifecycle),
        "videos": post_videos(post),
        "phones": [
            {"phone": phone, "name": names.get(phone), "whatsapp": whatsapp_link(phone)}
            for phone in shown_phones(post)
        ],
        "publications": [
            {"id": each.listing_id, "posted_at": each.posted_at.isoformat()}
            for each in publications
        ],
        "listing": None if seen is None else listing_json(seen.listing, area_names),
        "fields": [] if model is None else field_rows(model, seen),
        "classified": None
        if model is None
        else {
            "model_name": model.model_name,
            "prompt_version": model.prompt_version,
            "classified_at": model.classified_at.isoformat(),
        },
        "city": None if ruling is None else {"name": ruling.name, "source": ruling.source},
        "corrections": [correction_json(c, usernames) for c in corrections],
        "reports": [report_json(r, usernames) for r in reports],
        "marks": sorted(marks),
        "restore_preview": None if preview is None else _state(preview),
    }


def field_rows(model: Listing, seen: SeenListing | None) -> list[dict]:
    """Every reportable field (#277): the model's value as stored, the value users see, and whether
    a correction in force replaced it (#256)."""
    stored = model.model_dump(mode="json")
    shown = stored if seen is None else seen.listing.model_dump(mode="json")
    corrected = frozenset() if seen is None else seen.corrected
    return [
        {
            "field": name,
            "label": REPORT_LABELS[name],
            "model": stored[name],
            "seen": shown[name],
            "corrected": name in corrected,
        }
        for name in get_args(ReportableField)
    ]


def report_json(report: ClassificationReport, usernames: Mapping[str, str]) -> dict:
    return {
        "report_id": report.report_id,
        "listing_id": report.listing_id,
        "reporter": usernames.get(report.reported_by, UNKNOWN_USER),
        "reported_at": report.reported_at.isoformat(),
        "fields": [{"field": name, "label": REPORT_LABELS[name]} for name in report.fields],
        "note": report.note,
        "status": report.status,
        "resolved_by": _username(report.resolved_by, usernames),
        "resolved_at": _iso(report.resolved_at),
    }


def correction_json(correction: FieldCorrection, usernames: Mapping[str, str]) -> dict:
    dumped = correction.model_dump(mode="json")
    return {
        "correction_id": correction.correction_id,
        "listing_id": correction.listing_id,
        "field": correction.field,
        "label": REPORT_LABELS[correction.field],
        "model_value": dumped["model_value"],
        "corrected_value": dumped["corrected_value"],
        "corrected_by": usernames.get(correction.corrected_by, UNKNOWN_USER),
        "corrected_at": correction.corrected_at.isoformat(),
        "report_id": correction.report_id,
        "removed_by": _username(correction.removed_by, usernames),
        "removed_at": _iso(correction.removed_at),
    }


def key_json(key: SignupKey, usernames: Mapping[str, str]) -> dict:
    """A key as the list shows it (#243): never its hash, and never the key itself (#266)."""
    state = "cancelled" if key.cancelled_at else "used" if key.used_by else "usable"
    return {
        "key_id": key.key_id,
        "label": key.label,
        "created_at": key.created_at.isoformat(),
        "state": state,
        "used_by": _username(key.used_by, usernames),
        "used_at": _iso(key.used_at),
        "cancelled_at": _iso(key.cancelled_at),
    }


def user_json(user: User, key_labels: Mapping[str, str]) -> dict:
    """A user as the list shows it: by username only; never `user_id` or the password's hash."""
    return {
        "username": user.username,
        "created_at": user.created_at.isoformat(),
        "is_admin": user.is_admin,
        "key_label": None if user.signup_key_id is None else key_labels.get(user.signup_key_id),
        "disabled_at": _iso(user.disabled_at),
        "must_change_password": user.must_change_password,
        "failed_sign_ins": user.failed_sign_ins,
    }


def _state(lifecycle: PostLifecycle) -> dict[str, Any]:
    reason = lifecycle.rejection_reason
    return {
        "state": lifecycle.state,
        "state_words": STATE_WORDS[lifecycle.state],
        "reason": reason,
        "reason_words": None if reason is None else REASON_WORDS[reason],
    }


def _flag(lifecycle: PostLifecycle, usernames: Mapping[str, str]) -> dict[str, Any] | None:
    if lifecycle.flagged_by is None:
        return None
    return {
        "by": usernames.get(lifecycle.flagged_by, UNKNOWN_USER),
        "at": _iso(lifecycle.flagged_at),
        "note": lifecycle.flag_note,
    }


def _username(user_id: str | None, usernames: Mapping[str, str]) -> str | None:
    return None if user_id is None else usernames.get(user_id, UNKNOWN_USER)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()
