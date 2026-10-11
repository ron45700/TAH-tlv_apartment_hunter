"""Task 3.6 (c), test groups 3 and 4: the Gate D key and the cards it derives (`dedup/stage_b.py`;
DECISIONS.md #230, #232, #231, #287, #295, #297, #300). Posts and stores are built here: no `data/`
file is read and no network is used; nothing is written but a temporary store."""

import random
from collections.abc import Callable, Sequence
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import make_correction
from tests.test_gate_d import PHONE_A, PHONE_B, T0, add, add_pending, make_member, make_post
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.dedup.stage_b import (
    PHONE_AND_FIELDS,
    PHOTO,
    KeyInputs,
    KeyPost,
    PhotoHashes,
    TiedPair,
    cards,
    derive_cards,
    key_agent_numbers,
    load_key_posts,
    pair_rules,
    tied_pairs,
)
from tlv_hunter.gate_d.candidates import WINDOW
from tlv_hunter.postmodel.seen import seen_listing
from tlv_hunter.store.base import Repository

AGENT = "0501111111"
FIELDS: dict[str, Any] = {"price": [5000], "rooms": 3.0, "areas": [30, 31]}


def key_post(
    n: int,
    *,
    price: list[int] | None = None,
    rooms: float | None = None,
    areas: Sequence[int] = (),
    phone: str | None = None,
    at: Any = T0,
    text: str | None = None,
    photos: Sequence[str] = (),
    corrections: dict[str, Any] | None = None,
    published: Any = None,
) -> KeyPost:
    member = make_member(n, price=price, rooms=rooms, areas=areas, phone=phone, at=at, text=text)
    made = [
        make_correction(member.listing, field, value, n=i)
        for i, (field, value) in enumerate((corrections or {}).items(), start=1)
    ]
    lifecycle = member.lifecycle
    if published is not None:
        lifecycle = PostLifecycle(**{**dict(lifecycle), "last_published_at": published})
    return KeyPost(member.post, lifecycle, seen_listing(member.listing, made), frozenset(photos))


def duplicate_of(n: int, text: str, canonical_id: str, at: Any = T0) -> RawPost:
    return make_post(n, text, at=at).with_changes(is_canonical=False, duplicate_of=canonical_id)


def pairs_of(*members: KeyPost) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(p.first_id, p.second_id, p.rules) for p in tied_pairs(list(members))]


def ids(a: KeyPost, b: KeyPost) -> tuple[str, str]:
    low, high = sorted((a.listing_id, b.listing_id))
    return low, high


# --- 3. the key, rule by rule ---


def test_rule_1_a_shared_phone_and_the_fields() -> None:
    a = key_post(1, phone=PHONE_A, **FIELDS)
    b = key_post(2, phone=PHONE_A, price=[5000], rooms=3.0, areas=[31])
    assert pairs_of(a, b) == [(*ids(a, b), (PHONE_AND_FIELDS,))]


def test_rule_2_a_shared_photo_with_a_phone_or_with_the_fields() -> None:
    a = key_post(1, phone=PHONE_A, price=[5000], photos=["h1"])
    with_phone = key_post(2, phone=PHONE_A, price=[6000], photos=["h1"])
    assert pairs_of(a, with_phone) == [(*ids(a, with_phone), (PHOTO,))]
    c = key_post(3, photos=["h2"], **FIELDS)
    with_fields = key_post(4, photos=["h2", "h3"], **FIELDS)
    assert pairs_of(c, with_fields) == [(*ids(c, with_fields), (PHOTO,))]
    d = key_post(5, phone=PHONE_B, photos=["h4"], **FIELDS)
    both = key_post(6, phone=PHONE_B, photos=["h4"], **FIELDS)
    assert pairs_of(d, both) == [(*ids(d, both), (PHONE_AND_FIELDS, PHOTO))]


def agents_around(n: int) -> list[KeyPost]:
    """Two more posts carrying `AGENT`, with nothing else in common: with a pair, four posts."""
    return [
        key_post(n, phone=AGENT, price=[9000 + n], at=T0 + timedelta(days=10)),
        key_post(n + 1, phone=AGENT, price=[9100 + n], at=T0 + timedelta(days=20)),
    ]


@pytest.mark.parametrize(
    ("first", "second", "extra"),
    [
        # a phone alone
        ({"phone": PHONE_A, "price": [5000]}, {"phone": PHONE_A, "price": [6000]}, False),
        # the fields alone
        (FIELDS, FIELDS, False),
        # a photo alone
        ({"photos": ["h1"], "price": [5000]}, {"photos": ["h1"], "price": [6000]}, False),
        # an agent's phone and the fields
        ({"phone": AGENT, **FIELDS}, {"phone": AGENT, **FIELDS}, True),
        # a photo and only an agent's phone
        (
            {"phone": AGENT, "photos": ["h1"], "price": [5000]},
            {"phone": AGENT, "photos": ["h1"], "price": [6000]},
            True,
        ),
    ],
)
def test_nothing_else_ties(first: dict[str, Any], second: dict[str, Any], extra: bool) -> None:
    members = [key_post(1, **first), key_post(2, **second)]
    if extra:
        members += agents_around(10)
        assert key_agent_numbers(members) == {AGENT}
    assert tied_pairs(members) == ()


