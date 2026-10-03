from collections import defaultdict

import pytest

from tests.conftest import FETCHED_AT, KNOWN_DUPLICATE_PAIRS
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.textnorm.normalize import compute_text_hash
from tlv_hunter.textnorm.phones import canonical_phone, extract_phones

PHONES_FROM_TASK_1_2 = {
    "10163683432542695": ["0548008244"],
    "10163683412257695": ["0548008244"],
    "10163683084577695": ["0545530069"],
    "10163683075607695": ["0542281414"],
    "10163683074177695": ["0542670026"],
    "10163682885072695": ["0547916108"],
    "10163682680542695": ["0509636119"],
    "2178554076041449": ["0509184537"],
    "2178430789387111": ["0509184537"],
    "2178421059388084": ["0543133194"],
}


@pytest.fixture
def annotated(thedoor_items):
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in thedoor_items]


def test_all_20_have_text_and_a_hash(annotated) -> None:
    assert all(post.no_text is False and post.text_hash is not None for post in annotated)


def test_hash_groups_are_exactly_the_three_known_pairs(annotated) -> None:
    groups: dict[str, set[str]] = defaultdict(set)
    for post in annotated:
        groups[post.text_hash].add(post.source_post_id)
    assert len(groups) == 17
    colliding = {frozenset(ids) for ids in groups.values() if len(ids) > 1}
    assert colliding == KNOWN_DUPLICATE_PAIRS


def test_phones_match_task_1_2_findings(annotated) -> None:
    found = {post.source_post_id: post.phones for post in annotated if post.phones}
    assert found == PHONES_FROM_TASK_1_2
    assert all(post.phones == [] for post in annotated if post.source_post_id not in found)


def test_blank_text_is_no_text_with_no_hash() -> None:
    assert compute_text_hash("  \n\t ") is None


def test_normalization_folds_niqud_quotes_finals_emoji_whitespace_case() -> None:
    plain = compute_text_hash("שלומ עולמ מר abc")
    decorated = compute_text_hash("שָׁלוֹם  \r\n עוֹלָם 🏠 מ״ר ABC")
    assert plain == compute_text_hash("שלום עולם מר abc")
    assert decorated == compute_text_hash("שלום עולם מר abc")


def test_different_texts_do_not_collide() -> None:
    assert compute_text_hash("מחפשים שותף") != compute_text_hash("מחפשים שותפה")


def test_text_that_normalizes_to_nothing_has_no_hash() -> None:
    assert compute_text_hash("🏠🏠") is None


def test_emoji_only_post_is_no_text_and_raises_nothing(thedoor_items) -> None:
    item = {**thedoor_items[0], "text": "🏠🏠 ✨"}
    post = annotate(to_raw_post(item, FETCHED_AT))
    assert post.text_source == "text"
    assert post.no_text is True
    assert post.text_hash is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("050-1234567", ["0501234567"]),
        ("0501234567", ["0501234567"]),
        ("054-313-3194", ["0543133194"]),
        ("+972501234567", ["0501234567"]),
        ("+972-50-1234567", ["0501234567"]),
        ("להתקשר 0501234567 בערב", ["0501234567"]),
        ("לפרטים – נועה 0548008244", ["0548008244"]),
        ("שכר דירה: 8,200 ₪", []),
    ],
)
def test_phone_formats(text: str, expected: list[str]) -> None:
    assert extract_phones(text) == expected


def test_a_number_repeated_in_one_post_is_stored_once_in_order() -> None:
    text = "050-1234567 או 054-313-3194, שוב 0501234567, ובוואטסאפ +972501234567"
    assert extract_phones(text) == ["0501234567", "0543133194"]


def test_canonical_phone_unifies_formats() -> None:
    forms = ["050-918-4537", "0509184537", "+972509184537", "+972-50-918-4537"]
    assert {canonical_phone(form) for form in forms} == {"0509184537"}
