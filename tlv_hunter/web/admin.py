"""The admin's API (`PHASE_3.md` 3.8 (a), (b), (d); DECISIONS.md #389–#406). Wiring, as `routes.py`.

Every route checks the session through the one admin check, `accounts.actions.require_admin`
(#398): a guest 401, a user who is not the admin 403, the admin while a password change is due 403.
Every `POST` takes JSON only and checks `Origin` (`auth.check_write`, #330 point 19).

**Build step 1, the reads.** The post lists (rejected, pending, archive, flags) ride the
grouping's snapshot (#397): the same read of the store gives the users' cards and
`Snapshot.others`, every other canonical post; before the first grouping they answer "loading" as
the users' list does (#380). They come in pages as the users' list does (#376): the count, the
whole order and the first rows; the rest by id. Canonicals only (#75 B). The post's detail and
its photos are read fresh from the store, never from the snapshot. Reports, corrections, keys and
users are read from `UserDataStore` per request.

**Build step 3, keys and users,** through 3.5's actions (each compares and sets inside): a key is
issued with its label and shown once, in one answer that no cache keeps (#266); an unused key is
cancelled (#243); a user's password is reset to a temporary one (#262, #263), a user disabled and
enabled (#265, #291). A user is named by username in the address: `user_id` is never shown (Gate
C). The admin's own row takes no reset and no disable (R8).

**Build steps 4 and 5, the post writes** (`admin_writes.py`): retry, restore, leave out, remove
from the list, correct and remove a correction, each against the `version` the page showed (#391)
and by compare and set (#260). Every row and the detail carry that `version`; a write answers the
post's fresh detail. A post the site itself removes from the list (a report applied) leaves every
answer at once by the grouping's overlay (#379); a restored or corrected post follows at the next
background recompute. Never a `RawPost` or a `Listing`.

**Until 3.9 every write lands in the site's dated copy (#331, #400).**
"""

import json
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping
from typing import Annotated, Any, Literal, get_args

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import Field

from tlv_hunter.accounts import actions
from tlv_hunter.contracts.classification_report import ClassificationReport, ReportableField
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import OtherPost
from tlv_hunter.postmodel.rejects import ReportMark, report_marks, restored_lifecycle
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.store.base import StaleRecordError
from tlv_hunter.web import admin_writes
from tlv_hunter.web.admin_rows import (
    ListItem,
    correction_json,
    key_json,
    post_detail,
    post_row,
    report_json,
    user_json,
)
from tlv_hunter.web.auth import check_write, viewer
from tlv_hunter.web.cards import photo_name
from tlv_hunter.web.filters import FIRST_CARDS, MOST_BY_ID
from tlv_hunter.web.grouping import Snapshot
from tlv_hunter.web.routes import Site, _Body, _json, _refusal, _refused_json, _site
from tlv_hunter.web.writes import REPORT_LABELS

router = APIRouter(prefix="/api/admin")

ListName = Literal["rejected", "pending", "archive", "flags"]
Reason = Literal[
    "no_text",
    "no_images",
    "other_city",
    "seeking",
    "for_sale",
    "not_listing",
    "flagged",
    "misclassified",
]
ReportStatus = Literal["open", "left_out", "restored"]

# The account actions' refusals as the admin's page reads them: the HTTP status of each name.
REFUSALS: Mapping[str, int] = {
    "not_signed_in": 401,
    "must_change_password": 403,
    "not_admin": 403,
    "label_empty": 422,
    "password_too_short": 422,
    "unknown_key": 404,
    "unknown_user": 404,
    "key_used": 409,
    "admin_cannot_be_disabled": 403,
}


class PostsRequest(_Body):
    list: ListName
    reason: Reason | None = None
    first: Annotated[int, Field(ge=0, le=MOST_BY_ID)] = FIRST_CARDS


class PostsByIdRequest(_Body):
    list: ListName
    reason: Reason | None = None
    ids: Annotated[list[str], Field(min_length=1, max_length=MOST_BY_ID)]


class KeyBody(_Body):
    label: str


class TemporaryPasswordBody(_Body):
    temporary_password: str


class VersionBody(_Body):
    version: str


class RestoreItem(_Body):
    listing_id: str
    version: str


