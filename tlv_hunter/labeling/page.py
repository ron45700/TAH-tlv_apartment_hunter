"""The labelling page (`PHASE_2.md` 2.6; DECISIONS.md #142, #143, #171, #177, #183): one static
HTML file, `data/labeling/label_posts.html`, with every post's text and the controls for the
deciding fields.

The page carries the texts, their hashes and the 71 areas, and nothing else: no case label (the
labels are blind), no model answer, no provider field. The template, `label_page.html`, holds the
markup, the style and the script, all inline: no server, no network, no external script or font.
"""

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from tlv_hunter.areas.reference import Area
from tlv_hunter.labeling.labels import LABELS_FORMAT_VERSION
from tlv_hunter.labeling.regression_set import PostText
from tlv_hunter.parsing.datetimes import require_utc

LABEL_PAGE_FILE = "label_posts.html"
TEMPLATE = Path(__file__).with_name("label_page.html")
PLACEHOLDER = "__PAGE_DATA__"


def render_label_page(
    posts: Sequence[PostText], areas: Sequence[Area], generated_at: datetime
) -> str:
    data = {
        "format_version": LABELS_FORMAT_VERSION,
        "generated_at": require_utc(generated_at).isoformat(),
        "posts": [
            {"listing_id": post.listing_id, "text": post.text, "text_sha256": post.text_sha256}
            for post in posts
        ],
        "areas": [{"number": area.number, "name": area.display_name} for area in areas],
    }
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count(PLACEHOLDER) != 1:
        raise ValueError(f"{TEMPLATE}: expected {PLACEHOLDER} exactly once")
    return template.replace(PLACEHOLDER, script_json(data))


def script_json(data: object) -> str:
    """JSON safe inside a <script> element: ASCII only, so every character of a text survives
    exactly (lone surrogates included), and no "<", ">" or "&" that could end the element."""
    return (
        json.dumps(data, ensure_ascii=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
