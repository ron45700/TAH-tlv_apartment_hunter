"""Task 1.3: dedup stage A and the lifecycle changes of a repost (DECISIONS.md #70, #72, #74,
#75). Every test runs against local_json and SQLite (make_repository). No network."""

import random
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import FETCHED_AT, KNOWN_DUPLICATE_PAIRS, load_spike_1_1a
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import Media, RawPost
from tlv_hunter.dedup.stage_a import DedupResult, dedup_a
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.textnorm.annotate import annotate

MakeRepository = Callable[[], Repository]
FLAG = {"flagged_by": "ron", "flagged_at": datetime(2026, 10, 4, 9, 0, tzinfo=UTC)}
VIDEO = Media(
    type="Video",
    uri="https://video.invalid/v",
    width=None,
    height=None,
    media_id="v1",
    page_url="https://www.facebook.com/videos/1",
)


def _map(items: list[dict[str, Any]]) -> list[RawPost]:
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in items]


@pytest.fixture
def repo(make_repository: MakeRepository) -> Repository:
    return make_repository()


def _store(repo: Repository, result: DedupResult) -> None:
    """What the 1.14 store step will do; here only so a second run has history to read."""
    for post in result.posts:
        repo.upsert(post)
    for record in result.lifecycles:
        repo.save_lifecycle(record)


def _run(repo: Repository, batch: list[RawPost]) -> DedupResult:
    result = dedup_a(batch, repo)
    _store(repo, result)
    return result


def _outcome(posts) -> set[tuple[str, bool, str | None]]:
    return {(post.source_post_id, post.is_canonical, post.duplicate_of) for post in posts}


def _record(result: DedupResult, post: RawPost) -> PostLifecycle:
    return next(r for r in result.lifecycles if r.listing_id == post.listing_id)


def _other(post: RawPost, source_post_id: str, **changes: Any) -> RawPost:
    """Another Facebook post with this post's content: a repost."""
    return post.with_changes(
        source_post_id=source_post_id, listing_id=compute_listing_id(source_post_id), **changes
    )


def _with_text(post: RawPost, text: str) -> RawPost:
    assert post.text_source != "shared_post"
    return annotate(
        post.with_changes(
            text=text,
            text_source="text" if text.strip() else "none",
            no_text=None,
            text_hash=None,
            phones=None,
        )
    )


def _pair(posts: list[RawPost]) -> tuple[RawPost, RawPost]:
    """A known pair, earlier first; both carry their own text and media."""
    by_id = {post.source_post_id: post for post in posts}
    for pair in sorted(KNOWN_DUPLICATE_PAIRS, key=sorted):
        first, second = sorted((by_id[i] for i in pair), key=lambda p: p.posted_at)
        if first.text_source == second.text_source == "text" and first.media and second.media:
            return first, second
    raise AssertionError("no usable pair")


def _seed(repo: Repository, post: RawPost, **lifecycle: Any) -> RawPost:
    """Store a post as an earlier run would have, with a lifecycle record of the given state."""
    stored = post.with_changes(is_canonical=True, duplicate_of=None)
    record = PostLifecycle(**{**dict(initial_lifecycle(stored)), **lifecycle})
    repo.upsert_with_lifecycle(stored, record)
    return stored


# --- the canonical set ---


def test_twenty_posts_in_random_order_give_the_same_canonical_set(
    make_repository: MakeRepository, posts
) -> None:
    expected = _outcome(dedup_a(posts, make_repository()).posts)
    for seed in range(50):
        shuffled = random.Random(seed).sample(posts, len(posts))
        assert _outcome(dedup_a(shuffled, make_repository()).posts) == expected
    assert sum(canonical for _, canonical, _ in expected) == 17


def test_the_three_known_pairs_point_at_the_earlier_post(repo, posts) -> None:
    result = {post.source_post_id: post for post in dedup_a(posts, repo).posts}
    for pair in KNOWN_DUPLICATE_PAIRS:
        earlier, later = sorted((result[i] for i in pair), key=lambda p: p.posted_at)
        assert (earlier.is_canonical, earlier.duplicate_of) == (True, None)
        assert (later.is_canonical, later.duplicate_of) == (False, earlier.listing_id)
    paired = set().union(*KNOWN_DUPLICATE_PAIRS)
    assert all(p.is_canonical for p in result.values() if p.source_post_id not in paired)


