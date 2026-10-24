"""The block check (DECISIONS.md #519, #521; `PHASE_6.md` §6.4). PAID: one call for each of three
saved Yad2 listing pages, to see the labelled block's request shape (a second `input_text` part)
accepted and answered.

    uv run python -m tlv_hunter.jobs.yad2_block_check --check             # free: no key, no call
    uv run --env-file .env python -m tlv_hunter.jobs.yad2_block_check     # PAID, cap $0.01

The pages are read in place from `data/raw/` (`PAGES`); each is mapped and classified as a Yad2
listing would be (instructions version 7, the form merged). **The store is never opened.** Each
response is saved whole to `data/raw/yad2_block_check_<n>_<UTC date>.json`; nothing else is
written. Prints, per listing: accepted or not, `post_nature`, `apartment_kind`, `areas` (with their
names), `furnished`, `gender`, the fields the form gave, and the call's cost.

Reads `OPENAI_API_KEY`, as every command that calls the model may (#188); it is never logged.
Exit codes: 0, every call answered; 1, refused, failed or stopped, with what was done printed.
"""

import argparse
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO

from tlv_hunter.areas.reference import load_areas
from tlv_hunter.classify.base import ClassificationError
from tlv_hunter.classify.cost import CapReached, CostMeter
from tlv_hunter.classify.instructions import PROMPT_VERSION
from tlv_hunter.classify.openai_classifier import OpenAIClassifier
from tlv_hunter.classify.transport import ModelTransport, OpenAITransport
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.jobs.common import REPO_ROOT
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.yad2.mapping import model_block, to_raw_post
from tlv_hunter.yad2.pages import listing_data

KEY_VARIABLE = "OPENAI_API_KEY"
CAP = 0.01  # DECISIONS.md #519
RAW = Path("data") / "raw"
# The three pages of #521 and when each was fetched (the spikes' manifest, UTC).
PAGES = (
    ("yad2_listing_private_1_2026-10-24.html", datetime(2026, 10, 24, 11, 37, 54, tzinfo=UTC)),
    ("yad2_listing_private_3_2026-10-24.html", datetime(2026, 10, 24, 11, 38, 45, tzinfo=UTC)),
    ("yad2_listing_agency_1_2026-10-22.html", datetime(2026, 10, 22, 13, 48, 56, tzinfo=UTC)),
)

EXIT_DONE, EXIT_FAILED = 0, 1


class _Keeping:
    """The transport, keeping the last response it handed back."""

    def __init__(self, inner: ModelTransport) -> None:
        self._inner = inner
        self.last: dict[str, Any] | None = None

    def send(self, request: dict[str, Any]) -> dict[str, Any]:
        self.last = None
        self.last = self._inner.send(request)
        return self.last


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    repo_root: Path = REPO_ROOT,
    make_transport: Callable[[str], ModelTransport] = OpenAITransport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    out: TextIO = sys.stdout,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.yad2_block_check")
    parser.add_argument("--check", action="store_true", help="map the pages; no key, no call")
    args = parser.parse_args(argv)

    posts = []
    for name, fetched_at in PAGES:
        path = repo_root / RAW / name
        if not path.is_file():
            print(f"refused: no page {path}", file=out)
            return EXIT_FAILED
        post = annotate(to_raw_post(listing_data(path.read_text(encoding="utf-8")), fetched_at))
        if model_block(post.raw) is None:
            print(f"refused: {name} has no block", file=out)
            return EXIT_FAILED
        posts.append((name, post))
    print(f"block check: {len(posts)} pages mapped, prompt version {PROMPT_VERSION}", file=out)
    if args.check:
        return EXIT_DONE

    key = environ.get(KEY_VARIABLE, "").strip()
    if not key:
        print(f"refused: {KEY_VARIABLE} is not set", file=out)
        return EXIT_FAILED
    transport = _Keeping(make_transport(key))
    meter = CostMeter(cap=CAP)
    classifier = OpenAIClassifier(transport, meter, clock=clock)
    day = clock().strftime("%Y-%m-%d")
    failed = False
    for number, (name, post) in enumerate(posts, 1):
        print(f"\n[{number}] {name}", file=out)
        try:
            listing: Listing | None = classifier.classify_completed(post).listing
        except CapReached as error:
            print(f"  stopped by the cap: {error}", file=out)
            return EXIT_FAILED
        except ClassificationError as error:
            print(f"  NOT accepted: {error.kind} {error.detail}", file=out)
            failed = True
            listing = None
        if transport.last is not None:
            saved = repo_root / RAW / f"yad2_block_check_{number}_{day}.json"
            saved.write_text(json.dumps(transport.last, ensure_ascii=False, indent=2), "utf-8")
            print(f"  response saved: {saved.relative_to(repo_root).as_posix()}", file=out)
        cost = f"${meter.calls[-1].cost:.6f}" if meter.calls else "none"
        print(f"  cost: {cost}", file=out)
        if listing is not None:
            _print_listing(post, listing, out)
    print(f"\nspent ${meter.spent:.6f} of the ${CAP:.2f} cap, {len(meter.calls)} calls", file=out)
    return EXIT_FAILED if failed else EXIT_DONE


def _print_listing(post: RawPost, listing: Listing, out: TextIO) -> None:
    names = {area.number: area.display_name for area in load_areas()}
    neighbourhood = post.raw.get("address", {}).get("neighborhood", {}).get("text")
    form = sorted(field for field, source in listing.field_sources.items() if source == "form")
    for line in (
        "accepted: yes (status completed)",
        f"post_nature: {listing.post_nature}",
        f"apartment_kind: {listing.apartment_kind.state} {listing.apartment_kind.value}",
        f"furnished: {listing.furnished.state} {listing.furnished.value}",
        f"gender: {listing.gender}",
        f"Yad2's neighbourhood: {neighbourhood}",
        f"areas: {[(area, names.get(area)) for area in listing.areas]}",
        f"field_sources: form {form}; model the other {len(listing.field_sources) - len(form)}",
    ):
        print(f"  {line}", file=out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
