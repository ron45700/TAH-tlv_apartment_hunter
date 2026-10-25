"""Playwright's browser for the Yad2 seam (`PHASE_6.md` §6.5; #490): the only part of the collector
not run in tests (no browser runs in a test; the pages are read from saved HTML instead).

Headed Chromium on the persistent profile, with the spikes' launch flag and nothing more (#490: no
stealth plugin, no challenge solving). The profile holds only Yad2's own visitor cookies (#499);
nothing personal is sent (invariant 15). Nothing on a page is clicked: no phone request (#497).

**Only calls the spikes ran with `playwright==1.63.0`** (`data/spike_yad2/spike_yad2.py`,
`spike_yad2_2.py`): `sync_playwright()` as a context manager, `launch_persistent_context` with
`user_data_dir`, `headless` and `args`, `context.pages` / `new_page`, `page.on("response", …)`,
`page.goto`, `page.wait_for_timeout`, `page.url`, a response's `url`, `status`,
`request.resource_type` and `body()`, `context.close()`, and `playwright.sync_api.Error`. Their
use here is `ASSUMPTIONS.md` Y1.

Playwright is imported when the browser opens, so the package and its tests import without it; the
second image installs it (§6.5, build step 5).
"""

from contextlib import ExitStack
from pathlib import Path
from typing import Any, Self
from urllib.parse import urlparse

from tlv_hunter.yad2.block import API_HOST, PageLoad, PageLoadError
from tlv_hunter.yad2.feed import YAD2_HOST
from tlv_hunter.yad2.pages import NEXT_DATA_ID

LAUNCH_ARGS = ("--disable-blink-features=AutomationControlled",)
# After `goto`, the page is read once its data and a call to Yad2's API have arrived, checked each
# second, at most this long (the spikes waited a fixed 15 s; Radware's check page on a new profile
# is replaced within it, spike 2's server run).
WAIT_STEP_MS = 1_000
WAIT_STEPS = 15


class PlaywrightBrowser:
    """`with PlaywrightBrowser(profile) as browser:` one browser for one run."""

    def __init__(self, profile_dir: Path) -> None:
        self._profile_dir = Path(profile_dir)
        self._stack = ExitStack()
        self._page: Any = None
        self._error: type[Exception] = Exception
        self._hosts: set[str] = set()
        self._document: str | None = None

    def __enter__(self) -> Self:
        from playwright.sync_api import Error, sync_playwright

        self._error = Error
        playwright = self._stack.enter_context(sync_playwright())
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._profile_dir), headless=False, args=list(LAUNCH_ARGS)
        )
        self._stack.callback(context.close)
        self._page = context.pages[0] if context.pages else context.new_page()
        self._page.on("response", self._on_response)
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stack.close()

    def load(self, url: str) -> PageLoad:
        self._hosts = set()
        self._document = None
        try:
            self._page.goto(url)
            for _ in range(WAIT_STEPS):
                if self._document is not None and NEXT_DATA_ID in self._document:
                    if API_HOST in self._hosts:
                        break
                self._page.wait_for_timeout(WAIT_STEP_MS)
        except self._error as error:
            raise PageLoadError(f"{type(error).__name__}: {str(error)[:200]}") from None
        return PageLoad(
            url=url, final_url=self._page.url, html=self._document, hosts=frozenset(self._hosts)
        )

    def _on_response(self, response: Any) -> None:
        host = urlparse(response.url).hostname
        if host is None:
            return
        self._hosts.add(host)
        if (
            host == YAD2_HOST
            and response.status == 200
            and response.request.resource_type == "document"
        ):
            try:
                self._document = response.body().decode("utf-8")
            except (self._error, UnicodeDecodeError):
                pass  # the load's checks then find no data or an earlier document
