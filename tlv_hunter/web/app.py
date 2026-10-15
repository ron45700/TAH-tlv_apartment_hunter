"""The site's FastAPI app (`PHASE_3.md` 3.7 (g), (j); DECISIONS.md #258, #330). Wiring only.

Build step 2: the read-only API for a guest, over a **dated copy of the store** (#331; the copy is
`jobs/serve.py`'s). The site opens the copy's Repository read-only; it reads the corrections
through `UserDataStore`. From build step 5 it writes the copy's user-data tables (sessions, users,
profiles; `routes.py`); a cookie that fails the session check is cleared (`auth.py`). From build
step 6 it also writes viewed marks and reports, and a post's lifecycle record for a flag or a
report (`writes.py`, by compare and set, #260); never a `RawPost` or a `Listing`. From 3.8 the
admin's API is beside it (`admin.py`): its lists, and from 3.8's step 3 keys and users.

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

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from argon2 import PasswordHasher
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES, GZipMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tlv_hunter.accounts.passwords import PRODUCTION_HASHER
from tlv_hunter.areas.reference import load_area_groups, load_areas
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.admin import router as admin_router
from tlv_hunter.web.auth import ClearFailedCookie
from tlv_hunter.web.grouping import Grouping, NotReady
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
# Responses compressed for a browser that accepts gzip (#371 C: the list is about 15 MB at 40 days,
# about 15% of it compressed, which matters to a phone over Tailscale). Starlette 1.7.0's
# `GZipMiddleware`, read in the installed source: a body under `minimum_size` is sent as it is;
# `compresslevel` defaults to 9, and 6 (zlib's own default) is passed for a cheaper compression of a
# large list; its default exclusions keep the photos (`image/jpeg`, `image/png`) and the fonts
# (`font/woff2`) as they are, and they are passed explicitly.
GZIP_MINIMUM_SIZE = 500
GZIP_LEVEL = 6
LOADING_RETRY_SECONDS = 2


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
    app.include_router(admin_router)  # the admin's pages (3.8)
    app.add_exception_handler(NotReady, _loading)
    if site.pages is not None:
        _serve_pages(app, Path(site.pages))
    app.add_middleware(ClearFailedCookie)
    app.add_middleware(SecurityHeaders)
    app.add_middleware(
        GZipMiddleware,
        minimum_size=GZIP_MINIMUM_SIZE,
        compresslevel=GZIP_LEVEL,
        exclude_content_types=DEFAULT_EXCLUDED_CONTENT_TYPES,
    )
    return app


def _loading(request: Request, error: Exception) -> Response:
    """Before the first grouping after a start (background mode): "loading", and when to ask again
    (#380); the page keeps its "טוען מודעות…" and retries."""
    return Response(
        json.dumps({"refusal": "loading"}),
        status_code=503,
        media_type="application/json",
        headers={"Retry-After": str(LOADING_RETRY_SECONDS)},
    )


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
    background: bool = False,
) -> Site:
    """The site over a copy of the store (#331): the grouping reads it through a read-only
    Repository; the user's writes on a post (a flag, a report, build step 6) go through a second,
    writable one, `save_lifecycle` only; its user-data tables through `UserDataStore` (sessions,
    users, profiles, viewed marks, reports), the corrections read through it too; the photos read
    from `store_root`; the built pages from `pages`, when given."""
    repository = SqliteRepository(store_copy, read_only=True)
    userdata = SqliteUserDataStore(store_copy)
    return Site(
        grouping=Grouping(repository, userdata.find_corrections, store_root, background=background),
        posts=SqliteRepository(store_copy),
        areas=load_areas(),
        area_groups=load_area_groups(),
        store_root=Path(store_root),
        pages=pages,
        clock=clock,
        userdata=userdata,
        hasher=hasher,
    )
