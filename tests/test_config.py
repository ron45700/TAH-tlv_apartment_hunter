import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, REPO_ROOT
from tlv_hunter.config.base import ConfigSource
from tlv_hunter.config.yaml_config import YamlConfig

HANDOFF_GROUP_IDS = [
    "35819517694",
    "333022240594651",
    "101875683484689",
    "5612809662118963",
    "733810383372996",
    "295395253832427",
]

VALID_COLLECTION = """\
provider: thedoor
group_ids: ["35819517694"]
max_posts: 30
sorting_order: newest_posts
fetch_all_comments: false
store_root: data/store
"""


def _config_dir(tmp_path: Path, collection: str, user: str | None = None) -> YamlConfig:
    (tmp_path / "collection.yaml").write_text(collection, encoding="utf-8")
    if user is not None:
        (tmp_path / "users").mkdir()
        (tmp_path / "users" / "ron.yaml").write_text(user, encoding="utf-8")
    return YamlConfig(tmp_path)


def test_repo_collection_config_loads() -> None:
    config = YamlConfig(CONFIG_ROOT)
    assert isinstance(config, ConfigSource)
    collection = config.collection()
    assert collection.provider == "thedoor"
    assert collection.group_ids == HANDOFF_GROUP_IDS
    assert collection.max_posts == 30
    assert collection.sorting_order == "newest_posts"
    assert collection.fetch_all_comments is False
    assert collection.store_root == "data/store"


def test_repo_user_config_loads() -> None:
    user = YamlConfig(CONFIG_ROOT).user("ron")
    assert user.user_id == "ron"
    assert user.subscribed_group_ids == HANDOFF_GROUP_IDS


def test_newest_activity_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(tmp_path, VALID_COLLECTION.replace("newest_posts", "newest_activity"))
    with pytest.raises(ValidationError):
        config.collection()


def test_fetch_all_comments_true_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(
        tmp_path, VALID_COLLECTION.replace("fetch_all_comments: false", "fetch_all_comments: true")
    )
    with pytest.raises(ValidationError):
        config.collection()


def test_fetch_all_comments_missing_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(tmp_path, VALID_COLLECTION.replace("fetch_all_comments: false\n", ""))
    with pytest.raises(ValidationError):
        config.collection()


def test_unapproved_key_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(tmp_path, VALID_COLLECTION + "include_top_comment: false\n")
    with pytest.raises(ValidationError):
        config.collection()


def test_unquoted_numeric_group_id_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(tmp_path, VALID_COLLECTION.replace('["35819517694"]', "[35819517694]"))
    with pytest.raises(ValidationError):
        config.collection()


def test_user_file_must_match_its_user_id(tmp_path: Path) -> None:
    config = _config_dir(
        tmp_path, VALID_COLLECTION, "user_id: someone_else\nsubscribed_group_ids: []\n"
    )
    with pytest.raises(ValueError):
        config.user("ron")


def test_path_like_user_id_is_rejected(tmp_path: Path) -> None:
    config = _config_dir(tmp_path, VALID_COLLECTION)
    with pytest.raises(ValueError):
        config.user("../collection")


def test_no_module_outside_config_reads_yaml_directly() -> None:
    package = REPO_ROOT / "tlv_hunter"
    offenders = []
    for path in package.rglob("*.py"):
        if path.parent.name == "config" and path.parent.parent == package:
            continue
        source = path.read_text(encoding="utf-8")
        if re.search(r"^\s*(import|from)\s+yaml\b", source, re.MULTILINE) or re.search(
            r"\.ya?ml\b", source
        ):
            offenders.append(path.relative_to(REPO_ROOT))
    assert offenders == []
