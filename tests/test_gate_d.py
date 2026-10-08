"""Gate D's evidence (`PHASE_2.md` 2.10; DECISIONS.md #145, #226, #227): the candidate rules
(`gate_d/candidates.py`), `pair_verdicts.json` and its measurement (`gate_d/verdicts.py`), the page
(`gate_d/page.py`) and the command (`jobs/gate_d_pairs.py`). Posts and stores are built here: no
`data/` file is read and no network is used."""

import hashlib
import io
import json
import re
import sqlite3
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, make_listing
from tlv_hunter.areas.reference import load_areas
from tlv_hunter.contracts.post_lifecycle import PostImage, PostLifecycle
from tlv_hunter.contracts.raw_post import RAW_POST_SCHEMA_VERSION, Media, RawPost
from tlv_hunter.gate_d.candidates import (
    AGENT_PHONE_SAMPLE,
    AGENT_SAMPLE_SIZE,
    FIELDS,
    PHONE,
    WINDOW,
    Member,
    Population,
    find_candidates,
    load_population,
    pair_key,
)
from tlv_hunter.gate_d.page import PAGE_FILE, PHOTOS_PER_POST, TEMPLATE, render_pairs_page
from tlv_hunter.gate_d.verdicts import (
    VERDICTS,
    VerdictFile,
    check_against,
    measure,
    read_verdicts,
)
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.gate_d_pairs import main
from tlv_hunter.labeling.regression_set import text_sha256
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.postmodel.rejects import classified_lifecycle
from tlv_hunter.premodel.rejects import initial_lifecycle
from tlv_hunter.store.base import Repository
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.annotate import annotate

T0 = datetime(2026, 10, 4, 8, 0, tzinfo=UTC)
GENERATED_AT = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
PHONE_A = "0541234567"
PHONE_B = "0529876543"


def written(value: Any) -> dict[str, Any]:
    return {"state": "written", "value": value}


NOT_WRITTEN = {"state": "not_written", "value": None}


def letters(n: int) -> str:
    """A distinct word per n, so no two texts share a normalized hash."""
    return "".join(chr(97 + int(digit)) * 3 for digit in str(n))


def make_post(
    n: int,
    text: str,
    *,
    at: datetime = T0,
    group: str = "g1",
    media: bool = True,
    canonical: bool | None = True,
    author: str | None = "Dana",
) -> RawPost:
    source_post_id = f"post-{n}"
    post = RawPost(
        schema_version=RAW_POST_SCHEMA_VERSION,
        source="thedoor",
        source_post_id=source_post_id,
        listing_id=compute_listing_id(source_post_id),
        group_id=group,
        group_title=f"Group {group}",
        permalink=f"https://www.facebook.com/groups/{group}/posts/{n}",
        posted_at=at,
        fetched_at=at,
        raw={},
        text=text,
        text_source="text",
        post_type="text",
        media=(
            [
                Media(
                    type="Photo",
                    uri="https://example.invalid/x.jpg",
                    width=None,
                    height=None,
                    media_id=f"media-{n}",
                    page_url="https://example.invalid/p",
                )
            ]
            if media
            else []
        ),
        native_price=None,
        native_price_raw=None,
        native_currency=None,
        native_title=None,
        native_location=None,
        author_name=author,
        author_id_raw=None,
        author_profile_url=None,
        top_comment=None,
        reactions_count=None,
        comments_count=None,
        shares_count=None,
    )
    return annotate(post).with_changes(is_canonical=canonical)


def make_member(
    n: int,
    *,
    price: list[int] | None = None,
    rooms: float | None = None,
    areas: Sequence[int] = (),
    phone: str | None = None,
    at: datetime = T0,
    group: str = "g1",
    text: str | None = None,
    nature: str = "rental_offer",
) -> Member:
    body = text if text is not None else f"flat {letters(n)}"
    if phone is not None:
        body += f" call {phone}"
    post = make_post(n, body, at=at, group=group)
    listing = make_listing(
        post.listing_id,
        post_nature=nature,
        price=written(price) if price is not None else NOT_WRITTEN,
        price_source="text" if price is not None else None,
        rooms=written(rooms) if rooms is not None else NOT_WRITTEN,
        areas=sorted(set(areas)),
    )
    lifecycle = classified_lifecycle(initial_lifecycle(post), listing, post)
    return Member(post, lifecycle, listing)


