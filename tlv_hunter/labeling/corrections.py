"""`corrections.json`, the review report's export (`PHASE_2.md` 2.7; DECISIONS.md #143, #172,
#193, #195): Ron's review of classified posts, per `listing_id`.

Each record names the classification it reviewed (`prompt_version`, `model_name`,
`classified_at`), so a correction is never applied to another one. `reviewed` marks a post Ron went
through; a reviewed post with no corrected field means the model was right on every field. Ron moves
the file into `data/labeling/` and the code reads it only from there. A plain module: it reads,
and writes nothing.
"""

import json
from collections.abc import Iterator, Mapping
from collections.abc import Set as AbstractSet
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter, field_validator

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.postmodel.reclassify import PROPOSALS_FILE

CORRECTIONS_FILE = "corrections.json"
RUNS_DIR = "runs"
RESULTS_FILE = "results.json"

# Every Listing field Ron can correct: all but the provenance and `price_source`, which code
# derives from the price.
CORRECTABLE = (
    "post_nature",
    "apartment_kind",
    "price",
    "entry_date_written",
    "entry_date",
    "rooms",
    "floor",
    "building_floors",
    "size_sqm",
    "room_size_sqm",
    "broker",
    "balcony",
    "parking",
    "elevator",
    "air_conditioning",
    "furnished",
    "arnona",
    "house_committee",
    "gender",
    "streets",
    "stated_area_names",
    "areas",
    "other_city",
    "phone_names",
)


class Correction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text_sha256: str
    prompt_version: str
    model_name: str
    classified_at: datetime
    reviewed: bool
    fields: dict[str, Any]
    note: str

    @field_validator("classified_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @field_validator("fields")
    @classmethod
    def _fields(cls, value: dict[str, Any]) -> dict[str, Any]:
        for name, right in value.items():
            if name not in CORRECTABLE:
                raise ValueError(f"{name}: not a field Ron corrects")
            annotation = Listing.model_fields[name].annotation
            TypeAdapter(annotation).validate_json(json.dumps(right, ensure_ascii=False))
        return value

    def is_for(self, listing: Listing) -> bool:
        return (listing.prompt_version, listing.model_name, listing.classified_at) == (
            self.prompt_version,
            self.model_name,
            self.classified_at,
        )


class CorrectionFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    exported_at: datetime
    corrections: dict[str, Correction]

    @field_validator("exported_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    def reviewed(self) -> dict[str, Correction]:
        return {key: c for key, c in self.corrections.items() if c.reviewed}

    def errors_per_field(
        self, excluded: AbstractSet[tuple[str, str]] = frozenset()
    ) -> dict[str, int]:
        """Per correctable field, the reviewed posts where Ron corrected it (#172). An excluded
        (post, field) is not counted (#216)."""
        counts = dict.fromkeys(CORRECTABLE, 0)
        for listing_id, correction in self.reviewed().items():
            for name in correction.fields:
                if (listing_id, name) not in excluded:
                    counts[name] += 1
        return counts

    def effective_fields(
        self, listing_id: str, excluded: AbstractSet[tuple[str, str]] = frozenset()
    ) -> dict[str, Any]:
        """The corrected fields of a post, the excluded ones left out (#216)."""
        return {
            name: value
            for name, value in self.corrections[listing_id].fields.items()
            if (listing_id, name) not in excluded
        }

    def corrected_ids(self) -> list[str]:
        """The reviewed posts with at least one corrected field: they join the set (#195). A post
        whose only corrections are excluded (#216) still joins: its other fields were reviewed."""
        return sorted(key for key, c in self.reviewed().items() if c.fields)

    def stale(self, texts: Mapping[str, str]) -> list[str]:
        return sorted(
            key
            for key, c in self.corrections.items()
            if key in texts and text_sha256(texts[key]) != c.text_sha256
        )


def corrected_listing(
    listing: Listing, correction: Correction, excluded_fields: AbstractSet[str] = frozenset()
) -> Listing:
    """The reviewed classification with Ron's corrections: the truth of #193. `price_source`
    follows the corrected price: none when not written, else kept, or "text" when there was none.
    An excluded field keeps the model's value (#216), and no comparison uses it."""
    if not correction.is_for(listing):
        raise ValueError(f"{listing.listing_id}: the correction is for another classification")
    fields = {k: v for k, v in correction.fields.items() if k not in excluded_fields}
    merged = {**listing.model_dump(mode="json"), **fields}
    if "price" in fields:
        state = fields["price"]["state"]
        merged["price_source"] = (
            None if state == "not_written" else (listing.price_source or "text")
        )
    return Listing.model_validate_json(json.dumps(merged, ensure_ascii=False))


def read_corrections(path: Path) -> CorrectionFile | None:
    """None when there is no file yet: nothing was reviewed."""
    path = Path(path)
    if not path.is_file():
        return None
    return CorrectionFile.model_validate_json(path.read_text(encoding="utf-8"))


def run_listings(runs_dir: Path) -> Iterator[Listing]:
    """Every classification a regression run kept, from each run's `results.json`."""
    if not runs_dir.is_dir():
        return
    for results in sorted(runs_dir.glob(f"*/{RESULTS_FILE}")):
        data = json.loads(results.read_text(encoding="utf-8"))
        for run_pass in data.get("passes", []):
            for post in run_pass.get("posts", []):
                if post.get("listing") is not None:
                    yield Listing.model_validate_json(json.dumps(post["listing"]))


def reclassified_listings(reclassify_dir: Path) -> Iterator[Listing]:
    """The old `Listing` of every proposal a reclassify run kept (DECISIONS.md #222), from each
    run's `proposals.jsonl`: whether or not the proposal was applied, it holds the classification
    that was in the store when the run was made. A line cut short by a killed run is skipped."""
    if not reclassify_dir.is_dir():
        return
    for proposals in sorted(reclassify_dir.glob(f"*/{PROPOSALS_FILE}")):
        for line in proposals.read_text(encoding="utf-8").splitlines():
            try:
                old = json.loads(line)["old"]["listing"]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
            yield Listing.model_validate_json(json.dumps(old))


def find_reviewed(
    listing_id: str,
    correction: Correction,
    store_listing: Listing | None,
    runs_dir: Path,
    reclassify_dir: Path | None = None,
) -> Listing | None:
    """The classification a correction names: the store's, or one kept by a regression run, or one
    a reclassify replaced (#222). The truth of a reviewed post stays Ron's corrected old
    classification after the store holds a new one."""
    if store_listing is not None and correction.is_for(store_listing):
        return store_listing
    for listing in run_listings(runs_dir):
        if listing.listing_id == listing_id and correction.is_for(listing):
            return listing
    if reclassify_dir is not None:
        for listing in reclassified_listings(reclassify_dir):
            if listing.listing_id == listing_id and correction.is_for(listing):
                return listing
    return None
