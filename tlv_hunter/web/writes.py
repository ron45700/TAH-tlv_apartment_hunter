"""The writes a user makes on a card (`PHASE_3.md` 3.7 (i), build step 6; DECISIONS.md #260, #300,
#330 point 21). Wiring: the records are built by `postmodel/rejects.py` (`flagged_lifecycle`,
`reported_lifecycle`), the one place for Gate E's flag and report rules; this module reads, writes
by compare and set, and says what happened.

**Until 3.9 the site writes its dated copy of the store only (#331).** A flag or a report changes
`post_lifecycle`, so the store generation counter moves and the next request recomputes the grouping
(#316): the card leaves the list. No `RawPost` and no `Listing` is ever written (invariant 14), and
nothing per user is written on a post (invariant 12) beyond the flag fields Gate E allows.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from tlv_hunter.accounts.tokens import new_opaque_id
from tlv_hunter.contracts.classification_report import (
    CLASSIFICATION_REPORT_SCHEMA_VERSION,
    ClassificationReport,
    ReportableField,
)
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.postmodel.rejects import flagged_lifecycle, reported_lifecycle
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.base import UserDataStore

# A write that meets another writer reads the record again and tries once more (3.7 (i)).
ATTEMPTS = 2

# The reportable fields as a user reads them in the report's form (#277: the labels are the UI
# task's). The order is the form's.
REPORT_LABELS: Mapping[ReportableField, str] = {
    "post_nature": "סוג המודעה (השכרה, חיפוש, מכירה)",
    "apartment_kind": "חדר או דירה שלמה",
    "price": "מחיר",
    "entry_date": "תאריך כניסה",
    "rooms": "מספר חדרים",
    "floor": "קומה",
    "building_floors": "קומות בבניין",
    "size_sqm": "גודל הדירה",
    "room_size_sqm": "גודל החדר",
    "broker": "תיווך",
    "balcony": "מרפסת",
    "parking": "חניה",
    "elevator": "מעלית",
    "air_conditioning": "מיזוג",
    "furnished": "ריהוט",
    "arnona": "ארנונה",
    "house_committee": "ועד בית",
    "gender": "נשים בלבד או עדיפות לבנות",
    "areas": "אזור",
    "streets": "רחוב",
    "other_city": "עיר אחרת",
    "phone_names": "שמות ליד הטלפונים",
}


@dataclass(frozen=True)
class FlagResult:
    written: tuple[str, ...]
    """The members whose record now carries the flag."""
    not_written: tuple[str, ...]
    """The members left as they were: no longer active, or changed by another writer twice."""


@dataclass(frozen=True)
class ReportResult:
    report: ClassificationReport
    removed: bool
    """Whether the post's record now keeps it off the lists; when not, the report stays stored and
    the admin handles it (3.7 (i))."""


def flag_card(
    posts: SqliteRepository, card: Card, user_id: str, now: datetime, note: str | None
) -> FlagResult:
    """The "lied" flag on every one of the card's members (#300), each by compare and set; a member
    that is no longer active is skipped. Two records cannot be set in one transaction, so a result
    can be partial (#330 point 21)."""
    written: list[str] = []
    not_written: list[str] = []
    for listing_id in card.canonical_ids:
        done = _write(posts, listing_id, lambda r: flagged_lifecycle(r, user_id, now, note))
        (written if done else not_written).append(listing_id)
    return FlagResult(tuple(written), tuple(not_written))


def report_post(
    posts: SqliteRepository,
    userdata: UserDataStore,
    card: Card,
    user_id: str,
    fields: Sequence[ReportableField],
    note: str | None,
    now: datetime,
) -> ReportResult:
    """A "wrong classification" report on the card's shown post only (#300): the report first
    (`OpenReportExists` when the user already has an open one on it, #278), then the post's record
    by compare and set (#279, #280). Two seams, two transactions (#289 point 3)."""
    report = userdata.add_report(
        ClassificationReport(
            schema_version=CLASSIFICATION_REPORT_SCHEMA_VERSION,
            report_id=new_opaque_id(),
            listing_id=card.shown_id,
            reported_by=user_id,
            reported_at=now,
            fields=list(fields),
            note=note,
            status="open",
            resolved_by=None,
            resolved_at=None,
        )
    )
    removed = _write(posts, card.shown_id, lambda r: reported_lifecycle(r, user_id, now))
    return ReportResult(report, removed)


def _write(
    posts: SqliteRepository, listing_id: str, change: Callable[[PostLifecycle], PostLifecycle]
) -> bool:
    """Read, change, write by compare and set; on `StaleRecordError` read again and try once more.
    True when the stored record ends as the change wants it (already so counts)."""
    for _ in range(ATTEMPTS):
        existing = posts.get_lifecycle(listing_id)
        if existing is None:
            return False
        try:
            record = change(existing)
        except ValueError:
            return False  # no longer a post a user can flag or report
        if record == existing:
            return True
        try:
            posts.save_lifecycle(record, expected=existing)
        except StaleRecordError:
            continue
        return True
    return False