def ids(candidates: Any) -> list[tuple[str, tuple[str, ...]]]:
    return [(pair.key, pair.found_by) for pair in candidates.pairs]


def key(a: Member, b: Member) -> str:
    return pair_key(a.listing_id, b.listing_id)


# --- the fields rule ---


def test_the_fields_rule_needs_price_rooms_and_an_area_all_three() -> None:
    base = make_member(1, price=[5000], rooms=3.0, areas=[30, 31])
    match = make_member(2, price=[5000], rooms=3.0, areas=[31, 40])
    assert ids(find_candidates([base, match])) == [(key(base, match), (FIELDS,))]
    for other in (
        make_member(3, price=[5100], rooms=3.0, areas=[30]),
        make_member(4, price=[5000], rooms=2.5, areas=[30]),
        make_member(5, price=[5000], rooms=3.0, areas=[40]),
        make_member(6, price=[5000], rooms=3.0, areas=[]),
        make_member(7, price=None, rooms=3.0, areas=[30]),
        make_member(8, price=[5000], rooms=None, areas=[30]),
    ):
        assert find_candidates([base, other]).pairs == ()


def test_prices_are_compared_as_sets() -> None:
    a = make_member(1, price=[1000, 1200], rooms=2.0, areas=[5])
    same = make_member(2, price=[1200, 1000], rooms=2.0, areas=[5])
    subset = make_member(3, price=[1000], rooms=2.0, areas=[5])
    assert [p.key for p in find_candidates([a, same]).pairs] == [key(a, same)]
    assert find_candidates([a, subset]).pairs == ()


def test_two_posts_with_nothing_written_are_not_a_pair() -> None:
    assert find_candidates([make_member(1, areas=[5]), make_member(2, areas=[5])]).pairs == ()


def test_the_same_hash_is_no_pair() -> None:
    a = make_member(1, price=[5000], rooms=3.0, areas=[30], text="the very same words")
    b = make_member(2, price=[5000], rooms=3.0, areas=[30], text="the very same words")
    assert a.post.text_hash == b.post.text_hash
    assert find_candidates([a, b]).pairs == ()


def test_the_window_is_72_hours_on_posted_at() -> None:
    a = make_member(1, price=[5000], rooms=3.0, areas=[30], at=T0)
    inside = make_member(2, price=[5000], rooms=3.0, areas=[30], at=T0 + WINDOW)
    outside = make_member(
        3, price=[5000], rooms=3.0, areas=[30], at=T0 + WINDOW + timedelta(seconds=1)
    )
    assert [p.key for p in find_candidates([a, inside]).pairs] == [key(a, inside)]
    assert find_candidates([a, outside]).pairs == ()
    earlier = make_member(4, price=[5000], rooms=3.0, areas=[30], at=T0 - WINDOW)
    assert [p.key for p in find_candidates([a, earlier]).pairs] == [key(a, earlier)]


def test_the_sublet_pair_is_found_by_the_fields_rule_and_not_by_the_phone_rule() -> None:
    # The shape of 9136a715… and 9a6252c1…: price 1000 (the provider's), 4 rooms, areas 30 and 31,
    # six minutes apart in one group, different texts, no phone.
    first = make_member(1, price=[1000], rooms=4.0, areas=[30, 31], at=T0, text="sublet one two")
    second = make_member(
        2,
        price=[1000],
        rooms=4.0,
        areas=[30, 31],
        at=T0 + timedelta(minutes=6),
        text="sublet three",
    )
    (pair,) = find_candidates([first, second]).pairs
    assert pair.found_by == (FIELDS,)
    assert pair.shared_phones == () and pair.same_group
    assert pair.matched == ("price", "rooms", "areas")
    assert pair.gap_hours == pytest.approx(0.1)


# --- the phone rule and the agent numbers ---


def test_a_shared_number_is_a_pair_whatever_the_fields() -> None:
    a = make_member(1, price=[6000], rooms=2.0, areas=[52], phone=PHONE_A)
    b = make_member(2, price=[7000], rooms=3.0, areas=[10], phone=PHONE_A, group="g2")
    (pair,) = find_candidates([a, b]).pairs
    assert pair.found_by == (PHONE,)
    assert pair.shared_phones == (PHONE_A,)
    assert pair.matched == () and not pair.same_group


