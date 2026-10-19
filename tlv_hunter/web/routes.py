"""The site's API (`PHASE_3.md` 3.7 (g)). Wiring: the held grouping (`grouping.py`),
`policy.evaluate` and `policy.order.ordered`, the payloads of `cards.py`; the session cookie and the
write checks (`auth.py`); the account actions (`accounts/`).

Build step 2: the read-only API for a guest. Build steps 4 and 5: the session, sign-in, sign-out,
sign-up with a key (no filter field, #336), the password change, and the saved profile. **The site
writes only its copy of the store (#331):** a session, a user's failure count and password, a new
user with their profile and the key marked used, and a profile.
`save_profile` is called by `PUT /api/profile` alone, the preferences page (#335): the bar
(`/api/cards`) is never saved. Build step 6: a viewed mark on the shown post (#276), "mark as not
viewed" on every post of the card, a "lied" flag on every member and a report on the shown post
(#300), the last two by compare and set on the post's lifecycle record in the copy (`writes.py`,
#260). A user's cards carry `viewed`; a guest's do not. A write on a post that is no longer in a
current card is 409, `gone`. A user who must change the password reaches only the password change
and sign-out (Gate C, `Session`); for the posts they are a guest. Every write takes JSON only and
checks `Origin` (`auth.check_write`); a guest's write is 401.

Only the
posts of the current cards are reachable: the cards come from `dedup/stage_b` (active canonical
posts with a `Listing`) and only those `evaluate` shows, so no rejected, pending or archived post
reaches a guest; a dedup A duplicate's id opens its canonical's card. A photo is served only when
its file name is one of a current card member's stored photos; no path is built from the address.
"""

import json
import sqlite3
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import get_args

from argon2 import PasswordHasher
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, ValidationError

from tlv_hunter.accounts import actions, linking
from tlv_hunter.accounts.passwords import PRODUCTION_HASHER
from tlv_hunter.areas.reference import Area, AreaGroup
from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.policy.order import card_hidden, card_viewed, ordered
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.base import OpenReportExists, UserDataStore
from tlv_hunter.web.auth import (
    Viewer,
    check_write,
    clear_session_cookie,
    set_session_cookie,
    viewer,
)
from tlv_hunter.web.cards import card_payload, photo_name, post_payload
from tlv_hunter.web.filters import (
    FIRST_CARDS,
    bar_json,
    by_id_request,
    cards_request,
    empty_bar,
    owned_profile,
    same_values,
)
from tlv_hunter.web.grouping import Grouping
from tlv_hunter.web.writes import REPORT_LABELS, flag_card, report_post

router = APIRouter(prefix="/api")


@dataclass(frozen=True)
class Site:
    grouping: Grouping
    posts: SqliteRepository
    """The copy's Repository, writable: a flag's and a report's lifecycle writes only (#331)."""
    areas: Sequence[Area]
    area_groups: Sequence[AreaGroup]
    store_root: Path
    """Where the photos are read, read-only: `<store_root>/images/…` (#331)."""
    clock: Callable[[], datetime]
    userdata: UserDataStore
    """The copy's user-data tables: the only records the site writes (#331)."""
    pages: Path | None = None
    """The front end's build (`frontend/dist`), served beside the API; `None`: the API only."""
    hasher: PasswordHasher = PRODUCTION_HASHER
    """Tests pass `argon2.profiles.CHEAPEST`'s hasher, never the production one."""
    runs: SqliteRunStore | None = None
    """Gate G's records (#472): the admin's schedule page reads the runs and writes the settings
    and "run now"; `None`: no schedule page."""

    @property
    def area_names(self) -> Mapping[int, str]:
        return {area.number: area.display_name for area in self.areas}


def _site(request: Request) -> Site:
    return request.app.state.site


def _json(payload: object, headers: Mapping[str, str] | None = None) -> Response:
    body = json.dumps(payload, ensure_ascii=False)
    return Response(body, media_type="application/json", headers=dict(headers or {}))


@router.get("/reference")
def reference(request: Request) -> Response:
    """The 71 areas with their display names, the region groups (§6), the reportable fields."""
    site = _site(request)
    return _json(
        {
            "areas": [{"number": a.number, "name": a.display_name} for a in site.areas],
            "area_groups": [
                {"heading": g.heading, "collapsed": g.collapsed, "areas": list(g.areas)}
                for g in site.area_groups
            ],
            "reportable_fields": [
                {"field": name, "label": REPORT_LABELS[name]} for name in get_args(ReportableField)
            ],
        }
    )


