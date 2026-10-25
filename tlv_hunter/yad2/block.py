"""One page load as the browser saw it, and whether Yad2 blocked it (`PHASE_6.md` §6.6; spike 1 §8,
spike 2 §S2.5). Pure.

A load is blocked when either holds:
1. the top document ended on `validate.perfdrive.com` (Radware's challenge page), or
2. no request reached `gw.yad2.co.il` while the page loaded (every Yad2 page, list or listing,
   calls it: 20 to 34 answers a page in the spikes).

Nothing else is a block. Every Yad2 page loads Google's background challenge frame, so a word in a
frame's address or in the page proves nothing and is never looked at. Radware's own check page,
served on `www.yad2.co.il` before the real page to a new profile (spike 2's server run, the first
document of 118 KB), is not a block either when the real page follows it: the browser waits for
the page's data (`browser.py`).
"""

from dataclasses import dataclass
from urllib.parse import urlparse

CHALLENGE_HOST = "validate.perfdrive.com"
API_HOST = "gw.yad2.co.il"


class PageLoadError(RuntimeError):
    """The browser could not load the page (a navigation error or timeout); not a block."""


@dataclass(frozen=True)
class PageLoad:
    url: str
    """The address asked for."""
    final_url: str
    """The top document's address when the load ended, after any redirect."""
    html: str | None
    """The body of the last Yad2 document the page received; `None` when none arrived."""
    hosts: frozenset[str]
    """Every host that answered a request while the page loaded."""


def blocked_reason(load: PageLoad) -> str | None:
    """`None` for a page Yad2 served; else the reason, for the run's `failure_kind`."""
    if urlparse(load.final_url).hostname == CHALLENGE_HOST:
        return f"blocked: the page moved to {CHALLENGE_HOST}"
    if API_HOST not in load.hosts:
        return f"blocked: no request reached {API_HOST}"
    return None
