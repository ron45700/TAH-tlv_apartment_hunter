"""Reclassify, stage 1, the command `tlv_hunter/jobs/reclassify.py` (DECISIONS.md #217–#222). The
model through the fake transport of the classifier tests; no network. `repo_root` is the test's
directory, so the store never lands in the repo's `data/`. The store is a temporary one."""

import hashlib
import html
import io
import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT, make_listing
from tests.test_classification_run import lifecycle, store_pending
from tests.test_classify_pending_job import KEY, answers
from tests.test_openai_classifier import FakeTransport
from tlv_hunter.classify.instructions import PROMPT_FINGERPRINT, PROMPT_VERSION
from tlv_hunter.classify.transport import TransportError
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.reclassify import main
from tlv_hunter.labeling.regression_set import LABELING_DIR, text_sha256
from tlv_hunter.postmodel.reclassify import (
    ALLOW_STATE_CHANGES_FILE,
    ALLOW_UNCHANGED_FILE,
    PROPOSALS_FILE,
    RECLASSIFY_DIRECTORY,
    REPORT_FILE,
    SUMMARY_FILE,
)
from tlv_hunter.postmodel.reclassify_report import read_allow_file, read_proposals
from tlv_hunter.store.sqlite import SqliteRepository

STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root


def rental(count: int) -> FakeTransport:
    return answers(count, post_nature="rental_offer")


def database(tmp_path: Path) -> Path:
    return tmp_path / STORE_ROOT / SQLITE_FILENAME


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_old_store(tmp_path: Path, posts, count: int = 3, version: str = "2") -> list:
    """`count` canonicals, active, classified at `version`: selected when it is not the current."""
    path = database(tmp_path)
    path.parent.mkdir(parents=True)
    repository = SqliteRepository(path)
    stored = store_pending(repository, posts[:count])
    for post in stored:
        repository.save_classification(
            make_listing(post.listing_id, prompt_version=version),
            lifecycle(post, state="active"),
        )
    return stored


def run_main(
    tmp_path: Path,
    *argv: str,
    transport: Any = None,
    environ: dict[str, str] | None = None,
) -> tuple[int, str, list[dict[str, Any]], list[str], str]:
    out, log = io.StringIO(), io.StringIO()
    keys: list[str] = []

    def make_transport(key: str) -> Any:
        keys.append(key)
        if isinstance(transport, Exception):
            raise transport
        return transport

    code = main(
        list(argv),
        environ={"OPENAI_API_KEY": KEY} if environ is None else environ,
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        make_transport=make_transport,
        sleep=lambda seconds: None,
        stream=out,
        log_stream=log,
    )
    lines = [json.loads(line) for line in log.getvalue().splitlines()]
    return code, out.getvalue(), lines, keys, log.getvalue()


def run_folder(tmp_path: Path) -> Path:
    (folder,) = (tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY).iterdir()
    return folder


# --- the plan ---


def test_the_plan_needs_no_key_calls_nothing_and_writes_nothing(tmp_path: Path, posts) -> None:
    make_old_store(tmp_path, posts)
    before = sha(database(tmp_path))
    code, out, _, keys, _ = run_main(tmp_path, environ={})
    assert code == 0 and keys == []
    assert "reclassify plan: nothing written, no call" in out
    assert f"current: prompt {PROMPT_VERSION} / schema 1 / gpt-6-luna" in out
    assert "stored Listings: 3" in out and "prompt 2 / schema 1 / gpt-6-luna: 3" in out
    assert "selected: 3; to ask about with these flags: 3" in out
    assert "estimate: 3 x $0.000219 = $0.0007" in out and "worst case of one call" in out
    assert "--run --cap <USD> --limit 3" in out
    assert sha(database(tmp_path)) == before
    assert not (tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY).exists()


def test_the_plan_of_a_store_where_everything_is_current_has_nothing_to_do(
    tmp_path: Path, posts
) -> None:
    make_old_store(tmp_path, posts, version=PROMPT_VERSION)
    code, out, _, _, _ = run_main(tmp_path, environ={})
    assert code == 0 and "selected: 0" in out and "nothing to reclassify" in out
    assert "left out, current: 3" in out