def test_a_pair_found_by_both_rules_lists_first() -> None:
    a = make_member(1, price=[6000], rooms=2.0, areas=[52], phone=PHONE_A)
    b = make_member(2, price=[6000], rooms=2.0, areas=[52], phone=PHONE_A)
    c = make_member(3, price=[6000], rooms=2.0, areas=[52])
    d = make_member(4, price=[1], rooms=1.0, areas=[1], phone=PHONE_B)
    e = make_member(5, price=[2], rooms=1.5, areas=[2], phone=PHONE_B)
    candidates = find_candidates([e, d, c, b, a])
    ranked = [found for _, found in ids(candidates)]
    assert ranked.index((FIELDS, PHONE)) < ranked.index((FIELDS,)) < ranked.index((PHONE,))
    assert candidates.count(FIELDS) == 3 and candidates.count(PHONE) == 2


def agent_posts(count: int, **shared: Any) -> list[Member]:
    return [
        make_member(n, phone=PHONE_A, price=[1000 + n], rooms=float(n % 4 + 1), areas=[n], **shared)
        for n in range(1, count + 1)
    ]


def test_a_number_in_four_posts_lists_no_pair_one_by_one() -> None:
    candidates = find_candidates(agent_posts(4))
    assert candidates.pairs == ()
    assert candidates.agent_numbers == 1 and candidates.agent_pairs == 6
    # Three posts are not enough to make an agent number.
    three = find_candidates(agent_posts(3))
    assert three.agent_numbers == 0 and len(three.pairs) == 3 and three.agent_pairs == 0


def test_the_agent_sample_holds_only_pairs_with_a_price_or_rooms_and_an_area_in_common() -> None:
    posts = agent_posts(4)
    same_price = make_member(10, phone=PHONE_A, price=[1001], rooms=9.0, areas=[71])
    same_rooms_area = make_member(11, phone=PHONE_A, price=[7777], rooms=2.0, areas=[1])
    candidates = find_candidates([*posts, same_price, same_rooms_area])
    found = {pair.key: pair for pair in candidates.pairs}
    assert all(pair.found_by == (AGENT_PHONE_SAMPLE,) for pair in candidates.pairs)
    # posts[0] is 1001 for 2 rooms in area 1.
    assert set(found) == {key(posts[0], same_price), key(posts[0], same_rooms_area)}
    assert candidates.agent_numbers == 1


def test_the_agent_sample_is_capped_and_labelled() -> None:
    posts = [
        make_member(n, phone=PHONE_A, price=[3000], rooms=float(n), areas=[n]) for n in range(1, 6)
    ]
    candidates = find_candidates(posts)
    assert len(candidates.pairs) == AGENT_SAMPLE_SIZE
    assert all(pair.found_by == (AGENT_PHONE_SAMPLE,) for pair in candidates.pairs)
    assert candidates.agent_pairs == 10


def test_an_agent_pair_that_matches_the_fields_is_a_fields_pair() -> None:
    posts = agent_posts(4)
    twin = make_member(20, phone=PHONE_A, price=[1001], rooms=2.0, areas=[1])
    candidates = find_candidates([*posts, twin])
    assert [found for _, found in ids(candidates)] == [(FIELDS,)]


def test_a_light_number_beside_an_agent_number_is_a_phone_pair() -> None:
    posts = agent_posts(4)
    both = make_member(32, phone=PHONE_A, areas=[70], text=f"flat {letters(32)} call {PHONE_B}")
    # The first has both numbers in its text; the second has the light one only.
    both = Member(
        make_post(32, f"flat {letters(32)} call {PHONE_A} call {PHONE_B}"),
        both.lifecycle,
        both.listing,
    )
    light = make_member(33, phone=PHONE_B, areas=[71])
    candidates = find_candidates([*posts, both, light])
    (pair,) = [p for p in candidates.pairs if p.key == key(both, light)]
    assert pair.found_by == (PHONE,) and pair.shared_phones == (PHONE_B,)


def test_the_candidates_are_the_same_in_the_same_order_twice() -> None:
    posts = [
        make_member(
            n, price=[5000 + (n % 2)], rooms=2.0, areas=[7], phone=PHONE_B if n < 3 else None
        )
        for n in range(1, 8)
    ]
    first = find_candidates(posts)
    second = find_candidates(list(reversed(posts)))
    assert first == second and first.pairs