class RestoreBody(_Body):
    posts: Annotated[list[RestoreItem], Field(min_length=1, max_length=MOST_BY_ID)]


class CorrectionBody(_Body):
    listing_id: str
    field: ReportableField
    corrected_value: Any
    report_id: str
    version: str


def _admin(request: Request, site: Site) -> tuple[User, str]:
    """The admin's user and session token, else 401 or 403 (#398)."""
    now = site.clock()
    who = viewer(request, site.userdata, now)
    if who.user is None or who.token is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    try:
        return actions.require_admin(site.userdata, who.token, now), who.token
    except actions.Refused as refusal:
        status = REFUSALS.get(refusal.reason, 403)
        raise HTTPException(status_code=status, detail=refusal.reason) from None


# --- the post lists (#397) ---


@router.get("/summary")
def summary(request: Request) -> Response:
    """The overview's counts (3.8 (c), "Overview")."""
    site = _site(request)
    _admin(request, site)
    snapshot = site.grouping.current().snapshot
    others = list(snapshot.others.values())
    rejected = _in_list(snapshot, "rejected", None)
    pending = _in_list(snapshot, "pending", None)
    flagged = _in_list(snapshot, "flags", None)
    reports = site.userdata.find_reports()
    marks = _marks_by_post(site, snapshot, reports)
    keys = site.userdata.list_keys()
    return _json(
        {
            "generation": snapshot.generation,
            "rejected": len(rejected),
            "rejected_by_reason": dict(Counter(o.lifecycle.rejection_reason for o in rejected)),
            "pending": len(pending),
            "pending_failed": sum(1 for o in pending if o.lifecycle.classification_failures > 0),
            "archive": sum(1 for o in others if o.lifecycle.state == "archived"),
            "flag_actions": len({_flag_action(o) for o in flagged}),
            "flagged_posts": len(flagged),
            "open_reports": sum(1 for r in reports if r.status == "open"),
            "not_removed": sum(1 for m in marks.values() if "not_removed" in m),
            "restore_unfinished": sum(1 for m in marks.values() if "restore_unfinished" in m),
            "corrections": len(site.userdata.find_corrections(in_force=True)),
            "usable_keys": sum(1 for k in keys if k.used_by is None and k.cancelled_at is None),
            "users": len(site.userdata.list_users()),
        }
    )


@router.post("/posts")
async def posts(request: Request) -> Response:
    """A list's first answer (#376): its count, its whole order and its first rows; for the
    rejected list, the count of each reason (#403)."""
    site = _site(request)
    _admin(request, site)
    body = await _body(request, PostsRequest)
    snapshot = site.grouping.current().snapshot
    usernames = _usernames(site)
    items = _ordered(_in_list(snapshot, body.list, body.reason), body.list, usernames)
    payload: dict[str, object] = {
        "generation": snapshot.generation,
        "count": len(items),
        "order": [item.listing_id for item in items] if body.first else [],
        "rows": [_row(site, snapshot, item, usernames) for item in items[: body.first]],
    }
    if body.list == "rejected":
        every = _in_list(snapshot, "rejected", None)
        payload["reasons"] = dict(Counter(item.lifecycle.rejection_reason for item in every))
    return _json(payload)


@router.post("/posts/by-id")
async def posts_by_id(request: Request) -> Response:
    """A later page of a load (#376): the rows of the ids asked, in that order; an id no longer in
    the list is in `gone`."""
    site = _site(request)
    _admin(request, site)
    body = await _body(request, PostsByIdRequest)
    snapshot = site.grouping.current().snapshot
    usernames = _usernames(site)
    held = {item.listing_id: item for item in _in_list(snapshot, body.list, body.reason)}
    rows, gone = [], []
    for listing_id in dict.fromkeys(body.ids):
        item = held.get(listing_id)
        if item is None:
            gone.append(listing_id)
        else:
            rows.append(_row(site, snapshot, item, usernames))
    return _json({"generation": snapshot.generation, "rows": rows, "gone": gone})


@router.get("/posts/{listing_id}")
def post(listing_id: str, request: Request) -> Response:
    """The post's detail, read fresh from the store (3.8 (b)), never the snapshot's copy."""
    site = _site(request)
    _admin(request, site)
    return _json(_detail(site, listing_id))


