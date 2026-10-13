"""The site's FastAPI app (`PHASE_3.md` 3.7 (g), (j); DECISIONS.md #258, #330). Wiring only.

Build step 2: the read-only API for a guest, over a **dated copy of the store** (#331; the copy is
`jobs/serve.py`'s). The site opens the copy's Repository read-only; it reads the corrections
through `UserDataStore`. From build step 5 it writes the copy's user-data tables only (sessions,
users, profiles; `routes.py`); a cookie that fails the session check is cleared (`auth.py`).

Invariant 15 on the page: no request leaves the site. Every response carries a Content-Security-
Policy that allows only the site itself and `Referrer-Policy: no-referrer`. FastAPI's own pages
(`/docs`, `/redoc`, `/openapi.json`) are off: the docs page loads its scripts from a CDN. FastAPI's
telemetry is off explicitly (0.143.0: automatic exporter setup is opt-in, by
`FASTAPI_OTEL_AUTO_CONFIGURE` or `telemetry=`; an explicit `telemetry=` overrides the variable).

Build step 3: the built pages (`frontend/dist`, Vite's output) are served beside the API on the one
origin (3.7 (g)): `/assets/…` from the build's folder, a file at the build's top level by its name,
and every other path that is not under `/api` gets `index.html`, so `/post/<id>` loads the site.
A path under `/api` that no route answers stays a 404. Without a build only the API is served.
"""

import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from argon2 import PasswordHasher
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tlv_hunter.accounts.passwords import PRODUCTION_HASHER
from tlv_hunter.areas.reference import load_area_groups, load_areas
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.auth import ClearFailedCookie
from tlv_hunter.web.grouping import Grouping
from tlv_hunter.web.routes import Site, router

CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'"
)
SECURITY_HEADERS = (
    (b"content-security-policy", CONTENT_SECURITY_POLICY.encode()),
    (b"referrer-policy", b"no-referrer"),
)
TELEMETRY_OFF = {"auto_configure": False, "tracing": False, "metrics": False, "logs": False}


class SecurityHeaders:
    """Adds the two headers to every HTTP response the app sends, replacing any the app set."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                names = {name for name, _ in SECURITY_HEADERS}
                headers = [h for h in message.get("headers", []) if h[0].lower() not in names]
                message = {**message, "headers": [*headers, *SECURITY_HEADERS]}
            await send(message)

        await self.app(scope, receive, with_headers)


def create_app(site: Site) -> FastAPI:
    app = FastAPI(
        title="TLV Apartment Hunter",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        telemetry=TELEMETRY_OFF,
    )
    app.state.site = site
    app.include_router(router)
    if site.pages is not None:
        _serve_pages(app, Path(site.pages))
    app.add_middleware(ClearFailedCookie)
    app.add_middleware(SecurityHeaders)
    return app


def _serve_pages(app: FastAPI, pages: Path) -> None:
    index = pages / "index.html"
    if not index.is_file():
        raise FileNotFoundError(f"no built page at {index}: run the front end's build first")
    if (pages / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=pages / "assets"), name="assets")
    root = str(pages.resolve())

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        candidate = os.path.realpath(os.path.join(root, path))
        if path and os.path.commonpath([candidate, root]) == root and os.path.isfile(candidate):
            return FileResponse(candidate)
        # The page itself is never cached, so a new build is picked up on the next load; the
        # files under /assets carry a hash in their names.
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def site_over(
    store_copy: Path,
    store_root: Path,
    *,
    pages: Path | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    hasher: PasswordHasher = PRODUCTION_HASHER,
) -> Site:
    """The site over a copy of the store: its Repository opened read-only; its user-data tables
    through `UserDataStore`, the only records the site writes (sessions, users, profiles, #331),
    the corrections read through it too; the photos read from `store_root`; the built pages from
    `pages`, when given."""
    repository = SqliteRepository(store_copy, read_only=True)
    userdata = SqliteUserDataStore(store_copy)
    return Site(
        grouping=Grouping(repository, userdata.find_corrections, store_root),
        areas=load_areas(),
        area_groups=load_area_groups(),
        store_root=Path(store_root),
        pages=pages,
        clock=clock,
        userdata=userdata,
        hasher=hasher,
    )