# --- who is compared, and that nothing is written ---


def add_pending(repository: Repository, post: RawPost) -> None:
    repository.upsert_with_lifecycle(post, initial_lifecycle(post))


def add(repository: Repository, member: Member) -> None:
    add_pending(repository, member.post)
    repository.save_classification(member.listing, member.lifecycle)


def test_only_active_canonical_classified_posts_are_compared(
    make_repository: Callable[[], Repository],
) -> None:
    repository = make_repository()
    active = make_member(1, price=[5000], rooms=3.0, areas=[30])
    rejected = make_member(2, price=[5000], rooms=3.0, areas=[30], nature="seeking")
    add(repository, active)
    add(repository, rejected)
    add_pending(repository, make_post(3, "flat pending words"))
    add_pending(repository, make_post(4, "flat duplicate words", canonical=False))
    population = load_population(repository)
    assert rejected.lifecycle.state == "rejected"
    assert [m.listing_id for m in population.members] == [active.listing_id]
    assert population.total_posts == 4 and population.duplicates == 1


def test_the_population_reports_the_span_of_the_stored_posts(
    make_repository: Callable[[], Repository],
) -> None:
    repository = make_repository()
    add(repository, make_member(1, at=T0))
    add(repository, make_member(2, at=T0 + timedelta(hours=27)))
    assert load_population(repository).span_hours == pytest.approx(27.0)


def test_an_empty_store_has_no_span() -> None:
    assert Population((), 0, 0, None, None).span_hours == 0.0


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_rows(path: Path) -> list[tuple[str, str]]:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return list(conn.execute("SELECT listing_id, doc FROM raw_posts ORDER BY listing_id"))
    finally:
        conn.close()


def build_store(repo_root: Path, members: Sequence[Member]) -> Path:
    store_root = repo_root / "data" / "store"
    store_root.mkdir(parents=True)
    database = store_root / SQLITE_FILENAME
    repository = SqliteRepository(database)
    for member in members:
        add(repository, member)
    return database


def run(repo_root: Path, *args: str) -> tuple[int, str]:
    stream = io.StringIO()
    code = main(
        list(args),
        config_root=CONFIG_ROOT,
        repo_root=repo_root,
        clock=lambda: GENERATED_AT,
        stream=stream,
    )
    return code, stream.getvalue()


def sample_members() -> list[Member]:
    return [
        make_member(1, price=[1000], rooms=4.0, areas=[30, 31], text="sublet one two"),
        make_member(
            2,
            price=[1000],
            rooms=4.0,
            areas=[30, 31],
            at=T0 + timedelta(minutes=6),
            text="sublet three",
        ),
        make_member(3, price=[6000], rooms=2.0, areas=[52], phone=PHONE_A),
        make_member(4, price=[7000], rooms=3.0, areas=[10], phone=PHONE_A, group="g2"),
        make_member(5, price=[9], rooms=1.0, areas=[1]),
    ]


def test_the_command_writes_the_page_and_nothing_to_the_store(tmp_path: Path) -> None:
    database = build_store(tmp_path, sample_members())
    before, rows = digest(database), raw_rows(database)
    code, output = run(tmp_path)
    assert code == 0
    assert digest(database) == before and raw_rows(database) == rows
    page = tmp_path / "data" / "gate_d" / PAGE_FILE
    assert page.is_file() and "wrote" in output
    assert "pairs listed 2: found by the fields rule 1, by the phone rule 1" in output
    assert PHONE_A not in output  # a number is never printed
    code, output = run(tmp_path, "--dry-run")
    assert code == 0 and "dry run: nothing written" in output and PHONE_A not in output
    assert digest(database) == before


def test_a_dry_run_writes_no_file(tmp_path: Path) -> None:
    build_store(tmp_path, sample_members())
    code, output = run(tmp_path, "--dry-run")
    assert code == 0 and "fields" in output
    assert not (tmp_path / "data" / "gate_d").exists()


def test_the_store_is_opened_read_only(tmp_path: Path) -> None:
    database = build_store(tmp_path, sample_members())
    read_only = SqliteRepository(database, read_only=True)
    with pytest.raises(sqlite3.OperationalError):
        read_only.upsert(make_post(99, "flat other words"))