@router.get("/photos/{listing_id}/{file}")
def photo(listing_id: str, file: str, request: Request) -> FileResponse:
    """Any stored post's photo, for the admin only: the file must be one of the post's own stored
    photos, read fresh from its record; no path is built from the address."""
    site = _site(request)
    _admin(request, site)
    lifecycle = site.posts.get_lifecycle(listing_id)
    for image in [] if lifecycle is None else lifecycle.images:
        if image.local_path is not None and photo_name(image.local_path) == file:
            path = site.store_root / image.local_path
            if path.is_file():
                return FileResponse(path)
    raise HTTPException(status_code=404)


# --- reports and corrections ---


@router.get("/reports")
def reports(request: Request, status: ReportStatus = "open") -> Response:
    """The reports of one status grouped by field (#173, #254, #401): a post under every field one
    of its reports names, with those reports and the two derived marks (3.8 (c))."""
    site = _site(request)
    _admin(request, site)
    snapshot = site.grouping.current().snapshot
    usernames = _usernames(site)
    every = site.userdata.find_reports()
    marks = _marks_by_post(site, snapshot, every)
    chosen = sorted((r for r in every if r.status == status), key=lambda r: r.reported_at)
    by_field: dict[str, dict[str, list[ClassificationReport]]] = defaultdict(dict)
    for report in chosen:
        for name in report.fields:
            by_field[name].setdefault(report.listing_id, []).append(report)
    rows: dict[str, dict | None] = {}
    groups = []
    for name in get_args(ReportableField):
        held = by_field.get(name)
        if not held:
            continue
        entries = []
        for listing_id, its_reports in held.items():
            if listing_id not in rows:
                item = _item(site, snapshot, listing_id)
                rows[listing_id] = None if item is None else _row(site, snapshot, item, usernames)
            entries.append(
                {
                    "listing_id": listing_id,
                    "post": rows[listing_id],
                    "reports": [report_json(r, usernames) for r in its_reports],
                    "marks": sorted(marks.get(listing_id, ())),
                }
            )
        groups.append({"field": name, "label": REPORT_LABELS[name], "posts": entries})
    return _json(
        {
            "status": status,
            "count": len(chosen),
            "posts": len({r.listing_id for r in chosen}),
            "groups": groups,
        }
    )


@router.get("/corrections")
def corrections(request: Request, in_force: bool = True) -> Response:
    """The corrections in force, or the removed ones (the history), newest first, each with its
    post's row."""
    site = _site(request)
    _admin(request, site)
    snapshot = site.grouping.current().snapshot
    usernames = _usernames(site)
    found = site.userdata.find_corrections(in_force=in_force)
    if not in_force:
        found = [c for c in found if c.removed_at is not None]
    entries = []
    for correction in sorted(found, key=lambda c: c.corrected_at, reverse=True):
        item = _item(site, snapshot, correction.listing_id)
        row = None if item is None else _row(site, snapshot, item, usernames)
        entries.append({**correction_json(correction, usernames), "post": row})
    return _json({"in_force": in_force, "corrections": entries})


# --- the post writes (build steps 4 and 5) ---


@router.post("/retry/{listing_id}")
async def retry(listing_id: str, request: Request) -> Response:
    """A pending post's failure count back to 0 (Gate E, #139): the next `classify_pending` run
    takes it."""
    site = _site(request)
    _admin(request, site)
    body = await _body(request, VersionBody)
    return _post_write(
        site,
        listing_id,
        lambda: admin_writes.retry(site.posts, site.userdata, listing_id, body.version),
    )


@router.post("/restore")
async def restore(request: Request) -> Response:
    """One post, or a flag action's posts (#393), each by its own compare and set: a result per
    post, `restored`, `changed` or `not_restorable` (#392)."""
    site = _site(request)
    admin, _ = _admin(request, site)
    body = await _body(request, RestoreBody)
    asked = [(item.listing_id, item.version) for item in body.posts]
    now = site.clock()
    results = admin_writes.restore_many(site.posts, site.userdata, asked, admin.user_id, now)
    return _json(
        {
            "results": [
                {
                    "listing_id": result.listing_id,
                    "outcome": result.outcome,
                    "state": None if result.lifecycle is None else result.lifecycle.state,
                }
                for result in results
            ]
        }
    )


