"""One run of the classification job (`PHASE_2.md` 2.5): the pending canonicals, one at a time, each
result written as it comes. Wiring, like `pipeline.py`, plus one table of data: the attempts per
failure kind (DECISIONS.md #139, #182). The source text is never written (invariant 14): nothing
here calls a method that writes a `RawPost`.
"""

import logging
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from tlv_hunter.classify.base import ClassificationError, ErrorKind
from tlv_hunter.classify.complete import Completed
from tlv_hunter.classify.cost import CallRecord, CapReached, CostMeter
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.postmodel.rejects import classified_lifecycle, failed_lifecycle
from tlv_hunter.store.base import Repository

logger = logging.getLogger(__name__)

# The attempts in one run, per failure kind; then the post counts one failed run (#182).
ATTEMPTS: dict[ErrorKind, int] = {
    "network": 3,
    "timeout": 3,
    "rate_limit": 3,
    "server": 3,
    "invalid": 2,
    "incomplete": 2,
    "refusal": 1,
}
# These stop the job, and the post is not counted: every post would fail the same way.
STOP_KINDS: frozenset[ErrorKind] = frozenset(
    {"spend_limit", "quota", "auth", "bad_request", "not_found"}
)
# The waits before the second and third attempt of a transient failure, in seconds.
WAITS = (2.0, 10.0)
MAX_RETRY_AFTER = 60.0
FAILED_RUNS_TO_SKIP = 3  # #139
ERROR_TEXT_LIMIT = 200


class CompletingClassifier(Protocol):
    def classify_completed(self, post: RawPost) -> Completed: ...


@dataclass(frozen=True)
class PostOutcome:
    listing_id: str
    outcome: str
    """`active`, `rejected: <reason>`, `failed: <kind>` or `discarded`."""
    attempts: int
    calls: tuple[CallRecord, ...]


@dataclass(frozen=True)
class ClassifyRunResult:
    found: int
    skipped: tuple[str, ...]
    """Pending canonicals left out at three failed runs."""
    outcomes: tuple[PostOutcome, ...]
    stopped: str | None
    """Why the run stopped before the end, or None."""
    spent: float


def classify_pending(
    *,
    repository: Repository,
    classifier: CompletingClassifier,
    meter: CostMeter,
    sleep: Callable[[float], None],
    limit: int | None = None,
    on_written: Callable[[Completed], None] | None = None,
) -> ClassifyRunResult:
    """`on_written` receives each result after it is stored: the record of dropped names."""
    found = repository.find_pending_canonicals()
    eligible: list[RawPost] = []
    skipped: list[str] = []
    for post in found:
        record = repository.get_lifecycle(post.listing_id)
        if record is not None and record.classification_failures >= FAILED_RUNS_TO_SKIP:
            skipped.append(post.listing_id)
        else:
            eligible.append(post)
    if limit is not None:
        eligible = eligible[:limit]
    logger.info(
        "classification start: %d pending canonicals, %d skipped at %d failed runs, %d to "
        "classify, cap $%.2f",
        len(found),
        len(skipped),
        FAILED_RUNS_TO_SKIP,
        len(eligible),
        meter.cap,
    )

    outcomes: list[PostOutcome] = []
    stopped: str | None = None
    for post in eligible:
        first_call = len(meter.calls)
        try:
            outcome, attempts = _classify_one(post, repository, classifier, sleep, on_written)
        except RunStop as stop:
            stopped = stop.reason
            logger.warning("classification stopped before %s: %s", post.listing_id, stop.reason)
            break
        result = PostOutcome(post.listing_id, outcome, attempts, tuple(meter.calls[first_call:]))
        outcomes.append(result)
        _log_post(result)

    _log_end(len(found), skipped, outcomes, stopped, meter)
    return ClassifyRunResult(
        found=len(found),
        skipped=tuple(skipped),
        outcomes=tuple(outcomes),
        stopped=stopped,
        spent=meter.spent,
    )


