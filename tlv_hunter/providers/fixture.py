import json
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.providers.thedoor import to_raw_post


class FixtureProvider:
    """Serves a captured thedoor response from disk. Never touches the network."""

    def __init__(self, path: Path, clock: Callable[[], datetime]) -> None:
        self._path = Path(path)
        self._clock = clock

    def fetch(self, group_ids: Sequence[str], since: datetime) -> list[RawPost]:
        items = json.loads(self._path.read_text(encoding="utf-8"))
        fetched_at = self._clock()
        wanted = set(group_ids)
        posts = (to_raw_post(item, fetched_at) for item in items)
        return [post for post in posts if post.group_id in wanted and post.posted_at >= since]
