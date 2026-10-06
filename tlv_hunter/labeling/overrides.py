"""`label_overrides.json`: the changes Ron approved on top of his `labels.json`, each with its
reason (DECISIONS.md #196). Ron's file is never edited: the regression runner applies these on
top of it and lists them in every run report.

- `nature_only`: a post labelled with one of these natures is compared on `post_nature` only.
- `removed`: posts taken out of the set. `regression_set.json` keeps them, so positions stay put.
- `label_changes`: a deciding field's label replaced, in `labels.json`'s shape.
- `not_compared`: a deciding field left out of the comparison for one post.

Positions are 1-based in `regression_set.json`; each is checked against its `listing_id`. The file
names the SHA-256 of the `labels.json` it was reviewed against, and is refused with any other.
A plain module: it reads, and writes nothing.
"""

import hashlib
from collections.abc import Sequence
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from tlv_hunter.labeling.labels import PostLabel
from tlv_hunter.labeling.regression_set import RegressionEntry

OVERRIDES_FILE = "label_overrides.json"

LabelField = Literal[
    "post_nature",
    "apartment_kind",
    "price",
    "gender",
    "entry_date_parts",
    "areas",
    "other_city",
]
Nature = Literal["rental_offer", "sublet_offer", "seeking", "for_sale", "not_listing"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NatureOnly(_Strict):
    natures: list[Nature]
    reason: str


class Removed(_Strict):
    position: int
    listing_id: str
    reason: str


class LabelChange(_Strict):
    position: int
    listing_id: str
    field: LabelField
    value: object
    reason: str


class NotCompared(_Strict):
    position: int
    listing_id: str
    field: LabelField
    reason: str


class Overrides(_Strict):
    format_version: Literal[1]
    approved: str
    labels_sha256: str
    nature_only: NatureOnly
    removed: list[Removed]
    label_changes: list[LabelChange]
    not_compared: list[NotCompared]

    @model_validator(mode="after")
    def _no_change_twice(self) -> Self:
        changes = [(change.listing_id, change.field) for change in self.label_changes]
        if len(changes) != len(set(changes)):
            raise ValueError("a field of one post is changed twice")
        return self

    def check_positions(self, entries: Sequence[RegressionEntry]) -> list[str]:
        """Every entry whose position does not hold its listing_id, as messages."""
        problems = []
        for item in (*self.removed, *self.label_changes, *self.not_compared):
            if not 1 <= item.position <= len(entries):
                problems.append(f"position {item.position}: outside the set")
            elif entries[item.position - 1].listing_id != item.listing_id:
                problems.append(f"position {item.position}: does not hold {item.listing_id}")
        return problems

    def removed_ids(self) -> set[str]:
        return {item.listing_id for item in self.removed}

    def apply(self, listing_id: str, label: PostLabel) -> PostLabel:
        """The label with this post's changes, validated as `labels.json` is."""
        changes = {c.field: c.value for c in self.label_changes if c.listing_id == listing_id}
        if not changes:
            return label
        return PostLabel.model_validate({**label.model_dump(mode="json"), **changes})

    def not_compared_fields(self, listing_id: str) -> set[str]:
        return {item.field for item in self.not_compared if item.listing_id == listing_id}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_overrides(path: Path) -> Overrides:
    return Overrides.model_validate_json(Path(path).read_text(encoding="utf-8"))
