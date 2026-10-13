"""The session cookie and the checks every write passes (`PHASE_3.md` 3.7 (g); DECISIONS.md #263,
#330 point 19). Wiring: the session itself is `accounts.session_user`'s.

The cookie, exactly as 3.7 (g) proposed and every attribute passed explicitly (Starlette's defaults,
`secure=False` and `samesite="lax"`, are never relied on): `tlv_session`, the session token of 3.5,
`HttpOnly`, `Secure` (MDN: sent only over `https:`, "except on localhost"), `SameSite=Strict`,
`Path=/`, `Max-Age` 30 days (the session's own lifetime, R5), no `Domain`. Every request that
carries the cookie is checked through `accounts.session_user` (valid, not ended, not expired, the
user not disabled); a cookie that fails is cleared on that response, whatever the route answered.

Against cross-site requests (#330 point 19): `SameSite=Strict`, and every write takes JSON only and
checks `Origin`. The `Origin`'s host must be the request's own `Host`: the scheme is not compared,
since behind Tailscale Serve (3.9) the browser speaks `https:` and the site hears plain HTTP. A
write with no `Origin` is refused: a browser sends one on every same-origin request that is not a
`GET` or `HEAD` (MDN "Origin"); the page asks for it with the request's `referrerPolicy`, since the
site's `Referrer-Policy: no-referrer` would otherwise turn it into `null`.

The token is never logged and never put in a response body.
"""

from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from fastapi.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from tlv_hunter.accounts.actions import session_user
from tlv_hunter.contracts.session import SESSION_LIFETIME
from tlv_hunter.contracts.user import User
from tlv_hunter.userdata.base import UserDataStore

COOKIE_NAME = "tlv_session"
COOKIE_MAX_AGE = int(SESSION_LIFETIME.total_seconds())  # 2,592,000: 30 days
_CLEAR = "tlv_clear_session"


@dataclass(frozen=True)
class Viewer:
    """Who is asking: a guest (`user` None) or a user with a valid session."""

    user: User | None
    token: str | None = field(default=None, repr=False)


def viewer(request: Request, userdata: UserDataStore, now: datetime) -> Viewer:
    """The request's viewer. A cookie that names no valid session makes a guest and is cleared."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return Viewer(None)
    user = session_user(userdata, token, now)
    if user is None:
        request.scope.setdefault("state", {})[_CLEAR] = True
        return Viewer(None)
    return Viewer(user, token)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        path="/",
        domain=None,
        secure=True,
        httponly=True,
        samesite="strict",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME, path="/", domain=None, secure=True, httponly=True, samesite="strict"
    )


def check_write(request: Request) -> None:
    """A write takes JSON only and comes from the site's own page."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="JSON only")
    origin = request.headers.get("origin")
    host = request.headers.get("host")
    if not origin or not host or urlsplit(origin).netloc.lower() != host.lower():
        raise HTTPException(status_code=403, detail="the request did not come from the site")


class ClearFailedCookie:
    """Clears the cookie on the response to a request whose cookie failed the session check, so a
    browser does not send an ended or expired token again. A route that set or cleared the cookie
    itself has decided, and is left alone."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def clearing(message: Message) -> None:
            if message["type"] == "http.response.start" and scope.get("state", {}).get(_CLEAR):
                headers = list(message.get("headers", []))
                if all(name.lower() != b"set-cookie" for name, _ in headers):
                    cleared = Response()
                    clear_session_cookie(cleared)
                    cookie = [h for h in cleared.raw_headers if h[0] == b"set-cookie"]
                    message = {**message, "headers": [*headers, *cookie]}
            await send(message)

        await self.app(scope, receive, clearing)
