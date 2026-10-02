import json
import os
import uuid
from pathlib import Path

from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.textnorm.phones import canonical_phone

RAW_POSTS_COLLECTION = "raw_posts"


class LocalJsonRepository:
    """One JSON file per record at <root>/<collection>/<listing_id>.json. No index."""

    def __init__(self, root: Path) -> None:
        self._posts_dir = Path(root) / RAW_POSTS_COLLECTION

    def upsert(self, post: RawPost) -> RawPost:
        path = self._posts_dir / f"{post.listing_id}.json"
        if path.exists():
            post = post.with_changes(fetched_at=_read(path).fetched_at)
        self._posts_dir.mkdir(parents=True, exist_ok=True)
        _atomic_write(path, json.dumps(post.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return post

    def find_by_hash(self, text_hash: str | None) -> list[RawPost]:
        if text_hash is None:
            return []
        return [post for post in self.query() if post.text_hash == text_hash]

    def find_by_phone(self, phone: str) -> list[RawPost]:
        wanted = canonical_phone(phone)
        return [
            post
            for post in self.query()
            if post.phones and wanted in {canonical_phone(p) for p in post.phones}
        ]

    def query(self) -> list[RawPost]:
        if not self._posts_dir.is_dir():
            return []
        return [_read(path) for path in sorted(self._posts_dir.glob("*.json"))]


def _read(path: Path) -> RawPost:
    return RawPost.model_validate_json(path.read_text(encoding="utf-8"))


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