class RunStop(Exception):
    """The run stops before this post, which is not counted: the cap, or a failure every post would
    share (`STOP_KINDS`)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def attempt_post(
    post: RawPost, classifier: CompletingClassifier, sleep: Callable[[float], None]
) -> tuple[Completed | ClassificationError, int]:
    """The attempts of one post in one run, by the table above (#182): the completed answer, or the
    last error once the attempts are spent, and the number of attempts. Writes nothing; raises
    RunStop. Shared by this job and the regression runner (`PHASE_2.md` 2.6)."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return classifier.classify_completed(post), attempts
        except CapReached as error:
            raise RunStop(f"cap: {error}") from error
        except ClassificationError as error:
            if error.kind in STOP_KINDS:
                raise RunStop(str(error)) from error
            wait = _wait_before_next(error, attempts)
            if wait is None:
                return error, attempts
            if wait:
                sleep(wait)


def _classify_one(
    post: RawPost,
    repository: Repository,
    classifier: CompletingClassifier,
    sleep: Callable[[float], None],
    on_written: Callable[[Completed], None] | None,
) -> tuple[str, int]:
    result, attempts = attempt_post(post, classifier, sleep)
    if isinstance(result, ClassificationError):
        return _save_failure(post, repository, result), attempts
    return _save_success(post, repository, result, on_written), attempts


def _wait_before_next(error: ClassificationError, attempts: int) -> float | None:
    """Seconds to wait before another attempt, or None when this run's attempts are spent."""
    if attempts >= ATTEMPTS[error.kind]:
        return None
    if error.kind not in ("network", "timeout", "rate_limit", "server"):
        return 0.0
    wait = WAITS[attempts - 1]
    if error.retry_after is not None:
        if error.retry_after > MAX_RETRY_AFTER:
            return None
        wait = max(wait, error.retry_after)
    return wait


def _save_success(
    post: RawPost,
    repository: Repository,
    completed: Completed,
    on_written: Callable[[Completed], None] | None,
) -> str:
    # Read again right before the write: the record may have changed during the call (#182).
    fresh = repository.get_lifecycle(post.listing_id)
    if fresh is None or fresh.state != "pending":
        return "discarded"
    lifecycle = classified_lifecycle(fresh, completed.listing)
    repository.save_classification(completed.listing, lifecycle)
    if on_written is not None:
        on_written(completed)
    if lifecycle.rejection_reason is None:
        return lifecycle.state
    return f"{lifecycle.state}: {lifecycle.rejection_reason}"


def _save_failure(post: RawPost, repository: Repository, error: ClassificationError) -> str:
    fresh = repository.get_lifecycle(post.listing_id)
    if fresh is None or fresh.state != "pending":
        return "discarded"
    repository.save_lifecycle(failed_lifecycle(fresh, str(error)[:ERROR_TEXT_LIMIT]))
    return f"failed: {error.kind}"


def _log_post(result: PostOutcome) -> None:
    """No post text, name, phone or key: counts, kinds and identifiers only."""
    calls = result.calls
    logger.info(
        "post %s: %s, %d attempts, %d calls, tokens %s, $%.6f, reported model %s, %.1f s, "
        "dropped %d streets, %d area names, %d other city",
        result.listing_id,
        result.outcome,
        result.attempts,
        len(calls),
        _tokens(calls),
        sum(call.cost for call in calls),
        ",".join(sorted({str(call.reported_model) for call in calls})) or "-",
        sum(call.seconds for call in calls),
        sum(len(call.dropped_streets) for call in calls),
        sum(len(call.dropped_area_names) for call in calls),
        sum(call.dropped_other_city is not None for call in calls),
    )


def _log_end(
    found: int,
    skipped: Sequence[str],
    outcomes: Sequence[PostOutcome],
    stopped: str | None,
    meter: CostMeter,
) -> None:
    logger.info(
        "classification done: %d found, %d skipped, %d attempted, outcomes %s, %d calls, "
        "tokens %s, $%.6f of $%.2f, reported models %s, stopped %s",
        found,
        len(skipped),
        len(outcomes),
        dict(sorted(Counter(outcome.outcome for outcome in outcomes).items())),
        len(meter.calls),
        _tokens(meter.calls),
        meter.spent,
        meter.cap,
        ",".join(sorted({str(call.reported_model) for call in meter.calls})) or "-",
        stopped or "no",
    )


def _tokens(calls: Sequence[CallRecord]) -> dict[str, int]:
    return {
        "input": sum(call.usage.input_tokens for call in calls),
        "cached": sum(call.usage.cached_tokens for call in calls),
        "cache_write": sum(call.usage.cache_write_tokens for call in calls),
        "output": sum(call.usage.output_tokens for call in calls),
        "reasoning": sum(call.usage.reasoning_tokens for call in calls),
    }
