"""The read-only API for a guest (`PHASE_3.md` 3.7 (g), build step 2). Wiring: the held grouping
(`grouping.py`), `policy.evaluate` and `policy.order.ordered`, the payloads of `cards.py`.

Every request is a guest in this step (no session, no `viewed`); nothing is written. Only the
posts of the current cards are reachable: the cards come from `dedup/stage_b` (active canonical
posts with a `Listing`) and only those `evaluate` shows, so no rejected, pending or archived post
reaches a guest; a dedup A duplicate's id opens its canonical's card. A photo is served only when
its file name is one of a current card member's stored photos; no path is built from the address.
"""

import json
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import get_args

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response

from tlv_hunter.areas.reference import Area, AreaGroup
from tlv_hunter.contracts.classification_report import ReportableField
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.policy.order import ordered
from tlv_hunter.web.cards import card_payload, photo_name, post_payload
from tlv_hunter.web.filters import empty_bar, transient_profile
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
        "cards": [card_payload(card, evaluation, names) for card, evaluation in shown],
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
