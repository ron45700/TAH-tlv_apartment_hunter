"""The review report (`PHASE_2.md` 2.7; DECISIONS.md #143, #172, #193, #195): `corrections.json`
(`labeling/corrections.py`), the cards and the page (`labeling/review.py`), and the command
(`jobs/review_page.py`). No network; the store is a temporary one."""

import hashlib
import io
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, make_listing
from tests.test_classification_run import lifecycle
from tlv_hunter.areas.reference import load_areas
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.classify_pending import RUNS_DIRECTORY
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.review_page import main
from tlv_hunter.labeling.corrections import (
    CorrectionFile,
    corrected_listing,
    find_reviewed,
)
from tlv_hunter.labeling.regression_set import LABELING_DIR, text_sha256
from tlv_hunter.labeling.review import (
    TEMPLATE,
    ReviewCard,
    add_corrected_to_set,
    dropped_names,
    render_review_page,
    run_cards,
)
from tlv_hunter.store.sqlite import SqliteRepository

STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
CLASSIFIED_AT = "2026-10-05T12:00:00Z"
GENERATED_AT = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def correction(text: str, **changes: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "text_sha256": text_sha256(text),
        "prompt_version": "test-1",
        "model_name": "gpt-6-luna",
        "classified_at": CLASSIFIED_AT,
        "reviewed": True,
        "fields": {},
        "note": "",
    }
    return {**fields, **changes}


def corrections_file(records: dict[str, dict]) -> CorrectionFile:
    return CorrectionFile.model_validate(
        {"format_version": 1, "exported_at": "2026-10-06T08:00:00Z", "corrections": records}
    )


# --- corrections.json ---


def test_errors_per_field_count_reviewed_posts_only() -> None:
    file = corrections_file(
        {
            "a": correction("x", fields={"rooms": {"state": "written", "value": 3.0}}),
            "b": correction(
                "y", fields={"rooms": {"state": "unclear", "value": None}, "floor": NOT}
            ),
            "c": correction(
                "z", reviewed=False, fields={"rooms": {"state": "unclear", "value": None}}
            ),
            "d": correction("w"),
        }
    )
    errors = file.errors_per_field()
    assert (errors["rooms"], errors["floor"], errors["price"]) == (2, 1, 0)
    assert len(file.reviewed()) == 3
    assert file.corrected_ids() == ["a", "b"]


NOT = {"state": "not_written", "value": None}


@pytest.mark.parametrize(
    "fields",
    [
        {"rooms": {"state": "written", "value": "three"}},
        {"price_source": "text"},
        {"listing_id": "x"},
        {"areas": "30"},
        {"price": {"state": "written", "value": None}},
    ],
)
def test_a_correction_of_the_wrong_type_or_field_is_refused(fields: dict) -> None:
    with pytest.raises(ValidationError):
        corrections_file({"a": correction("x", fields=fields)})


def test_the_corrected_listing_follows_the_corrections_and_the_price_source() -> None:
    listing = make_listing("a" * 64)
    record = corrections_file(
        {
            "a": correction(
                "x", fields={"price": {"state": "written", "value": [4000]}, "areas": [30]}
            )
        }
    ).corrections["a"]
    corrected = corrected_listing(listing, record)
    assert corrected.price.value == [4000] and corrected.price_source == "text"
    assert corrected.areas == [30]
    other = make_listing("a" * 64, prompt_version="test-2")
    with pytest.raises(ValueError, match="another classification"):
        corrected_listing(other, record)
    unsorted = corrections_file({"a": correction("x", fields={"areas": [31, 30]})}).corrections["a"]
    with pytest.raises(ValidationError):
        corrected_listing(listing, unsorted)


def test_the_reviewed_classification_is_found_in_a_run(tmp_path: Path) -> None:
    listing = make_listing("a" * 64)
    record = corrections_file({"a": correction("x")}).corrections["a"]
    assert find_reviewed("a" * 64, record, None, tmp_path) is None
    run = tmp_path / "v1-x-run"
    run.mkdir()
    (run / "results.json").write_text(
        json.dumps({"passes": [{"posts": [{"listing": listing.model_dump(mode="json")}]}]}),
        encoding="utf-8",
    )
    assert find_reviewed("a" * 64, record, None, tmp_path) == listing
    assert find_reviewed("a" * 64, record, listing, tmp_path / "none") == listing


