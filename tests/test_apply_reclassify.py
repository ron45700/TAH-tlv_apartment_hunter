"""Reclassify, stage 2, the command `tlv_hunter/jobs/apply_reclassify.py` (DECISIONS.md #217–#222).
The run folders come from the real stage 1 over a temporary store with the fake transport; the
store written here is always a temporary one."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT
from tests.test_classify_pending_job import ANSWER, answers
from tests.test_openai_classifier import FakeTransport, spike_response
from tests.test_reclassify_job import (
    STORE_ROOT,
    database,
    make_old_store,
    rental,
    run_folder,
    run_main,
    sha,
)
from tlv_hunter.classify.instructions import PROMPT_VERSION
from tlv_hunter.classify.transport import TransportError
from tlv_hunter.jobs.apply_reclassify import RUNS_DIRECTORY, main
from tlv_hunter.jobs.common import raw_post_rows
from tlv_hunter.labeling.review import dropped_names
from tlv_hunter.postmodel.reclassify import (
    ALLOW_STATE_CHANGES_FILE,
    ALLOW_UNCHANGED_FILE,
    SUMMARY_FILE,
)
from tlv_hunter.store.sqlite import SqliteRepository

CLOCK = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
BACKUP = "tlv_hunter.2026-10-08.backup.sqlite3"


def apply(tmp_path: Path, run_id: str, *argv: str) -> tuple[int, str, str]:
    out, log = io.StringIO(), io.StringIO()
    code = main(
        [run_id, *argv],
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        clock=lambda: CLOCK,
        stream=out,
        log_stream=log,
    )
    return code, out.getvalue(), log.getvalue()


def stage1(tmp_path: Path, posts, transport: Any = None, count: int = 3):
    stored = make_old_store(tmp_path, posts, count)
    code, *_ = run_main(
        tmp_path, "--run", "--cap", "1", "--limit", str(count), transport=transport or rental(count)
    )
    assert code == 0
    folder = run_folder(tmp_path)
    return stored, folder, folder.name


def listing_versions(tmp_path: Path, stored) -> list[str]:
    repository = SqliteRepository(database(tmp_path), read_only=True)
    return [repository.get_listing(p.listing_id).prompt_version for p in stored]


def backups(tmp_path: Path) -> list[Path]:
    return sorted(database(tmp_path).parent.glob("*.backup.sqlite3"))


# --- the dry run ---


def test_the_dry_run_shows_the_proposals_and_writes_nothing(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    before = sha(database(tmp_path))
    code, out, _ = apply(tmp_path, run_id)
    assert code == 0 and "dry run: nothing written" in out
    assert f"run {run_id}: 3 proposals; showing all the proposals (no --allow)" in out
    for post in stored:
        assert post.listing_id[:12] in out
    assert sha(database(tmp_path)) == before and backups(tmp_path) == []
    assert listing_versions(tmp_path, stored) == ["2", "2", "2"]


def test_the_dry_run_with_an_allow_file_checks_it_and_shows_only_those_named(
    tmp_path: Path, posts
) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    path = tmp_path / "mine.txt"
    path.write_text(f"# mine\n{stored[1].listing_id}\n", encoding="utf-8")
    code, out, _ = apply(tmp_path, run_id, "--allow-file", str(path))
    assert code == 0 and "1 named" in out
    assert stored[1].listing_id[:12] in out and stored[0].listing_id[:12] not in out


# --- the refusals: nothing is written, no backup is made ---


def refused(tmp_path: Path, run_id: str, message: str, *argv: str) -> None:
    before = sha(database(tmp_path))
    code, out, _ = apply(tmp_path, run_id, *argv)
    assert code == 1 and "refused" in out and message in out, out
    assert sha(database(tmp_path)) == before and backups(tmp_path) == []


def test_a_run_id_that_is_not_a_run_id_is_refused(tmp_path: Path, posts) -> None:
    stage1(tmp_path, posts)
    refused(tmp_path, "../../etc", "12 hexadecimal characters", "--apply", "--allow", "abcdefgh")
    refused(tmp_path, "000000000000", "no run at", "--apply", "--allow", "abcdefgh")


def test_a_missing_store_is_refused_and_not_created(tmp_path: Path) -> None:
    code, out, _ = apply(tmp_path, "0123456789ab")
    assert code == 1 and "no store at" in out and not database(tmp_path).exists()


def test_a_run_without_a_finished_report_is_refused(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    (folder / SUMMARY_FILE).unlink()
    refused(
        tmp_path, run_id, "the report was not finished", "--apply", "--allow", stored[0].listing_id
    )


def test_a_run_made_for_another_prompt_is_refused(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    summary = json.loads((folder / SUMMARY_FILE).read_text(encoding="utf-8"))
    summary["prompt_fingerprint"] = "0" * 64
    (folder / SUMMARY_FILE).write_text(json.dumps(summary), encoding="utf-8")
    refused(
        tmp_path,
        run_id,
        "another prompt than the code's",
        "--apply",
        "--allow",
        stored[0].listing_id,
    )


def test_apply_needs_an_allow(tmp_path: Path, posts) -> None:
    _, _, run_id = stage1(tmp_path, posts)
    refused(tmp_path, run_id, "--apply needs --allow or --allow-file", "--apply")


def test_there_is_no_apply_all(tmp_path: Path, posts) -> None:
    _, _, run_id = stage1(tmp_path, posts)
    with pytest.raises(SystemExit):
        apply(tmp_path, run_id, "--apply", "--all")


@pytest.mark.parametrize(
    ("allow", "message"),
    [
        ("abc", "needs at least 8 characters"),
        ("ffffffffffff", "matches no post of this run"),
    ],
)
def test_an_allow_entry_must_match_a_post_of_the_run(
    tmp_path: Path, posts, allow: str, message: str
) -> None:
    stored, _, run_id = stage1(tmp_path, posts)
    refused(tmp_path, run_id, message, "--apply", "--allow", f"{stored[0].listing_id[:12]},{allow}")


def test_one_bad_line_in_an_allow_file_refuses_the_whole_apply(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    path = tmp_path / "list.txt"
    path.write_text(f"{stored[0].listing_id}\nffffffffffff\n", encoding="utf-8")
    refused(tmp_path, run_id, "matches no post of this run", "--apply", "--allow-file", str(path))
    assert listing_versions(tmp_path, stored) == ["2", "2", "2"]  # not even the good line


def test_a_missing_allow_file_is_refused(tmp_path: Path, posts) -> None:
    _, _, run_id = stage1(tmp_path, posts)
    refused(tmp_path, run_id, "refused", "--apply", "--allow-file", str(tmp_path / "nope.txt"))


def test_a_post_that_failed_has_nothing_to_apply(tmp_path: Path, posts) -> None:
    ok = spike_response(**{**ANSWER, "post_nature": "rental_offer"})
    down = TransportError("server", status=503)
    transport = FakeTransport(ok, down, down, down, ok)
    stored, folder, run_id = stage1(tmp_path, posts, transport)
    refused(
        tmp_path,
        run_id,
        "the run has no new Listing for it",
        "--apply",
        "--allow",
        stored[1].listing_id,
    )


# --- --apply ---


def test_apply_with_the_unchanged_list_replaces_exactly_those_and_no_raw_post(
    tmp_path: Path, posts
) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    before = sha(database(tmp_path))
    rows = raw_post_rows(database(tmp_path))
    code, out, _ = apply(
        tmp_path, run_id, "--apply", "--allow-file", str(folder / ALLOW_UNCHANGED_FILE)
    )
    assert code == 0, out
    (backup,) = backups(tmp_path)
    assert backup.name == BACKUP and sha(backup) == before
    assert f"backup SHA-256: {before}" in out and str(backup) in out
    assert "stored RawPost documents identical to the backup's: True" in out
    assert raw_post_rows(database(tmp_path)) == rows  # invariant 14
    assert listing_versions(tmp_path, stored) == [PROMPT_VERSION] * 3
    assert out.count("written: ") == 3 and "still selected for reclassify, any run: 0" in out
    repository = SqliteRepository(database(tmp_path), read_only=True)
    assert all(repository.get_lifecycle(p.listing_id).state == "active" for p in stored)


def test_the_two_lists_apply_separately_and_only_what_they_name(tmp_path: Path, posts) -> None:
    transport = answers(3, post_nature="rental_offer")
    stored, folder, run_id = stage1(tmp_path, posts, transport)
    # Make the middle post a state change by hand: the proposals file is the run's record.
    lines = (folder / "proposals.jsonl").read_text(encoding="utf-8").splitlines()
    middle = json.loads(lines[1])
    middle["new"]["listing"]["post_nature"] = "seeking"
    middle["new"]["state"], middle["new"]["rejection_reason"] = "rejected", "seeking"
    lines[1] = json.dumps(middle, ensure_ascii=False)
    (folder / "proposals.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (folder / ALLOW_STATE_CHANGES_FILE).write_text(f"{stored[1].listing_id}\n", encoding="utf-8")

    code, out, _ = apply(
        tmp_path, run_id, "--apply", "--allow-file", str(folder / ALLOW_STATE_CHANGES_FILE)
    )
    assert code == 0 and out.count("written: ") == 1
    assert listing_versions(tmp_path, stored) == ["2", PROMPT_VERSION, "2"]
    record = SqliteRepository(database(tmp_path), read_only=True).get_lifecycle(
        stored[1].listing_id
    )
    assert (record.state, record.rejection_reason) == ("rejected", "seeking")
    assert f"{stored[1].listing_id[:12]} active -> rejected: seeking" in out

    code, out, _ = apply(
        tmp_path, run_id, "--apply", "--allow-file", str(folder / ALLOW_UNCHANGED_FILE)
    )
    assert code == 0 and out.count("already applied") == 1  # the middle post, done by the first
    assert listing_versions(tmp_path, stored) == [PROMPT_VERSION] * 3


def test_allow_and_several_allow_files_are_combined(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    one, two = tmp_path / "one.txt", tmp_path / "two.txt"
    one.write_text(f"{stored[0].listing_id}\n", encoding="utf-8")
    two.write_text(f"# the second\n\n{stored[1].listing_id[:20]}\n", encoding="utf-8")
    code, out, _ = apply(
        tmp_path,
        run_id,
        "--apply",
        "--allow",
        stored[0].listing_id[:10],  # also in the first file: counted once
        "--allow-file",
        str(one),
        str(two),
    )
    assert code == 0 and out.count("written: ") == 2
    assert listing_versions(tmp_path, stored) == [PROMPT_VERSION, PROMPT_VERSION, "2"]


def test_a_second_apply_is_a_no_op_and_exits_0(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    args = ("--apply", "--allow-file", str(folder / ALLOW_UNCHANGED_FILE))
    apply(tmp_path, run_id, *args)
    after_first = raw_post_rows(database(tmp_path)), listing_versions(tmp_path, stored)
    code, out, _ = apply(tmp_path, run_id, *args)
    assert code == 0 and out.count("already applied") == 3 and "written: " not in out
    assert (raw_post_rows(database(tmp_path)), listing_versions(tmp_path, stored)) == after_first
    assert len(backups(tmp_path)) == 2  # the second one has the time in its name


def test_a_post_that_changed_since_the_run_is_not_written_and_the_exit_is_2(
    tmp_path: Path, posts
) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    repository = SqliteRepository(database(tmp_path))
    record = repository.get_lifecycle(stored[1].listing_id)
    repository.save_lifecycle(
        record.model_copy(update={"state": "rejected", "rejection_reason": "seeking"})
    )
    code, out, _ = apply(
        tmp_path, run_id, "--apply", "--allow-file", str(folder / ALLOW_UNCHANGED_FILE)
    )
    assert code == 2
    assert f"NOT written: {stored[1].listing_id[:12]}: the record changed since the run" in out
    assert out.count("written: ") == 3  # "NOT written: " contains it: two written, one not
    assert listing_versions(tmp_path, stored) == [PROMPT_VERSION, "2", PROMPT_VERSION]


def test_the_dropped_names_go_to_a_file_the_review_report_reads(tmp_path: Path, posts) -> None:
    transport = answers(
        3, post_nature="rental_offer", streets=["רחוב שאינו בטקסט"], other_city="עיר שאינה בטקסט"
    )
    stored, folder, run_id = stage1(tmp_path, posts, transport)
    list_path = tmp_path / "two.txt"
    list_path.write_text("\n".join(p.listing_id for p in stored[:2]) + "\n", encoding="utf-8")
    code, out, log = apply(tmp_path, run_id, "--apply", "--allow-file", str(list_path))
    assert code == 0
    apply_run_id = json.loads(log.splitlines()[0])["run_id"] if log else None
    files = sorted((tmp_path / STORE_ROOT / RUNS_DIRECTORY).glob("*.jsonl"))
    assert len(files) == 1 and apply_run_id in files[0].name
    written = [json.loads(line) for line in files[0].read_text(encoding="utf-8").splitlines()]
    assert [line["listing_id"] for line in written] == [p.listing_id for p in stored[:2]]
    assert written[0] == {
        "listing_id": stored[0].listing_id,
        "prompt_version": PROMPT_VERSION,
        "dropped_streets": ["רחוב שאינו בטקסט"],
        "dropped_area_names": [],
        "dropped_other_city": "עיר שאינה בטקסט",
    }
    names = dropped_names(tmp_path / STORE_ROOT / RUNS_DIRECTORY)
    assert (stored[0].listing_id, PROMPT_VERSION) in names
    assert (stored[2].listing_id, PROMPT_VERSION) not in names  # not applied: no line


def test_no_dropped_names_file_when_nothing_is_written(tmp_path: Path, posts) -> None:
    stored, folder, run_id = stage1(tmp_path, posts)
    repository = SqliteRepository(database(tmp_path))
    for post in stored:
        record = repository.get_lifecycle(post.listing_id)
        repository.save_lifecycle(record.model_copy(update={"state": "archived"}))
    code, out, _ = apply(
        tmp_path, run_id, "--apply", "--allow-file", str(folder / ALLOW_UNCHANGED_FILE)
    )
    assert code == 2 and out.count("NOT written") == 3
    assert not (tmp_path / STORE_ROOT / RUNS_DIRECTORY).exists()