def test_history_in_time_order_gives_the_same_result_as_one_batch(
    make_repository: MakeRepository, posts
) -> None:
    one_batch = _outcome(dedup_a(posts, make_repository()).posts)
    repo = make_repository()
    by_time = sorted(posts, key=lambda p: p.posted_at)
    first = _run(repo, by_time[:10]).posts
    second = _run(repo, by_time[10:]).posts
    assert _outcome(first + second) == one_batch


def test_spike_main_then_control(repo, tmp_path) -> None:
    main = _map(load_spike_1_1a())
    control = _map(load_spike_1_1a("_control"))
    first = _run(repo, main)
    stored_before = {p.listing_id: p for p in first.posts}
    records_before = {r.listing_id: r for r in first.lifecycles}

    second = dedup_a(control, repo)
    by_id = {p.listing_id: p for p in second.posts}
    refetched = [p for p in second.posts if p.listing_id in stored_before]
    new = [p for p in second.posts if p.listing_id not in stored_before]
    assert (len(refetched), len(new)) == (105, 75)

    # Sticky: every main post keeps its result, and its record, except a later publication.
    for post in refetched:
        before = stored_before[post.listing_id]
        assert (post.is_canonical, post.duplicate_of) == (before.is_canonical, before.duplicate_of)
        after = _record(second, post)
        assert after == records_before[post.listing_id].model_copy(
            update={"last_published_at": after.last_published_at}
        )
        assert after.last_published_at >= records_before[post.listing_id].last_published_at

    # Every duplicate points at a canonical; a group points at one post.
    for post in second.posts:
        if not post.is_canonical:
            target = by_id.get(post.duplicate_of) or stored_before[post.duplicate_of]
            assert target.is_canonical
    groups = defaultdict(set)
    for post in second.posts:
        if post.text_hash:
            groups[post.text_hash].add(post.listing_id if post.is_canonical else post.duplicate_of)
    assert all(len(targets) == 1 for targets in groups.values())
    assert Counter(len([p for p in second.posts if p.text_hash == h]) for h in groups)[4] == 1

    # #75 A: the four late, older posts join the stored canonical instead of replacing it.
    stored_hashes = {p.text_hash: p for p in stored_before.values() if p.is_canonical}
    late = [
        p
        for p in new
        if p.text_hash in stored_hashes and p.posted_at < stored_hashes[p.text_hash].posted_at
    ]
    assert len(late) == 4
    for post in late:
        assert (post.is_canonical, post.duplicate_of) == (
            False,
            stored_hashes[post.text_hash].listing_id,
        )
    alone = {p.listing_id: p for p in dedup_a(control, _empty(tmp_path)).posts}
    # Without history, each of these groups would have had another canonical.
    assert not any(alone[stored_hashes[p.text_hash].listing_id].is_canonical for p in late)


def _empty(tmp_path: Path) -> Repository:
    """An empty store beside the one under test, to compare with a run that has no history."""
    return LocalJsonRepository(tmp_path / "alone")


# --- layers 1 and 3 ---


def test_a_post_repeated_in_the_batch_is_kept_once(repo, posts) -> None:
    result = dedup_a([posts[0], posts[0], posts[1]], repo)
    assert [p.listing_id for p in result.posts] == [posts[0].listing_id, posts[1].listing_id]
    assert len(result.lifecycles) == 2


def test_a_refetched_post_is_not_a_duplicate_of_itself(repo, posts, tmp_path) -> None:
    _run(repo, posts)
    again = dedup_a(posts, repo)
    assert _outcome(again.posts) == _outcome(dedup_a(posts, _empty(tmp_path)).posts)


def test_a_phone_only_match_is_not_a_duplicate(repo) -> None:
    main = _map(load_spike_1_1a())
    result = {p.listing_id: p for p in dedup_a(main, repo).posts}
    by_phone = defaultdict(set)
    for post in result.values():
        for phone in post.phones or []:
            by_phone[phone].add(post.listing_id)
    phone_only = 0
    for ids in by_phone.values():
        for a in ids:
            for b in ids:
                if result[a].text_hash != result[b].text_hash:
                    phone_only += 1
                    assert result[a].duplicate_of != b
    assert phone_only > 0


# --- #75 A, D2–D5 ---


def test_a_later_arriving_older_post_becomes_a_duplicate(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [later])
    result = dedup_a([earlier], repo)
    assert (result.posts[0].is_canonical, result.posts[0].duplicate_of) == (
        False,
        later.listing_id,
    )
    assert repo.get_lifecycle(later.listing_id).last_published_at == later.posted_at
    assert len(result.lifecycles) == 1  # the canonical's clock does not move back


