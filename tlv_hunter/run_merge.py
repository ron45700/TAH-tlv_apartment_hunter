"""A collection run's lifecycle change, merged into a record another writer changed (task 3.4).

A plain module: pure functions, no storage (like `premodel/rejects.py`). The run reads a record in
dedup and writes it after the image download, up to 30 minutes later (#77 D5b); meanwhile the site
may have flagged or reported the post, or the admin restored or retried it. The store refuses the
stale write (#260); the run then merges by DECISIONS.md #289, point 2:

- the site's fields come from the fresh record: `flagged_by`, `flagged_at`, `flag_note`,
  `classification_failures`, `last_classification_error`, and a `"flagged"` or `"misclassified"`
  state and reason;
- the run's fields come from the run's record: `last_published_at`, `images`, and a state change
  the run made (a repost of an archived post, #74; the pre-model re-check, #72.1);
- when both changed the state, the flag or report wins.
"""

from typing import Any

from tlv_hunter.contracts.post_lifecycle import USER_REASONS, PostLifecycle
from tlv_hunter.store.base import StaleRecordError

_SITE_FIELDS = (
    "flagged_by",
    "flagged_at",
    "flag_note",
    "classification_failures",
    "last_classification_error",
)


def merge_run_record(
    read: PostLifecycle, run: PostLifecycle, fresh: PostLifecycle
) -> PostLifecycle:
    """The record to write over `fresh`. `read` is what the run read, `run` what it would write.

    Raises `StaleRecordError` when the two changes cannot both stand: the run and the site both
    changed the state and the fresh record carries no flag or report (for example the admin
    restored a post that a repost brought back from archive). The run then fails and moves no
    watermark (invariant 2); the next run reads the new record.
    """
    if not read.listing_id == run.listing_id == fresh.listing_id:
        raise ValueError("the three records belong to different posts")
    site: dict[str, Any] = {field: getattr(fresh, field) for field in _SITE_FIELDS}
    run_changed = _status(run) != _status(read)
    site_changed = _status(fresh) != _status(read)
    if fresh.rejection_reason in USER_REASONS or not run_changed:
        state, reason = _status(fresh)
    elif not site_changed:
        state, reason = _status(run)
    else:
        raise StaleRecordError(run.listing_id)
    return PostLifecycle(**{**dict(run), **site, "state": state, "rejection_reason": reason})


def _status(record: PostLifecycle) -> tuple[str, str | None]:
    return record.state, record.rejection_reason
