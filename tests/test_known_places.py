"""The known places (DECISIONS.md #205): `reference/known_places.yaml` and its loader in
`tlv_hunter/areas/reference.py`. The file's areas are checked against layer 511's polygons, fetched
once into `data/raw/` and read in place; a missing fixture fails the test, never skips it."""

import json
import math
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from tests.conftest import REPO_ROOT
from tlv_hunter.areas.reference import (
    KNOWN_PLACES_FILE,
    KnownPlace,
    load_areas,
    load_known_places,
)

POLYGONS = REPO_ROOT / "data" / "raw" / "tlv_gis_layer511_polygons_2026-10-06.json"
POINT_QUERIES = REPO_ROOT / "data" / "raw" / "tlv_gis_layer511_point_queries_2026-10-06.json"
TOUCH_METERS = 40


def entry(**changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": "כיכר א",
        "aliases": [],
        "lat": 32.08,
        "lon": 34.78,
        "coordinates_source": "OpenStreetMap node 1, by a test",
        "coordinates_date": "2026-10-06",
        "areas": [31],
    }
    return {**fields, **changes}


def write_places(root: Path, places: list[dict[str, Any]]) -> Path:
    (root / KNOWN_PLACES_FILE).write_text(
        yaml.safe_dump({"places": places}, allow_unicode=True), encoding="utf-8"
    )
    return root


# --- the loader ---


def test_a_valid_entry_loads(tmp_path: Path) -> None:
    (place,) = load_known_places(write_places(tmp_path, [entry(aliases=["כיכר ב"])]))
    assert (place.name, place.areas, place.written) == ("כיכר א", [31], ("כיכר א", "כיכר ב"))
    assert place.coordinates_date.isoformat() == "2026-10-06"


def test_an_unquoted_yaml_date_loads_too(tmp_path: Path) -> None:
    (tmp_path / KNOWN_PLACES_FILE).write_text(
        "places:\n- name: כיכר א\n  lat: 32.08\n  lon: 34.78\n  coordinates_source: s\n"
        "  coordinates_date: 2026-10-06\n  areas: [31]\n",
        encoding="utf-8",
    )
    assert load_known_places(tmp_path)[0].coordinates_date.isoformat() == "2026-10-06"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"aliases": [""]},
        {"coordinates_source": ""},
        {"areas": []},
        {"areas": [0]},
        {"areas": [72]},
        {"areas": [31, 30]},
        {"areas": [31, 31]},
        {"lat": 31.0},
        {"lon": 35.5},
        {"coordinates_date": "yesterday"},
    ],
)
def test_an_invalid_entry_is_refused(tmp_path: Path, changes: dict[str, Any]) -> None:
    with pytest.raises((ValidationError, ValueError)):
        load_known_places(write_places(tmp_path, [entry(**changes)]))


@pytest.mark.parametrize(
    "missing", ["name", "lat", "lon", "coordinates_source", "coordinates_date", "areas"]
)
def test_an_incomplete_entry_is_refused(tmp_path: Path, missing: str) -> None:
    incomplete = entry()
    del incomplete[missing]
    with pytest.raises(ValidationError):
        load_known_places(write_places(tmp_path, [incomplete]))


def test_an_unknown_field_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        load_known_places(write_places(tmp_path, [entry(population=3)]))


def test_a_name_written_for_two_places_is_refused(tmp_path: Path) -> None:
    places = [entry(), entry(name="כיכר ב", aliases=["כיכר א"])]
    with pytest.raises(ValueError, match="is written for"):
        load_known_places(write_places(tmp_path, places))
    with pytest.raises(ValueError, match="is written for"):
        load_known_places(write_places(tmp_path, [entry(aliases=["כיכר א"])]))


def test_an_empty_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-empty list"):
        load_known_places(write_places(tmp_path, []))


# --- the real file ---

SEVEN = {
    # Ron's seven places (#203) as the file writes them, with the area each must reach (#203, #205).
    "כיכר דיזנגוף": {31},
    "כיכר רבין": {31},
    "דיזנגוף סנטר": {31},
    "קניון רמת אביב": {10},
    "ז'בוטינסקי פינת אבן גבירול": {30, 34},
    "מלון רויאל ביץ'": {38},
    "ארלוזורוב פינת הנרייטה סולד": {34},
}


