"""The regression set's comparison (`PHASE_2.md` 2.6; DECISIONS.md #142, #177, #190–#193, #196,
#198; `areas` is measured by reach, at 90%):
the truth of each post, the model's answer compared field by field, and each pass judged against
the bar on its own. A plain module: no call, no storage.

The truth of a post:
- **Blind** (`truth: "blind"`): the deciding fields from Ron's label, after `label_overrides.json`,
  completed with the classifier's own rules (the native price, the entry date's year). The other
  fields from the reviewed, corrected classification, when Ron reviewed the post (#193).
- **Review** (`truth: "review"`): every field from the corrected classification (#195).
- A post labelled with a nature in `nature_only` is compared on `post_nature` only (#196). So is a
  review post whose corrected classification has one of those natures (#239).
- A post whose truth says the apartment is in another city (`other_city` not null), blind or from
  the review, is compared on `post_nature` and `other_city` only (#240).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from tlv_hunter.classify.complete import entry_date_from_parts, price_with_fallback
from tlv_hunter.contracts.listing import Listing, Marked
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.labeling.labels import PostLabel
from tlv_hunter.labeling.regression_set import RegressionEntry

DECIDING = ("post_nature", "apartment_kind", "price", "gender", "entry_date", "areas", "other_city")
# Every other field, measured from the review (#193). Not compared: the provenance,
# `price_source` (code's), and the streets and area names as written (#177).
OTHER = (
    "entry_date_written",
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
    "phone_names",
)
FIELDS = DECIDING + OTHER
NO_ERROR = frozenset({"post_nature", "other_city"})
OTHER_CITY_FIELDS = (
    "post_nature",
    "other_city",
)  # all that is compared on an other-city post (#240)
BAR_95 = frozenset({"apartment_kind", "price", "gender"})
BAR_OTHER = 0.90  # every other field, and `areas` by reach (#198)


def bar(name: str) -> float:
    if name in NO_ERROR:
        return 1.0
    return 0.95 if name in BAR_95 else BAR_OTHER


@dataclass(frozen=True)
class Truth:
    listing_id: str
    position: int
    values: dict[str, Any]
    """Field name to the true value, in `Listing`'s types. A field absent is not compared."""
    source: str
    """"label", or "review"."""


def blind_truth(
    entry: RegressionEntry,
    position: int,
    post: RawPost,
    label: PostLabel,
    *,
    nature_only: frozenset[str],
    not_compared: set[str],
    reviewed: Listing | None,
) -> Truth:
    """`label` already has the overrides' changes. Raises ValueError naming a compared deciding
    field that is not labelled (#196 point 5)."""
    values: dict[str, Any] = {"post_nature": label.post_nature}
    if label.post_nature not in nature_only:
        values.update(
            apartment_kind=label.apartment_kind,
            price=None
            if label.price is None
            else price_with_fallback(label.price, post.native_price)[0],
            gender=label.gender,
            entry_date=(
                None
                if label.entry_date_parts is None
                else entry_date_from_parts(label.entry_date_parts, post.posted_at.date())
            ),
            areas=label.areas,
            other_city=label.other_city,
        )
        for name in not_compared:
            values.pop(name if name != "entry_date_parts" else "entry_date", None)
        if label.other_city is not None and "other_city" in values:
            values = {name: values[name] for name in OTHER_CITY_FIELDS}  # #240
        elif reviewed is not None:
            values.update({name: getattr(reviewed, name) for name in OTHER})
    blank = sorted(name for name in DECIDING if name in values and values[name] is None)
    blank = [name for name in blank if name != "other_city"]  # null is Tel Aviv-Yafo
    if blank:
        raise ValueError(f"position {position}: not labelled: {', '.join(blank)}")
    return Truth(entry.listing_id, position, values, "label")


def review_truth(
    entry: RegressionEntry,
    position: int,
    corrected: Listing,
    nature_only: frozenset[str] = frozenset(),
    excluded: frozenset[str] = frozenset(),
) -> Truth:
    """Every field of the corrected classification; only `post_nature` when its nature is one of
    `nature_only` (#239), the same natures and the same field as for a blind post; only
    `post_nature` and `other_city` when the corrected `other_city` is not null (#240), unless that
    field is excluded (#216: then the model's value is not a truth)."""
    if corrected.post_nature in nature_only:
        return Truth(entry.listing_id, position, {"post_nature": corrected.post_nature}, "review")
    if corrected.other_city is not None and "other_city" not in excluded:
        values = {name: getattr(corrected, name) for name in OTHER_CITY_FIELDS}
        return Truth(entry.listing_id, position, values, "review")
    values = {name: getattr(corrected, name) for name in FIELDS}
    return Truth(entry.listing_id, position, values, "review")


# --- comparing one field ---


