"""The regression runner (`PHASE_2.md` 2.6; DECISIONS.md #142, #186–#196): the comparison
(`labeling/compare.py`), the overrides (`labeling/overrides.py`), the checks before any call
(`labeling/regression.py`) and the command (`jobs/regression_run.py`). No network: the model is
the fake transport of the classifier tests; the store is a temporary one."""

import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from tests.conftest import CONFIG_ROOT, load_openai_spike, make_listing
from tests.test_classification_run import lifecycle
from tests.test_classify_complete import extraction
from tests.test_openai_classifier import FakeTransport, with_answer
from tlv_hunter.classify.instructions import PROMPT_VERSION
from tlv_hunter.classify.transport import TransportError
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.listing import Marked
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.regression_run import main
from tlv_hunter.labeling.compare import (
    FieldResult,
    Truth,
    blind_truth,
    filled_in,
    judge,
    reaches,
    same,
)
from tlv_hunter.labeling.corrections import CORRECTIONS_FILE
from tlv_hunter.labeling.labels import PostLabel
from tlv_hunter.labeling.overrides import Overrides
from tlv_hunter.labeling.regression import prepare
from tlv_hunter.labeling.regression_set import (
    LABELING_DIR,
    TEST_POSTS_POSTED_AT,
    RegressionEntry,
    regression_posts,
    text_sha256,
)
from tlv_hunter.parsing.ids import compute_listing_id
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository

STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
KEY = "sk-test-SENTINEL-never-logged"
NOT_WRITTEN = {"state": "not_written", "value": None}
NATURE_ONLY = ["seeking", "for_sale", "not_listing", "sublet_offer"]
CLOCK = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def marked(state: str, value: Any = None) -> Marked:
    return Marked[Any](state=state, value=value)


def label_dict(text: str, **changes: Any) -> dict[str, Any]:
    """A complete label that the default model answer (`extraction()`) matches."""
    fields: dict[str, Any] = {
        "text_sha256": text_sha256(text),
        "post_nature": "rental_offer",
        "apartment_kind": NOT_WRITTEN,
        "price": NOT_WRITTEN,
        "gender": "no_restriction",
        "entry_date_parts": NOT_WRITTEN,
        "areas": [],
        "other_city": None,
        "ambiguous": False,
        "note": "",
    }
    return {**fields, **changes}


# --- comparing one field ---


def test_prices_compare_as_a_set() -> None:
    assert same("price", marked("written", [3200, 3500]), marked("written", [3500, 3200]))
    assert not same("price", marked("written", [3200]), marked("written", [3200, 3500]))
    assert not same("price", marked("unclear"), marked("not_written"))


def test_areas_compare_as_a_set_and_other_city_as_tel_aviv_or_not() -> None:
    assert same("areas", [30, 31], [31, 30])
    assert not same("areas", [30], [30, 31])
    assert same("other_city", "חולון", "בחולון")
    assert same("other_city", None, None)
    assert not same("other_city", None, "חולון")


def test_a_value_where_the_truth_says_not_written_is_filled_in() -> None:
    assert filled_in(marked("not_written"), marked("written", [3000]))
    assert not filled_in(marked("unclear"), marked("written", [3000]))
    assert not filled_in(marked("not_written"), marked("unclear"))


# --- the truth ---


def _entry(post) -> RegressionEntry:
    return RegressionEntry(listing_id=post.listing_id, case="c", source="store")


def _truth(post, nature_only=frozenset(NATURE_ONLY), not_compared=(), **label: Any) -> Truth:
    return blind_truth(
        _entry(post),
        1,
        post,
        PostLabel.model_validate(label_dict(post.text, **label)),
        nature_only=nature_only,
        not_compared=set(not_compared),
        reviewed=None,
    )


def test_the_label_goes_through_the_native_fallback_and_the_year(posts) -> None:
    post = posts[0].with_changes(native_price=4200, posted_at=datetime(2026, 10, 4, tzinfo=UTC))
    truth = _truth(
        post,
        entry_date_parts={
            "state": "written",
            "value": {"immediate": False, "day": 1, "month": 1, "year": None},
        },
    )
    assert truth.values["price"] == marked("written", [4200])
    assert truth.values["entry_date"] == marked("written", date(2027, 1, 1))


