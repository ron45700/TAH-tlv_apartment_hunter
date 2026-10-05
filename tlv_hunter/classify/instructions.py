"""Everything the model receives except the post: the instructions, the response schema and the
setting (DECISIONS.md #157, #178, #179). One version for all of it.

`PROMPT_VERSION` changes whenever any of it changes: the text in `instructions.txt`, the 71 areas
in `reference/` (read through `areas/reference.py`), `ListingExtraction`, the model or the
setting. `PROMPT_FINGERPRINT` is the SHA-256 of all of it; the classifier refuses to start when
the two disagree, and a test pins them, so no `Listing` is written under a version that does not
describe what was sent.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai.lib._parsing._responses import type_to_text_format_param

from tlv_hunter.areas.reference import Area, load_areas
from tlv_hunter.contracts.listing_extraction import ListingExtraction

PROMPT_VERSION = "1"
PROMPT_FINGERPRINT = "7cebac222642268f0f51ee981abe537c114ab1d473afaf74629bbcfd64c65501"

TEMPLATE_FILE = Path(__file__).with_name("instructions.txt")
AREAS_MARKER = "<<AREAS>>"

MODEL_NAME = "gpt-6-luna"  # DECISIONS.md #127
REASONING_EFFORT = "none"  # #157
TEMPERATURE = 0  # #157; accepted only at effort `none` (ASSUMPTIONS.md O4)
MAX_OUTPUT_TOKENS = 2000  # #179


@dataclass(frozen=True)
class Prompt:
    instructions: str
    text_format: dict[str, Any]
    model: str
    reasoning_effort: str
    temperature: float
    max_output_tokens: int

    def fingerprint(self) -> str:
        sent = json.dumps(
            {
                "instructions": self.instructions,
                "text_format": self.text_format,
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(sent.encode("utf-8")).hexdigest()


def render_instructions(areas: Sequence[Area], template: str | None = None) -> str:
    """The template with the 71 areas generated into it, one `number: display name` per line."""
    if template is None:
        template = TEMPLATE_FILE.read_text(encoding="utf-8")
    if template.count(AREAS_MARKER) != 1:
        raise ValueError(f"the instructions must hold {AREAS_MARKER} exactly once")
    lines = "\n".join(f"{area.number}: {area.display_name}" for area in areas)
    return template.replace(AREAS_MARKER, lines)


def build_prompt(areas: Sequence[Area] | None = None) -> Prompt:
    return Prompt(
        instructions=render_instructions(load_areas() if areas is None else areas),
        text_format=dict(type_to_text_format_param(ListingExtraction)),
        model=MODEL_NAME,
        reasoning_effort=REASONING_EFFORT,
        temperature=TEMPERATURE,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