@router.post("/cards")
async def cards_for_bar(request: Request) -> Response:
    """The ordered cards for the bar in the body; 422 for a bar that breaks a rule."""
    site = _site(request)
    body = await request.body()
    try:
        profile, first, show_hidden = cards_request(body, site.clock())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None
    return _cards(site, profile, _list_user(request, site), first, show_hidden)


@router.get("/cards")
def cards_for_a_new_guest(request: Request) -> Response:
    """The cards a guest sees before touching the bar (#315: a guest's bar starts empty), so the
    list can be read in a browser's address bar."""
    site = _site(request)
    return _cards(site, empty_bar(site.clock()), _list_user(request, site), FIRST_CARDS)


@router.post("/cards/by-id")
async def cards_by_id(request: Request) -> Response:
    """A later page of a load (#376): the cards holding the ids asked, in the order asked, each
    evaluated against the same bar; an id no longer in a shown card is in `gone`. Any post of a
    card finds it (as `/api/posts`), and a card asked twice comes once."""
    site = _site(request)
    body = await request.body()
    try:
        profile, ids, show_hidden = by_id_request(body, site.clock())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None
    user = _list_user(request, site)
    snapshot = site.grouping.current().snapshot
    now = site.clock()
    viewed_ids = site.userdata.viewed_listing_ids(user.user_id) if user is not None else set()
    hidden_ids = site.userdata.hidden_listing_ids(user.user_id) if user is not None else set()
    leaves_hidden = _hiding(site, user, profile) and not show_hidden
    cards, gone, given = [], [], set()
    for listing_id in ids:
        card = snapshot.card_of.get(listing_id)
        evaluation = None if card is None else evaluate(card.shown.seen, profile, now)
        if card is None or evaluation is None or not evaluation.shown:
            gone.append(listing_id)
            continue
        hidden = card_hidden(card, hidden_ids)
        if hidden and leaves_hidden:  # hidden meanwhile (another tab): it leaves the load
            gone.append(listing_id)
            continue
        if card.shown_id in given:
            continue
        given.add(card.shown_id)
        viewed = None if user is None else card_viewed(card, viewed_ids)
        cards.append(
            card_payload(
                card,
                evaluation,
                profile,
                site.area_names,
                viewed=viewed,
                hidden=None if user is None else hidden,
            )
        )
    return _json({"generation": snapshot.generation, "cards": cards, "gone": gone})


@router.get("/posts/{listing_id}")
def post(listing_id: str, request: Request) -> Response:
    site = _site(request)
    card = site.grouping.current().snapshot.card_of.get(listing_id)
    if card is None:
        raise HTTPException(status_code=404)
    return _json(post_payload(card, site.area_names))


@router.get("/photos/{listing_id}/{file}")
def photo(listing_id: str, file: str, request: Request) -> FileResponse:
    site = _site(request)
    member = site.grouping.current().snapshot.members.get(listing_id)
    if member is None:
        raise HTTPException(status_code=404)
    for image in member.lifecycle.images:
        if image.local_path is not None and photo_name(image.local_path) == file:
            path = site.store_root / image.local_path
            if path.is_file():
                return FileResponse(path)
    raise HTTPException(status_code=404)


# --- the session and the account (build step 5) ---

# A refusal of 3.5 as the page reads it: its name and the HTTP status. `wrong_credentials` is
# "wrong" (3.7 (g)); a delay carries its seconds.
REFUSALS: Mapping[str, tuple[str, int]] = {
    "wrong_credentials": ("wrong", 401),
    "delayed": ("delayed", 429),
    "disabled": ("disabled", 403),
    "not_signed_in": ("not_signed_in", 401),
    "must_change_password": ("must_change_password", 403),
    "key_not_usable": ("key_not_usable", 403),
    "username_invalid": ("username_invalid", 422),
    "username_taken": ("username_taken", 409),
    "password_too_short": ("password_too_short", 422),
    "changed": ("changed", 409),
}


