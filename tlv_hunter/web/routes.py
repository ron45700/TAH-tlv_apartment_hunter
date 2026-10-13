"""The site's API (`PHASE_3.md` 3.7 (g)). Wiring: the held grouping (`grouping.py`),
`policy.evaluate` and `policy.order.ordered`, the payloads of `cards.py`; the session cookie and the
write checks (`auth.py`); the account actions (`accounts/`).

Build step 2: the read-only API for a guest. Build steps 4 and 5: the session, sign-in, sign-out,
sign-up with a key (no filter field, #336), the password change, and the saved profile. **The site
writes only the user-data tables of its copy of the store (#331):** a session, a user's failure
count and password, a new user with their profile and the key marked used, and a profile.
`save_profile` is called by `PUT /api/profile` alone, the preferences page (#335): the bar
(`/api/cards`) is never saved. Viewed marks, flags and reports are build step 6's, so a user's cards
carry no `viewed` yet. A user who must change the password reaches only the password change and
sign-out (Gate C, `Session`); for the posts they are a guest. Every write takes JSON only and checks
`Origin` (`auth.check_write`); a guest's write is 401.

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

from tlv_hunter.accounts import actions
from tlv_hunter.accounts.passwords import PRODUCTION_HASHER
from tlv_hunter.areas.reference import Area, AreaGroup
from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.user import User
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.policy.order import ordered
from tlv_hunter.userdata.base import UserDataStore
from tlv_hunter.web.auth import (
    Viewer,
    check_write,
    clear_session_cookie,
    set_session_cookie,
    viewer,
)
from tlv_hunter.web.cards import card_payload, photo_name, post_payload
from tlv_hunter.web.filters import bar_json, empty_bar, owned_profile, transient_profile
from tlv_hunter.web.grouping import Grouping

router = APIRouter(prefix="/api")


@dataclass(frozen=True)
class Site:
    grouping: Grouping
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
            "reportable_fields": list(get_args(ReportableField)),
        }
    )


@router.post("/cards")
async def cards_for_bar(request: Request) -> Response:
    """The ordered cards for the bar in the body; 422 for a bar that breaks a rule."""
    site = _site(request)
    body = await request.body()
    try:
        profile = transient_profile(body, site.clock())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=_refusal(error)) from None
    return _cards(site, profile)


@router.get("/cards")
def cards_for_a_new_guest(request: Request) -> Response:
    """The cards a guest sees before touching the bar (#315: a guest's bar starts empty), so the
    list can be read in a browser's address bar."""
    site = _site(request)
    return _cards(site, empty_bar(site.clock()))


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


def _cards(site: Site, profile: Profile) -> Response:
    held = site.grouping.current()
    now = site.clock()
    started = time.perf_counter()
    entries = [(card, evaluate(card.shown.seen, profile, now)) for card in held.snapshot.cards]
    eval_ms = _ms_since(started)
    started = time.perf_counter()
    shown = ordered(entries, viewed_ids=())  # a guest has no viewed marks
    order_ms = _ms_since(started)
    started = time.perf_counter()
    names = site.area_names
    payload = {
        "generation": held.snapshot.generation,
        "count": len(shown),
        "cards": [card_payload(card, evaluation, profile, names) for card, evaluation in shown],
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
