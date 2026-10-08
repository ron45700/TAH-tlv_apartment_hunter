"""`pair_verdicts.json`, the candidate-pairs page's export (`PHASE_2.md` 2.10; DECISIONS.md #226,
#227), and the measurement read from it.

Ron judges each pair with one of four verdicts. Only `same_listing` is a rewritten repost, for the
rate and for the threshold; `same_apartment_other_listing` is reported on its own line, per signal
too; `not_sure` counts as `different` for the threshold, with the upper figure beside it. Ron
moves the file into `data/gate_d/` and the code reads it only from there. A plain module: it
reads and prints, and writes nothing.
"""

import json
import math
from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.gate_d.candidates import (
    AGENT_PHONE_SAMPLE,
    FIELDS,
    PHONE,
    RULES_VERSION,
    CandidatePair,
    Population,
)
from tlv_hunter.parsing.datetimes import require_utc

GATE_D_DIR = "data/gate_d"
VERDICTS_FILE = "pair_verdicts.json"
FORMAT_VERSION = 1

SAME_LISTING = "same_listing"
SAME_APARTMENT = "same_apartment_other_listing"
DIFFERENT = "different"
NOT_SURE = "not_sure"
VERDICTS = (SAME_LISTING, SAME_APARTMENT, DIFFERENT, NOT_SURE)

# DECISIONS.md #227: common at 5% or more of the active canonicals the rules compare.
THRESHOLD = 0.05

# The groups of the per-signal lines, in the order they print.
SIGNAL_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    ("fields only", frozenset({FIELDS})),
    ("phone only", frozenset({PHONE})),
    ("fields and phone", frozenset({FIELDS, PHONE})),
    ("agent-number sample", frozenset({AGENT_PHONE_SAMPLE})),
)


class PairVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text_sha256: tuple[str, str]
    found_by: list[Literal["fields", "phone", "agent_phone_sample"]]
    verdict: Literal["same_listing", "same_apartment_other_listing", "different", "not_sure"]
    note: str

    @field_validator("found_by")
    @classmethod
    def _some_signal(cls, value: list[str]) -> list[str]:
        if not value or len(set(value)) != len(value):
            raise ValueError("found_by is a non-empty set of signals")
        return value


class VerdictFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    exported_at: datetime
    rules_version: str
    pairs: dict[str, PairVerdict]

    @field_validator("exported_at")
    @classmethod
    def _require_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def _keys_are_ordered_pairs(self) -> "VerdictFile":
        for key in self.pairs:
            first, bar, second = key.partition("|")
            if not (first and bar and second) or not first < second:
                raise ValueError(f"{key!r}: a pair key is '<smaller listing_id>|<larger>'")
        return self


def _no_repeated_key(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    found: dict[str, Any] = {}
    for key, value in pairs:
        if key in found:
            raise ValueError(f"{key!r} appears twice")
        found[key] = value
    return found


def read_verdicts(path: Path) -> VerdictFile:
    """The export, validated. A repeated pair (the same key twice in the file) is refused, and so
    is any verdict value of the three-verdict draft (`"same"`)."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_no_repeated_key)
    return VerdictFile.model_validate(raw)


def check_against(
    verdicts: VerdictFile, current: Mapping[str, CandidatePair], hashes: Mapping[str, str]
) -> None:
    """Refuse a verdict for a pair the rules do not list now, or for a text that changed since the
    page was made. `hashes` maps listing_id to the SHA-256 of its stored text."""
    for key, verdict in verdicts.pairs.items():
        if key not in current:
            raise ValueError(f"{key[:12]}…: not a candidate pair of this store")
        first, _, second = key.partition("|")
        if (hashes.get(first), hashes.get(second)) != tuple(verdict.text_sha256):
            raise ValueError(f"{key[:12]}…: the text changed since the verdict")


def _group_of(found_by: list[str]) -> str:
    wanted = frozenset(found_by)
    for name, signals in SIGNAL_GROUPS:
        if wanted == signals:
            return name
    raise ValueError(f"found_by {sorted(wanted)} is not a known group of signals")


def _percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def measure(
    verdicts: VerdictFile,
    population: Population,
    listed: int,
    *,
    rules_version: str = RULES_VERSION,
) -> list[str]:
    """The lines `--measure` prints (`PHASE_2.md` 2.10, point 4). Prints a fact, not a decision:
    whether the threshold is reached is Ron's to record."""
    if verdicts.rules_version != rules_version:
        raise ValueError(
            f"the export is for rules version {verdicts.rules_version!r}, not {rules_version!r}"
        )
    members = len(population.members)
    counts = Counter(v.verdict for v in verdicts.pairs.values())
    judged = len(verdicts.pairs)

    def in_pairs(*wanted: str) -> int:
        posts: set[str] = set()
        for key, v in verdicts.pairs.items():
            if v.verdict in wanted:
                posts.update(key.split("|"))
        return len(posts)

    low, high = counts[SAME_LISTING], counts[SAME_LISTING] + counts[NOT_SURE]
    lower_posts, upper_posts = in_pairs(SAME_LISTING), in_pairs(SAME_LISTING, NOT_SURE)
    needed = math.ceil(THRESHOLD * members - 1e-9)
    lines = [
        f"pairs judged: {judged} of {listed} listed",
        "  " + ", ".join(f"{name} {counts[name]}" for name in VERDICTS),
        f"active canonicals compared: {members}; the posts span {population.span_hours:.1f} hours",
        "rewritten reposts (same_listing only):",
        f"  pairs / active canonicals: {low} / {members} = {_percent(low, members)}"
        f" (not_sure read as different); up to {high} / {members} = {_percent(high, members)}"
        " (not_sure read as same_listing)",
        f"  active canonicals in at least one such pair: {lower_posts} of {members}"
        f" = {_percent(lower_posts, members)}; up to"
        f" {upper_posts} = {_percent(upper_posts, members)}",
        f"  threshold {THRESHOLD:.0%} (#227) = {needed} pairs of {members}:"
        f" lower figure {'reaches' if low >= needed else 'does not reach'} it,"
        f" upper figure {'reaches' if high >= needed else 'does not reach'} it",
        f"same apartment, another listing (not counted above): {counts[SAME_APARTMENT]} pairs"
        f" / {members} = {_percent(counts[SAME_APARTMENT], members)}",
        "by signal (judged pairs: same_listing / same_apartment_other_listing / different /"
        " not_sure; share that is same_listing):",
    ]
    groups: dict[str, Counter[str]] = {name: Counter() for name, _ in SIGNAL_GROUPS}
    for v in verdicts.pairs.values():
        groups[_group_of(list(v.found_by))][v.verdict] += 1
    for name, _ in SIGNAL_GROUPS:
        group = groups[name]
        total = sum(group.values())
        lines.append(
            f"  {name}: {total} judged: "
            + " / ".join(str(group[verdict]) for verdict in VERDICTS)
            + f"; {_percent(group[SAME_LISTING], total)}"
        )
    duplicates = population.duplicates
    lines.append(
        f"for scale, dedup A's exact-hash duplicates: {duplicates} of {population.total_posts}"
        f" stored posts = {_percent(duplicates, population.total_posts)}"
    )
    lines.append(
        f"a lower bound: the window is {population.span_hours:.1f} hours of posts, and the rules"
        " miss a repost with a changed price and no shared number, and posts missing a price,"
        " rooms or an area"
    )
    return lines
