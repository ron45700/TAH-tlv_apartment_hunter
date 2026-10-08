"""The regression set and its labelling page (`PHASE_2.md` 2.6; DECISIONS.md #142, #143, #165,
#171, #177, #183): `tlv_hunter/labeling/regression_set.py`, `page.py`, and the command
`tlv_hunter/jobs/label_page.py`. No network; the store is a temporary one."""

import hashlib
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, REPO_ROOT
from tlv_hunter.areas.reference import load_areas
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.label_page import main
from tlv_hunter.labeling.page import TEMPLATE, render_label_page
from tlv_hunter.labeling.regression_set import (
    LABELING_DIR,
    REGRESSION_SET_FILE,
    PostText,
    RegressionEntry,
    RegressionSet,
    load_regression_set,
    post_texts,
)
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository

GENERATED_AT = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
SPIKE_IDS = REPO_ROOT / "data" / "spike_openai_2026-10-05" / "listing_ids.json"
PROPOSED_SET = REPO_ROOT / LABELING_DIR / REGRESSION_SET_FILE
TEST_POST_ID = "999000111"


def _fixture(path: Path) -> str:
    if not path.is_file():
        pytest.fail(f"fixture missing: {path}. data/ is gitignored; tests fail, never skip.")
    return path.read_text(encoding="utf-8")


def _page_data(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="page-data">(.*?)</script>', html, re.DOTALL
    )
    assert match is not None
    return json.loads(match.group(1))


def _entry(listing_id: str, case: str = "a case") -> dict:
    return {"listing_id": listing_id, "case": case, "source": "store"}


# --- the proposed set, read in place ---


def test_the_proposed_set_holds_the_spike_posts_and_about_fifty() -> None:
    regression_set = RegressionSet.model_validate_json(_fixture(PROPOSED_SET))
    cases = {entry.listing_id: entry.case for entry in regression_set.posts}
    spike = json.loads(_fixture(SPIKE_IDS))
    assert {entry["listing_id"] for entry in spike} <= set(cases)
    # Only the proposed set is bounded: a post that joins from a review (#195, #216) has
    # `truth: "review"` and is not counted.
    assert 45 <= sum(entry.truth == "blind" for entry in regression_set.posts) <= 55
    # The spike's two wrong labels are corrected (DECISIONS.md #165).
    for entry in spike:
        if entry["case"] in ("seeking", "Jaffa"):
            assert "for sale" in cases[entry["listing_id"]]


# --- the set file ---


def test_an_entry_from_test_posts_needs_its_post_id() -> None:
    with pytest.raises(ValidationError):
        RegressionEntry(listing_id="x", case="c", source="data/raw/test_posts.json")
    with pytest.raises(ValidationError):
        RegressionEntry(listing_id="x", case="c", source="store", post_id="1")


def test_a_listing_id_twice_is_refused() -> None:
    with pytest.raises(ValidationError, match="twice"):
        RegressionSet.model_validate({"format_version": 1, "posts": [_entry("a"), _entry("a")]})


def test_another_format_version_is_refused() -> None:
    with pytest.raises(ValidationError):
        RegressionSet.model_validate({"format_version": 2, "posts": []})


# --- the texts ---


def test_texts_come_from_the_store_verbatim_and_in_the_set_order(tmp_path: Path, posts) -> None:
    store = LocalJsonRepository(tmp_path / "store")
    for post in posts[:3]:
        store.upsert(post)
    entries = [RegressionEntry(**_entry(post.listing_id)) for post in reversed(posts[:3])]
    texts = post_texts(entries, store, tmp_path)
    assert texts == [PostText(post.listing_id, post.text) for post in reversed(posts[:3])]
    assert texts[0].text_sha256 == hashlib.sha256(posts[2].text.encode("utf-8")).hexdigest()


def test_a_post_missing_from_the_store_raises(tmp_path: Path) -> None:
    store = LocalJsonRepository(tmp_path / "store")
    with pytest.raises(LookupError, match="not in the store"):
        post_texts([RegressionEntry(**_entry("absent"))], store, tmp_path)


def _test_posts(root: Path, text: str) -> None:
    path = root / "data" / "raw" / "test_posts.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"post_id": TEST_POST_ID, "text": text}]), encoding="utf-8")


def test_a_text_from_test_posts_is_found_by_its_post_id(tmp_path: Path) -> None:
    _test_posts(tmp_path, "אנחנו שני שותפים")
    entry = RegressionEntry(
        listing_id=compute_listing_id(TEST_POST_ID),
        case="#45",
        source="data/raw/test_posts.json",
        post_id=TEST_POST_ID,
    )
    store = LocalJsonRepository(tmp_path / "store")
    assert post_texts([entry], store, tmp_path) == [
        PostText(compute_listing_id(TEST_POST_ID), "אנחנו שני שותפים")
    ]


def test_a_post_id_that_does_not_give_the_listing_id_raises(tmp_path: Path) -> None:
    _test_posts(tmp_path, "text")
    entry = RegressionEntry(
        listing_id="0" * 64, case="#45", source="data/raw/test_posts.json", post_id=TEST_POST_ID
    )
    with pytest.raises(ValueError, match="does not match"):
        post_texts([entry], LocalJsonRepository(tmp_path / "store"), tmp_path)


# --- the page ---


