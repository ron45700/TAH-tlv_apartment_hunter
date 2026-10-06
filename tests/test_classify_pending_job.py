"""The classification job's command, `tlv_hunter/jobs/classify_pending.py` (DECISIONS.md #128,
#182). The model through the fake transport of the classifier tests; no network. `repo_root` is the
test's directory, so the store never lands in the repo's `data/`."""

import io
import json
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT
from tests.test_classification_run import store_pending
from tests.test_openai_classifier import FakeTransport, spike_response
from tlv_hunter.classify.instructions import PROMPT_VERSION
from tlv_hunter.classify.transport import TransportError
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.classify_pending import RUNS_DIRECTORY, main
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.store.sqlite import SqliteRepository

KEY = "sk-test-SENTINEL-never-logged"
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
# An answer that fits any post: no names to check against its text.
ANSWER = {"streets": [], "stated_area_names": [], "other_city": None, "phone_name_pairs": []}


def database(tmp_path: Path) -> Path:
    return tmp_path / STORE_ROOT / SQLITE_FILENAME


def make_store(tmp_path: Path, posts, count: int = 3) -> list:
    path = database(tmp_path)
    path.parent.mkdir(parents=True)
    return store_pending(SqliteRepository(path), posts[:count])


def _main(
    tmp_path: Path,
    *argv: str,
    transport: Any = None,
    environ: dict[str, str] | None = None,
) -> tuple[int, list[dict[str, Any]], str, list[str]]:
    stream = io.StringIO()
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
        stream=stream,
    )
    text = stream.getvalue()
    return code, [json.loads(line) for line in text.splitlines()], text, keys


def answers(count: int, **changes: Any) -> FakeTransport:
    return FakeTransport(*[spike_response(**{**ANSWER, **changes}) for _ in range(count)])


def test_a_run_classifies_every_pending_canonical_and_exits_0(tmp_path: Path, posts) -> None:
    stored = make_store(tmp_path, posts)
    code, lines, _, keys = _main(tmp_path, "--cap", "1.00", transport=answers(3))
    assert code == 0
    assert keys == [KEY]  # read here and passed to the transport only
    repository = SqliteRepository(database(tmp_path))
    assert all(repository.get_lifecycle(p.listing_id).state != "pending" for p in stored)
    assert lines[-1]["msg"].startswith("classification done: 3 found, 0 skipped, 3 attempted")


def test_cap_is_required(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _main(tmp_path)


@pytest.mark.parametrize("cap", ["0", "-1"])
def test_cap_must_be_above_zero(tmp_path: Path, cap: str) -> None:
    with pytest.raises(SystemExit):
        _main(tmp_path, "--cap", cap)


def test_a_missing_key_exits_1_and_opens_nothing(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    code, lines, _, keys = _main(tmp_path, "--cap", "1", transport=answers(3), environ={})
    assert (code, keys) == (1, [])
    assert lines[-1]["msg"] == "OPENAI_API_KEY is not set"


def test_a_missing_store_exits_1_and_is_not_created(tmp_path: Path) -> None:
    code, lines, _, keys = _main(tmp_path, "--cap", "1", transport=answers(1))
    assert (code, keys) == (1, [])
    assert not database(tmp_path).exists()
    assert "no store at" in lines[-1]["msg"]


def test_every_line_is_json_with_one_run_id_and_the_reported_model(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    _, lines, _, _ = _main(tmp_path, "--cap", "1", transport=answers(3))
    assert len({line["run_id"] for line in lines}) == 1
    post_lines = [line for line in lines if line["msg"].startswith("post ")]
    assert len(post_lines) == 3
    assert all("reported model gpt-6-luna" in line["msg"] for line in post_lines)


@pytest.mark.parametrize(
    "transport",
    [
        "answers",
        FakeTransport(TransportError("auth", status=401, code="invalid_api_key")),
        RuntimeError("boom"),
    ],
)
def test_the_key_appears_in_no_log_line(tmp_path: Path, posts, transport: Any) -> None:
    make_store(tmp_path, posts)
    transport = answers(3) if transport == "answers" else transport
    _, _, text, _ = _main(tmp_path, "--cap", "1", transport=transport)
    assert KEY not in text


def test_a_tiny_cap_stops_before_any_call_and_exits_2(tmp_path: Path, posts) -> None:
    stored = make_store(tmp_path, posts)
    transport = answers(3)
    code, lines, _, _ = _main(tmp_path, "--cap", "0.001", transport=transport)
    assert code == 2
    assert transport.requests == []
    assert any(line["msg"].startswith("classification stopped before") for line in lines)
    record = SqliteRepository(database(tmp_path)).get_lifecycle(stored[0].listing_id)
    assert (record.state, record.classification_failures) == ("pending", 0)


def test_a_refused_key_exits_2(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    transport = FakeTransport(TransportError("auth", status=401, code="invalid_api_key"))
    code, _, _, _ = _main(tmp_path, "--cap", "1", transport=transport)
    assert code == 2


def test_an_unexpected_error_exits_1(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    code, lines, _, _ = _main(tmp_path, "--cap", "1", transport=RuntimeError("boom"))
    assert code == 1
    assert lines[-1]["msg"].startswith("run failed: RuntimeError: boom")


def test_limit(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    transport = answers(3)
    code, _, _, _ = _main(tmp_path, "--cap", "1", "--limit", "2", transport=transport)
    assert (code, len(transport.requests)) == (0, 2)


def test_the_dropped_names_file_has_one_line_per_post_written(tmp_path: Path, posts) -> None:
    stored = make_store(tmp_path, posts, count=2)
    transport = answers(2, streets=["רחוב שאינו בטקסט"], other_city="עיר שאינה בטקסט")
    _, lines, _, _ = _main(tmp_path, "--cap", "1", transport=transport)
    run_id = lines[0]["run_id"]
    path = tmp_path / STORE_ROOT / RUNS_DIRECTORY / f"{run_id}.jsonl"
    written = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [line["listing_id"] for line in written] == [p.listing_id for p in stored]
    assert written[0] == {
        "listing_id": stored[0].listing_id,
        "prompt_version": PROMPT_VERSION,
        "dropped_streets": ["רחוב שאינו בטקסט"],
        "dropped_area_names": [],
        "dropped_other_city": "עיר שאינה בטקסט",
    }


def test_no_dropped_names_file_when_nothing_is_written(tmp_path: Path, posts) -> None:
    make_store(tmp_path, posts)
    _main(tmp_path, "--cap", "0.001", transport=answers(3))
    assert not (tmp_path / STORE_ROOT / RUNS_DIRECTORY).exists()
