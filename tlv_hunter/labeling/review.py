"""The review report (`PHASE_2.md` 2.7; DECISIONS.md #143, #172, #177, #193, #195): one card per
classified post, from the store or from a regression run's pass 1, and the corrections export.

The page carries each post's text, its classification, its rejection reason and the names the
classifier dropped (#162, #180). `review_page.html` holds the markup, the style and the script,
all inline. Corrected posts join the regression set here (#195): the only write besides the page.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tlv_hunter.areas.reference import Area
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.labeling.corrections import CORRECTABLE, RESULTS_FILE, CorrectionFile
from tlv_hunter.labeling.page import script_json
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.postmodel.rejects import model_reason
from tlv_hunter.store.base import Repository

REVIEW_PAGE_FILE = "review.html"
TEMPLATE = Path(__file__).with_name("review_page.html")
PLACEHOLDER = "__PAGE_DATA__"
REVIEW_FORMAT_VERSION = 1


@dataclass(frozen=True)
class ReviewCard:
    listing_id: str
    text: str
    listing: Listing
    rejection_reason: str | None
    dropped_streets: tuple[str, ...]
    dropped_area_names: tuple[str, ...]
    dropped_other_city: str | None


# --- the cards ---


def dropped_names(classify_runs: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """Per (listing_id, prompt_version), the newest line of `classify_runs/*.jsonl` (#182 A). A
    line has no time of its own: files are taken in order of modification, oldest first."""
    found: dict[tuple[str, str], dict[str, Any]] = {}
    if not classify_runs.is_dir():
        return found
    for path in sorted(classify_runs.glob("*.jsonl"), key=lambda p: (p.stat().st_mtime, p.name)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                found[(record["listing_id"], record["prompt_version"])] = record
    return found


def store_cards(store: Repository, classify_runs: Path) -> list[ReviewCard]:
    """Every stored post with a classification, by listing_id."""
    names = dropped_names(classify_runs)
    cards = []
    for post in store.query():
        listing = store.get_listing(post.listing_id)
        if listing is None:
            continue
        lifecycle = store.get_lifecycle(post.listing_id)
        line = names.get((post.listing_id, listing.prompt_version), {})
        cards.append(
            ReviewCard(
                listing_id=post.listing_id,
                text=post.text,
                listing=listing,
                rejection_reason=None if lifecycle is None else lifecycle.rejection_reason,
                dropped_streets=tuple(line.get("dropped_streets", ())),
                dropped_area_names=tuple(line.get("dropped_area_names", ())),
                dropped_other_city=line.get("dropped_other_city"),
            )
        )
    return cards


def run_cards(run_dir: Path, texts: Mapping[str, str]) -> list[ReviewCard]:
    """Pass 1 of a regression run (#193), in set order. The rejection is derived from the answer
    (`model_reason`), as the job would write it. A post whose text changed since the run is
    refused: its classification was made on another text."""
    data = json.loads((run_dir / RESULTS_FILE).read_text(encoding="utf-8"))
    cards = []
    for post in data["passes"][0]["posts"]:
        if post["listing"] is None:
            continue
        listing_id = post["listing_id"]
        if listing_id not in texts:
            raise LookupError(f"{listing_id}: its text is not found")
        if text_sha256(texts[listing_id]) != post["text_sha256"]:
            raise ValueError(f"{listing_id}: the text changed since the run")
        listing = Listing.model_validate_json(json.dumps(post["listing"]))
        cards.append(
            ReviewCard(
                listing_id=listing_id,
                text=texts[listing_id],
                listing=listing,
                rejection_reason=model_reason(listing),
                dropped_streets=tuple(post["dropped_streets"]),
                dropped_area_names=tuple(post["dropped_area_names"]),
                dropped_other_city=post["dropped_other_city"],
            )
        )
    return cards


# --- corrected posts join the set (#195) ---


def add_corrected_to_set(
    set_path: Path, corrections: CorrectionFile, stored_ids: set[str]
) -> list[str]:
    """Appends every reviewed, corrected post the set does not hold, with the corrected
    classification as its truth. Only stored posts can join: the set reads their text from the
    store. Returns the ids added; writes nothing when there are none."""
    data = json.loads(set_path.read_text(encoding="utf-8"))
    held = {entry["listing_id"] for entry in data["posts"]}
    added = []
    for listing_id in corrections.corrected_ids():
        if listing_id in held or listing_id not in stored_ids:
            continue
        fields = ", ".join(sorted(corrections.corrections[listing_id].fields))
        data["posts"].append(
            {
                "listing_id": listing_id,
                "case": f"corrected in review: {fields}",
                "source": "store",
                "truth": "review",
            }
        )
        added.append(listing_id)
    if added:
        set_path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return added


# --- the page ---


def render_review_page(
    cards: Sequence[ReviewCard],
    areas: Sequence[Area],
    *,
    set_positions: Mapping[str, int],
    corrections: CorrectionFile | None,
    source: str,
    generated_at: datetime,
) -> str:
    errors = None if corrections is None else corrections.errors_per_field()
    data = {
        "format_version": REVIEW_FORMAT_VERSION,
        "generated_at": require_utc(generated_at).isoformat(),
        "source": source,
        "fields": list(CORRECTABLE),
        "areas": [{"number": area.number, "name": area.display_name} for area in areas],
        "errors": errors,
        "reviewed": None if corrections is None else len(corrections.reviewed()),
        "cards": [
            {
                "listing_id": card.listing_id,
                "position": set_positions.get(card.listing_id),
                "text": card.text,
                "text_sha256": text_sha256(card.text),
                "listing": card.listing.model_dump(mode="json"),
                "rejection_reason": card.rejection_reason,
                "dropped_streets": list(card.dropped_streets),
                "dropped_area_names": list(card.dropped_area_names),
                "dropped_other_city": card.dropped_other_city,
            }
            for card in cards
        ],
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"{TEMPLATE}: expected {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, script_json(data))
