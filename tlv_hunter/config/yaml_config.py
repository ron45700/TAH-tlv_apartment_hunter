from pathlib import Path
from typing import Any

import yaml

from tlv_hunter.config.base import CollectionConfig


class YamlConfig:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def collection(self) -> CollectionConfig:
        return CollectionConfig.model_validate(_load_mapping(self._root / "collection.yaml"))


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data