def test_the_window_is_72_hours_inclusive_on_posted_at() -> None:
    a = key_post(1, phone=PHONE_A, at=T0, **FIELDS)
    inside = key_post(2, phone=PHONE_A, at=T0 + WINDOW, **FIELDS)
    outside = key_post(3, phone=PHONE_A, at=T0 + WINDOW + timedelta(seconds=1), **FIELDS)
    assert pairs_of(a, inside) == [(*ids(a, inside), (PHONE_AND_FIELDS,))]
    assert pairs_of(a, outside) == []


def test_the_same_text_hash_is_not_compared() -> None:
    a = key_post(1, phone=PHONE_A, text="the very same words", photos=["h1"], **FIELDS)
    b = key_post(2, phone=PHONE_A, text="the very same words", photos=["h1"], **FIELDS)
    assert a.post.text_hash == b.post.text_hash
    assert tied_pairs([a, b]) == ()


def test_the_key_reads_the_corrected_values() -> None:
    """#287: a correction that makes the fields match ties; one that breaks them unties."""
    a = key_post(1, phone=PHONE_A, **FIELDS)
    off = key_post(2, phone=PHONE_A, price=[5000], rooms=4.0, areas=[30])
    assert tied_pairs([a, off]) == ()
    fixed = key_post(
        2,
        phone=PHONE_A,
        price=[5000],
        rooms=4.0,
        areas=[30],
        corrections={"rooms": {"state": "written", "value": 3.0}},
    )
    assert pairs_of(a, fixed) == [(*ids(a, fixed), (PHONE_AND_FIELDS,))]
    broken = key_post(2, phone=PHONE_A, corrections={"areas": [52]}, **FIELDS)
    assert tied_pairs([a, broken]) == ()


def test_only_compared_posts_are_accepted() -> None:
    a = key_post(1, phone=PHONE_A, **FIELDS)
    pending = KeyPost(
        a.post,
        PostLifecycle(**{**dict(a.lifecycle), "state": "pending"}),
        a.seen,
        a.photo_hashes,
    )
    duplicate = KeyPost(
        a.post.with_changes(is_canonical=False, duplicate_of="x" * 64),
        a.lifecycle,
        a.seen,
        a.photo_hashes,
    )
    for member in (pending, duplicate):
        with pytest.raises(ValueError, match="not one the key compares"):
            tied_pairs([member, key_post(2, phone=PHONE_A, **FIELDS)])


@pytest.mark.parametrize("seed", range(8))
def test_the_shared_phone_or_photo_search_equals_every_pair(seed: int) -> None:
    rng = random.Random(seed)
    # Ten numbers among 30 posts: some reach four posts (agents), most do not.
    phones = [f"05{digit}1234567" for digit in range(10)] + [None]
    members = [
        key_post(
            n,
            phone=rng.choice(phones),
            price=rng.choice([[5000], [5000], [6000], None]),
            rooms=rng.choice([3.0, 3.0, 2.5, None]),
            areas=rng.choice([[30], [30, 31], [52], []]),
            at=T0 + timedelta(hours=rng.randint(0, 200)),
            photos=rng.sample(["h1", "h2", "h3", "h4"], rng.randint(0, 2)),
        )
        for n in range(1, 31)
    ]
    agents = key_agent_numbers(members)
    every = sorted(
        (*sorted((a.listing_id, b.listing_id)), pair_rules(a, b, agents))
        for i, a in enumerate(members)
        for b in members[i + 1 :]
        if pair_rules(a, b, agents)
    )
    assert every, "the population should tie some pairs"
    assert pairs_of(*members) == every


# --- 4. cards ---


def inputs(
    *members: KeyPost, duplicates: dict[str, tuple[RawPost, ...]] | None = None
) -> KeyInputs:
    return KeyInputs(tuple(sorted(members, key=lambda m: m.listing_id)), duplicates or {})


def test_a_connected_group_is_one_card_and_every_member_is_in_one_card() -> None:
    """#295, point 5: A tied to B and B to C, A and C more than 72 hours apart."""
    a = key_post(1, phone=PHONE_A, at=T0, **FIELDS)
    b = key_post(2, phone=PHONE_A, at=T0 + timedelta(hours=60), **FIELDS)
    c = key_post(3, phone=PHONE_A, at=T0 + timedelta(hours=120), **FIELDS)
    alone = key_post(4, price=[7000])
    assert len(tied_pairs([a, b, c, alone])) == 2  # a and c are not tied
    derived = derive_cards(inputs(a, b, c, alone))
    assert sorted(card.canonical_ids for card in derived) == sorted(
        [(a.listing_id, b.listing_id, c.listing_id), (alone.listing_id,)]
    )
    assert sorted(i for card in derived for i in card.canonical_ids) == sorted(
        m.listing_id for m in (a, b, c, alone)
    )