def test_a_missing_store_fails_and_creates_nothing(tmp_path: Path) -> None:
    code, output = run(tmp_path)
    assert code == 1 and "no store" in output
    assert not (tmp_path / "data").exists()


# --- the page ---


def page_data(html: str) -> dict[str, Any]:
    (blob,) = re.findall(
        r'<script type="application/json" id="page-data">(.*?)</script>', html, re.S
    )
    return json.loads(blob)


def with_images(member: Member, paths: list[str]) -> Member:
    images = [
        PostImage(listing_id=member.listing_id, media_id=f"m{i}", local_path=path, error=None)
        for i, path in enumerate(paths)
    ]
    lifecycle = PostLifecycle(**{**dict(member.lifecycle), "images": images})
    return Member(member.post, lifecycle, member.listing)


def test_the_page_holds_each_text_verbatim_and_the_matched_fields(tmp_path: Path) -> None:
    store_root = tmp_path / "data" / "store"
    page_dir = tmp_path / "data" / "gate_d"
    paths = [f"images/x/{i}.jpg" for i in range(6)]
    for path in paths[:5]:
        (store_root / path).parent.mkdir(parents=True, exist_ok=True)
        (store_root / path).write_bytes(b"\xff\xd8")
    text_a = 'דירה <script>alert(1)</script> & "quotes"\nשותף/ה'
    a = with_images(
        make_member(1, price=[5000], rooms=3.0, areas=[30], text=text_a, phone=PHONE_A), paths
    )
    b = make_member(2, price=[5000], rooms=3.0, areas=[30, 31], group="g2", phone=PHONE_A)
    population = Population((a, b), 2, 0, T0, T0 + timedelta(hours=27))
    candidates = find_candidates(population.members)
    html = render_pairs_page(
        candidates,
        population,
        load_areas(),
        store_root=store_root,
        page_dir=page_dir,
        generated_at=GENERATED_AT,
    )
    assert "<script>alert(1)</script>" not in html
    data = page_data(html)
    (pair,) = data["pairs"]
    by_id = {post["listing_id"]: post for post in pair["posts"]}
    first, second = by_id[a.listing_id], by_id[b.listing_id]
    sent = text_a + f" call {PHONE_A}"  # make_member appends the number
    assert first["text"] == sent  # verbatim, markup characters and all
    assert first["text_sha256"] == text_sha256(sent)
    assert pair["found_by"] == [FIELDS, PHONE]
    assert pair["matched"] == ["price", "rooms", "areas"]
    assert pair["shared_phones"] == [PHONE_A] and pair["same_group"] is False
    assert first["posted_at"] == "2026-10-04T08:00:00+00:00"  # UTC in the data (invariant 9)
    assert first["group_title"] == "Group g1" and second["group_title"] == "Group g2"
    assert first["author_name"] == "Dana" and first["permalink"].startswith("https://")
    assert first["photos"] == paths[:PHOTOS_PER_POST]  # existing files only, at most four
    assert second["photos"] == []
    assert data["images_base"] == "../store"
    assert data["verdicts"] == list(VERDICTS)
    assert sorted(first) == sorted(
        [
            "listing_id",
            "text",
            "text_sha256",
            "posted_at",
            "group_id",
            "group_title",
            "permalink",
            "author_name",
            "photos",
            "listing",
        ]
    )  # nothing else, no normalized text
    # The browser converts to Israel time at display only.
    assert "Asia/Jerusalem" in TEMPLATE.read_text(encoding="utf-8")


def test_a_template_without_its_placeholder_is_refused(tmp_path: Path, monkeypatch: Any) -> None:
    bare = tmp_path / "bare.html"
    bare.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr("tlv_hunter.gate_d.page.TEMPLATE", bare)
    with pytest.raises(ValueError, match="__PAGE_DATA__"):
        render_pairs_page(
            find_candidates([]),
            Population((), 0, 0, None, None),
            load_areas(),
            store_root=tmp_path,
            page_dir=tmp_path,
            generated_at=GENERATED_AT,
        )


# --- the export and the measurement ---


def population_of(count: int, *, duplicates: int = 39, total: int = 266) -> Population:
    members = tuple(make_member(1000 + n) for n in range(count))
    return Population(members, total, duplicates, T0, T0 + timedelta(hours=27))