def test_a_post_labelled_with_a_nature_only_nature_compares_post_nature_only(posts) -> None:
    truth = _truth(posts[0], post_nature="seeking", price=None, areas=None, gender=None)
    assert truth.values == {"post_nature": "seeking"}


def test_a_field_not_compared_leaves_the_truth(posts) -> None:
    truth = _truth(posts[0], not_compared=("areas", "entry_date_parts"), areas=None)
    assert "areas" not in truth.values and "entry_date" not in truth.values


def test_a_blank_compared_deciding_field_refuses(posts) -> None:
    with pytest.raises(ValueError, match="not labelled: areas, price"):
        _truth(posts[0], price=None, areas=None)


# --- judging a pass ---


def test_the_bar_per_field() -> None:
    assert FieldResult("post_nature", 46, 1, 1.0).passed is False
    assert FieldResult("price", 46, 2, 0.95).passed is True  # 95.7%
    assert FieldResult("price", 46, 3, 0.95).passed is False  # 93.5%
    assert FieldResult("rooms", 0, 0, 0.90).passed is None


def test_judge_counts_mismatches_and_the_verdict(posts) -> None:
    from tlv_hunter.classify.complete import Provenance, complete

    provenance = Provenance("gpt-6-luna", "1", CLOCK)
    truths = [_truth(posts[0]), _truth(posts[1], price=NOT_WRITTEN)]
    right = complete(extraction(), posts[0], provenance).listing
    filled = complete(
        extraction(price={"state": "written", "value": [999]}),
        posts[1].with_changes(native_price=None),
        provenance,
    ).listing
    result = judge(1, truths, {posts[0].listing_id: right, posts[1].listing_id: filled})
    assert [(m.position, m.field, m.filled_in) for m in result.mismatches] == [(1, "price", True)]
    assert result.verdict == "fail"
    clean = judge(1, truths[:1], {posts[0].listing_id: right})
    assert clean.verdict == "pass on the measured fields"  # the review's fields are not measured
    assert judge(1, truths[:1], {posts[0].listing_id: None}).verdict == "incomplete"
    assert judge(1, truths[:1], {}).missing_posts == [1]


# --- the overrides ---


def _overrides(**changes: Any) -> dict[str, Any]:
    return {
        "format_version": 1,
        "approved": "test",
        "labels_sha256": "x",
        "nature_only": {"natures": NATURE_ONLY, "reason": "r"},
        "removed": [],
        "label_changes": [],
        "not_compared": [],
        **changes,
    }


def test_a_label_change_is_validated_as_labels_json_is(posts) -> None:
    lid = posts[0].listing_id
    label = PostLabel.model_validate(label_dict(posts[0].text))
    good = Overrides.model_validate(
        _overrides(
            label_changes=[
                {
                    "position": 1,
                    "listing_id": lid,
                    "field": "price",
                    "value": {"state": "written", "value": [2900]},
                    "reason": "r",
                }
            ]
        )
    )
    assert good.apply(lid, label).price.value == [2900]
    bad = Overrides.model_validate(
        _overrides(
            label_changes=[
                {"position": 1, "listing_id": lid, "field": "areas", "value": [72], "reason": "r"}
            ]
        )
    )
    with pytest.raises(ValidationError):
        bad.apply(lid, label)


def test_overrides_refuse_a_field_changed_twice_and_check_positions(posts) -> None:
    change = {"position": 1, "listing_id": "a", "field": "areas", "value": [], "reason": "r"}
    with pytest.raises(ValidationError, match="twice"):
        Overrides.model_validate(_overrides(label_changes=[change, change]))
    overrides = Overrides.model_validate(
        _overrides(removed=[{"position": 2, "listing_id": "a", "reason": "r"}])
    )
    entries = [_entry(posts[0]), _entry(posts[1])]
    assert overrides.check_positions(entries) == ["position 2: does not hold a"]


# --- #45's post ---