def test_the_plan_narrows_with_limit_and_allow(tmp_path: Path, posts) -> None:
    stored = make_old_store(tmp_path, posts)
    _, out, _, _, _ = run_main(tmp_path, "--limit", "2", environ={})
    assert "selected: 3; to ask about with these flags: 2" in out
    _, out, _, _, _ = run_main(tmp_path, "--allow", stored[1].listing_id[:10], environ={})
    assert "to ask about with these flags: 1" in out and stored[1].listing_id[:12] in out


def write_corrections(tmp_path: Path, post, fields: dict[str, Any]) -> None:
    listing = make_listing(post.listing_id, prompt_version="2")
    folder = tmp_path / LABELING_DIR
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "text_sha256": text_sha256(post.text),
        "prompt_version": listing.prompt_version,
        "model_name": listing.model_name,
        "classified_at": listing.classified_at.isoformat(),
        "reviewed": True,
        "fields": fields,
        "note": "",
    }
    (folder / "corrections.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-08T08:00:00Z",
                "corrections": {post.listing_id: record},
            }
        ),
        encoding="utf-8",
    )


def test_the_plan_and_the_proposals_mark_a_post_with_a_reviewed_correction(
    tmp_path: Path, posts
) -> None:
    stored = make_old_store(tmp_path, posts)
    write_corrections(tmp_path, stored[0], {"gender": "women_only"})
    _, out, _, _, _ = run_main(tmp_path, environ={})
    assert "reviewed by Ron, corrected gender" in out
    assert out.count("reviewed by Ron") == 1
    run_main(tmp_path, "--run", "--cap", "1", "--limit", "3", transport=answers(3))
    proposals = {p.listing_id: p for p in read_proposals(run_folder(tmp_path) / PROPOSALS_FILE)}
    assert proposals[stored[0].listing_id].reviewed
    assert proposals[stored[0].listing_id].corrected_fields == ["gender"]
    assert not proposals[stored[1].listing_id].reviewed
    assert "Posts with a reviewed correction on file (1)" in (
        run_folder(tmp_path) / REPORT_FILE
    ).read_text(encoding="utf-8")


# --- the refusals, before any key is used and any call is made ---


@pytest.mark.parametrize(
    ("argv", "environ", "message"),
    [
        (("--cap", "1"), None, "--cap goes with --run"),
        (("--run",), None, "--run needs --cap"),
        (("--run", "--cap", "1"), None, "--run needs --limit or --allow"),
        (("--run", "--cap", "1", "--limit", "2"), {}, "OPENAI_API_KEY is not set"),
        (("--run", "--cap", "1", "--allow", "abc"), None, "at least 8 characters"),
        (("--run", "--cap", "1", "--allow", "ffffffffffff"), None, "no selected post starts"),
    ],
)
def test_refusals_exit_1_with_nothing_called_or_written(
    tmp_path: Path, posts, argv: tuple[str, ...], environ: dict | None, message: str
) -> None:
    make_old_store(tmp_path, posts)
    before = sha(database(tmp_path))
    transport = answers(3)
    code, out, _, keys, _ = run_main(tmp_path, *argv, transport=transport, environ=environ)
    assert code == 1 and "refused" in out and message in out
    assert transport.requests == [] and keys == []
    assert sha(database(tmp_path)) == before
    assert not (tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY).exists()


@pytest.mark.parametrize("cap", ["0", "-1"])
def test_cap_must_be_above_zero(tmp_path: Path, cap: str) -> None:
    with pytest.raises(SystemExit):
        run_main(tmp_path, "--run", "--cap", cap, "--limit", "1")


def test_a_missing_store_is_refused_and_not_created(tmp_path: Path) -> None:
    for argv in ((), ("--run", "--cap", "1", "--limit", "1")):
        code, out, _, keys, _ = run_main(tmp_path, *argv, transport=answers(1))
        assert code == 1 and "no store at" in out and keys == []
    assert not database(tmp_path).exists()


# --- --run ---