def test_a_tie_on_posted_at_goes_to_the_smaller_listing_id(repo, posts) -> None:
    a = posts[0]
    b = _other(a, "999000111")
    result = dedup_a([b, a], repo)
    canonical = min(a.listing_id, b.listing_id)
    assert {p.listing_id: p.is_canonical for p in result.posts} == {
        canonical: True,
        max(a.listing_id, b.listing_id): False,
    }


def test_a_no_text_post_is_its_own_canonical(repo) -> None:
    post = next(p for p in _map(load_spike_1_1a("_control")) if p.no_text)
    result = dedup_a([post], repo)
    assert (result.posts[0].is_canonical, result.posts[0].duplicate_of) == (True, None)
    assert _record(result, post).rejection_reason == "no_text"


def test_two_stored_canonicals_on_one_hash_a_new_post_joins_the_earliest(repo, posts) -> None:
    paired = set().union(*KNOWN_DUPLICATE_PAIRS)
    singles = [p for p in posts if p.source_post_id not in paired and p.text_source == "text"]
    earlier, later = sorted(singles[:2], key=lambda p: p.posted_at)
    _run(repo, [earlier, later])
    # `later` is edited to `earlier`'s text: both are stored canonicals on one hash (sticky).
    _run(repo, [_with_text(later, earlier.text)])
    new = _other(earlier, "999000222", posted_at=later.posted_at + timedelta(hours=1))
    result = dedup_a([new], repo)
    assert result.posts[0].duplicate_of == earlier.listing_id
    assert repo.get(later.listing_id).is_canonical  # stored groups are never merged


def test_a_stored_post_with_no_dedup_result_raises(repo, posts) -> None:
    repo.upsert(posts[0])
    with pytest.raises(ValueError, match="no dedup result"):
        dedup_a([posts[0]], repo)
    with pytest.raises(ValueError, match="no dedup result"):
        dedup_a([_other(posts[0], "999000333")], repo)


# --- §5: sticky results, edited text, #72.2 ---


def test_an_edited_canonical_keeps_its_group(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier, later])
    edited = _with_text(earlier, earlier.text + " עודכן")
    result = dedup_a([edited], repo)
    assert result.posts[0].text_hash != earlier.text_hash
    assert (result.posts[0].is_canonical, result.posts[0].duplicate_of) == (True, None)
    _store(repo, result)
    # A new copy of the old text reaches the canonical through its stored duplicate.
    copy = _other(later, "999000444", posted_at=later.posted_at + timedelta(hours=1))
    assert dedup_a([copy], repo).posts[0].duplicate_of == earlier.listing_id


def test_an_edited_duplicate_keeps_its_canonical(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier, later])
    result = dedup_a([_with_text(later, later.text + " עודכן")], repo)
    assert result.posts[0].duplicate_of == earlier.listing_id


def test_a_no_text_post_that_comes_back_with_text_goes_through_dedup(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier, _with_text(later, "")])
    assert repo.get(later.listing_id).is_canonical
    result = dedup_a([later], repo)
    assert result.posts[0].duplicate_of == earlier.listing_id
    assert _record(result, later).state == "pending"


# --- lifecycle: last_published_at, #70, #72.4, #72.6, #75 D1, F4 ---


def test_a_newer_repost_moves_last_published_at_forward(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier])
    result = dedup_a([later], repo)
    assert _record(result, earlier).last_published_at == later.posted_at
    assert _record(result, later).last_published_at == later.posted_at


def test_an_unchanged_stored_canonical_is_not_returned(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier, later])
    result = dedup_a([later], repo)
    assert [r.listing_id for r in result.lifecycles] == [later.listing_id]


def test_media_through_a_repost_returns_the_canonical_to_pending(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier.with_changes(media=[])])
    assert repo.get_lifecycle(earlier.listing_id).rejection_reason == "no_images"
    result = dedup_a([later], repo)
    assert _record(result, earlier).state == "pending"
    assert _record(result, earlier).rejection_reason is None


def test_a_video_only_repost_returns_the_canonical_to_pending(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier.with_changes(media=[])])
    result = dedup_a([later.with_changes(media=[VIDEO])], repo)
    assert _record(result, earlier).state == "pending"


def test_a_repost_with_no_media_leaves_the_canonical_rejected(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier.with_changes(media=[])])
    result = dedup_a([later.with_changes(media=[])], repo)
    assert _record(result, earlier).rejection_reason == "no_images"