def test_the_real_file_loads_with_a_few_dozen_places_in_every_region() -> None:
    places = load_known_places()
    assert 30 <= len(places) <= 100
    reached = {number for place in places for number in place.areas}
    # The centre, the Old and New North, Ramat Aviv, Florentin and the south, Jaffa.
    assert {37, 31, 30, 34, 35, 10, 52, 53, 42, 44} <= reached
    assert reached <= {area.number for area in load_areas()}


@pytest.mark.parametrize("name", sorted(SEVEN))
def test_ron_s_seven_places_are_in_the_file_and_reach_their_area(name: str) -> None:
    by_name = {place.name: place for place in load_known_places()}
    assert SEVEN[name] <= set(by_name[name].areas)


def test_every_place_names_its_source_and_its_date() -> None:
    for place in load_known_places():
        assert place.coordinates_source.startswith(("OpenStreetMap", "Tel Aviv"))
        assert place.coordinates_date.isoformat() == "2026-10-06"


def test_the_source_block_states_both_sources_and_the_touch_distance() -> None:
    data = yaml.safe_load((REPO_ROOT / "reference" / KNOWN_PLACES_FILE).read_text(encoding="utf-8"))
    source = data["source"]
    assert "OpenStreetMap" in source["coordinates"] and "ODbL" in source["coordinates"]
    assert "layer 511" in source["areas"]
    assert source["touch_meters"] == TOUCH_METERS


# --- the areas, against layer 511's polygons (fixtures read in place) ---


def _fixture(path: Path) -> Any:
    if not path.is_file():
        pytest.fail(f"fixture missing: {path}. data/ is gitignored; tests fail, never skip.")
    return json.loads(path.read_text(encoding="utf-8"))


def _polygons() -> dict[int, list[list[list[float]]]]:
    return {
        f["attributes"]["ms_shchuna"]: f["geometry"]["rings"]
        for f in _fixture(POLYGONS)["features"]
    }


def _inside(lon: float, lat: float, ring: list[list[float]]) -> bool:
    inside, j = False, len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _meters(lon: float, lat: float, ring: list[list[float]]) -> float:
    k = math.cos(math.radians(lat)) * 111320.0
    px, py = lon * k, lat * 110574.0
    best = math.inf
    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1], strict=True):
        ax, ay, bx, by = x1 * k, y1 * 110574.0, x2 * k, y2 * 110574.0
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = 0 if length == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / length))
        best = min(best, math.hypot(px - (ax + t * dx), py - (ay + t * dy)))
    return best


def test_the_polygons_fixture_is_the_71_areas() -> None:
    assert sorted(_polygons()) == list(range(1, 72))


def test_every_place_lies_in_its_first_area_and_every_listed_area_is_within_reach() -> None:
    polygons = _polygons()
    for place in load_known_places():
        containing = {
            n
            for n, rings in polygons.items()
            if any(_inside(place.lon, place.lat, r) for r in rings)
        }
        assert containing, f"{place.name}: the point is in no area"
        assert containing <= set(place.areas), place.name
        for number in place.areas:
            distance = min(_meters(place.lon, place.lat, r) for r in polygons[number])
            assert number in containing or distance <= TOUCH_METERS, (place.name, number, distance)


def test_no_area_within_reach_is_left_out() -> None:
    polygons = _polygons()
    for place in load_known_places():
        near = {
            n
            for n, rings in polygons.items()
            if min(_meters(place.lon, place.lat, r) for r in rings) <= TOUCH_METERS
        }
        assert near <= set(place.areas), (place.name, near - set(place.areas))


def test_the_layer_service_gave_the_same_containing_area_for_every_place() -> None:
    """The point queries of 2026-10-06, one per place, saved as they came back."""
    queries = _fixture(POINT_QUERIES)
    for place in load_known_places():
        features = queries[place.name]["response"]["features"]
        assert features, place.name
        assert {f["attributes"]["ms_shchuna"] for f in features} <= set(place.areas), place.name


def test_a_known_place_is_a_frozen_strict_model() -> None:
    place = KnownPlace.model_validate(entry())
    with pytest.raises(ValidationError):
        place.name = "x"  # type: ignore[misc]