# --- dropped names, cards, the set ---


def test_dropped_names_take_the_newest_line_per_post_and_version(tmp_path: Path) -> None:
    old, new = tmp_path / "old.jsonl", tmp_path / "new.jsonl"
    line = {
        "listing_id": "a",
        "prompt_version": "1",
        "dropped_area_names": [],
        "dropped_other_city": None,
    }
    old.write_text(json.dumps({**line, "dropped_streets": ["x"]}) + "\n", encoding="utf-8")
    new.write_text(json.dumps({**line, "dropped_streets": ["y"]}) + "\n", encoding="utf-8")
    os.utime(old, (1_000, 1_000))
    os.utime(new, (2_000, 2_000))
    assert dropped_names(tmp_path)[("a", "1")]["dropped_streets"] == ["y"]
    assert dropped_names(tmp_path / "absent") == {}


def _run_folder(root: Path, listing, text: str, **post: Any) -> Path:
    run = root / "v1-x-run"
    run.mkdir(parents=True)
    entry = {
        "listing_id": listing.listing_id,
        "text_sha256": text_sha256(text),
        "listing": listing.model_dump(mode="json"),
        "dropped_streets": ["רחוב"],
        "dropped_area_names": [],
        "dropped_other_city": None,
        **post,
    }
    (run / "results.json").write_text(
        json.dumps({"passes": [{"posts": [entry]}]}, ensure_ascii=False), encoding="utf-8"
    )
    return run


def test_run_cards_read_pass_1_and_refuse_a_changed_text(tmp_path: Path) -> None:
    listing = make_listing("a" * 64, post_nature="seeking")
    run = _run_folder(tmp_path, listing, "text")
    (card,) = run_cards(run, {"a" * 64: "text"})
    assert (card.rejection_reason, card.dropped_streets) == ("seeking", ("רחוב",))
    with pytest.raises(ValueError, match="text changed"):
        run_cards(run, {"a" * 64: "other"})


def test_corrected_posts_join_the_set_once(tmp_path: Path) -> None:
    path = tmp_path / "regression_set.json"
    path.write_text(
        json.dumps(
            {"format_version": 1, "posts": [{"listing_id": "a", "case": "c", "source": "store"}]}
        ),
        encoding="utf-8",
    )
    file = corrections_file(
        {
            "a": correction("x", fields={"rooms": NOT}),
            "b": correction("y", fields={"floor": NOT, "rooms": NOT}),
            "c": correction("z"),
            "d": correction("w", fields={"rooms": NOT}),
        }
    )
    assert add_corrected_to_set(path, file, {"a", "b", "c"}) == ["b"]
    posts = json.loads(path.read_text(encoding="utf-8"))["posts"]
    assert posts[-1] == {
        "listing_id": "b",
        "case": "corrected in review: floor, rooms",
        "source": "store",
        "truth": "review",
    }
    assert add_corrected_to_set(path, file, {"a", "b", "c"}) == []


# --- the page ---


def _page_data(html: str) -> dict:
    match = re.search(r'<script type="application/json" id="page-data">(.*?)</script>', html, re.S)
    assert match is not None
    return json.loads(match.group(1))


def _card(text: str = "מתפנה חדר </script><script>alert(1)</script>") -> ReviewCard:
    return ReviewCard("a" * 64, text, make_listing("a" * 64), None, (), (), None)


def test_the_page_carries_the_text_exactly_and_every_correctable_field() -> None:
    card = _card()
    html = render_review_page(
        [card],
        load_areas(),
        set_positions={"a" * 64: 7},
        corrections=None,
        source="s",
        generated_at=GENERATED_AT,
    )
    assert "<script>alert(1)" not in html
    data = _page_data(html)
    (shown,) = data["cards"]
    assert shown["text"] == card.text and shown["position"] == 7
    assert shown["listing"]["classified_at"] == CLASSIFIED_AT
    assert "price_source" not in data["fields"] and "areas" in data["fields"]
    assert data["errors"] is None