def test_the_card_shows_the_earliest_post_then_the_smaller_listing_id() -> None:
    """#297."""
    early = key_post(1, phone=PHONE_A, at=T0 + timedelta(hours=1), **FIELDS)
    late = key_post(2, phone=PHONE_A, at=T0 + timedelta(hours=5), **FIELDS)
    (card,) = derive_cards(inputs(late, early))
    assert card.shown_id == early.listing_id and card.canonical_ids[0] == early.listing_id
    same_a = key_post(3, phone=PHONE_B, at=T0, **FIELDS)
    same_b = key_post(4, phone=PHONE_B, at=T0, **FIELDS)
    (tie,) = derive_cards(inputs(same_a, same_b))
    assert tie.shown_id == min(same_a.listing_id, same_b.listing_id)


def test_a_card_holds_its_dedup_a_duplicates_its_latest_time_and_its_publications() -> None:
    first = key_post(1, phone=PHONE_A, at=T0, published=T0 + timedelta(hours=30), **FIELDS)
    second = key_post(
        2, phone=PHONE_A, at=T0 + timedelta(hours=2), published=T0 + timedelta(hours=8), **FIELDS
    )
    repost = duplicate_of(9, "a repost", second.listing_id, at=T0 - timedelta(hours=3))
    (card,) = derive_cards(inputs(first, second, duplicates={second.listing_id: (repost,)}))
    assert card.post_ids == {first.listing_id, second.listing_id, repost.listing_id}
    assert card.canonical_ids == (first.listing_id, second.listing_id)
    assert card.last_published_at == T0 + timedelta(hours=30)  # the card's main time (#122)
    assert [(p.listing_id, p.posted_at) for p in card.publications] == [
        (repost.listing_id, T0 - timedelta(hours=3)),  # the earliest first (#75 A)
        (first.listing_id, T0),
        (second.listing_id, T0 + timedelta(hours=2)),
    ]
    assert card.shown_id == first.listing_id  # a duplicate is never the shown post


def test_a_pair_naming_a_post_that_is_not_compared_raises() -> None:
    a = key_post(1)
    with pytest.raises(KeyError):
        cards(inputs(a), [TiedPair(a.listing_id, "z" * 64, (PHOTO,))])


# --- the loader and the photo memo ---


def image(listing_id: str, media_id: str, path: str | None) -> PostImage:
    return PostImage(
        listing_id=listing_id,
        media_id=media_id,
        local_path=path,
        error=None if path is not None else "http 404",
    )


def with_photo(repository: Repository, listing_id: str, store_root: Path, name: str) -> None:
    path = f"images/{listing_id[:8]}/{name}.jpg"
    (store_root / path).parent.mkdir(parents=True, exist_ok=True)
    (store_root / path).write_bytes(b"the same photo bytes")
    current = repository.get_lifecycle(listing_id)
    assert current is not None
    updated = PostLifecycle(**{**dict(current), "images": [image(listing_id, "m1", path)]})
    repository.save_lifecycle(updated, expected=current)


def test_the_loader_reads_only_compared_posts_as_users_see_them(
    make_repository: Callable[[], Repository], tmp_path: Path
) -> None:
    repository = make_repository()
    store_root = tmp_path / "store_root"
    a = make_member(1, phone=PHONE_A, price=[5000], rooms=3.0, areas=[30])
    b = make_member(2, phone=PHONE_A, price=[5000], rooms=4.0, areas=[30])
    rejected = make_member(3, phone=PHONE_A, price=[5000], rooms=3.0, areas=[30], nature="seeking")
    for member in (a, b, rejected):
        add(repository, member)
    add_pending(repository, make_post(4, f"waiting {PHONE_A}"))
    duplicate = duplicate_of(5, "a copy", a.listing_id)
    add_pending(repository, duplicate)
    with_photo(repository, a.listing_id, store_root, "x")
    with_photo(repository, b.listing_id, store_root, "y")
    fix = make_correction(b.listing, "rooms", {"state": "written", "value": 3.0})

    loaded = load_key_posts(repository, [fix], store_root, PhotoHashes())

    assert [m.listing_id for m in loaded.members] == sorted([a.listing_id, b.listing_id])
    assert loaded.duplicates == {a.listing_id: (duplicate,)}
    by_id = {m.listing_id: m for m in loaded.members}
    assert by_id[b.listing_id].seen.corrected == {"rooms"}
    assert by_id[a.listing_id].photo_hashes == by_id[b.listing_id].photo_hashes != frozenset()
    (card,) = derive_cards(loaded)
    assert card.post_ids == {a.listing_id, b.listing_id, duplicate.listing_id}


def test_the_photo_memo_reads_a_file_once_and_skips_a_missing_one(tmp_path: Path) -> None:
    member = make_member(1)
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "a.jpg").write_bytes(b"bytes")
    images = [
        image(member.listing_id, "1", "images/a.jpg"),
        image(member.listing_id, "2", "images/gone.jpg"),
        image(member.listing_id, "3", None),
    ]
    lifecycle = PostLifecycle(**{**dict(member.lifecycle), "images": images})
    photos = PhotoHashes()
    first = photos.of(tmp_path, lifecycle)
    assert len(first) == 1 and len(photos._memo) == 1
    assert photos.of(tmp_path, lifecycle) == first and len(photos._memo) == 1