def test_a_run_writes_the_report_and_the_lists_and_never_the_store(tmp_path: Path, posts) -> None:
    stored = make_old_store(tmp_path, posts)
    before = sha(database(tmp_path))
    code, out, lines, keys, raw_log = run_main(
        tmp_path, "--run", "--cap", "1", "--limit", "3", transport=rental(3)
    )
    assert code == 0 and keys == [KEY]
    assert sha(database(tmp_path)) == before  # opened read-only: not a byte differs
    assert "the store was not written" in out

    folder = run_folder(tmp_path)
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        [PROPOSALS_FILE, SUMMARY_FILE, REPORT_FILE, ALLOW_UNCHANGED_FILE, ALLOW_STATE_CHANGES_FILE]
    )
    assert len({line["run_id"] for line in lines}) == 1
    assert folder.name == lines[0]["run_id"]

    summary = json.loads((folder / SUMMARY_FILE).read_text(encoding="utf-8"))
    assert summary["complete"] is True and summary["stopped"] is None
    assert summary["current_prompt_version"] == PROMPT_VERSION
    assert summary["prompt_fingerprint"] == PROMPT_FINGERPRINT
    assert (summary["selected"], summary["attempted"], summary["proposed"], summary["failed"]) == (
        3,
        3,
        3,
        0,
    )
    assert summary["selected_by_triple"] == [
        {"prompt_version": "2", "schema_version": 1, "model_name": "gpt-6-luna", "count": 3}
    ]
    assert summary["reported_models"] == ["gpt-6-luna"] and summary["calls"] == 3
    assert 0 < summary["spent"] < 0.01

    proposals = read_proposals(folder / PROPOSALS_FILE)
    assert [p.listing_id for p in proposals] == [p.listing_id for p in stored]
    assert all(p.new.listing.prompt_version == PROMPT_VERSION for p in proposals)
    assert all(p.old.listing.prompt_version == "2" for p in proposals)

    # A rental offer for the three: no status changes, three on the one list.
    assert read_allow_file(folder / ALLOW_UNCHANGED_FILE) == [p.listing_id for p in stored]
    assert read_allow_file(folder / ALLOW_STATE_CHANGES_FILE) == []

    page = (folder / REPORT_FILE).read_text(encoding="utf-8")
    assert html.escape(stored[0].text) in page  # the original text, escaped
    assert "No post changes state." in page

    # No key anywhere; the log lines hold ids and counts, never a post's text.
    everything = out + raw_log + page + (folder / SUMMARY_FILE).read_text(encoding="utf-8")
    assert KEY not in everything
    post_lines = [line["msg"] for line in lines if line["msg"].startswith("post ")]
    assert len(post_lines) == 3
    assert all(post.text[:20] not in raw_log for post in stored)
    assert all("reported model gpt-6-luna" in line for line in post_lines)


def test_limit_and_allow_choose_the_posts(tmp_path: Path, posts) -> None:
    stored = make_old_store(tmp_path, posts)
    transport = answers(3)
    code, *_ = run_main(tmp_path, "--run", "--cap", "1", "--limit", "2", transport=transport)
    assert code == 0 and len(transport.requests) == 2
    shutil_run = run_folder(tmp_path)
    assert [p.listing_id for p in read_proposals(shutil_run / PROPOSALS_FILE)] == [
        p.listing_id for p in stored[:2]
    ]


def test_allow_names_one_post(tmp_path: Path, posts) -> None:
    stored = make_old_store(tmp_path, posts)
    transport = answers(3)
    run_main(
        tmp_path,
        "--run",
        "--cap",
        "1",
        "--allow",
        stored[2].listing_id[:9],
        transport=transport,
    )
    (proposal,) = read_proposals(run_folder(tmp_path) / PROPOSALS_FILE)
    assert proposal.listing_id == stored[2].listing_id and len(transport.requests) == 1


