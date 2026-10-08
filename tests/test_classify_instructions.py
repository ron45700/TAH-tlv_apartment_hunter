"""The instructions, the 71 areas generated into them, and the version pin (DECISIONS.md #167,
#175, #178, #179)."""

import dataclasses
from pathlib import Path

import pytest

from tlv_hunter.areas.reference import Area, KnownPlace, load_areas, load_known_places
from tlv_hunter.classify.instructions import (
    AREAS_MARKER,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    PLACES_MARKER,
    PROMPT_FINGERPRINT,
    PROMPT_VERSION,
    REASONING_EFFORT,
    TEMPERATURE,
    TEMPLATE_FILE,
    build_prompt,
    render_instructions,
    render_places,
)


def test_the_version_pins_everything_sent_except_the_post() -> None:
    """A change to the text, to reference/areas.yaml, to ListingExtraction or to the setting
    fails here until PROMPT_VERSION and PROMPT_FINGERPRINT are updated together."""
    assert PROMPT_VERSION == "4"
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
    template = f"before\n{AREAS_MARKER}\nmid\n{PLACES_MARKER}\nafter"
    rendered = render_instructions(areas, [], template=template)
    assert rendered == "before\n1: א\n2: ב ג'\nmid\n\nafter"


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


@pytest.mark.parametrize(
    "template",
    [
        "no marker",
        f"{AREAS_MARKER}{AREAS_MARKER}{PLACES_MARKER}",
        f"{AREAS_MARKER}",
        f"{PLACES_MARKER}",
        f"{AREAS_MARKER}{PLACES_MARKER}{PLACES_MARKER}",
    ],
)
def test_a_template_without_exactly_one_of_each_marker_is_refused(template: str) -> None:
    with pytest.raises(ValueError):
        render_instructions(load_areas(), load_known_places(), template=template)


def test_the_draft_left_docs() -> None:
    """#178: the text lives in the package only."""
    docs = Path(__file__).resolve().parent.parent / "docs"
    assert not (docs / "INSTRUCTIONS_V1_DRAFT.md").exists()


def test_a_run_at_effort_low_carries_no_temperature_and_its_own_fingerprint() -> None:
    low = build_prompt(reasoning_effort="low")
    assert (low.reasoning_effort, low.temperature) == ("low", None)
    assert low.fingerprint() != PROMPT_FINGERPRINT
    assert low.with_production_setting().fingerprint() == PROMPT_FINGERPRINT


def test_version_2_holds_its_sentences() -> None:
    """Version 2's roommates sentence ("Feminine wording about the roommates who stay") was
    replaced in version 4 (#237)."""
    text = build_prompt().instructions
    for sentence in (
        "Lean towards more areas, not fewer.",
        "return the areas of the precise place as well.",
        'A date followed by "flexible"',
        "An entry that depends on an event with no date",
    ):
        assert sentence in text


# --- version 3 (#205, #206): the known places, generated; the age sentence ---

PLACE = KnownPlace(
    name="כיכר א",
    aliases=["כיכר ב", "ג"],
    lat=32.08,
    lon=34.78,
    coordinates_source="test",
    coordinates_date="2026-10-06",
    areas=[30, 31],
)


def test_a_place_renders_with_its_other_names_and_all_its_areas() -> None:
    assert render_places([PLACE]) == "כיכר א / כיכר ב / ג: 30, 31"
    assert render_places([]) == ""


def test_the_real_render_holds_every_known_place_once_and_the_template_none() -> None:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    instructions = build_prompt().instructions
    assert PLACES_MARKER not in instructions
    for place in load_known_places():
        line = render_places([place])
        assert instructions.count(f"\n{line}\n") == 1  # generated into the instructions
        assert (chr(10) + line + chr(10)) not in template  # and never typed in the template


def test_a_changed_place_changes_the_fingerprint_and_so_the_version_pin() -> None:
    other = PLACE.model_copy(update={"areas": [30]})
    assert build_prompt(places=[PLACE]).fingerprint() != build_prompt(places=[other]).fingerprint()
    assert build_prompt(places=[PLACE]).fingerprint() != PROMPT_FINGERPRINT


def test_version_3_holds_its_sentences() -> None:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    assert "Known places. These places, written as people write them" in template
    assert "Use this list, not your own memory of where" in template
    assert "An age preference" in template and "(25-35) is not a gender restriction." in template
    # Version 2's sentences stay, rule (a) included (#205).
    assert "Lean towards more areas, not fewer." in template


# --- version 4 (#233-#237): the five approved changes ---


def test_version_4_holds_its_sentences_and_no_longer_the_one_it_replaced() -> None:
    text = " ".join(TEMPLATE_FILE.read_text(encoding="utf-8").split())  # line breaks do not count
    for sentence in (
        'A range of rooms ("2-3 חדרים") is "unclear".',
        'An amount whose digits are malformed ("7,2000") is "unclear"; never repair it.',
        "When the apartment is in another city, return [].",
        'An area named only as nearby or within walking distance ("במרחק הליכה מפלורנטין") is not'
        " a stated area name and does not decide the areas.",
        "Decide gender only from the words about the person wanted.",
        '("נשארות שתי שותפות", "יש שני שותפים ושותפה") say nothing about it.',
        'A preference worded for both sexes ("עדיפות לדיירות/ים") is "no_restriction"; '
        '"women_preferred" needs a preference for women alone.',
    ):
        assert sentence in text
    assert "Feminine wording about the roommates who stay" not in text
