"""reference/areas.yaml: the 71 areas (DECISIONS.md #81, #83, #119), read only through
tlv_hunter.areas.reference."""

from pathlib import Path

import pytest
import yaml

from tests.conftest import REPO_ROOT, _load_fixture
from tlv_hunter.areas.reference import REFERENCE_ROOT, load_areas

LAYER_511 = REPO_ROOT / "data" / "raw" / "tlv_gis_layer511_rows_2026-10-05.json"
LABELS = {
    5: "תכנית ל'",
    7: "רמת אביב ג'",
    17: "נאות אפקה ב'",
    18: "נאות אפקה א'",
    49: "יפו ד' (גבעת התמרים)",
}


def test_the_reference_root_is_the_repository_folder() -> None:
    assert REFERENCE_ROOT == REPO_ROOT / "reference"


def test_there_are_71_areas_numbered_1_to_71() -> None:
    assert [area.number for area in load_areas()] == list(range(1, 72))


def test_every_name_is_the_layer_511_name_verbatim() -> None:
    features = _load_fixture(LAYER_511)["features"]
    expected = {f["attributes"]["ms_shchuna"]: f["attributes"]["shem_shchuna"] for f in features}
    assert {area.number: area.name for area in load_areas()} == expected


def test_exactly_the_five_display_labels() -> None:
    areas = load_areas()
    assert {area.number: area.label for area in areas if area.label is not None} == LABELS
    assert {area.number: area.display_name for area in areas if area.number in LABELS} == LABELS
    assert all(area.display_name == area.name for area in areas if area.number not in LABELS)


def test_the_source_block_names_layer_511() -> None:
    source = yaml.safe_load((REFERENCE_ROOT / "areas.yaml").read_text(encoding="utf-8"))["source"]
    assert source["layer"] == 511
    assert source["date_import"] == "18/11/2024 00:59:04"


def _write(root: Path, entries: list[dict]) -> Path:
    (root / "areas.yaml").write_text(
        yaml.safe_dump({"areas": entries}, allow_unicode=True), encoding="utf-8"
    )
    return root


@pytest.mark.parametrize(
    "numbers",
    [
        list(range(1, 71)),
        list(range(1, 72)) + [72],
        [2, 1] + list(range(3, 72)),
        [1, 1] + list(range(3, 72)),
    ],
)
def test_a_list_missing_repeating_or_reordering_an_area_is_refused(tmp_path, numbers) -> None:
    _write(tmp_path, [{"number": n, "name": f"area {n}"} for n in numbers])
    with pytest.raises(ValueError, match="numbered 1-71"):
        load_areas(tmp_path)


def test_an_unknown_key_is_refused(tmp_path) -> None:
    entries = [{"number": n, "name": f"area {n}"} for n in range(1, 72)]
    entries[0]["alias"] = "x"
    _write(tmp_path, entries)
    with pytest.raises(ValueError):
        load_areas(tmp_path)
