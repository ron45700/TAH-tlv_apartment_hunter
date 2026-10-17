from collections import defaultdict

import pytest

from tests.conftest import FETCHED_AT, KNOWN_DUPLICATE_PAIRS, load_thedoor_phones
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.textnorm.annotate import annotate
from tlv_hunter.textnorm.normalize import compute_text_hash
from tlv_hunter.textnorm.phones import canonical_phone, extract_phones


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
    expected = load_thedoor_phones()
    assert len(expected) == 10
    assert found == expected
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
        ("052-765-4321", ["0527654321"]),
        ("+972501234567", ["0501234567"]),
        ("+972-50-1234567", ["0501234567"]),
        ("להתקשר 0501234567 בערב", ["0501234567"]),
        ("לפרטים – דני 0529876543", ["0529876543"]),
        ("שכר דירה: 8,200 ₪", []),
    ],
)
def test_phone_formats(text: str, expected: list[str]) -> None:
    assert extract_phones(text) == expected


def test_a_number_repeated_in_one_post_is_stored_once_in_order() -> None:
    text = "050-1234567 או 052-765-4321, שוב 0501234567, ובוואטסאפ +972501234567"
    assert extract_phones(text) == ["0501234567", "0527654321"]


def test_canonical_phone_unifies_formats() -> None:
    forms = ["050-111-2233", "0501112233", "+972501112233", "+972-50-111-2233"]
    assert {canonical_phone(form) for form in forms} == {"0501112233"}