def _key(name: str, value: Any) -> Any:
    """The comparable form: prices and areas as sets (#190, #142), `other_city` as Tel Aviv-Yafo
    or not (#191), phone names as a set."""
    if name == "other_city":
        return value is None
    if name == "areas":
        return frozenset(value)
    if name == "phone_names":
        return frozenset((pair.phone, pair.name) for pair in value)
    if isinstance(value, Marked):
        inner = value.value
        if name == "price" and inner is not None:
            inner = frozenset(inner)
        return (value.state, inner)
    return value


def same(name: str, truth: Any, answer: Any) -> bool:
    return _key(name, truth) == _key(name, answer)


def reaches(truth: list[int], answer: list[int]) -> bool:
    """The `areas` test (#198): the answer and the label share at least one number, or both are
    empty. An empty answer against a labelled area is an error, and so is an area against an empty
    label."""
    if not truth and not answer:
        return True
    return bool(set(truth) & set(answer))


def filled_in(truth: Any, answer: Any) -> bool:
    """A value where the truth says not written (#142)."""
    if isinstance(truth, Marked) and isinstance(answer, Marked):
        return truth.state == "not_written" and answer.state == "written"
    return False


def shown(value: Any) -> str:
    """A value as the report and the log show it: no post text, only the value."""
    if isinstance(value, Marked):
        if value.value is None:
            return value.state
        return shown(value.value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return "[" + ", ".join(shown(item) for item in value) + "]"
    if hasattr(value, "phone"):
        return f"{value.phone} {value.name}"
    if value is None:
        return "null"
    return str(value)


# --- judging a pass ---


@dataclass(frozen=True)
class Mismatch:
    position: int
    listing_id: str
    field: str
    truth: str
    answer: str
    filled_in: bool


@dataclass(frozen=True)
class FieldResult:
    field: str
    counted: int
    errors: int
    bar: float

    @property
    def rate(self) -> float | None:
        return None if not self.counted else 1 - self.errors / self.counted

    @property
    def passed(self) -> bool | None:
        """None when no post measured the field."""
        if not self.counted:
            return None
        if self.bar == 1.0:
            return self.errors == 0
        rate = self.rate
        assert rate is not None
        return rate >= self.bar


@dataclass(frozen=True)
class AreasExact:
    counted: int
    errors: int
    average_returned: float
    average_labelled: float

    @property
    def rate(self) -> float | None:
        return None if not self.counted else 1 - self.errors / self.counted


@dataclass
class PassResult:
    number: int
    fields: list[FieldResult]
    mismatches: list[Mismatch]
    areas_exact: "AreasExact | None" = None
    """Information, not a bar (#198): `areas` by exact match, and the answers' average length."""
    failed_posts: list[int] = field(default_factory=list)
    """Positions whose attempts were spent with no answer: the pass is incomplete."""
    missing_posts: list[int] = field(default_factory=list)
    """Positions never attempted: the run stopped."""

    @property
    def filled_in(self) -> list[Mismatch]:
        return [mismatch for mismatch in self.mismatches if mismatch.filled_in]

    @property
    def not_measured(self) -> list[str]:
        return [result.field for result in self.fields if result.passed is None]

    @property
    def verdict(self) -> str:
        if self.failed_posts or self.missing_posts:
            return "incomplete"
        if self.filled_in or any(result.passed is False for result in self.fields):
            return "fail"
        if self.not_measured:
            return "pass on the measured fields"
        return "pass"


def judge(number: int, truths: Sequence[Truth], answers: dict[str, Listing | None]) -> PassResult:
    """`answers`: per listing_id, the pass's Listing; None when its attempts were spent; absent
    when the run stopped before it."""
    counted = dict.fromkeys(FIELDS, 0)
    errors = dict.fromkeys(FIELDS, 0)
    exact_errors = returned = labelled = 0
    mismatches: list[Mismatch] = []
    failed: list[int] = []
    missing: list[int] = []
    for truth in truths:
        if truth.listing_id not in answers:
            missing.append(truth.position)
            continue
        answer = answers[truth.listing_id]
        if answer is None:
            failed.append(truth.position)
            continue
        for name, true_value in truth.values.items():
            given = getattr(answer, name)
            counted[name] += 1
            if name == "areas":
                returned += len(given)
                labelled += len(true_value)
                exact_errors += not same(name, true_value, given)
                is_error = not reaches(true_value, given)
            else:
                is_error = not same(name, true_value, given)
            if is_error:
                errors[name] += 1
                mismatches.append(
                    Mismatch(
                        truth.position,
                        truth.listing_id,
                        name,
                        shown(true_value),
                        shown(given),
                        filled_in(true_value, given),
                    )
                )
    results = [FieldResult(name, counted[name], errors[name], bar(name)) for name in FIELDS]
    n = counted["areas"]
    exact = AreasExact(n, exact_errors, returned / n if n else 0.0, labelled / n if n else 0.0)
    return PassResult(number, results, mismatches, exact, failed, missing)
