"""The admin's writes on a post (`PHASE_3.md` 3.8 (e); DECISIONS.md #389–#406). Wiring, as
`writes.py`: the records are built by `postmodel/rejects.py` (`restored_lifecycle`,
`reported_lifecycle`) and the contracts; this module reads, checks the post's `version`, writes by
compare and set, and says what happened.

**The post's `version` (#391).** SHA-256 of the canonical JSON of what a post write depends on: the
post's `PostLifecycle`, its reports and its corrections, every status. The page sends back the
`version` it showed; a different one is `Changed` and nothing is written. Each record is then
written by compare and set against the record just read (#260), so a write between that read and
the write is refused as well. No automatic retry: the admin decided on what the page showed.

**Restore (#251, #281–#283, #392):** the reports first (every open or left-out report of the post to
`"restored"`), then the lifecycle (`restored_lifecycle` over the post as users see it). A conflict
on the lifecycle leaves the reports restored and the post rejected: `report_marks` derives it as
`"restore_unfinished"`, and running the restore again finishes it.

No write here touches a `RawPost` or a `Listing` (invariant 14); nothing per user is written on a
post (invariant 12). **Until 3.9 the site writes its dated copy only (#331, #400).**
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

from tlv_hunter.accounts.tokens import new_opaque_id
from tlv_hunter.contracts.classification_report import ClassificationReport, ReportableField
from tlv_hunter.contracts.field_correction import FIELD_CORRECTION_SCHEMA_VERSION, FieldCorrection
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rejects import reported_lifecycle, restored_lifecycle
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.base import CorrectionInForce, UserDataStore
from tlv_hunter.web.writes import REPORT_LABELS

RESOLVABLE = ("open", "left_out")


class Changed(Exception):
    """The post changed since the page read it (another `version`, or another writer)."""


class Invalid(Exception):
    """A corrected value that breaks Gate B; `words` says which rule, in plain Hebrew (#410)."""

    def __init__(self, words: str) -> None:
        super().__init__(words)
        self.words = words


# Gate B's rules as the admin reads them (#410): each validator's own message
# (`contracts/listing.py`) and the words shown for it. A value that breaks no rule named here is
# "not of the field's type".
RULE_WORDS: tuple[tuple[str, str], ...] = (
    (
        "value is set exactly when state is 'written'",
        "כשהערך כתוב במודעה צריך למלא אותו; כשלא צוין או לא ברור, בלי ערך.",
    ),
    (
        "rooms is a positive multiple of 0.5",
        "מספר החדרים הוא מספר חיובי בקפיצות של חצי, למשל 2 או 2.5.",
    ),
    ("areas are municipal numbers 1-71", "אזור: רק מתוך 71 האזורים שברשימה."),
    ("areas are sorted with no repeats", "אזור: כל אזור פעם אחת."),
    ("a written price holds at least one amount", "מחיר שכתוב במודעה צריך לפחות סכום אחד."),
    ("prices are greater than 0", "כל סכום במחיר גדול מ-0."),
    ("phone must be in the stored format", "טלפון: רק מספר מהטלפונים של המודעה."),
)


def invalid_words(field: ReportableField, error: Exception) -> str:
    """The words for a value Gate B refuses: the rule it breaks, else that it does not fit the
    field. Never the validator's own text, which is English and technical (#410)."""
    text = str(error)
    for rule, words in RULE_WORDS:
        if rule in text:
            return words
    return f'הערך לא מתאים לשדה "{REPORT_LABELS[field]}".'


class Refused(Exception):
    """The write does not apply to the post as it is; `reason` names why."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class PostState:
    """What a post write reads, fresh from the store."""

    post: RawPost
    lifecycle: PostLifecycle
    listing: Listing | None
    reports: tuple[ClassificationReport, ...]
    corrections: tuple[FieldCorrection, ...]

    @property
    def version(self) -> str:
        return post_version(self.lifecycle, self.reports, self.corrections)

    @property
    def in_force(self) -> tuple[FieldCorrection, ...]:
        return tuple(c for c in self.corrections if c.in_force)


def post_version(
    lifecycle: PostLifecycle,
    reports: Sequence[ClassificationReport],
    corrections: Sequence[FieldCorrection],
) -> str:
    """The `version` of a post write (#391): its record, reports and corrections, in a fixed
    order."""
    payload = {
        "lifecycle": lifecycle.model_dump(mode="json"),
        "reports": sorted(
            (r.model_dump(mode="json") for r in reports), key=lambda r: r["report_id"]
        ),
        "corrections": sorted(
            (c.model_dump(mode="json") for c in corrections), key=lambda c: c["correction_id"]
        ),
    }
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def read_state(posts: SqliteRepository, userdata: UserDataStore, listing_id: str) -> PostState:
    """The post as a write reads it; `Refused("unknown_post")` when it is not stored."""
    post = posts.get(listing_id)
    lifecycle = None if post is None else posts.get_lifecycle(listing_id)
    if post is None or lifecycle is None:
        raise Refused("unknown_post")
    return PostState(
        post=post,
        lifecycle=lifecycle,
        listing=posts.get_listing(listing_id),
        reports=tuple(userdata.find_reports(listing_id=listing_id)),
        corrections=tuple(userdata.find_corrections(listing_id=listing_id, in_force=False)),
    )


def _checked(
    posts: SqliteRepository, userdata: UserDataStore, listing_id: str, version: str
) -> PostState:
    state = read_state(posts, userdata, listing_id)
    if state.version != version:
        raise Changed(listing_id)
    return state


# --- retry, restore, leave out, remove from the list (build step 4) ---


def retry(
    posts: SqliteRepository, userdata: UserDataStore, listing_id: str, version: str
) -> PostLifecycle:
    """A pending post's failure count back to 0 (Gate E, #139, #152); the error is kept. The next
    `classify_pending` run takes it."""
    state = _checked(posts, userdata, listing_id, version)
    life = state.lifecycle
    if life.state != "pending" or life.classification_failures == 0:
        raise Refused("not_retryable")
    return _save(posts, _changed(life, classification_failures=0), life)


Outcome = Literal["restored", "changed", "not_restorable"]


@dataclass(frozen=True)
class RestoreResult:
    listing_id: str
    outcome: Outcome
    lifecycle: PostLifecycle | None = None
    """The post's record after the restore, when `restored`."""


def restore(
    posts: SqliteRepository,
    userdata: UserDataStore,
    listing_id: str,
    version: str,
    admin_id: str,
    now: datetime,
) -> PostLifecycle:
    """One rule for a flagged and a reported post (#251, #282): the reports first, then the record
    (#392). An archived post stays archived, its reason re-derived (#283)."""
    state = _checked(posts, userdata, listing_id, version)
    resolvable = [r for r in state.reports if r.status in RESOLVABLE]
    if state.lifecycle.flagged_by is None and not resolvable:
        raise Refused("not_restorable")
    for report in resolvable:
        restored = _changed(report, status="restored", resolved_by=admin_id, resolved_at=now)
        try:
            userdata.save_report(restored, expected=report)
        except StaleRecordError:
            raise Changed(listing_id) from None
    if state.lifecycle.flagged_by is None or state.listing is None:
        return state.lifecycle  # a report whose post was never removed: the reports only
    seen = seen_listing(state.listing, state.in_force)
    record = restored_lifecycle(state.lifecycle, state.post, seen)
    return _save(posts, record, state.lifecycle)


def restore_many(
    posts: SqliteRepository,
    userdata: UserDataStore,
    asked: Sequence[tuple[str, str]],
    admin_id: str,
    now: datetime,
) -> list[RestoreResult]:
    """A flag action's posts (#393), each by its own compare and set: a result can be partial."""
    results = []
    for listing_id, version in asked:
        try:
            record = restore(posts, userdata, listing_id, version, admin_id, now)
        except Changed:
            results.append(RestoreResult(listing_id, "changed"))
        except Refused:
            results.append(RestoreResult(listing_id, "not_restorable"))
        else:
            results.append(RestoreResult(listing_id, "restored", record))
    return results


def leave_out(
    posts: SqliteRepository,
    userdata: UserDataStore,
    listing_id: str,
    version: str,
    admin_id: str,
    now: datetime,
) -> list[ClassificationReport]:
    """Every open report of the post to `"left_out"`; the record is not written: the post stays
    rejected `"misclassified"`, kept from deletion (#255, #286). Restored later at will."""
    state = _checked(posts, userdata, listing_id, version)
    opened = [r for r in state.reports if r.status == "open"]
    if not opened:
        raise Refused("no_open_report")
    written = []
    for report in opened:
        left = _changed(report, status="left_out", resolved_by=admin_id, resolved_at=now)
        try:
            written.append(userdata.save_report(left, expected=report))
        except StaleRecordError:
            raise Changed(listing_id) from None
    return written


def apply_reports(
    posts: SqliteRepository, userdata: UserDataStore, listing_id: str, version: str
) -> PostLifecycle:
    """A report stored while its post stayed on the list (3.4 point 3): the post's record as the
    report should have left it, `flagged_by` and `flagged_at` the earliest open report's (#280,
    #402). Only while the post is still active."""
    state = _checked(posts, userdata, listing_id, version)
    opened = sorted(
        (r for r in state.reports if r.status == "open"),
        key=lambda r: (r.reported_at, r.report_id),
    )
    if not opened or state.lifecycle.state != "active" or state.lifecycle.flagged_by is not None:
        raise Refused("not_applicable")
    first = opened[0]
    record = reported_lifecycle(state.lifecycle, first.reported_by, first.reported_at)
    return _save(posts, record, state.lifecycle)


# --- corrections (build step 5) ---


def correct(
    posts: SqliteRepository,
    userdata: UserDataStore,
    listing_id: str,
    version: str,
    field: ReportableField,
    corrected_value: Any,
    report_id: str,
    admin_id: str,
    now: datetime,
) -> FieldCorrection:
    """The admin's correction of one field, made from a report (#395): `model_value` the stored
    `Listing`'s value now; checked by its Gate B type and as the whole post (#405) before anything
    is written. A correction in force on the field is replaced: the old removed, then the new added
    (#404). The record is not written: the post stays as it is until the admin restores it."""
    state = _checked(posts, userdata, listing_id, version)
    if state.listing is None:
        raise Refused("not_classified")
    report = next((r for r in state.reports if r.report_id == report_id), None)
    if report is None or report.status not in RESOLVABLE:
        raise Refused("no_report")
    old = next((c for c in state.in_force if c.field == field), None)
    others = [c for c in state.in_force if c.field != field]
    try:
        correction = FieldCorrection(
            schema_version=FIELD_CORRECTION_SCHEMA_VERSION,
            correction_id=new_opaque_id(),
            listing_id=listing_id,
            field=field,
            model_value=_plain(getattr(state.listing, field)),
            corrected_value=corrected_value,
            corrected_by=admin_id,
            corrected_at=now,
            report_id=report_id,
            removed_by=None,
            removed_at=None,
        )
        seen_listing(state.listing, [*others, correction])  # the whole post still a valid `Listing`
    except ValueError as error:  # pydantic's ValidationError included
        raise Invalid(invalid_words(field, error)) from None
    if old is not None:
        removed = _changed(old, removed_by=admin_id, removed_at=now)
        try:
            userdata.save_correction(removed, expected=old)
        except StaleRecordError:
            raise Changed(listing_id) from None
    try:
        return userdata.add_correction(correction)
    except CorrectionInForce:
        raise Changed(listing_id) from None


def remove_correction(
    posts: SqliteRepository,
    userdata: UserDataStore,
    listing_id: str,
    version: str,
    correction_id: str,
    admin_id: str,
    now: datetime,
) -> FieldCorrection:
    """A correction in force removed; the record stays (#284) and is never put back in force. The
    post's state is not re-derived (#394)."""
    state = _checked(posts, userdata, listing_id, version)
    current = next((c for c in state.in_force if c.correction_id == correction_id), None)
    if current is None:
        raise Refused("not_in_force")
    try:
        return userdata.save_correction(
            _changed(current, removed_by=admin_id, removed_at=now), expected=current
        )
    except StaleRecordError:
        raise Changed(listing_id) from None


# --- helpers ---


def _save(posts: SqliteRepository, record: PostLifecycle, expected: PostLifecycle) -> PostLifecycle:
    try:
        return posts.save_lifecycle(record, expected=expected)
    except StaleRecordError:
        raise Changed(expected.listing_id) from None


def _changed[M: BaseModel](record: M, **changes: object) -> M:
    """A copy with `changes`, validated: `model_copy` alone skips the validators."""
    return type(record).model_validate({**record.model_dump(), **changes})


def _plain(value: Any) -> Any:
    """A `Listing` field's value as JSON, as the correction stores it from a document."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value
