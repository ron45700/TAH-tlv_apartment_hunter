"""DECISIONS.md #80: a network error waits on a fixed schedule (decision 1), and failed photos of
stored posts are retried from the stored link (decision 2). One test or more per decision, against
local_json and SQLite. No network and no real wait: a fake transport, an injected sleep that moves
a fake clock, and the guards in conftest."""

from datetime import timedelta
from typing import Any

import pytest

from tests.conftest import FETCHED_AT
from tests.test_image_download import (
    OK,
    FakeTransport,
    _failed,
    _held,
    _media,
    _post,
    _record,
    _seed,
)
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_a import DedupResult, dedup_a
from tlv_hunter.images import download
from tlv_hunter.images.download import (
    NETWORK_WAITS_SECS,
    NOT_ATTEMPTED,
    STORED_LINK_MAX_AGE,
    ImageFetchError,
    ImageResponse,
    download_images,
    is_network_error,
)
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.store.base import Repository

DNS = "network: gaierror"
DOWN = ImageFetchError(DNS)
FORBIDDEN = ImageResponse(403, "text/html", b"")
# The run's start: one hour after the test posts were first fetched.
NOW = FETCHED_AT + timedelta(hours=1)


class Clock:
    """The download step's monotonic clock; only the injected sleep moves it."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class Sleep:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.now += seconds


@pytest.fixture
def repo(make_repository) -> Repository:
    return make_repository()


@pytest.fixture
def base(posts: list[RawPost]) -> RawPost:
    return next(p for p in posts if p.text_source == "text" and not p.no_text)


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def sleep(clock: Clock) -> Sleep:
    return Sleep(clock)


def _go(
    repo: Repository,
    batch: list[RawPost],
    tmp_path,
    transport: FakeTransport,
    clock: Clock,
    sleep: Sleep,
    **kwargs: Any,
) -> DedupResult:
    return download_images(
        dedup_a(batch, repo),
        repo,
        tmp_path,
        transport,
        clock=clock,
        sleep=sleep,
        **{"now": NOW, **kwargs},
    )


def _errors(result: DedupResult, post: RawPost) -> list[str | None]:
    return [image.error for image in _record(result, post).images]


# --- decision 1: what counts as a network error (U1) -------------------------------------------


@pytest.mark.parametrize(
    ("reason", "network"),
    [
        ("network: gaierror", True),
        ("network: ConnectionResetError", True),
        ("network: RemoteDisconnected", True),
        ("timeout", True),  # U1: the socket timeout and the 60 s cap alike
        ("http 403", False),
        ("http 500", False),
        ("not an image: text/html", False),
        ("empty body", False),
        ("unrecognized bytes", False),
        ("too large", False),
        (NOT_ATTEMPTED, False),
        (None, False),
    ],
)
def test_which_errors_are_network_errors(reason, network) -> None:
    assert is_network_error(reason) is network


# --- decision 1: the schedule -------------------------------------------------------------------


def test_the_schedule_is_ron_s(clock) -> None:
    assert NETWORK_WAITS_SECS == (60, 180, 300, 600)


def test_a_network_error_waits_a_minute_and_tries_the_same_photo(
    repo, base, tmp_path, clock, sleep
) -> None:
    post = _post(base, "1", [_media("p1"), _media("p2")])
    transport = FakeTransport({"p1": [DOWN, OK]})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [60]
    assert transport.calls == ["p1", "p1", "p2"]
    assert _errors(result, post) == [None, None]


def test_the_waits_follow_the_schedule(repo, base, tmp_path, clock, sleep) -> None:
    post = _post(base, "1", [_media("p1")])
    transport = FakeTransport({"p1": [DOWN, DOWN, DOWN, DOWN, OK]})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [60, 180, 300, 600]
    assert transport.calls == ["p1"] * 5
    assert _errors(result, post) == [None]


def test_a_timeout_waits_like_a_network_error(repo, base, tmp_path, clock, sleep) -> None:
    post = _post(base, "1", [_media("p1")])
    transport = FakeTransport({"p1": [ImageFetchError("timeout"), OK]})
    _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [60]


def test_a_network_error_gets_no_second_pass(repo, base, tmp_path, clock, sleep) -> None:
    # #63's one retry within a run is for other errors; the schedule replaces it (#80).
    post = _post(base, "1", [_media("p1"), _media("p2")])
    transport = FakeTransport({"p1": [DOWN] * 5})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert transport.calls == ["p1"] * 5 + ["p2"]
    assert _errors(result, post) == [DNS, None]


def test_after_the_schedule_each_remaining_photo_is_tried_once_without_waiting(
    repo, base, tmp_path, clock, sleep
) -> None:
    # U3. No entry claims an attempt that never happened (U2: no "not attempted" here).
    post = _post(base, "1", [_media("p1"), _media("p2"), _media("p3")])
    transport = FakeTransport({media: [DOWN] for media in ("p1", "p2", "p3")})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == list(NETWORK_WAITS_SECS)
    assert transport.calls == ["p1"] * 5 + ["p2", "p3"]
    assert _errors(result, post) == [DNS, DNS, DNS]


@pytest.mark.parametrize("reply", [OK, FORBIDDEN])
def test_any_reply_restarts_the_schedule(repo, base, tmp_path, clock, sleep, reply) -> None:
    # Ron, 2026-10-04: an HTTP error is a reply, so the network is up again.
    post = _post(base, "1", [_media("p1"), _media("p2"), _media("p3")])
    transport = FakeTransport({"p1": [DOWN], "p2": [reply], "p3": [DOWN, OK]})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [*NETWORK_WAITS_SECS, 60]
    assert _errors(result, post)[2] is None


def test_a_later_outage_starts_the_schedule_from_one_minute(
    repo, base, tmp_path, clock, sleep
) -> None:
    post = _post(base, "1", [_media("p1"), _media("p2"), _media("p3")])
    transport = FakeTransport({"p1": [DOWN, DOWN, OK], "p3": [DOWN, OK]})
    _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [60, 180, 60]


# --- §4: the waits count inside the budget ------------------------------------------------------


def test_a_wait_stops_when_the_budget_runs_out(
    repo, base, tmp_path, clock, sleep, monkeypatch
) -> None:
    monkeypatch.setattr(download, "TIME_BUDGET_SECS", 100)
    post = _post(base, "1", [_media("p1"), _media("p2")])
    transport = FakeTransport({"p1": [DOWN]})
    result = _go(repo, [post], tmp_path, transport, clock, sleep)
    assert sleep.calls == [60, 40]  # the second wait is cut at the budget
    assert transport.calls == ["p1", "p1"]
    assert _errors(result, post) == [DNS, NOT_ATTEMPTED]


# --- decision 2: retries from the stored link ---------------------------------------------------


def _stored(repo: Repository, base: RawPost, error: str, media_id: str = "p1") -> RawPost:
    post = _post(base, "1", [_media(media_id)])
    return _seed(repo, post, images=[_failed(post.listing_id, media_id, error)])


def _retry(repo, tmp_path, transport, clock, sleep, **kwargs: Any) -> DedupResult:
    """A run whose batch holds nothing new: only the stored links."""
    return _go(repo, [], tmp_path, transport, clock, sleep, **kwargs)


@pytest.mark.parametrize("error", [DNS, "network: ConnectionResetError", "timeout", NOT_ATTEMPTED])
def test_a_stored_failure_is_retried_from_the_stored_link(
    repo, base, tmp_path, clock, sleep, error
) -> None:
    post = _stored(repo, base, error)
    transport = FakeTransport()
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == ["p1"]
    # Returned at the end, for the store step to save first (#79 O2).
    assert result.lifecycles[-1].listing_id == post.listing_id
    assert result.lifecycles[-1].images[0].local_path is not None


def test_every_retried_photo_of_a_stored_post_is_kept(repo, base, tmp_path, clock, sleep) -> None:
    # Run A's 53 posts have several photos each; each retry result must reach the store step.
    post = _post(base, "1", [_media("p1"), _media("p2"), _media("p3")])
    _seed(repo, post, images=[_failed(post.listing_id, m, DNS) for m in ("p1", "p2", "p3")])
    transport = FakeTransport({"p2": [FORBIDDEN]})
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert [image.error for image in result.lifecycles[-1].images] == [None, "http 403", None]
    assert len(result.lifecycles) == 1


@pytest.mark.parametrize(
    "error", ["http 403", "http 500", "not an image: text/html", "empty body", "too large"]
)
def test_other_failures_are_not_retried_from_the_stored_link(
    repo, base, tmp_path, clock, sleep, error
) -> None:
    _stored(repo, base, error)
    transport = FakeTransport()
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == [] and result.lifecycles == ()


def test_an_http_error_replaces_the_entry_and_ends_the_retries(
    repo, base, tmp_path, clock, sleep
) -> None:
    post = _stored(repo, base, DNS)
    transport = FakeTransport({"p1": [FORBIDDEN]})
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert result.lifecycles[-1].images == [_failed(post.listing_id, "p1", "http 403")]
    repo.save_lifecycle(result.lifecycles[-1])

    _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == ["p1"]


def test_a_network_error_on_a_stored_retry_does_not_wait_and_the_entry_stays(
    repo, base, tmp_path, clock, sleep
) -> None:
    # U4: one attempt per run, never a wait.
    post = _stored(repo, base, DNS)
    transport = FakeTransport({"p1": [DOWN]})
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert sleep.calls == []
    assert transport.calls == ["p1"]
    assert result.lifecycles[-1].images == [_failed(post.listing_id, "p1", DNS)]


@pytest.mark.parametrize(
    ("age", "retried"),
    [(timedelta(days=4), False), (timedelta(days=4) - timedelta(seconds=1), True)],
)
def test_a_stored_link_is_retried_only_while_the_post_is_less_than_four_days_old(
    repo, base, tmp_path, clock, sleep, age, retried
) -> None:
    # U5: the post's first fetched_at, against the run's start.
    assert STORED_LINK_MAX_AGE == timedelta(days=4)
    _stored(repo, base, DNS)
    transport = FakeTransport()
    _retry(repo, tmp_path, transport, clock, sleep, now=FETCHED_AT + age)
    assert transport.calls == (["p1"] if retried else [])


def test_a_photo_gone_from_the_stored_post_is_skipped_and_its_entry_left(
    repo, base, tmp_path, clock, sleep
) -> None:
    # U6: the stored post (edited, fetched again) no longer has p1; #77 D5d kept its entry.
    post = _post(base, "1", [_media("p2")])
    _seed(repo, post, images=[_failed(post.listing_id, "p1", DNS)])
    transport = FakeTransport()
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == [] and result.lifecycles == ()


def test_an_archived_post_is_not_retried(repo, base, tmp_path, clock, sleep) -> None:
    post = _post(base, "1", [_media("p1")])
    _seed(repo, post, state="archived", images=[_failed(post.listing_id, "p1", DNS)])
    transport = FakeTransport()
    _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == []


def test_a_rejected_canonical_is_retried(repo, base, tmp_path, clock, sleep) -> None:
    # #76: photos for every canonical, whatever its state.
    post = _post(base, "1", [_media("p1")])
    _seed(
        repo,
        post,
        state="rejected",
        rejection_reason="other_city",
        images=[_failed(post.listing_id, "p1", DNS)],
    )
    transport = FakeTransport()
    _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == ["p1"]


def test_retries_come_after_the_batch(repo, base, tmp_path, clock, sleep) -> None:
    _stored(repo, base, DNS, media_id="old")
    fresh = _post(base, "2", [_media("new")]).with_changes(text=base.text + " (2)")
    from tlv_hunter.textnorm.annotate import annotate

    transport = FakeTransport()
    _go(repo, [annotate(fresh)], tmp_path, transport, clock, sleep)
    assert transport.calls == ["new", "old"]


def test_a_post_in_the_batch_is_retried_once_by_the_batch_path(
    repo, base, tmp_path, clock, sleep
) -> None:
    post = _stored(repo, base, DNS)
    transport = FakeTransport({"p1": [FORBIDDEN]})
    _go(repo, [post], tmp_path, transport, clock, sleep)
    # The batch path: one attempt and #63's one retry for an HTTP error; no stored-link retry.
    assert transport.calls == ["p1", "p1"]


def test_a_stored_retry_past_the_budget_leaves_the_entry(
    repo, base, tmp_path, clock, sleep, monkeypatch
) -> None:
    monkeypatch.setattr(download, "TIME_BUDGET_SECS", 0)
    _stored(repo, base, DNS)
    transport = FakeTransport()
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == [] and result.lifecycles == ()


# --- decision 2 and the repost rules (#72.3, #77 D2, D3; U7) ------------------------------------


def _with_reposts(repo: Repository, base: RawPost, own: bool) -> tuple[RawPost, list[RawPost]]:
    """A stored canonical with no image held, and two stored reposts whose photos failed."""
    canonical = _post(base, "1", [_media("c1")] if own else [])
    later = _post(base, "3", [_media("r3")], minutes=20)
    earlier = _post(base, "2", [_media("r2")], minutes=10)
    images = [_failed(earlier.listing_id, "r2", DNS), _failed(later.listing_id, "r3", DNS)]
    if own:
        images.insert(0, _failed(canonical.listing_id, "c1", DNS))
    stored = _seed(repo, canonical, images=images)
    for repost in (later, earlier):
        duplicate = repost.with_changes(is_canonical=False, duplicate_of=stored.listing_id)
        repo.upsert_with_lifecycle(duplicate, initial_lifecycle(duplicate))
    return stored, [earlier, later]


def test_a_canonical_s_own_photo_first_then_its_reposts_stay(
    repo, base, tmp_path, clock, sleep
) -> None:
    # U7: once the canonical holds an image, its reposts' failed photos keep their error.
    canonical, _ = _with_reposts(repo, base, own=True)
    transport = FakeTransport()
    result = _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == ["c1"]
    assert [image.error for image in _record(result, canonical).images] == [None, DNS, DNS]


def test_reposts_are_retried_in_canonical_order_while_the_canonical_holds_nothing(
    repo, base, tmp_path, clock, sleep
) -> None:
    canonical, (earlier, later) = _with_reposts(repo, base, own=False)
    transport = FakeTransport({"r2": [FORBIDDEN]})
    result = _retry(repo, tmp_path, transport, clock, sleep)
    # The earlier repost first (#77 D3); it fails, so the later one is tried and holds.
    assert transport.calls == ["r2", "r3"]
    assert [image.error for image in _record(result, canonical).images] == ["http 403", None]


def test_a_held_canonical_s_repost_failures_are_never_tried(
    repo, base, tmp_path, clock, sleep
) -> None:
    canonical = _post(base, "1", [_media("c1")])
    repost = _post(base, "2", [_media("r2")], minutes=10)
    stored = _seed(
        repo,
        canonical,
        images=[_held(canonical.listing_id, "c1"), _failed(repost.listing_id, "r2", DNS)],
    )
    duplicate = repost.with_changes(is_canonical=False, duplicate_of=stored.listing_id)
    repo.upsert_with_lifecycle(duplicate, initial_lifecycle(duplicate))
    transport = FakeTransport()
    _retry(repo, tmp_path, transport, clock, sleep)
    assert transport.calls == []