def test_a_state_change_goes_on_its_own_list(tmp_path: Path, posts) -> None:
    stored = make_old_store(tmp_path, posts)
    transport = answers(3, post_nature="seeking")
    run_main(tmp_path, "--run", "--cap", "1", "--limit", "3", transport=transport)
    folder = run_folder(tmp_path)
    assert read_allow_file(folder / ALLOW_STATE_CHANGES_FILE) == [p.listing_id for p in stored]
    assert read_allow_file(folder / ALLOW_UNCHANGED_FILE) == []
    page = (folder / REPORT_FILE).read_text(encoding="utf-8")
    assert "State changes (3)" in page and "rejected: seeking" in page


def test_a_tiny_cap_stops_before_any_call_and_exits_2_with_a_report(tmp_path: Path, posts) -> None:
    make_old_store(tmp_path, posts)
    transport = answers(3)
    code, _, lines, _, _ = run_main(
        tmp_path, "--run", "--cap", "0.001", "--limit", "3", transport=transport
    )
    assert code == 2 and transport.requests == []
    summary = json.loads((run_folder(tmp_path) / SUMMARY_FILE).read_text(encoding="utf-8"))
    assert summary["complete"] and "cap" in summary["stopped"]
    assert (summary["attempted"], summary["not_attempted"]) == (0, 3)
    assert any(line["msg"].startswith("reclassify stopped before") for line in lines)


def test_a_refused_key_exits_2_and_the_report_says_so(tmp_path: Path, posts) -> None:
    make_old_store(tmp_path, posts)
    transport = FakeTransport(TransportError("auth", status=401, code="invalid_api_key"))
    code, _, _, _, raw_log = run_main(
        tmp_path, "--run", "--cap", "1", "--limit", "3", transport=transport
    )
    assert code == 2 and KEY not in raw_log
    summary = json.loads((run_folder(tmp_path) / SUMMARY_FILE).read_text(encoding="utf-8"))
    assert summary["stopped"] is not None and summary["proposed"] == 0


def test_an_unexpected_error_exits_1_and_leaves_no_finished_report(tmp_path: Path, posts) -> None:
    make_old_store(tmp_path, posts)
    code, _, lines, _, _ = run_main(
        tmp_path, "--run", "--cap", "1", "--limit", "3", transport=RuntimeError("boom")
    )
    assert code == 1 and lines[-1]["msg"].startswith("run failed: RuntimeError: boom")
    assert not (tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY).exists()


def test_a_run_killed_after_some_posts_keeps_their_lines_and_has_no_summary(
    tmp_path: Path, posts, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tlv_hunter.jobs.reclassify as module

    make_old_store(tmp_path, posts)

    def killed(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("killed while writing the report")

    monkeypatch.setattr(module, "write_run_files", killed)
    code, *_ = run_main(tmp_path, "--run", "--cap", "1", "--limit", "3", transport=answers(3))
    assert code == 1
    folder = run_folder(tmp_path)
    assert len(read_proposals(folder / PROPOSALS_FILE)) == 3  # every paid answer is kept
    assert not (folder / SUMMARY_FILE).exists()


def test_a_run_with_nothing_selected_makes_no_call_and_no_folder(tmp_path: Path, posts) -> None:
    make_old_store(tmp_path, posts, version=PROMPT_VERSION)
    transport = answers(1)
    code, out, _, _, _ = run_main(
        tmp_path, "--run", "--cap", "1", "--limit", "5", transport=transport
    )
    assert code == 0 and "nothing selected" in out and transport.requests == []
    assert not (tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY).exists()


def test_the_state_changes_table_shows_the_city_from_facebook_and_its_source(
    tmp_path: Path, posts
) -> None:
    """DECISIONS.md #214: a post whose location field names Holon is rejected `other_city`, whatever
    the model returned; the page says which city and where it came from."""
    stored = make_old_store(tmp_path, posts)
    repository = SqliteRepository(database(tmp_path))
    repository.upsert(stored[1].with_changes(native_location="חולון, תל אביב"))
    run_main(tmp_path, "--run", "--cap", "1", "--limit", "3", transport=rental(3))
    page = (run_folder(tmp_path) / REPORT_FILE).read_text(encoding="utf-8")
    assert "State changes (1)" in page
    assert "was חולון (native_location); becomes חולון (native_location)" in page
    assert page.count("(native_location)") == 2  # only the one row
