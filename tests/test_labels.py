"""Reading `labels.json`, the labelling page's export: `tlv_hunter/labeling/labels.py`
(`PHASE_2.md` 2.6; DECISIONS.md #142, #143, #177, #183)."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tlv_hunter.labeling.labels import LabelFile, read_labels
from tlv_hunter.labeling.regression_set import text_sha256

TEXT = "מתפנה חדר בדירת 3 שותפים, 2,900 ש״ח"
ID = "a" * 64


def label(**changes: Any) -> dict[str, Any]:
    """A complete label, as the page exports it."""
    fields: dict[str, Any] = {
        "text_sha256": text_sha256(TEXT),
        "post_nature": "rental_offer",
        "apartment_kind": {"state": "written", "value": "room"},
        "price": {"state": "written", "value": [2900]},
        "gender": "no_restriction",
        "entry_date_parts": {
            "state": "written",
            "value": {"immediate": False, "day": 12, "month": 10, "year": None},
        },
        "areas": [30, 31],
        "other_city": None,
        "ambiguous": False,
        "note": "",
    }
    fields.update(changes)
    return fields


def file(labels: dict[str, dict[str, Any]], **changes: Any) -> dict[str, Any]:
    return {
        "format_version": 1,
        "exported_at": "2026-10-05T18:51:22.529Z",
        "labels": labels,
    } | changes


def write(tmp_path: Path, content: dict[str, Any]) -> Path:
    path = tmp_path / "labels.json"
    path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return path


def test_reads_a_complete_label(tmp_path: Path) -> None:
    labels = read_labels(write(tmp_path, file({ID: label()})))
    assert labels.exported_at.utcoffset().total_seconds() == 0
    one = labels.labels[ID]
    assert one.is_complete
    assert one.price.value == [2900]
    assert one.entry_date_parts.value.day == 12
    assert labels.incomplete() == []


def test_a_field_not_labelled_yet_makes_the_label_incomplete(tmp_path: Path) -> None:
    labels = read_labels(write(tmp_path, file({ID: label(areas=None), "b" * 64: label()})))
    assert labels.incomplete() == [ID]


def test_an_ambiguous_post_is_complete_with_nothing_labelled() -> None:
    empty = dict.fromkeys(
        ("post_nature", "apartment_kind", "price", "gender", "entry_date_parts", "areas")
    )
    labels = LabelFile.model_validate(file({ID: label(ambiguous=True, note="two flats", **empty)}))
    assert labels.labels[ID].is_complete


def test_no_area_and_tel_aviv_are_labelled_values() -> None:
    one = LabelFile.model_validate(file({ID: label(areas=[], other_city=None)})).labels[ID]
    assert one.is_complete
    assert (one.areas, one.other_city) == ([], None)


def test_marked_states_and_an_immediate_entry() -> None:
    one = LabelFile.model_validate(
        file(
            {
                ID: label(
                    apartment_kind={"state": "unclear", "value": None},
                    price={"state": "not_written", "value": None},
                    entry_date_parts={
                        "state": "written",
                        "value": {"immediate": True, "day": None, "month": None, "year": None},
                    },
                    other_city="חולון",
                )
            }
        )
    ).labels[ID]
    assert one.is_complete
    assert one.entry_date_parts.value.immediate


def test_stale_finds_a_changed_text_and_an_unknown_post() -> None:
    labels = LabelFile.model_validate(file({ID: label(), "b" * 64: label()}))
    assert labels.stale({ID: TEXT, "b" * 64: TEXT + " "}) == ["b" * 64]
    assert labels.stale({ID: TEXT}) == ["b" * 64]


@pytest.mark.parametrize(
    "changes",
    [
        {"price": {"state": "written", "value": []}},
        {"price": {"state": "written", "value": [0]}},
        {"price": {"state": "written", "value": [-5]}},
        {"price": {"state": "written", "value": [2900.5]}},
        {"price": {"state": "not_written", "value": [2900]}},
        {"apartment_kind": {"state": "written", "value": None}},
        {"apartment_kind": {"state": "written", "value": "studio"}},
        {"areas": [31, 30]},
        {"areas": [30, 30]},
        {"areas": [72]},
        {"areas": [0]},
        {"other_city": "  "},
        {"post_nature": "rental"},
        {"gender": "men_only"},
        {
            "entry_date_parts": {
                "state": "written",
                "value": {"immediate": True, "day": 1, "month": None, "year": None},
            }
        },
        {
            "entry_date_parts": {
                "state": "written",
                "value": {"immediate": False, "day": 32, "month": 1, "year": None},
            }
        },
        {"streets": ["דיזנגוף"]},
        {"ambiguous": None},
    ],
)
def test_an_invalid_label_is_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LabelFile.model_validate_json(json.dumps(file({ID: label(**changes)})))


@pytest.mark.parametrize(
    "changes",
    [
        {"format_version": 2},
        {"exported_at": "2026-10-05T18:51:22"},
        {"exported_at": "2026-10-05T21:51:22+03:00"},
        {"extra": True},
    ],
)
def test_an_invalid_file_is_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        LabelFile.model_validate_json(json.dumps(file({ID: label()}, **changes)))


def test_a_missing_file_says_where_it_belongs(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="label_posts.html"):
        read_labels(tmp_path / "labels.json")