def test_the_test_posts_entry_is_dated_2026_09_13_and_annotated(tmp_path: Path) -> None:
    path = tmp_path / "data" / "raw" / "test_posts.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"post_id": "77", "text": "054-1234567 מחפשים"}]), encoding="utf-8")
    entry = RegressionEntry(
        listing_id=compute_listing_id("77"),
        case="#45",
        source="data/raw/test_posts.json",
        post_id="77",
    )
    (post,) = regression_posts([entry], LocalJsonRepository(tmp_path / "s"), tmp_path)
    assert post.posted_at == TEST_POSTS_POSTED_AT == datetime(2026, 9, 13, tzinfo=UTC)
    assert post.phones and post.is_canonical


# --- the checks before any call, and the command ---


def _repo(tmp_path: Path, posts, count: int = 3, labels: dict | None = None) -> tuple[Path, list]:
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    store = SqliteRepository(database)
    chosen = [post.with_changes(native_price=None) for post in posts[:count]]
    for post in chosen:
        store.upsert(post)
    labeling = tmp_path / LABELING_DIR
    labeling.mkdir(parents=True)
    entries = [{"listing_id": p.listing_id, "case": "c", "source": "store"} for p in chosen]
    (labeling / "regression_set.json").write_text(
        json.dumps({"format_version": 1, "posts": entries}), encoding="utf-8"
    )
    if labels is None:
        labels = {p.listing_id: label_dict(p.text) for p in chosen}
    (labeling / "labels.json").write_text(
        json.dumps({"format_version": 1, "exported_at": "2026-10-05T20:15:36Z", "labels": labels}),
        encoding="utf-8",
    )
    return database, chosen


def _write_overrides(tmp_path: Path, **changes: Any) -> None:
    labeling = tmp_path / LABELING_DIR
    sha = hashlib.sha256((labeling / "labels.json").read_bytes()).hexdigest()
    (labeling / "label_overrides.json").write_text(
        json.dumps(_overrides(labels_sha256=sha, **changes)), encoding="utf-8"
    )


def _prepare(tmp_path: Path):
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    return prepare(tmp_path, SqliteRepository(database, read_only=True))


