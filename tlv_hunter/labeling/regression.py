"""Everything the regression runner checks and reads before its first call (`PHASE_2.md` 2.6;
DECISIONS.md #186–#196). Free: no call. It refuses with every reason at once: a post with no label,
a compared deciding field left blank, a label or correction whose post text changed, overrides
reviewed against another `labels.json`, a reviewed classification that cannot be found.
A plain module: it reads, and writes nothing.
"""

from dataclasses import dataclass, field
from pathlib import Path

from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.labeling.compare import Truth, blind_truth, review_truth
from tlv_hunter.labeling.corrections import (
    CORRECTIONS_FILE,
    RUNS_DIR,
    CorrectionFile,
    corrected_listing,
    find_reviewed,
    read_corrections,
)
from tlv_hunter.labeling.labels import LABELS_FILE, read_labels
from tlv_hunter.labeling.overrides import OVERRIDES_FILE, Overrides, file_sha256, read_overrides
from tlv_hunter.labeling.regression_set import (
    LABELING_DIR,
    REGRESSION_SET_FILE,
    load_regression_set,
    regression_posts,
)
from tlv_hunter.store.base import Repository


@dataclass
class Prepared:
    posts: list[RawPost] = field(default_factory=list)
    """The posts to classify, in set order: one per truth."""
    truths: list[Truth] = field(default_factory=list)
    positions: dict[str, int] = field(default_factory=dict)
    removed: list[int] = field(default_factory=list)
    ambiguous: list[int] = field(default_factory=list)
    """Marked ambiguous by Ron: not counted, not classified (#142)."""
    overrides: Overrides | None = None
    labels_sha256: str | None = None
    refusals: list[str] = field(default_factory=list)


def prepare(repo_root: Path, store: Repository) -> Prepared:
    labeling = repo_root / LABELING_DIR
    prepared = Prepared()
    regression_set = load_regression_set(labeling / REGRESSION_SET_FILE)
    entries = regression_set.posts
    labels_path = labeling / LABELS_FILE
    try:
        labels = read_labels(labels_path)
    except FileNotFoundError as error:
        prepared.refusals.append(str(error))
        return prepared
    prepared.labels_sha256 = file_sha256(labels_path)

    overrides_path = labeling / OVERRIDES_FILE
    overrides = read_overrides(overrides_path) if overrides_path.is_file() else None
    prepared.overrides = overrides
    if overrides is not None:
        if overrides.labels_sha256 != prepared.labels_sha256:
            prepared.refusals.append(
                f"{OVERRIDES_FILE} was reviewed against another {LABELS_FILE}: review it again"
            )
        prepared.refusals.extend(overrides.check_positions(entries))
        if prepared.refusals:
            return prepared
    removed = set() if overrides is None else overrides.removed_ids()
    nature_only = frozenset() if overrides is None else frozenset(overrides.nature_only.natures)
    corrections: CorrectionFile | None = read_corrections(labeling / CORRECTIONS_FILE)
    runs_dir = labeling / RUNS_DIR

    active = [(i, e) for i, e in enumerate(entries, 1) if e.listing_id not in removed]
    prepared.removed = [i for i, e in enumerate(entries, 1) if e.listing_id in removed]
    try:
        posts = regression_posts([e for _, e in active], store, repo_root)
    except (LookupError, ValueError) as error:
        prepared.refusals.append(str(error))
        return prepared
    texts = {post.listing_id: post.text for post in posts}
    for listing_id in labels.stale(texts):
        if listing_id in texts:
            prepared.refusals.append(f"position {_position(entries, listing_id)}: label is stale")
    if corrections is not None:
        for listing_id in corrections.stale(texts):
            prepared.refusals.append(
                f"position {_position(entries, listing_id)}: correction is stale"
            )

    for (position, entry), post in zip(active, posts, strict=True):
        reviewed = None
        correction = None if corrections is None else corrections.reviewed().get(entry.listing_id)
        if correction is not None:
            found = find_reviewed(
                entry.listing_id, correction, store.get_listing(entry.listing_id), runs_dir
            )
            if found is None:
                prepared.refusals.append(
                    f"position {position}: the reviewed classification is not found"
                )
                continue
            reviewed = corrected_listing(found, correction)
        if entry.truth == "review":
            if reviewed is None:
                prepared.refusals.append(f"position {position}: joined from review, no review")
                continue
            truth = review_truth(entry, position, reviewed)
        else:
            label = labels.labels.get(entry.listing_id)
            if label is None:
                prepared.refusals.append(f"position {position}: no label")
                continue
            if label.ambiguous:
                prepared.ambiguous.append(position)
                continue
            if overrides is not None:
                label = overrides.apply(entry.listing_id, label)
            try:
                truth = blind_truth(
                    entry,
                    position,
                    post,
                    label,
                    nature_only=nature_only,
                    not_compared=set()
                    if overrides is None
                    else overrides.not_compared_fields(entry.listing_id),
                    reviewed=reviewed,
                )
            except ValueError as error:
                prepared.refusals.append(str(error))
                continue
        prepared.truths.append(truth)
        prepared.posts.append(post)
        prepared.positions[entry.listing_id] = position
    return prepared


def _position(entries, listing_id: str) -> int:
    return next(i for i, e in enumerate(entries, 1) if e.listing_id == listing_id)