def verdict_record(first: str, second: str, verdict: str, found_by: list[str]) -> tuple[str, dict]:
    return pair_key(first, second), {
        "text_sha256": [first[:8] * 8, second[:8] * 8],
        "found_by": found_by,
        "verdict": verdict,
        "note": "",
    }


def verdict_file(records: Sequence[tuple[str, dict]], **changes: Any) -> VerdictFile:
    return VerdictFile.model_validate(
        {
            "format_version": 1,
            "exported_at": "2026-10-09T10:00:00Z",
            "rules_version": "1",
            "pairs": dict(records),
            **changes,
        }
    )


def many(count: int, verdict: str, found_by: list[str], start: int) -> list[tuple[str, dict]]:
    return [
        verdict_record(f"{start + i:04d}a", f"{start + i:04d}b", verdict, found_by)
        for i in range(count)
    ]


def test_the_measurement_follows_the_four_verdicts() -> None:
    records = [
        *many(2, "same_listing", ["fields"], 0),
        *many(1, "same_listing", ["phone"], 10),
        *many(1, "same_listing", ["fields", "phone"], 20),
        *many(1, "same_apartment_other_listing", ["phone"], 30),
        *many(2, "different", ["fields"], 40),
        *many(1, "not_sure", ["agent_phone_sample"], 50),
        *many(1, "different", ["agent_phone_sample"], 60),
    ]
    lines = measure(verdict_file(records), population_of(40), 12)
    text = "\n".join(lines)
    assert "pairs judged: 9 of 12 listed" in text
    assert "same_listing 4, same_apartment_other_listing 1, different 3, not_sure 1" in text
    # 4 of 40 is 10%; with the not_sure pair, 5 of 40.
    assert "4 / 40 = 10.0%" in text and "up to 5 / 40 = 12.5%" in text
    assert (
        "threshold 5% (#227) = 2 pairs of 40: lower figure reaches it, upper figure reaches it"
        in text
    )
    assert "same apartment, another listing (not counted above): 1 pairs / 40 = 2.5%" in text
    assert "fields only: 4 judged: 2 / 0 / 2 / 0; 50.0%" in text
    assert "phone only: 2 judged: 1 / 1 / 0 / 0; 50.0%" in text
    assert "fields and phone: 1 judged: 1 / 0 / 0 / 0; 100.0%" in text
    assert "agent-number sample: 2 judged: 0 / 0 / 1 / 1; 0.0%" in text
    assert "39 of 266 stored posts = 14.7%" in text
    assert "27.0 hours" in text and "lower bound" in text


def test_only_same_listing_reaches_the_threshold() -> None:
    other_flat = many(10, "same_apartment_other_listing", ["phone"], 0)
    text = "\n".join(measure(verdict_file(other_flat), population_of(139), 24))
    assert "0 / 139 = 0.0%" in text
    assert "threshold 5% (#227) = 7 pairs of 139: lower figure does not reach it" in text


def test_the_threshold_is_seven_pairs_of_139_and_not_sure_only_raises_the_upper_figure() -> None:
    six = many(6, "same_listing", ["fields"], 0)
    one_unsure = many(1, "not_sure", ["phone"], 10)
    text = "\n".join(measure(verdict_file([*six, *one_unsure]), population_of(139), 24))
    assert "lower figure does not reach it, upper figure reaches it" in text
    seven = many(7, "same_listing", ["fields"], 0)
    text = "\n".join(measure(verdict_file(seven), population_of(139), 24))
    assert "lower figure reaches it" in text


def test_posts_in_two_pairs_count_once_in_the_share() -> None:
    first = pair_key("aaaa", "bbbb")
    second = pair_key("aaaa", "cccc")
    shape = {
        "text_sha256": ["x", "y"],
        "found_by": ["fields"],
        "verdict": "same_listing",
        "note": "",
    }
    text = "\n".join(measure(verdict_file([(first, shape), (second, shape)]), population_of(40), 5))
    assert "2 / 40 = 5.0%" in text
    assert "in at least one such pair: 3 of 40 = 7.5%" in text


def test_a_measurement_for_other_rules_is_refused() -> None:
    with pytest.raises(ValueError, match="rules version"):
        measure(verdict_file([], rules_version="0"), population_of(3), 0)


