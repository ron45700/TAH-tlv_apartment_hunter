"""The regression set (`PHASE_2.md` 2.6; DECISIONS.md #142, #165): the posts by `listing_id`, each
with the case it covers, in `data/labeling/regression_set.json`.

The file holds ids and cases only. The texts are read where they live: the store, or, for #45's
case, `data/raw/test_posts.json`. Both are under `data/`, gitignored: real people's phone numbers.
A plain module: it reads, and writes nothing.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, model_validator

from tlv_hunter.contracts.raw_post import RAW_POST_SCHEMA_VERSION, RawPost
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.textnorm.annotate import annotate

LABELING_DIR = Path("data") / "labeling"
REGRESSION_SET_FILE = "regression_set.json"
TEST_POSTS = "data/raw/test_posts.json"
REGRESSION_SET_FORMAT_VERSION = 1
# #45's post has no publication date; the day the fixture was captured (DECISIONS.md #189).
TEST_POSTS_POSTED_AT = datetime(2026, 9, 13, tzinfo=UTC)


class RegressionEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    listing_id: str
    case: str
    source: Literal["store", "data/raw/test_posts.json"]
    # The post's id in `data/raw/test_posts.json`, whose listing_id is computed from it.
    post_id: str | None = None
    # "blind": the deciding fields' truth is Ron's label (`labels.json`). "review": a post that
    # joined from the review report; its truth is the corrected classification (#195).
    truth: Literal["blind", "review"] = "blind"

    @model_validator(mode="after")
    def _post_id_for_test_posts(self) -> Self:
        if (self.source == TEST_POSTS) != (self.post_id is not None):
            raise ValueError(f"post_id is given exactly when the source is {TEST_POSTS}")
        return self


class RegressionSet(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    format_version: Literal[1]
    posts: list[RegressionEntry]

    @model_validator(mode="after")
    def _unique(self) -> Self:
        ids = [entry.listing_id for entry in self.posts]
        if len(ids) != len(set(ids)):
            raise ValueError("a listing_id appears twice in the regression set")
        return self


@dataclass(frozen=True)
class PostText:
    """A post's text as stored, never changed, and the hash that ties a label to it."""

    listing_id: str
    text: str

    @property
    def text_sha256(self) -> str:
        return text_sha256(self.text)


class PostSource(Protocol):
    def get(self, listing_id: str) -> RawPost | None: ...


def text_sha256(text: str) -> str:
    """The SHA-256 of the exact text, never normalized: a label holds it, so a post whose text
    changed after labelling is found (`labels.py`). `surrogatepass`: a lone surrogate, which a
    provider's JSON can carry, still hashes."""
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()


def load_regression_set(path: Path) -> RegressionSet:
    return RegressionSet.model_validate_json(Path(path).read_text(encoding="utf-8"))


def regression_posts(
    entries: Sequence[RegressionEntry], store: PostSource, repo_root: Path
) -> list[RawPost]:
    """Each entry's post, in the set's order, as the classifier takes it. #45's post is built in
    memory from `data/raw/test_posts.json`; nothing is stored. Raises when a post is missing."""
    test_posts: dict[str, str] | None = None
    found = []
    for entry in entries:
        if entry.source == "store":
            post = store.get(entry.listing_id)
            if post is None:
                raise LookupError(f"{entry.listing_id}: not in the store")
            found.append(post)
            continue
        if test_posts is None:
            test_posts = _load_test_posts(repo_root / TEST_POSTS)
        found.append(_test_post(entry, test_posts))
    return found


def _test_post(entry: RegressionEntry, test_posts: dict[str, str]) -> RawPost:
    assert entry.post_id is not None
    if compute_listing_id(entry.post_id) != entry.listing_id:
        raise ValueError(f"{entry.listing_id}: does not match post_id {entry.post_id}")
    if entry.post_id not in test_posts:
        raise LookupError(f"{entry.listing_id}: post_id {entry.post_id} not in {TEST_POSTS}")
    text = test_posts[entry.post_id]
    post = RawPost(
        schema_version=RAW_POST_SCHEMA_VERSION,
        source="thedoor",
        source_post_id=entry.post_id,
        listing_id=entry.listing_id,
        group_id="test_posts",
        group_title=None,
        permalink="",
        posted_at=TEST_POSTS_POSTED_AT,
        fetched_at=TEST_POSTS_POSTED_AT,
        raw={"post_id": entry.post_id, "text": text},
        text=text,
        text_source="text",
        post_type="regular",
        media=[],
        native_price=None,
        native_price_raw=None,
        native_currency=None,
        native_title=None,
        native_location=None,
        author_name=None,
        author_id_raw=None,
        author_profile_url=None,
        top_comment=None,
        reactions_count=None,
        comments_count=None,
        shares_count=None,
    )
    return annotate(post).with_changes(is_canonical=True)


def post_texts(
    entries: Sequence[RegressionEntry], store: PostSource, repo_root: Path
) -> list[PostText]:
    """Each entry's text, in the set's order. Raises when a post cannot be found."""
    test_posts: dict[str, str] | None = None
    texts = []
    for entry in entries:
        if entry.source == "store":
            post = store.get(entry.listing_id)
            if post is None:
                raise LookupError(f"{entry.listing_id}: not in the store")
            texts.append(PostText(entry.listing_id, post.text))
            continue
        if test_posts is None:
            test_posts = _load_test_posts(repo_root / TEST_POSTS)
        assert entry.post_id is not None
        if compute_listing_id(entry.post_id) != entry.listing_id:
            raise ValueError(f"{entry.listing_id}: does not match post_id {entry.post_id}")
        if entry.post_id not in test_posts:
            raise LookupError(f"{entry.listing_id}: post_id {entry.post_id} not in {TEST_POSTS}")
        texts.append(PostText(entry.listing_id, test_posts[entry.post_id]))
    return texts


def _load_test_posts(path: Path) -> dict[str, str]:
    items = json.loads(path.read_text(encoding="utf-8"))
    return {item["post_id"]: item["text"] for item in items}
