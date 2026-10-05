"""The instructions, the 71 areas generated into them, and the version pin (DECISIONS.md #167,
#175, #178, #179)."""

import dataclasses
from pathlib import Path

import pytest

from tlv_hunter.areas.reference import Area, load_areas
from tlv_hunter.classify.instructions import (
    AREAS_MARKER,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    PROMPT_FINGERPRINT,
    PROMPT_VERSION,
    REASONING_EFFORT,
    TEMPERATURE,
    TEMPLATE_FILE,
    build_prompt,
    render_instructions,
)


def test_the_version_pins_everything_sent_except_the_post() -> None:
    """A change to the text, to reference/areas.yaml, to ListingExtraction or to the setting
    fails here until PROMPT_VERSION and PROMPT_FINGERPRINT are updated together."""
    assert PROMPT_VERSION == "1"
    assert build_prompt().fingerprint() == PROMPT_FINGERPRINT


@pytest.mark.parametrize(
    "change",
    [
        {"instructions": "x"},
        {"model": "gpt-6-astra"},
        {"reasoning_effort": "low"},
        {"temperature": 1},
        {"max_output_tokens": 4000},
        {"text_format": {}},
    ],
)
def test_every_part_of_the_prompt_changes_the_fingerprint(change: dict) -> None:
    prompt = build_prompt()
    assert dataclasses.replace(prompt, **change).fingerprint() != prompt.fingerprint()


def test_the_setting_is_the_approved_one() -> None:
    """#157, #179."""
    assert (MODEL_NAME, REASONING_EFFORT, TEMPERATURE, MAX_OUTPUT_TOKENS) == (
        "gpt-6-luna",
        "none",
        0,
        2000,
    )


def test_render_generates_every_area_once_with_its_display_name() -> None:
    areas = [Area(number=1, name="א"), Area(number=2, name="'ב ג", label="ב ג'")]
    rendered = render_instructions(areas, template=f"before\n{AREAS_MARKER}\nafter")
    assert rendered == "before\n1: א\n2: ב ג'\nafter"


def test_the_real_render_holds_all_71_and_no_marker() -> None:
    instructions = build_prompt().instructions
    assert AREAS_MARKER not in instructions
    for area in load_areas():
        assert instructions.count(f"\n{area.number}: {area.display_name}\n") == 1


def test_the_two_additions_of_178_are_in_the_text() -> None:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    assert 'a two-digit year is 20YY ("1.11.26" is 2026)' in template
    assert "a well-known landmark that places the apartment" in template
    assert "A landmark on a border gives every number it touches" in template


@pytest.mark.parametrize("template", ["no marker", f"{AREAS_MARKER}{AREAS_MARKER}"])
def test_a_template_without_exactly_one_marker_is_refused(template: str) -> None:
    with pytest.raises(ValueError):
        render_instructions(load_areas(), template=template)


def test_the_draft_left_docs() -> None:
    """#178: the text lives in the package only."""
    docs = Path(__file__).resolve().parent.parent / "docs"
    assert not (docs / "INSTRUCTIONS_V1_DRAFT.md").exists()
