"""The only reader of `reference/` (DECISIONS.md #132; PHASE_1.md's YAML anchor, as reworded).

`reference/areas.yaml` holds the closed list of 71 areas (#81): the municipal number is the
identity, the name a label (#83), and five entries carry a hand-corrected display label (#119).
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

REFERENCE_ROOT = Path(__file__).resolve().parents[2] / "reference"
AREAS_FILE = "areas.yaml"
AREA_COUNT = 71


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