def test_the_review_page_loads_nothing_from_outside() -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    assert re.search(r"<script[^>]*\bsrc=", template) is None
    for word in ("<link", "@import", "url(", "http"):
        assert word not in template


# --- the command ---


def _store(tmp_path: Path, posts, count: int = 2) -> tuple[Path, list]:
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    store = SqliteRepository(database)
    chosen = posts[:count]
    for post in chosen:
        store.upsert_with_lifecycle(post, lifecycle(post))
    store.save_classification(make_listing(chosen[0].listing_id), lifecycle(chosen[0]))
    labeling = tmp_path / LABELING_DIR
    labeling.mkdir(parents=True)
    (labeling / "regression_set.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "posts": [{"listing_id": chosen[1].listing_id, "case": "c", "source": "store"}],
            }
        ),
        encoding="utf-8",
    )
    return database, chosen


def _main(tmp_path: Path, *argv: str) -> tuple[int, str]:
    stream = io.StringIO()
    code = main(
        list(argv),
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        clock=lambda: GENERATED_AT,
        stream=stream,
    )
    return code, stream.getvalue()


def test_the_command_reviews_the_store_and_leaves_it_untouched(tmp_path: Path, posts) -> None:
    database, chosen = _store(tmp_path, posts)
    runs = tmp_path / STORE_ROOT / RUNS_DIRECTORY
    runs.mkdir()
    (runs / "r.jsonl").write_text(
        json.dumps(
            {
                "listing_id": chosen[0].listing_id,
                "prompt_version": "test-1",
                "dropped_streets": ["x"],
                "dropped_area_names": [],
                "dropped_other_city": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    code, output = _main(tmp_path)
    assert code == 0 and "(1 posts)" in output
    data = _page_data((tmp_path / LABELING_DIR / "review.html").read_text(encoding="utf-8"))
    (card,) = data["cards"]
    assert card["text"] == chosen[0].text and card["dropped_streets"] == ["x"]
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_corrections_are_counted_and_corrected_posts_join_the_set(tmp_path: Path, posts) -> None:
    _, chosen = _store(tmp_path, posts)
    labeling = tmp_path / LABELING_DIR
    (labeling / "corrections.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-06T08:00:00Z",
                "corrections": {
                    chosen[0].listing_id: correction(chosen[0].text, fields={"rooms": NOT})
                },
            }
        ),
        encoding="utf-8",
    )
    code, output = _main(tmp_path)
    assert code == 0
    assert "rooms: 1 of 1" in output
    assert f"joined the regression set: {chosen[0].listing_id}" in output
    entries = json.loads((labeling / "regression_set.json").read_text(encoding="utf-8"))["posts"]
    assert entries[-1]["truth"] == "review"
    data = _page_data((labeling / "review.html").read_text(encoding="utf-8"))
    assert data["errors"]["rooms"] == 1 and data["reviewed"] == 1


def test_a_stale_correction_fails_with_nothing_written(tmp_path: Path, posts) -> None:
    _, chosen = _store(tmp_path, posts)
    labeling = tmp_path / LABELING_DIR
    (labeling / "corrections.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-06T08:00:00Z",
                "corrections": {chosen[0].listing_id: correction("another text")},
            }
        ),
        encoding="utf-8",
    )
    code, output = _main(tmp_path)
    assert code == 1 and "text changed" in output
    assert not (labeling / "review.html").exists()


def test_the_command_reviews_a_runs_pass_1(tmp_path: Path, posts) -> None:
    _, chosen = _store(tmp_path, posts)
    listing = make_listing(chosen[1].listing_id)
    _run_folder(tmp_path / LABELING_DIR / "runs", listing, chosen[1].text)
    code, output = _main(tmp_path, "--run", "v1-x-run")
    assert code == 0 and "pass 1 of regression run" not in output
    data = _page_data((tmp_path / LABELING_DIR / "review.html").read_text(encoding="utf-8"))
    assert data["source"] == "pass 1 of regression run v1-x-run"
    assert [card["listing_id"] for card in data["cards"]] == [chosen[1].listing_id]
    assert _main(tmp_path, "--run", "absent")[0] == 1