@router.post("/leave-out/{listing_id}")
async def leave_out(listing_id: str, request: Request) -> Response:
    """Every open report of the post left out (#286): the post stays rejected, kept."""
    site = _site(request)
    admin, _ = _admin(request, site)
    body = await _body(request, VersionBody)
    now = site.clock()
    return _post_write(
        site,
        listing_id,
        lambda: admin_writes.leave_out(
            site.posts, site.userdata, listing_id, body.version, admin.user_id, now
        ),
    )


@router.post("/apply-reports/{listing_id}")
async def apply_reports(listing_id: str, request: Request) -> Response:
    """A report stored while its post stayed on the list: the post leaves it now (#402), and every
    answer at once by the overlay (#379)."""
    site = _site(request)
    _admin(request, site)
    body = await _body(request, VersionBody)
    response = _post_write(
        site,
        listing_id,
        lambda: admin_writes.apply_reports(site.posts, site.userdata, listing_id, body.version),
    )
    if response.status_code == 200:
        site.grouping.remove([listing_id])
    return response


@router.post("/corrections")
async def add_correction(request: Request) -> Response:
    """A correction made from a report (#395), checked as the whole post (#405); one in force on
    the field is replaced (#404). 422 for a value that breaks Gate B, named."""
    site = _site(request)
    admin, _ = _admin(request, site)
    body = await _body(request, CorrectionBody)
    now = site.clock()
    return _post_write(
        site,
        body.listing_id,
        lambda: admin_writes.correct(
            site.posts,
            site.userdata,
            body.listing_id,
            body.version,
            body.field,
            body.corrected_value,
            body.report_id,
            admin.user_id,
            now,
        ),
    )


@router.post("/corrections/{correction_id}/remove")
async def remove_correction(correction_id: str, request: Request) -> Response:
    """A correction in force removed (#284); the post's state is not re-derived (#394)."""
    site = _site(request)
    admin, _ = _admin(request, site)
    body = await _body(request, VersionBody)
    every = site.userdata.find_corrections(in_force=False)
    found = next((c for c in every if c.correction_id == correction_id), None)
    if found is None:
        raise HTTPException(status_code=404, detail="unknown_correction")
    now = site.clock()
    return _post_write(
        site,
        found.listing_id,
        lambda: admin_writes.remove_correction(
            site.posts,
            site.userdata,
            found.listing_id,
            body.version,
            correction_id,
            admin.user_id,
            now,
        ),
    )


# --- keys and users (build step 3) ---


@router.get("/keys")
def keys(request: Request) -> Response:
    """Every key: the usable ones first, each part newest first (#243)."""
    site = _site(request)
    _admin(request, site)
    usernames = _usernames(site)
    found = sorted(site.userdata.list_keys(), key=lambda k: k.created_at, reverse=True)
    found.sort(key=lambda k: k.used_by is not None or k.cancelled_at is not None)
    return _json({"keys": [key_json(key, usernames) for key in found]})


@router.post("/keys")
async def issue_key(request: Request) -> Response:
    """A new key with its label, shown in this answer only (#266), which no cache keeps."""
    site = _site(request)
    _, token = _admin(request, site)
    body = await _body(request, KeyBody)
    try:
        issued = actions.issue_key(site.userdata, token, body.label.strip(), site.clock())
    except actions.Refused as refusal:
        return _refused(refusal)
    key = next(k for k in site.userdata.list_keys() if k.key_id == issued.key_id)
    payload = {"key": issued.key, **key_json(key, _usernames(site))}
    return _json(payload, headers={"Cache-Control": "no-store"})


@router.post("/keys/{key_id}/cancel")
async def cancel_key(key_id: str, request: Request) -> Response:
    """An unused key cancelled, for good (#243, #266)."""
    site = _site(request)
    _, token = _admin(request, site)
    check_write(request)
    try:
        actions.cancel_key(site.userdata, token, key_id, site.clock())
    except actions.Refused as refusal:
        return _refused(refusal)
    except StaleRecordError:
        return _refused_json("changed", 409)
    key = next(k for k in site.userdata.list_keys() if k.key_id == key_id)
    return _json(key_json(key, _usernames(site)))


