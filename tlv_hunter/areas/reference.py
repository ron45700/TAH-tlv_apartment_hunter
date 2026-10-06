"""The only reader of `reference/` (DECISIONS.md #132; PHASE_1.md's YAML anchor, as reworded).

`reference/areas.yaml` holds the closed list of 71 areas (#81): the municipal number is the
identity, the name a label (#83), and five entries carry a hand-corrected display label (#119).

`reference/known_places.yaml` holds the known places (#205): well-known squares, junctions, markets,
malls, hospitals, stations and the like, each with its coordinates, their source and date, and the
areas it lies in. Ron adds entries by hand; the loader refuses an entry that is incomplete, whose
areas are not municipal numbers, or whose name is written twice.
"""

from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

REFERENCE_ROOT = Path(__file__).resolve().parents[2] / "reference"
AREAS_FILE = "areas.yaml"
AREA_COUNT = 71
KNOWN_PLACES_FILE = "known_places.yaml"
# A place outside this box is a typo, not a place in Tel Aviv-Yafo (its municipal area is a few
# kilometres wide); WGS84.
LAT_RANGE = (32.00, 32.15)
LON_RANGE = (34.72, 34.86)


class Area(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    number: int
    name: str
    label: str | None = None

    @property
    def display_name(self) -> str:
        return self.label if self.label is not None else self.name


def load_areas(root: Path = REFERENCE_ROOT) -> tuple[Area, ...]:
    """The 71 areas in municipal-number order. Raises on any entry missing, repeated or extra."""
    path = Path(root) / AREAS_FILE
    data = _load_mapping(path)
    entries = data.get("areas")
    if not isinstance(entries, list):
        raise ValueError(f"{path}: expected a list under 'areas'")
    areas = tuple(Area.model_validate(entry) for entry in entries)
    numbers = [area.number for area in areas]
    if numbers != list(range(1, AREA_COUNT + 1)):
        raise ValueError(f"{path}: expected areas numbered 1-{AREA_COUNT} in order, once each")
    if any(not area.name.strip() for area in areas):
        raise ValueError(f"{path}: every area needs a name")
    return areas


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


class KnownPlace(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: str
    aliases: list[str] = Field(default_factory=list)
    lat: float
    lon: float
    coordinates_source: str
    coordinates_date: date
    areas: list[int]

    @field_validator("name", "coordinates_source")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @field_validator("coordinates_date", mode="before")
    @classmethod
    def _iso_date(cls, value: Any) -> Any:
        """YAML reads an unquoted 2026-10-06 as a date and a quoted one as text: both are fine."""
        return date.fromisoformat(value) if isinstance(value, str) else value

    @field_validator("aliases")
    @classmethod
    def _aliases(cls, value: list[str]) -> list[str]:
        if any(not alias.strip() for alias in value):
            raise ValueError("an alias must not be blank")
        return value

    @field_validator("lat")
    @classmethod
    def _lat(cls, value: float) -> float:
        if not LAT_RANGE[0] <= value <= LAT_RANGE[1]:
            raise ValueError(f"lat {value} is outside Tel Aviv-Yafo")
        return value

    @field_validator("lon")
    @classmethod
    def _lon(cls, value: float) -> float:
        if not LON_RANGE[0] <= value <= LON_RANGE[1]:
            raise ValueError(f"lon {value} is outside Tel Aviv-Yafo")
        return value

    @field_validator("areas")
    @classmethod
    def _areas(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("a place lies in at least one area")
        if any(not 1 <= number <= AREA_COUNT for number in value):
            raise ValueError(f"areas are municipal numbers 1-{AREA_COUNT}")
        if value != sorted(set(value)):
            raise ValueError("areas are sorted with no repeats")
        return value

    @property
    def written(self) -> tuple[str, ...]:
        """Every way the place is written: its name, then its aliases."""
        return (self.name, *self.aliases)


def load_known_places(root: Path = REFERENCE_ROOT) -> tuple[KnownPlace, ...]:
    """The known places in file order. Raises on an invalid entry, and on a name or alias that is
    written for two entries or twice for one."""
    path = Path(root) / KNOWN_PLACES_FILE
    data = _load_mapping(path)
    entries = data.get("places")
    if not isinstance(entries, list) or not entries:
        raise ValueError(f"{path}: expected a non-empty list under 'places'")
    places = tuple(KnownPlace.model_validate(entry) for entry in entries)
    seen: dict[str, str] = {}
    for place in places:
        for written in place.written:
            key = written.strip()
            if key in seen:
                raise ValueError(f"{path}: {key!r} is written for {seen[key]!r} and {place.name!r}")
            seen[key] = place.name
    return places