class _Body(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SignInBody(_Body):
    username: str
    password: str


class SignUpBody(_Body):
    key: str
    username: str
    password: str


class PasswordBody(_Body):
    current: str
    new: str


@router.get("/session")
def session(request: Request) -> Response:
    site = _site(request)
    return _json(_session_json(viewer(request, site.userdata, site.clock()).user))


@router.post("/sign-in")
async def sign_in(request: Request) -> Response:
    site = _site(request)
    body = await _write_body(request, SignInBody)
    now = site.clock()
    _end_current(request, site, now)
    try:
        signed = actions.sign_in(
            site.userdata, body.username, body.password, now, hasher=site.hasher
        )
    except actions.Refused as refusal:
        return _refused(refusal)
    return _signed_in(site, signed)


@router.post("/sign-up")
async def sign_up(request: Request) -> Response:
    """A new user with a key, their profile at #268's defaults (#336), then signed in."""
    site = _site(request)
    body = await _write_body(request, SignUpBody)
    now = site.clock()
    _end_current(request, site, now)
    try:
        actions.sign_up(
            site.userdata, body.key, body.username, body.password, now, hasher=site.hasher
        )
        signed = actions.sign_in(
            site.userdata, body.username, body.password, now, hasher=site.hasher
        )
    except actions.Refused as refusal:
        return _refused(refusal)
    return _signed_in(site, signed)


@router.post("/sign-out")
async def sign_out(request: Request) -> Response:
    site = _site(request)
    who = _signed_in_viewer(request, site, allow_password_due=True)
    check_write(request)
    actions.sign_out(site.userdata, _token(who), site.clock())
    response = _json({"user": None})
    clear_session_cookie(response)
    return response


@router.post("/password")
async def change_password(request: Request) -> Response:
    """The user's own change, also the one a temporary password requires (#262); the user's
    other sessions end (R3)."""
    site = _site(request)
    who = _signed_in_viewer(request, site, allow_password_due=True)
    body = await _write_body(request, PasswordBody)
    try:
        actions.change_password(
            site.userdata, _token(who), body.current, body.new, site.clock(), hasher=site.hasher
        )
    except actions.Refused as refusal:
        return _refused(refusal)
    return _json(_session_json(site.userdata.get_user(_user(who).user_id)))


@router.get("/profile")
def get_profile(request: Request) -> Response:
    site = _site(request)
    who = _signed_in_viewer(request, site)
    profile = site.userdata.get_profile(_user(who).user_id)
    if profile is None:
        raise HTTPException(status_code=404)
    return _json(_profile_json(profile))


@router.put("/profile")
async def put_profile(request: Request) -> Response:
    """The preferences page's save, the only place a profile is saved (#335): the whole record
    (#289 point 4). A database error answers 503, "not saved"; the page keeps its values."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    body = await request.body()
    try:
        profile = owned_profile(body, _user(who).user_id, site.clock())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None
    try:
        saved = site.userdata.save_profile(profile)
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="not saved") from None
    return _json(_profile_json(saved))


# --- linking Telegram (Phase 4, `PHASE_4.md` 4.4, point 5 A; #453) ---


@router.get("/telegram")
def telegram(request: Request) -> Response:
    """Whether the user's account is linked to a Telegram chat, and since when."""
    site = _site(request)
    user = _user(_signed_in_viewer(request, site))
    linked_at = user.telegram_linked_at
    return _json(
        {
            "linked": user.telegram_chat_id is not None,
            "linked_at": None if linked_at is None else linked_at.isoformat(),
        }
    )


@router.post("/telegram/link")
async def telegram_link(request: Request) -> Response:
    """A new one-time code, shown once: the deep link that opens the bot with it, and the code by
    itself to type to the bot. Valid for 15 minutes; never cached."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    issued = linking.new_link_code(site.userdata, _token(who), site.clock())
    return _json(
        {"link": issued.link, "code": issued.code, "expires_at": issued.expires_at.isoformat()},
        headers={"Cache-Control": "no-store"},
    )


@router.delete("/telegram")
async def telegram_unlink(request: Request) -> Response:
    """Unlinking from the preferences page: no more alerts (as `/stop` to the bot)."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    linking.unlink_session_user(site.userdata, _token(who), site.clock())
    return _json({"linked": False, "linked_at": None})


# --- a user's writes on a card (build step 6, 3.7 (i)) ---


class FlagBody(_Body):
    note: str | None = None


class ReportBody(_Body):
    fields: list[ReportableField]
    note: str | None = None


@router.post("/viewed/{listing_id}")
async def mark_viewed(listing_id: str, request: Request) -> Response:
    """Opening a post marks its card viewed: the shown post, the first time kept (#253, #276)."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    site.userdata.mark_viewed(_user(who).user_id, card.shown_id, site.clock())
    return _json({"viewed": True})


@router.delete("/viewed/{listing_id}")
async def unmark_viewed(listing_id: str, request: Request) -> Response:
    """Mark as not viewed: the user's marks on every post of the card (SCHEMA.md `ViewedPost`)."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    site.userdata.unmark_viewed(_user(who).user_id, card.post_ids)
    return _json({"viewed": False})


@router.post("/hidden/{listing_id}")
async def hide(listing_id: str, request: Request) -> Response:
    """ "הסתר" (#464, #468): the card's shown post, the first time kept."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    site.userdata.hide(_user(who).user_id, card.shown_id, site.clock())
    return _json({"hidden": True})


@router.delete("/hidden/{listing_id}")
async def unhide(listing_id: str, request: Request) -> Response:
    """ "בטל הסתרה": the user's marks on every post of the card (SCHEMA.md `HiddenPost`)."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    check_write(request)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    site.userdata.unhide(_user(who).user_id, card.post_ids)
    return _json({"hidden": False})


@router.post("/flag/{listing_id}")
async def flag(listing_id: str, request: Request) -> Response:
    """The "lied" flag on every member of the card (#300). `flagged` of `of`; `remaining` names
    the members left as they were, the first of which a retry sends (#330 point 21)."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    body = await _write_body(request, FlagBody)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    result = flag_card(site.posts, card, _user(who).user_id, site.clock(), body.note)
    if result.written:
        site.grouping.remove(result.written)  # out of every answer at once (#379)
    return _json(
        {
            "flagged": len(result.written),
            "of": len(card.canonical_ids),
            "remaining": list(result.not_written),
        }
    )


@router.post("/report/{listing_id}")
async def report(listing_id: str, request: Request) -> Response:
    """A "wrong classification" report on the card's shown post (#254, #300). A second open report
    by the same user on it is 409, `already_reported` (#278). `removed` false: the report is stored
    and the post stays until the admin handles it (3.7 (i))."""
    site = _site(request)
    who = _signed_in_viewer(request, site)
    body = await _write_body(request, ReportBody)
    card = _current_card(site, listing_id)
    if card is None:
        return _gone()
    try:
        result = report_post(
            site.posts,
            site.userdata,
            card,
            _user(who).user_id,
            body.fields,
            body.note,
            site.clock(),
        )
    except OpenReportExists:
        return _refused_json("already_reported", 409)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None
    if result.removed:
        site.grouping.remove([card.shown_id])  # out of every answer at once (#379)
    return _json({"removed": result.removed})


def _current_card(site: Site, listing_id: str) -> Card | None:
    """The current card that holds the post (any of its `post_ids`), or None for a stale page."""
    return site.grouping.current().snapshot.card_of.get(listing_id)


def _gone() -> Response:
    """The post is no longer in a current card: removed meanwhile (3.7 (i))."""
    return _refused_json("gone", 409)


def _refused_json(name: str, status: int) -> Response:
    body = json.dumps({"refusal": name}, ensure_ascii=False)
    return Response(body, status_code=status, media_type="application/json")


def _signed_in_viewer(request: Request, site: Site, *, allow_password_due: bool = False) -> Viewer:
    """A valid session, else 401; while a password change is due, only what allows it (else
    403)."""
    who = viewer(request, site.userdata, site.clock())
    if who.user is None:
        raise HTTPException(status_code=401, detail="not_signed_in")
    if who.user.must_change_password and not allow_password_due:
        raise HTTPException(status_code=403, detail="must_change_password")
    return who


def _user(who: Viewer) -> User:
    assert who.user is not None
    return who.user


def _token(who: Viewer) -> str:
    assert who.token is not None
    return who.token


async def _write_body[B: BaseModel](request: Request, model: type[B]) -> B:
    check_write(request)
    try:
        return model.model_validate_json(await request.body())
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None


def _end_current(request: Request, site: Site, now: datetime) -> None:
    """Signing in again ends the session the browser held, so none is left behind open."""
    who = viewer(request, site.userdata, now)
    if who.token is not None:
        actions.sign_out(site.userdata, who.token, now)


def _signed_in(site: Site, signed: actions.SignedIn) -> Response:
    response = _json(_session_json(site.userdata.get_user(signed.user_id)))
    set_session_cookie(response, signed.token)
    return response


def _refused(refusal: actions.Refused) -> Response:
    name, status = REFUSALS.get(refusal.reason, (refusal.reason, 400))
    payload: dict[str, object] = {"refusal": name}
    headers: dict[str, str] = {}
    if refusal.retry_after_seconds is not None:
        payload["retry_after_seconds"] = refusal.retry_after_seconds
        headers["Retry-After"] = str(refusal.retry_after_seconds)
    body = json.dumps(payload, ensure_ascii=False)
    return Response(body, status_code=status, media_type="application/json", headers=headers)


def _session_json(user: User | None) -> dict[str, object]:
    if user is None:
        return {"user": None}
    return {
        "user": {
            "username": user.username,
            "is_admin": user.is_admin,
            "must_change_password": user.must_change_password,
        }
    }


def _profile_json(profile: Profile) -> dict[str, object]:
    return {**bar_json(profile), "updated_at": profile.updated_at.isoformat()}


def _list_user(request: Request, site: Site) -> User | None:
    """The user whose viewed marks order the list; a guest, or a user whose password change is
    due, has none."""
    user = viewer(request, site.userdata, site.clock()).user
    return None if user is None or user.must_change_password else user


def _hiding(site: Site, user: User | None, profile: Profile) -> bool:
    """Whether hiding applies to this list (#465; appendix A point 10, decided here): a signed-in
    user whose bar holds the saved preferences, value by value. A guest, or a temporary filter,
    sees everything."""
    if user is None:
        return False
    saved = site.userdata.get_profile(user.user_id)
    return saved is not None and same_values(profile, saved)


def _cards(
    site: Site, profile: Profile, user: User | None, first: int, show_hidden: bool = False
) -> Response:
    """Every card is evaluated and ordered; `order` holds the whole order of this load (each
    card's shown id), and `cards` the first `first` of it whole (#376). `first` 0: the count alone,
    no order (#378). For a signed-in user (#464–#466, #468): `hiding` says whether the bar holds
    the saved preferences; there, with `show_hidden` off, the hidden cards leave the list and the
    count; `hidden_count` is how many of the shown cards are hidden; each card carries `hidden`,
    and a hidden card that is shown keeps its place."""
    held = site.grouping.current()
    now = site.clock()
    started = time.perf_counter()
    entries = [(card, evaluate(card.shown.seen, profile, now)) for card in held.snapshot.cards]
    eval_ms = _ms_since(started)
    started = time.perf_counter()
    viewed_ids = site.userdata.viewed_listing_ids(user.user_id) if user is not None else set()
    hidden_ids = site.userdata.hidden_listing_ids(user.user_id) if user is not None else set()
    shown = ordered(entries, viewed_ids=viewed_ids)  # unviewed before viewed (#62)
    hiding = _hiding(site, user, profile)
    hidden_count = sum(card_hidden(card, hidden_ids) for card, _ in shown)
    if hiding and not show_hidden:
        shown = [(card, ev) for card, ev in shown if not card_hidden(card, hidden_ids)]
    order_ms = _ms_since(started)
    started = time.perf_counter()
    names = site.area_names
    payload = {
        "generation": held.snapshot.generation,
        "count": len(shown),
        **({} if user is None else {"hiding": hiding, "hidden_count": hidden_count}),
        "order": [card.shown_id for card, _ in shown] if first else [],
        "cards": [
            card_payload(
                card,
                evaluation,
                profile,
                names,
                viewed=None if user is None else card_viewed(card, viewed_ids),
                hidden=None if user is None else card_hidden(card, hidden_ids),
            )
            for card, evaluation in shown[:first]
        ],
    }
    body = json.dumps(payload, ensure_ascii=False)
    json_ms = _ms_since(started)
    timings = [("gen", held.generation_ms)]
    if held.group_ms is not None:
        timings.append(("group", held.group_ms))
    timings += [("eval", eval_ms), ("order", order_ms), ("json", json_ms)]
    server_timing = ", ".join(f"{name};dur={ms:.1f}" for name, ms in timings)
    return Response(body, media_type="application/json", headers={"Server-Timing": server_timing})


def _refusal(error: ValueError) -> str:
    """The rule a bar broke, without echoing the values sent."""
    errors = getattr(error, "errors", None)
    if callable(errors):
        return "; ".join(
            f"{'.'.join(str(part) for part in entry['loc']) or 'bar'}: {entry['msg']}"
            for entry in errors(include_input=False, include_url=False)
        )
    return str(error)


def _ms_since(started: float) -> float:
    return (time.perf_counter() - started) * 1000
