"""The review report (`PHASE_2.md` 2.7; DECISIONS.md #143, #172, #177, #193, #195): one card per
classified post, from the store or from a regression run's pass 1, and the corrections export.

The page carries each post's text, its classification, its rejection reason and the names the
classifier dropped (#162, #180). `review_page.html` holds the markup, the style and the script,
all inline. Corrected posts join the regression set here (#195): the only write besides the page.
"""

import json
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tlv_hunter.areas.reference import Area
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.labeling.corrections import CORRECTABLE, RESULTS_FILE, CorrectionFile
from tlv_hunter.labeling.page import script_json
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.postmodel.rejects import model_reason, other_city_ruling
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
    city: str | None = None
    """The city of an other-city post and where it came from (DECISIONS.md #214), derived."""
    city_source: str | None = None


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
        ruling = other_city_ruling(post, listing)
        cards.append(
            ReviewCard(
                listing_id=post.listing_id,
                text=post.text,
                listing=listing,
                rejection_reason=None if lifecycle is None else lifecycle.rejection_reason,
                dropped_streets=tuple(line.get("dropped_streets", ())),
                dropped_area_names=tuple(line.get("dropped_area_names", ())),
                dropped_other_city=line.get("dropped_other_city"),
                city=ruling.name,
                city_source=ruling.source,
            )
        )
    return cards


def run_cards(run_dir: Path, posts: Mapping[str, RawPost]) -> list[ReviewCard]:
    """Pass 1 of a regression run (#193), in set order. The rejection is derived from the answer
    and the post's own location (`model_reason`), as the job would write it. A post whose text
    changed since the run is refused: its classification was made on another text."""
    data = json.loads((run_dir / RESULTS_FILE).read_text(encoding="utf-8"))
    cards = []
    for post in data["passes"][0]["posts"]:
        if post["listing"] is None:
            continue
        listing_id = post["listing_id"]
        if listing_id not in posts:
            raise LookupError(f"{listing_id}: its text is not found")
        raw = posts[listing_id]
        if text_sha256(raw.text) != post["text_sha256"]:
            raise ValueError(f"{listing_id}: the text changed since the run")
        listing = Listing.model_validate_json(json.dumps(post["listing"]))
        ruling = other_city_ruling(raw, listing)
        cards.append(
            ReviewCard(
                listing_id=listing_id,
                text=raw.text,
                listing=listing,
                rejection_reason=model_reason(raw, listing),
                dropped_streets=tuple(post["dropped_streets"]),
                dropped_area_names=tuple(post["dropped_area_names"]),
                dropped_other_city=post["dropped_other_city"],
                city=ruling.name,
                city_source=ruling.source,
            )
        )
    return cards


# --- corrected posts join the set (#195) ---


@dataclass(frozen=True)
class JoinPreview:
    joins: list[tuple[str, list[str], list[str]]]
    """Per post that would join the set: its id, its corrected fields that count, and those
    excluded (#216)."""
    skipped_pairs: list[tuple[str, str, bool]]
    """Every excluded (post, field): its id, the field, and whether the review file holds a
    correction for it."""


def _read_set(set_path: Path) -> dict:
    return json.loads(set_path.read_text(encoding="utf-8"))


def join_preview(
    set_path: Path,
    corrections: CorrectionFile,
    stored_ids: set[str],
    excluded: AbstractSet[tuple[str, str]],
) -> JoinPreview:
    """What `add_corrected_to_set` would do, writing nothing."""
    held = {entry["listing_id"] for entry in _read_set(set_path)["posts"]}
    joins = []
    for listing_id in corrections.corrected_ids():
        if listing_id in held or listing_id not in stored_ids:
            continue
        kept = sorted(corrections.effective_fields(listing_id, excluded))
        dropped = sorted(set(corrections.corrections[listing_id].fields) - set(kept))
        joins.append((listing_id, kept, dropped))
    skipped = []
    for listing_id, field in sorted(excluded):
        record = corrections.corrections.get(listing_id)
        skipped.append((listing_id, field, record is not None and field in record.fields))
    return JoinPreview(joins, skipped)


def add_corrected_to_set(
    set_path: Path,
    corrections: CorrectionFile,
    stored_ids: set[str],
    excluded: AbstractSet[tuple[str, str]] = frozenset(),
) -> list[str]:
    """Appends every reviewed post with a correction that the set does not hold, with the corrected
    classification as its truth (#195), the excluded fields (#216) left out of it. Only stored posts
    can join: the set reads their text from the store. Returns the ids added; writes nothing when
    there are none."""
    data = _read_set(set_path)
    added = []
    preview = join_preview(set_path, corrections, stored_ids, excluded)
    for listing_id, kept, dropped in preview.joins:
        case = (
            f"corrected in review: {', '.join(kept)}"
            if kept
            else f"reviewed in the review (corrections excluded: {', '.join(dropped)})"
        )
        data["posts"].append(
            {"listing_id": listing_id, "case": case, "source": "store", "truth": "review"}
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
    excluded: AbstractSet[tuple[str, str]] = frozenset(),
) -> str:
    errors = None if corrections is None else corrections.errors_per_field(excluded)
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
                "city": card.city,
                "city_source": card.city_source,
            }
            for card in cards
        ],
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"{TEMPLATE}: expected {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, script_json(data))
