"""The candidate-pairs page (`PHASE_2.md` 2.10; DECISIONS.md #226, #227):
`data/gate_d/candidate_pairs.html`.

Per pair, side by side: the original text verbatim (never normalized text, invariant 8), the stored
photos (display only: no image is compared), the `Listing` fields, what matched, the dates (UTC in
the data, shown in Israel time by the browser, invariant 9), the groups, the author's display name
(shown, never used by a rule, invariant 5) and a verdict. `candidate_pairs.html` holds the markup,
the style and the script, all inline.
"""

import os
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from tlv_hunter.areas.reference import Area
from tlv_hunter.gate_d.candidates import (
    AGENT_NUMBER_POSTS,
    AGENT_SAMPLE_SIZE,
    RULES_VERSION,
    WINDOW,
    Candidates,
    Member,
    Population,
)
from tlv_hunter.gate_d.verdicts import FORMAT_VERSION, VERDICTS
from tlv_hunter.labeling.page import script_json
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.datetimes import require_utc

PAGE_FILE = "candidate_pairs.html"
TEMPLATE = Path(__file__).with_name("candidate_pairs.html")
PLACEHOLDER = "__PAGE_DATA__"
PHOTOS_PER_POST = 4


def photo_paths(member: Member, store_root: Path) -> list[str]:
    """The stored photos of a post that exist on disk, relative to `store_root` and written with
    `/`, at most `PHOTOS_PER_POST`."""
    found = []
    for image in member.lifecycle.images:
        if image.local_path is not None and (store_root / image.local_path).is_file():
            found.append(image.local_path)
        if len(found) == PHOTOS_PER_POST:
            break
    return found


def _post_data(member: Member, store_root: Path) -> dict[str, Any]:
    post, listing = member.post, member.listing
    return {
        "listing_id": post.listing_id,
        "text": post.text,
        "text_sha256": text_sha256(post.text),
        "posted_at": require_utc(post.posted_at).isoformat(),
        "group_id": post.group_id,
        "group_title": post.group_title,
        "permalink": post.permalink,
        "author_name": post.author_name,
        "photos": photo_paths(member, store_root),
        "listing": {
            "post_nature": listing.post_nature,
            "apartment_kind": listing.apartment_kind.model_dump(mode="json"),
            "price": listing.price.model_dump(mode="json"),
            "price_source": listing.price_source,
            "rooms": listing.rooms.model_dump(mode="json"),
            "areas": listing.areas,
        },
    }


def render_pairs_page(
    candidates: Candidates,
    population: Population,
    areas: Sequence[Area],
    *,
    store_root: Path,
    page_dir: Path,
    generated_at: datetime,
) -> str:
    by_id: Mapping[str, Member] = {member.listing_id: member for member in population.members}
    # The photos are linked, not copied: `images_base` is the way from the page to the store root.
    images_base = quote(Path(os.path.relpath(store_root, page_dir)).as_posix(), safe="/.")
    data = {
        "format_version": FORMAT_VERSION,
        "rules_version": RULES_VERSION,
        "verdicts": list(VERDICTS),
        "generated_at": require_utc(generated_at).isoformat(),
        "images_base": images_base,
        "areas": [{"number": area.number, "name": area.display_name} for area in areas],
        "summary": {
            "members": candidates.members,
            "window_hours": WINDOW.total_seconds() / 3600,
            "span_hours": round(population.span_hours, 1),
            "agent_number_posts": AGENT_NUMBER_POSTS,
            "agent_sample_size": AGENT_SAMPLE_SIZE,
            "agent_numbers": candidates.agent_numbers,
            "agent_pairs": candidates.agent_pairs,
        },
        "pairs": [
            {
                "key": pair.key,
                "found_by": list(pair.found_by),
                "matched": list(pair.matched),
                "shared_phones": list(pair.shared_phones),
                "gap_hours": round(pair.gap_hours, 2),
                "same_group": pair.same_group,
                "posts": [
                    _post_data(by_id[pair.first_id], store_root),
                    _post_data(by_id[pair.second_id], store_root),
                ],
            }
            for pair in candidates.pairs
        ],
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"{TEMPLATE}: expected {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, script_json(data))