def test_canonical_and_repost_new_in_the_same_run(repo, posts) -> None:
    earlier, later = _pair(posts)
    result = dedup_a([later, earlier.with_changes(media=[])], repo)
    assert _record(result, earlier).state == "pending"
    assert _record(result, later).state == "pending"


def test_media_through_a_stored_repost_holds_when_the_canonical_is_refetched(repo, posts) -> None:
    earlier, later = _pair(posts)
    no_media = earlier.with_changes(media=[])
    _run(repo, [no_media, later])
    assert repo.get_lifecycle(earlier.listing_id).state == "pending"
    result = dedup_a([no_media], repo)  # recheck alone would say no_images
    assert _record(result, earlier).state == "pending"


def test_a_stored_canonical_with_no_record_gets_one(repo, posts) -> None:
    earlier, later = _pair(posts)
    repo.upsert(earlier.with_changes(is_canonical=True, duplicate_of=None))
    result = dedup_a([later], repo)
    built = _record(result, earlier)
    assert built == initial_lifecycle(earlier).model_copy(
        update={"last_published_at": later.posted_at}
    )


# --- #74 and #75 E1–E3: a repost of an archived post ---


@pytest.mark.parametrize(
    ("reason", "flag", "state"),
    [
        (None, {}, "pending"),
        ("other_city", {}, "rejected"),
        ("seeking", {}, "rejected"),
        ("for_sale", {}, "rejected"),
        ("not_listing", {}, "rejected"),
        ("flagged", FLAG, "rejected"),
    ],
)
def test_a_repost_returns_an_archived_post_to_its_state(repo, posts, reason, flag, state) -> None:
    earlier, later = _pair(posts)
    _seed(repo, earlier, state="archived", rejection_reason=reason, **flag)
    record = _record(dedup_a([later], repo), earlier)
    assert (record.state, record.rejection_reason) == (state, reason)
    assert record.flagged_by == flag.get("flagged_by")
    assert record.last_published_at == later.posted_at


def test_an_archived_no_images_post_with_a_media_repost_returns_to_pending(repo, posts) -> None:
    earlier, later = _pair(posts)
    _seed(repo, earlier.with_changes(media=[]), state="archived", rejection_reason="no_images")
    record = _record(dedup_a([later], repo), earlier)
    assert (record.state, record.rejection_reason) == ("pending", None)


def test_an_archived_no_images_post_with_a_repost_without_media_stays_rejected(repo, posts) -> None:
    earlier, later = _pair(posts)
    _seed(repo, earlier.with_changes(media=[]), state="archived", rejection_reason="no_images")
    record = _record(dedup_a([later.with_changes(media=[])], repo), earlier)
    assert (record.state, record.rejection_reason) == ("rejected", "no_images")


def test_a_refetched_stored_duplicate_does_not_bring_back_an_archived_post(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier, later])
    archived = repo.get_lifecycle(earlier.listing_id).model_copy(update={"state": "archived"})
    repo.save_lifecycle(archived)
    result = dedup_a([later], repo)
    assert earlier.listing_id not in {r.listing_id for r in result.lifecycles}
    assert repo.get_lifecycle(earlier.listing_id).state == "archived"


def test_an_older_new_duplicate_does_not_bring_back_an_archived_post(repo, posts) -> None:
    earlier, later = _pair(posts)
    _seed(repo, later, state="archived")
    result = dedup_a([earlier], repo)
    assert result.posts[0].duplicate_of == later.listing_id
    assert later.listing_id not in {r.listing_id for r in result.lifecycles}


# --- #75 B, F1 ---


def test_a_duplicate_gets_an_ordinary_record_from_its_own_content(repo, posts) -> None:
    earlier, later = _pair(posts)
    no_media = later.with_changes(media=[])
    result = dedup_a([earlier, no_media], repo)
    assert _record(result, no_media) == initial_lifecycle(no_media)
    assert _record(result, no_media).rejection_reason == "no_images"


class _ReadOnly:
    """Forwards the reads; any write fails the test."""

    def __init__(self, inner: Repository) -> None:
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        if name in {"upsert", "upsert_with_lifecycle", "save_lifecycle"}:
            raise AssertionError(f"dedup_a called {name}")
        return getattr(self._inner, name)


def test_dedup_writes_nothing(repo, posts) -> None:
    earlier, later = _pair(posts)
    _run(repo, [earlier.with_changes(media=[])])
    result = dedup_a(posts, _ReadOnly(repo))
    assert len(result.posts) == 20
    assert repo.get(later.listing_id) is None