@router.get("/users")
def users(request: Request) -> Response:
    """Every user, the admin first, then by username."""
    site = _site(request)
    _admin(request, site)
    labels = {key.key_id: key.label for key in site.userdata.list_keys()}
    found = sorted(site.userdata.list_users(), key=lambda u: (not u.is_admin, u.username.lower()))
    return _json({"users": [user_json(user, labels) for user in found]})


@router.post("/users/{username}/password")
async def reset_password(username: str, request: Request) -> Response:
    """A temporary password (#262), changed at the user's next sign-in; every session of the user
    ends (#263). Not the admin's own: theirs is changed from the preferences page, or on the machine
    (#294)."""
    site = _site(request)
    _, token = _admin(request, site)
    body = await _body(request, TemporaryPasswordBody)
    target = _user_named(site, username)
    if target.is_admin:
        return _refused_json("admin_row", 403)
    return _user_action(
        site,
        target,
        lambda: actions.reset_password(
            site.userdata,
            token,
            target.user_id,
            body.temporary_password,
            site.clock(),
            hasher=site.hasher,
        ),
    )


@router.post("/users/{username}/disable")
async def disable_user(username: str, request: Request) -> Response:
    """Disabled, then every session ended (#265, #291); the admin cannot be (R8)."""
    site = _site(request)
    _, token = _admin(request, site)
    check_write(request)
    target = _user_named(site, username)
    now = site.clock()
    return _user_action(
        site, target, lambda: actions.disable_user(site.userdata, token, target.user_id, now)
    )


@router.post("/users/{username}/enable")
async def enable_user(username: str, request: Request) -> Response:
    """The user can sign in again; their ended sessions stay ended."""
    site = _site(request)
    _, token = _admin(request, site)
    check_write(request)
    target = _user_named(site, username)
    now = site.clock()
    return _user_action(
        site, target, lambda: actions.enable_user(site.userdata, token, target.user_id, now)
    )


# --- helpers ---


def _in_list(snapshot: Snapshot, name: ListName, reason: Reason | None) -> list[OtherPost]:
    """The canonical posts of one list (#75 B): `others` holds no duplicate and no member."""
    items = list(snapshot.others.values())
    if name == "rejected":
        found = [o for o in items if o.lifecycle.state == "rejected"]
        return [o for o in found if reason is None or o.lifecycle.rejection_reason == reason]
    if name == "pending":
        return [o for o in items if o.lifecycle.state == "pending"]
    if name == "archive":
        return [o for o in items if o.lifecycle.state == "archived"]
    return [
        o
        for o in items
        if o.lifecycle.state in ("rejected", "archived")
        and o.lifecycle.rejection_reason == "flagged"
    ]


def _ordered(
    items: list[OtherPost], name: ListName, usernames: Mapping[str, str]
) -> list[OtherPost]:
    """The newest last publication first (#403); the flags by the user who flagged, then the newest
    flag action, so each action's posts stand together (#393)."""
    items = sorted(items, key=lambda o: o.listing_id)
    if name == "flags":
        items.sort(key=lambda o: o.lifecycle.flagged_at or o.lifecycle.last_published_at)
        items.reverse()
        items.sort(key=lambda o: usernames.get(o.lifecycle.flagged_by or "", "").lower())
        return items
    items.sort(key=lambda o: o.lifecycle.last_published_at, reverse=True)
    return items


def _flag_action(item: OtherPost) -> tuple[str | None, object]:
    """One "lied" flag on one card: the posts it wrote share the user and the time (#393)."""
    return item.lifecycle.flagged_by, item.lifecycle.flagged_at


def _item(site: Site, snapshot: Snapshot, listing_id: str) -> ListItem | None:
    """A post as the snapshot holds it, or read fresh when the snapshot does not (a post that
    changed since the last grouping)."""
    held = snapshot.others.get(listing_id) or snapshot.members.get(listing_id)
    if held is not None:
        return held
    stored = site.posts.get(listing_id)
    lifecycle = site.posts.get_lifecycle(listing_id)
    if stored is None or lifecycle is None:
        return None
    model = site.posts.get_listing(listing_id)
    in_force = site.userdata.find_corrections(listing_id=listing_id, in_force=True)
    seen = None if model is None else seen_listing(model, in_force)
    return OtherPost(post=stored, lifecycle=lifecycle, seen=seen)