def test_no_labels_file_refuses(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    (tmp_path / LABELING_DIR / "labels.json").unlink()
    assert "no labels" in _prepare(tmp_path).refusals[0]


def test_a_missing_label_an_incomplete_one_and_a_stale_one_refuse(tmp_path: Path, posts) -> None:
    chosen = [p.with_changes(native_price=None) for p in posts[:3]]
    labels = {
        chosen[0].listing_id: label_dict(chosen[0].text, areas=None),
        chosen[1].listing_id: label_dict("another text"),
    }
    _repo(tmp_path, posts, labels=labels)
    refusals = _prepare(tmp_path).refusals
    assert "position 2: label is stale" in refusals
    assert "position 1: not labelled: areas" in refusals
    assert "position 3: no label" in refusals


def test_overrides_complete_the_labels_and_remove_posts(tmp_path: Path, posts) -> None:
    chosen = [p.with_changes(native_price=None) for p in posts[:3]]
    labels = {
        chosen[0].listing_id: label_dict(
            chosen[0].text, post_nature="seeking", areas=None, price=None
        ),
        chosen[1].listing_id: label_dict(chosen[1].text, areas=None),
        chosen[2].listing_id: label_dict(chosen[2].text, price=None),
    }
    _repo(tmp_path, posts, labels=labels)
    _write_overrides(
        tmp_path,
        removed=[{"position": 3, "listing_id": chosen[2].listing_id, "reason": "r"}],
        not_compared=[
            {"position": 2, "listing_id": chosen[1].listing_id, "field": "areas", "reason": "r"}
        ],
    )
    prepared = _prepare(tmp_path)
    assert prepared.refusals == []
    assert [t.position for t in prepared.truths] == [1, 2]
    assert prepared.removed == [3]


def test_overrides_reviewed_against_another_labels_file_refuse(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    _write_overrides(tmp_path)
    labels_path = tmp_path / LABELING_DIR / "labels.json"
    labels_path.write_text(labels_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    assert "review it again" in _prepare(tmp_path).refusals[0]


def answer_response(**changes: Any) -> dict[str, Any]:
    response = load_openai_spike("none_t0_p1_01")["response"]
    return with_answer(response, extraction(**changes).model_dump(mode="json"))


def _main(tmp_path: Path, *argv: str, transport: Any = None, environ: dict | None = None):
    stream = io.StringIO()
    keys: list[str] = []

    def make_transport(key: str) -> Any:
        keys.append(key)
        return transport

    code = main(
        list(argv),
        environ={"OPENAI_API_KEY": KEY} if environ is None else environ,
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        make_transport=make_transport,
        clock=lambda: CLOCK,
        sleep=lambda seconds: None,
        stream=stream,
    )
    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    return code, lines, stream.getvalue(), keys


def _runs(tmp_path: Path) -> list[Path]:
    runs = tmp_path / LABELING_DIR / "runs"
    return sorted(runs.iterdir()) if runs.is_dir() else []


def test_check_reads_no_key_and_calls_nothing(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    code, lines, _, keys = _main(tmp_path, "--check", environ={})
    assert code == 0 and keys == []
    assert "ready: 3 posts" in lines[-1]["msg"]
    assert _runs(tmp_path) == []


def test_a_refusal_exits_1_before_the_key_and_any_call(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts, labels={})
    code, lines, _, keys = _main(tmp_path, transport=FakeTransport())
    assert code == 1 and keys == []
    assert any("refused: position 1: no label" in line["msg"] for line in lines)


def test_two_passes_a_report_and_the_store_untouched(tmp_path: Path, posts) -> None:
    database, chosen = _repo(tmp_path, posts)
    before = hashlib.sha256(database.read_bytes()).hexdigest()
    wrong = answer_response(gender="women_only")
    transport = FakeTransport(answer_response(), wrong, answer_response(), *[answer_response()] * 3)
    code, lines, raw, keys = _main(tmp_path, transport=transport)
    assert code == 0 and keys == [KEY]
    assert KEY not in raw
    assert len(transport.requests) == 6
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    (folder,) = _runs(tmp_path)
    assert folder.name.startswith(f"v{PROMPT_VERSION}-none-")
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    one, two = results["passes"]
    assert one["verdict"] == "fail" and two["verdict"] == "pass on the measured fields"
    assert one["mismatches"] == [
        {
            "position": 2,
            "listing_id": chosen[1].listing_id,
            "field": "gender",
            "truth": "no_restriction",
            "answer": "women_only",
            "filled_in": False,
        }
    ]
    assert results["flips"] == [
        {"position": 2, "field": "gender", "pass_1": "women_only", "pass_2": "no_restriction"}
    ]
    assert one["posts"][0]["listing"]["listing_id"] == chosen[0].listing_id
    report = (folder / "report.html").read_text(encoding="utf-8")
    assert "<script" not in report and "Pass 1" in report
    for line in lines:
        for post in chosen:
            assert post.text[:20] not in line["msg"]


def test_the_cap_stops_the_run_with_a_partial_report(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    transport = FakeTransport(*[answer_response()] * 6)
    # Below one call's worst case (about $0.003): the cap stops the run before its first call.
    code, lines, _, _ = _main(tmp_path, "--cap", "0.001", transport=transport)
    assert code == 2
    assert transport.requests == []
    (folder,) = _runs(tmp_path)
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    assert results["stopped"].startswith("cap")
    assert results["spent"] == 0
    assert results["passes"][0]["verdict"] == "incomplete"
    assert results["passes"][0]["missing_positions"] == [1, 2, 3]


def test_an_invalid_answer_records_its_field_paths_and_no_value(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts, count=1)
    bad = answer_response()
    bad = with_answer(bad, {**extraction().model_dump(mode="json"), "areas": [99]})
    transport = FakeTransport(bad, bad, answer_response())
    assert _main(tmp_path, transport=transport)[0] == 0
    (folder,) = _runs(tmp_path)
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    failed = results["passes"][0]["posts"][0]
    assert failed["outcome"] == "failed: invalid" and failed["attempts"] == 2
    assert failed["error"] == "invalid: areas are municipal numbers 1-71"
    assert "99" not in failed["error"]


def test_a_post_whose_attempts_are_spent_makes_the_pass_incomplete(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts, count=1)
    refused = TransportError("timeout")
    transport = FakeTransport(refused, refused, refused, answer_response())
    code, _, _, _ = _main(tmp_path, transport=transport)
    assert code == 0
    (folder,) = _runs(tmp_path)
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    assert results["passes"][0]["verdict"] == "incomplete"
    assert results["passes"][0]["failed_positions"] == [1]
    failed = results["passes"][0]["posts"][0]
    assert (failed["outcome"], failed["error"]) == ("failed: timeout", "timeout")
    assert results["passes"][1]["verdict"] == "pass on the measured fields"


# --- areas by reach (#198) ---


@pytest.mark.parametrize(
    ("truth", "answer", "ok"),
    [
        ([30], [30, 31], True),
        ([30, 31], [31], True),
        ([30], [35], False),
        ([], [], True),
        ([30], [], False),
        ([], [30], False),
    ],
)
def test_areas_reach(truth: list[int], answer: list[int], ok: bool) -> None:
    assert reaches(truth, answer) is ok


def test_areas_are_judged_by_reach_and_reported_by_exact_match(posts) -> None:
    from tlv_hunter.classify.complete import Provenance, complete

    provenance = Provenance("gpt-6-luna", "2", CLOCK)
    truths = [_truth(p, areas=[30]) for p in posts[:3]]
    answers = {
        posts[0].listing_id: [30],  # exact
        posts[1].listing_id: [30, 31, 35],  # reaches, not exact
        posts[2].listing_id: [37],  # misses
    }
    listings = {
        lid: complete(extraction(areas=areas), post, provenance).listing
        for (lid, areas), post in zip(answers.items(), posts[:3], strict=True)
    }
    # `_truth` numbers every post 1: renumber them for the report.
    truths = [Truth(t.listing_id, i, t.values, t.source) for i, t in enumerate(truths, 1)]
    result = judge(1, truths, listings)
    areas = next(f for f in result.fields if f.field == "areas")
    assert (areas.counted, areas.errors, areas.bar) == (3, 1, 0.90)
    assert areas.passed is False  # 2 of 3
    assert [(m.position, m.field) for m in result.mismatches] == [(3, "areas")]
    exact = result.areas_exact
    assert (exact.counted, exact.errors) == (3, 2)
    assert exact.average_returned == pytest.approx(5 / 3)
    assert exact.average_labelled == 1.0


def test_the_areas_bar_is_90_percent() -> None:
    assert FieldResult("areas", 30, 3, 0.90).passed is True
    assert FieldResult("areas", 30, 4, 0.90).passed is False


# --- the effort option (#201) ---


def test_effort_low_sends_no_temperature_and_is_recorded(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts, count=1)
    transport = FakeTransport(answer_response(), answer_response())
    code, _, _, _ = _main(tmp_path, "--effort", "low", transport=transport)
    assert code == 0
    for request in transport.requests:
        assert request["reasoning"] == {"effort": "low"}
        assert "temperature" not in request
    (folder,) = _runs(tmp_path)
    assert folder.name.startswith(f"v{PROMPT_VERSION}-low-")
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    assert (results["reasoning_effort"], results["temperature"]) == ("low", None)


def test_the_two_efforts_have_their_own_fingerprints(tmp_path: Path, posts) -> None:
    prints = {}
    for effort in ("none", "low"):
        root = tmp_path / effort
        _repo(root, posts, count=1)
        _main(
            root, "--effort", effort, transport=FakeTransport(answer_response(), answer_response())
        )
        (folder,) = _runs(root)
        prints[effort] = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    assert prints["none"]["prompt_fingerprint"] != prints["low"]["prompt_fingerprint"]
    assert prints["none"]["temperature"] == 0


def test_the_report_counts_the_posts_that_changed_between_the_passes(tmp_path: Path, posts) -> None:
    _repo(tmp_path, posts)
    changed = answer_response(gender="women_only")
    transport = FakeTransport(*[answer_response()] * 3, changed, answer_response(), changed)
    _main(tmp_path, transport=transport)
    (folder,) = _runs(tmp_path)
    results = json.loads((folder / "results.json").read_text(encoding="utf-8"))
    assert results["changed_posts"] == 2
    assert "in 2 posts" in (folder / "report.html").read_text(encoding="utf-8")
    assert results["passes"][0]["areas_exact"]["average_returned"] == 0.0


# --- corrections_excluded (DECISIONS.md #216) ---


def _excluded(listing_id: str, field: str) -> dict[str, str]:
    return {"listing_id": listing_id, "field": field, "reason": "r"}


def test_corrections_excluded_default_to_none_and_are_keyed_by_post_and_field() -> None:
    assert Overrides.model_validate(_overrides()).excluded_pairs() == frozenset()
    overrides = Overrides.model_validate(
        _overrides(corrections_excluded=[_excluded("a", "price"), _excluded("a", "other_city")])
    )
    assert overrides.excluded_pairs() == {("a", "price"), ("a", "other_city")}
    assert overrides.excluded_fields("a") == {"price", "other_city"}
    assert overrides.excluded_fields("b") == frozenset()


def test_an_exclusion_of_an_unknown_field_or_twice_is_refused() -> None:
    with pytest.raises(ValidationError, match="not a field of the review"):
        Overrides.model_validate(_overrides(corrections_excluded=[_excluded("a", "price_source")]))
    with pytest.raises(ValidationError, match="excluded twice"):
        Overrides.model_validate(
            _overrides(corrections_excluded=[_excluded("a", "price"), _excluded("a", "price")])
        )


def test_a_review_truth_leaves_an_excluded_field_out(tmp_path: Path, posts) -> None:
    """A post that joined from the review is compared on its corrected classification, the excluded
    fields left out of it."""

    database, chosen = _repo(tmp_path, posts, count=1)
    post = chosen[0]
    store = SqliteRepository(database)
    store.upsert_with_lifecycle(post, lifecycle(post))
    listing = make_listing(post.listing_id, post_nature="rental_offer", other_city="חולון")
    store.save_classification(
        listing, lifecycle(post, state="rejected", rejection_reason="other_city")
    )
    labeling = tmp_path / LABELING_DIR
    (labeling / "regression_set.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "posts": [
                    {
                        "listing_id": post.listing_id,
                        "case": "c",
                        "source": "store",
                        "truth": "review",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    record = {
        "text_sha256": hashlib.sha256(post.text.encode("utf-8")).hexdigest(),
        "prompt_version": listing.prompt_version,
        "model_name": listing.model_name,
        "classified_at": listing.classified_at.isoformat(),
        "reviewed": True,
        "fields": {
            "price": {"state": "written", "value": [3540000]},
            "other_city": "רמת החייל",
            "rooms": {"state": "written", "value": 3.0},
        },
        "note": "",
    }
    (labeling / CORRECTIONS_FILE).write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-06T08:00:00Z",
                "corrections": {post.listing_id: record},
            }
        ),
        encoding="utf-8",
    )

    def values() -> dict[str, Any]:
        prepared = _prepare(tmp_path)
        assert prepared.refusals == []
        (truth,) = prepared.truths
        return truth.values

    # With the city corrected to another one, only the nature and the city are compared (#240).
    assert values() == {"post_nature": "rental_offer", "other_city": "רמת החייל"}
    _write_overrides(
        tmp_path,
        corrections_excluded=[
            _excluded(post.listing_id, "price"),
            _excluded(post.listing_id, "other_city"),
        ],
    )
    kept = values()
    assert "price" not in kept and "other_city" not in kept
    assert kept["rooms"].value == 3.0  # the other correction still counts
    assert kept["post_nature"] == "rental_offer"


# --- a review post with a nature_only nature (#239) ---


def _review_post(
    tmp_path: Path,
    posts,
    *,
    nature: str,
    state: str,
    reason: str | None,
    city: str | None = "חולון",
):
    """A store with one post that joined from the review, its corrected `rooms` on file."""
    database, chosen = _repo(tmp_path, posts, count=1)
    post = chosen[0]
    store = SqliteRepository(database)
    store.upsert_with_lifecycle(post, lifecycle(post))
    listing = make_listing(post.listing_id, post_nature=nature, other_city=city)
    store.save_classification(listing, lifecycle(post, state=state, rejection_reason=reason))
    labeling = tmp_path / LABELING_DIR
    entry = {"listing_id": post.listing_id, "case": "c", "source": "store", "truth": "review"}
    (labeling / "regression_set.json").write_text(
        json.dumps({"format_version": 1, "posts": [entry]}), encoding="utf-8"
    )
    record = {
        "text_sha256": hashlib.sha256(post.text.encode("utf-8")).hexdigest(),
        "prompt_version": listing.prompt_version,
        "model_name": listing.model_name,
        "classified_at": listing.classified_at.isoformat(),
        "reviewed": True,
        "fields": {"rooms": {"state": "written", "value": 3.0}},
        "note": "",
    }
    (labeling / CORRECTIONS_FILE).write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-06T08:00:00Z",
                "corrections": {post.listing_id: record},
            }
        ),
        encoding="utf-8",
    )
    _write_overrides(tmp_path)
    prepared = _prepare(tmp_path)
    assert prepared.refusals == []
    return post, prepared.truths[0]


@pytest.mark.parametrize("nature", NATURE_ONLY)
def test_a_review_post_with_a_nature_only_nature_compares_post_nature_only(
    tmp_path: Path, posts, nature: str
) -> None:
    _, truth = _review_post(tmp_path, posts, nature=nature, state="rejected", reason="for_sale")
    assert truth.source == "review"
    assert truth.values == {"post_nature": nature}


def test_the_filled_in_rule_does_not_read_the_other_fields_of_such_a_post(
    tmp_path: Path, posts
) -> None:
    post, truth = _review_post(
        tmp_path, posts, nature="for_sale", state="rejected", reason="for_sale"
    )
    answer = make_listing(post.listing_id, post_nature="for_sale", balcony=marked("written", True))
    result = judge(1, [truth], {post.listing_id: answer})
    assert result.mismatches == [] and result.verdict == "pass on the measured fields"
    wrong = make_listing(post.listing_id, post_nature="rental_offer")
    assert [m.field for m in judge(1, [truth], {post.listing_id: wrong}).mismatches] == [
        "post_nature"
    ]


def test_a_review_post_in_tel_aviv_of_another_nature_is_compared_in_full(
    tmp_path: Path, posts
) -> None:
    """Neither `nature_only` (#239) nor the other-city rule (#240) covers a rental in Tel Aviv."""
    _, truth = _review_post(
        tmp_path, posts, nature="rental_offer", state="active", reason=None, city=None
    )
    assert set(truth.values) > {"post_nature", "rooms", "other_city", "balcony"}
    assert truth.values["rooms"].value == 3.0


def test_a_review_post_in_another_city_is_compared_on_nature_and_city_only(
    tmp_path: Path, posts
) -> None:
    post, truth = _review_post(
        tmp_path, posts, nature="rental_offer", state="rejected", reason="other_city"
    )
    assert truth.values == {"post_nature": "rental_offer", "other_city": "חולון"}
    answer = make_listing(
        post.listing_id,
        post_nature="rental_offer",
        other_city="חולון",
        balcony=marked("written", True),
        rooms=marked("written", 9.0),
    )
    result = judge(1, [truth], {post.listing_id: answer})
    assert result.mismatches == [] and result.verdict == "pass on the measured fields"


def test_a_blind_post_in_another_city_is_compared_on_nature_and_city_only(posts) -> None:
    truth = _truth(posts[0], other_city="חולון")
    assert truth.values == {"post_nature": "rental_offer", "other_city": "חולון"}
    kept = _truth(posts[0], other_city=None)
    assert {"price", "gender", "areas", "entry_date", "apartment_kind"} <= set(kept.values)


def test_an_other_city_label_that_is_not_compared_leaves_the_rest_in_place(posts) -> None:
    """The rule needs `other_city` among the compared fields: a post whose city is `not_compared`
    keeps its other fields (nothing says it is disqualified)."""
    truth = _truth(posts[0], other_city="חולון", not_compared=("other_city",))
    assert "other_city" not in truth.values and "price" in truth.values
