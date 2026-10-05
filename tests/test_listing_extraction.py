"""The model's response model (SCHEMA.md, `ListingExtraction`; DECISIONS.md #137, #151, #167,
#179)."""

import copy
import json
from typing import Any

import pytest
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import ValidationError

from tests.conftest import OPENAI_SPIKE, load_openai_spike, spike_answer
from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.listing_extraction import EntryDateParts, ListingExtraction

# SCHEMA.md: the Listing fields code fills, and the response fields code turns into others.
CODE_FILLED = {
    "schema_version",
    "listing_id",
    "model_name",
    "prompt_version",
    "classified_at",
    "price_source",
    "entry_date",
    "phone_names",
}
RESPONSE_ONLY = {"entry_date_parts", "phone_name_pairs"}
FORBIDDEN_KEYWORDS = {"allOf", "not", "if", "then", "else", "dependentRequired", "dependentSchemas"}


def test_every_listing_field_is_in_the_response_or_filled_by_code() -> None:
    """The drift test (#137)."""
    listing = Listing.model_fields
    response = ListingExtraction.model_fields
    for name, field in listing.items():
        if name in CODE_FILLED:
            assert name not in response, name
        else:
            assert name in response, name
            assert response[name].annotation == field.annotation, name
    assert set(response) - set(listing) == RESPONSE_ONLY


def _schema() -> dict[str, Any]:
    return dict(type_to_text_format_param(ListingExtraction))


def _walk(node: Any, path: str = ""):
    if isinstance(node, dict):
        yield path, node
        for key, value in node.items():
            yield from _walk(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, f"{path}[{index}]")


def test_the_derived_schema_obeys_strict_mode() -> None:
    """RESEARCH.md §15: every property required, no extra properties, no unsupported keyword."""
    text_format = _schema()
    assert text_format["strict"] is True
    assert text_format["schema"]["type"] == "object"
    for path, node in _walk(text_format["schema"]):
        assert not FORBIDDEN_KEYWORDS & node.keys(), path
        if node.get("type") == "object":
            assert node.get("additionalProperties") is False, path
            assert sorted(node["required"]) == sorted(node["properties"]), path


def test_the_derived_schema_is_the_spikes_but_for_areas_and_the_value_description() -> None:
    """DECISIONS.md #179: the schema sent in spike 2.1 passed strict mode; only two differences
    are expected, so an SDK upgrade that changes the derivation fails here, before any call."""
    sent = load_openai_spike("schema_sent")
    derived = copy.deepcopy(_schema())
    assert derived["name"] == sent["name"] == "ListingExtraction"

    assert derived["schema"]["properties"].pop("areas") == {
        "items": {"type": "integer"},
        "title": "Areas",
        "type": "array",
    }
    derived["schema"]["required"].remove("areas")
    expected = copy.deepcopy(sent)
    for name, definition in expected["schema"]["$defs"].items():
        if name.startswith("Marked_"):
            definition["properties"]["value"].pop("description")
    assert derived == expected


def test_every_spike_answer_validates_once_areas_is_added() -> None:
    names = sorted(path.stem for path in OPENAI_SPIKE.glob("*_p[12]_*.json"))
    assert len(names) == 120
    for name in names:
        answer = spike_answer(name)
        with pytest.raises(ValidationError):
            ListingExtraction.model_validate_json(json.dumps(answer))
        ListingExtraction.model_validate_json(json.dumps({**answer, "areas": []}))


@pytest.mark.parametrize(
    "parts",
    [
        {"immediate": True, "day": None, "month": None, "year": None},
        {"immediate": False, "day": 1, "month": 11, "year": None},
        {"immediate": False, "day": 31, "month": 12, "year": 2026},
    ],
)
def test_entry_date_parts_accepted(parts: dict[str, Any]) -> None:
    EntryDateParts.model_validate(parts)


@pytest.mark.parametrize(
    "parts",
    [
        {"immediate": True, "day": 1, "month": None, "year": None},
        {"immediate": True, "day": None, "month": None, "year": 2026},
        {"immediate": False, "day": None, "month": 11, "year": None},
        {"immediate": False, "day": 1, "month": None, "year": None},
        {"immediate": False, "day": 0, "month": 11, "year": None},
        {"immediate": False, "day": 32, "month": 11, "year": None},
        {"immediate": False, "day": 1, "month": 13, "year": None},
    ],
)
def test_entry_date_parts_refused(parts: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        EntryDateParts.model_validate(parts)