def _row(site: Site, snapshot: Snapshot, item: ListItem, usernames: Mapping[str, str]) -> dict:
    """A row, with the `version` a write from it sends back (#391): its record as the snapshot
    holds it, its reports and corrections read now."""
    listing_id = item.listing_id
    version = admin_writes.post_version(
        item.lifecycle,
        site.userdata.find_reports(listing_id=listing_id),
        site.userdata.find_corrections(listing_id=listing_id, in_force=False),
    )
    row = post_row(
        item,
        duplicates=len(snapshot.duplicates.get(listing_id, ())),
        area_names=site.area_names,
        usernames=usernames,
    )
    return {**row, "version": version}


def _detail(site: Site, listing_id: str) -> dict:
    """The post's detail read fresh (3.8 (c)), with its `version` (#391) and what a restore would
    leave now (#406)."""
    try:
        state = admin_writes.read_state(site.posts, site.userdata, listing_id)
    except admin_writes.Refused:
        raise HTTPException(status_code=404) from None
    seen = None if state.listing is None else seen_listing(state.listing, state.in_force)
    life = state.lifecycle
    preview = (
        restored_lifecycle(life, state.post, seen)
        if seen is not None and life.flagged_by is not None
        else None
    )
    snapshot = site.grouping.current().snapshot
    detail = post_detail(
        state.post,
        life,
        state.listing,
        seen,
        corrections=sorted(state.corrections, key=lambda c: c.corrected_at, reverse=True),
        reports=sorted(state.reports, key=lambda r: r.reported_at),
        duplicates=snapshot.duplicates.get(listing_id, ()),
        marks=report_marks(life, state.reports),
        preview=preview,
        area_names=site.area_names,
        usernames=_usernames(site),
    )
    return {**detail, "version": state.version}


def _post_write(site: Site, listing_id: str, run: Callable[[], object]) -> Response:
    """A post write's answer: the post's fresh detail; 409 `changed` when the post changed since
    the page read it (#391), 409 with the reason when the write does not apply, 422 for a value
    that breaks Gate B."""
    try:
        run()
    except admin_writes.Changed:
        return _refused_json("changed", 409)
    except admin_writes.Refused as refusal:
        return _refused_json(refusal.reason, 409)
    except ValueError as error:  # pydantic's ValidationError included
        payload = {"refusal": "invalid_value", "detail": _refusal(error)}
        body = json.dumps(payload, ensure_ascii=False)
        return Response(body, status_code=422, media_type="application/json")
    return _json(_detail(site, listing_id))


def _marks_by_post(
    site: Site, snapshot: Snapshot, reports: list[ClassificationReport]
) -> dict[str, frozenset[ReportMark]]:
    by_post: dict[str, list[ClassificationReport]] = defaultdict(list)
    for report in reports:
        by_post[report.listing_id].append(report)
    marks = {}
    for listing_id, its_reports in by_post.items():
        item = _item(site, snapshot, listing_id)
        if item is not None:
            marks[listing_id] = report_marks(item.lifecycle, its_reports)
    return marks


def _usernames(site: Site) -> dict[str, str]:
    return {user.user_id: user.username for user in site.userdata.list_users()}


def _user_named(site: Site, username: str) -> User:
    user = site.userdata.find_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="unknown_user")
    return user


def _user_action(site: Site, target: User, run: Callable[[], object]) -> Response:
    try:
        run()
    except actions.Refused as refusal:
        return _refused(refusal)
    except StaleRecordError:
        return _refused_json("changed", 409)
    labels = {key.key_id: key.label for key in site.userdata.list_keys()}
    fresh = site.userdata.get_user(target.user_id)
    assert fresh is not None
    return _json(user_json(fresh, labels))


async def _body[B: _Body](request: Request, model: type[B]) -> B:
    check_write(request)
    try:
        return model.model_validate_json(await request.body())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None


def _refused(refusal: actions.Refused) -> Response:
    return _refused_json(refusal.reason, REFUSALS.get(refusal.reason, 400))