def test_the_page_carries_each_text_exactly_and_nothing_else_per_post() -> None:
    texts = [
        PostText("a" * 64, "מתפנה חדר 🏠\n‎שותף/ה\r\nend"),
        PostText("b" * 64, "English & <b>bold</b>"),
    ]
    data = _page_data(render_label_page(texts, load_areas(), GENERATED_AT))
    assert data["format_version"] == 1
    assert data["generated_at"] == GENERATED_AT.isoformat()
    assert data["posts"] == [
        {"listing_id": post.listing_id, "text": post.text, "text_sha256": post.text_sha256}
        for post in texts
    ]


def test_a_text_cannot_end_the_data_element() -> None:
    text = "</script><script>alert(1)</script> \ud83d"
    html = render_label_page([PostText("a" * 64, text)], load_areas(), GENERATED_AT)
    assert "<script>alert(1)" not in html
    assert html.count("</script>") == TEMPLATE.read_text(encoding="utf-8").count("</script>")
    assert _page_data(html)["posts"][0]["text"] == text


def test_the_page_lists_the_71_areas_by_display_name() -> None:
    areas = _page_data(render_label_page([], load_areas(), GENERATED_AT))["areas"]
    assert [area["number"] for area in areas] == list(range(1, 72))
    names = {area["number"]: area["name"] for area in areas}
    assert names[5] == "תכנית ל'"
    assert names[49] == "יפו ד' (גבעת התמרים)"
    assert names[30] == "הצפון הישן - החלק הצפוני"


def test_the_page_loads_nothing_from_outside() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"<script[^>]*\bsrc=", template) is None
    assert "<link" not in template
    assert "@import" not in template
    assert "url(" not in template
    assert "http" not in template.lower()


def test_the_page_has_no_control_for_streets_area_names_or_a_model_answer() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    for word in ("streets", "stated_area_names", "phone", "rooms", "model"):
        assert word not in template.replace("a model's answer", "")


def test_the_page_needs_a_utc_time() -> None:
    with pytest.raises(ValueError, match="UTC"):
        render_label_page([], load_areas(), datetime(2026, 10, 5, 18, 0))


# --- the command ---


def _repo(tmp_path: Path, posts, entries: list[dict] | None = None) -> Path:
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    store = SqliteRepository(database)
    for post in posts[:3]:
        store.upsert(post)
    labeling = tmp_path / LABELING_DIR
    labeling.mkdir(parents=True)
    if entries is None:
        entries = [_entry(post.listing_id, f"SECRET-CASE-{i}") for i, post in enumerate(posts[:3])]
    (labeling / REGRESSION_SET_FILE).write_text(
        json.dumps({"format_version": 1, "posts": entries}), encoding="utf-8"
    )
    return database


def _main(tmp_path: Path) -> tuple[int, str]:
    stream = io.StringIO()
    code = main(
        [], config_root=CONFIG_ROOT, repo_root=tmp_path, clock=lambda: GENERATED_AT, stream=stream
    )
    return code, stream.getvalue()


def test_the_command_writes_the_page_and_leaves_the_store_untouched(tmp_path: Path, posts) -> None:
    database = _repo(tmp_path, posts)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    code, output = _main(tmp_path)
    assert code == 0
    page = tmp_path / LABELING_DIR / "label_posts.html"
    assert "(3 posts)" in output
    html = page.read_text(encoding="utf-8")
    assert [post["text"] for post in _page_data(html)["posts"]] == [p.text for p in posts[:3]]
    assert "SECRET-CASE" not in html  # the labels are blind: no case is shown
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    assert sorted(path.name for path in database.parent.iterdir()) == [SQLITE_FILENAME]


def test_the_command_reads_the_test_posts_entry(tmp_path: Path, posts) -> None:
    _test_posts(tmp_path, "#45's text")
    entry = {
        "listing_id": compute_listing_id(TEST_POST_ID),
        "case": "#45",
        "source": "data/raw/test_posts.json",
        "post_id": TEST_POST_ID,
    }
    _repo(tmp_path, posts, [_entry(posts[0].listing_id), entry])
    assert _main(tmp_path)[0] == 0
    html = (tmp_path / LABELING_DIR / "label_posts.html").read_text(encoding="utf-8")
    assert [post["text"] for post in _page_data(html)["posts"]] == [posts[0].text, "#45's text"]


def test_with_no_store_the_command_fails_and_creates_nothing(tmp_path: Path, posts) -> None:
    database = _repo(tmp_path, posts)
    database.unlink()
    code, output = _main(tmp_path)
    assert code == 1
    assert "no store" in output
    assert not database.exists()
    assert not (tmp_path / LABELING_DIR / "label_posts.html").exists()


def test_a_post_missing_from_the_store_fails_with_no_page(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts, [_entry("absent")])
    code, output = _main(tmp_path)
    assert (code, "not in the store" in output) == (1, True)
    assert not (tmp_path / LABELING_DIR / "label_posts.html").exists()


def test_with_no_regression_set_the_command_fails(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    (tmp_path / LABELING_DIR / REGRESSION_SET_FILE).unlink()
    assert _main(tmp_path)[0] == 1


def test_the_real_set_loads(tmp_path: Path) -> None:
    _fixture(PROPOSED_SET)
    assert load_regression_set(PROPOSED_SET).posts


def test_a_post_that_joined_from_the_review_gets_no_blind_label(tmp_path: Path, posts) -> None:
    entries = [_entry(posts[0].listing_id), {**_entry(posts[1].listing_id), "truth": "review"}]
    _repo(tmp_path, posts, entries)
    assert _main(tmp_path)[0] == 0
    html = (tmp_path / LABELING_DIR / "label_posts.html").read_text(encoding="utf-8")
    assert [post["listing_id"] for post in _page_data(html)["posts"]] == [posts[0].listing_id]
