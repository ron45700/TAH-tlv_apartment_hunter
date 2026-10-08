"""Everything the model receives except the post: the instructions, the response schema and the
setting (DECISIONS.md #157, #178, #179). One version for all of it.

`PROMPT_VERSION` changes whenever any of it changes: the text in `instructions.txt`, the 71 areas
and the known places in `reference/` (read through `areas/reference.py`), `ListingExtraction`, the
model or the setting. `PROMPT_FINGERPRINT` is the SHA-256 of all of it; the classifier refuses to
start when the two disagree, and a test pins them, so no `Listing` is written under a version
that does not describe what was sent.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from openai.lib._parsing._responses import type_to_text_format_param

from tlv_hunter.areas.reference import Area, KnownPlace, load_areas, load_known_places
from tlv_hunter.contracts.listing_extraction import ListingExtraction

PROMPT_VERSION = "4"
PROMPT_FINGERPRINT = "0ad0bb4b236ed0baac778e4bd56b6780ac465c6c769dc1bdd45cd14f746e7c32"

TEMPLATE_FILE = Path(__file__).with_name("instructions.txt")
AREAS_MARKER = "<<AREAS>>"
PLACES_MARKER = "<<PLACES>>"

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
    temperature: float | None
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

    def with_production_setting(self) -> "Prompt":
        """The same prompt at the production setting (#157). The classifier's guard compares this
        one, so a regression run at another effort (#201) is still held to the approved text."""
        return replace(self, reasoning_effort=REASONING_EFFORT, temperature=TEMPERATURE)


def render_places(places: Sequence[KnownPlace]) -> str:
    """The known places (DECISIONS.md #205), one per line: the name, the other ways it is written
    after a slash, then its area numbers."""
    return "\n".join(
        f"{' / '.join(place.written)}: {', '.join(str(number) for number in place.areas)}"
        for place in places
    )


def render_instructions(
    areas: Sequence[Area], places: Sequence[KnownPlace], template: str | None = None
) -> str:
    """The template with the 71 areas, one `number: display name` per line, and the known places
    generated into it. Neither list is typed in the template."""
    if template is None:
        template = TEMPLATE_FILE.read_text(encoding="utf-8")
    for marker in (AREAS_MARKER, PLACES_MARKER):
        if template.count(marker) != 1:
            raise ValueError(f"the instructions must hold {marker} exactly once")
    lines = "\n".join(f"{area.number}: {area.display_name}" for area in areas)
    return template.replace(AREAS_MARKER, lines).replace(PLACES_MARKER, render_places(places))


def build_prompt(
    areas: Sequence[Area] | None = None,
    *,
    places: Sequence[KnownPlace] | None = None,
    reasoning_effort: str = REASONING_EFFORT,
) -> Prompt:
    """The production prompt, or the same at another effort for a regression run (#201). A
    temperature goes only with effort `none` (ASSUMPTIONS.md O4)."""
    return Prompt(
        instructions=render_instructions(
            load_areas() if areas is None else areas,
            load_known_places() if places is None else places,
        ),
        text_format=dict(type_to_text_format_param(ListingExtraction)),
        model=MODEL_NAME,
        reasoning_effort=reasoning_effort,
        temperature=TEMPERATURE if reasoning_effort == "none" else None,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )
