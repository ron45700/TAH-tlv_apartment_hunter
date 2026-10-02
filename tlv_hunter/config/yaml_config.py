import re
from pathlib import Path
from typing import Any

import yaml

from tlv_hunter.config.base import CollectionConfig, UserConfig

_USER_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


class YamlConfig:
    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def collection(self) -> CollectionConfig:
        return CollectionConfig.model_validate(_load_mapping(self._root / "collection.yaml"))

    def user(self, user_id: str) -> UserConfig:
        if not _USER_ID_RE.fullmatch(user_id):
            raise ValueError(f"invalid user_id: {user_id!r}")
        path = self._root / "users" / f"{user_id}.yaml"
        config = UserConfig.model_validate(_load_mapping(path))
        if config.user_id != user_id:
            raise ValueError(f"{path}: user_id {config.user_id!r} does not match file name")
        return config


def _load_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data