def test_the_export_is_checked_against_the_store() -> None:
    a = make_member(1, price=[5000], rooms=3.0, areas=[30])
    b = make_member(2, price=[5000], rooms=3.0, areas=[30])
    candidates = find_candidates([a, b])
    current = {pair.key: pair for pair in candidates.pairs}
    hashes = {m.listing_id: text_sha256(m.post.text) for m in (a, b)}
    good = {
        "text_sha256": [
            hashes[min(a.listing_id, b.listing_id)],
            hashes[max(a.listing_id, b.listing_id)],
        ],
        "found_by": ["fields"],
        "verdict": "same_listing",
        "note": "",
    }
    check_against(verdict_file([(key(a, b), good)]), current, hashes)
    with pytest.raises(ValueError, match="not a candidate pair"):
        check_against(verdict_file([("aaaa|bbbb", good)]), current, hashes)
    changed = {**good, "text_sha256": ["0" * 64, good["text_sha256"][1]]}
    with pytest.raises(ValueError, match="text changed"):
        check_against(verdict_file([(key(a, b), changed)]), current, hashes)


@pytest.mark.parametrize(
    "change",
    [
        {"verdict": "same"},  # the three-verdict draft
        {"verdict": "yes"},
        {"found_by": []},
        {"found_by": ["fields", "fields"]},
        {"found_by": ["names"]},
        {"text_sha256": ["only-one"]},
        {"extra": 1},
    ],
)
def test_a_malformed_verdict_is_refused(change: dict) -> None:
    _, record = verdict_record("aaaa", "bbbb", "same_listing", ["fields"])
    with pytest.raises(ValidationError):
        verdict_file([("aaaa|bbbb", {**record, **change})])


@pytest.mark.parametrize("bad_key", ["bbbb|aaaa", "aaaa|aaaa", "aaaa", "|bbbb", "aaaa|"])
def test_a_pair_key_must_be_the_smaller_id_first(bad_key: str) -> None:
    _, record = verdict_record("aaaa", "bbbb", "same_listing", ["fields"])
    with pytest.raises(ValidationError):
        verdict_file([(bad_key, record)])


def test_a_repeated_pair_in_the_file_is_refused(tmp_path: Path) -> None:
    _, record = verdict_record("aaaa", "bbbb", "same_listing", ["fields"])
    body = json.dumps(record)
    path = tmp_path / "pair_verdicts.json"
    path.write_text(
        '{"format_version": 1, "exported_at": "2026-10-09T10:00:00Z", "rules_version": "1", '
        f'"pairs": {{"aaaa|bbbb": {body}, "aaaa|bbbb": {body}}}}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="twice"):
        read_verdicts(path)


def test_a_naive_export_time_is_refused() -> None:
    with pytest.raises(ValidationError):
        verdict_file([], exported_at="2026-10-09T10:00:00")


def test_the_measure_command_reads_the_file_from_data_gate_d(tmp_path: Path) -> None:
    members = sample_members()
    database = build_store(tmp_path, members)
    code, output = run(tmp_path, "--measure")
    assert code == 1 and "pair_verdicts.json" in output
    candidates = find_candidates(members)
    records = {
        pair.key: {
            "text_sha256": [
                text_sha256(next(m.post.text for m in members if m.listing_id == pair.first_id)),
                text_sha256(next(m.post.text for m in members if m.listing_id == pair.second_id)),
            ],
            "found_by": list(pair.found_by),
            "verdict": "same_listing"
            if FIELDS in pair.found_by
            else "same_apartment_other_listing",
            "note": "",
        }
        for pair in candidates.pairs
    }
    folder = tmp_path / "data" / "gate_d"
    folder.mkdir(parents=True)
    (folder / "pair_verdicts.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-09T10:00:00Z",
                "rules_version": "1",
                "pairs": records,
            }
        ),
        encoding="utf-8",
    )
    before = digest(database)
    code, output = run(tmp_path, "--measure")
    assert code == 0, output
    assert "pairs judged: 2 of 2 listed" in output
    assert "1 / 5 = 20.0%" in output  # one same_listing pair of five compared posts
    assert digest(database) == before
    assert sorted(p.name for p in folder.iterdir()) == ["pair_verdicts.json"]
