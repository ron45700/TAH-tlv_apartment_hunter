"""Task 1.14: the run command, `tlv_hunter/jobs/run_once.py` (DECISIONS.md #79). thedoor through
the fake Apify transport of the fetch tests, photos through a fake; no network. `repo_root` is the
test's directory, so the store never lands in the repo's `data/`."""

import io
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT, load_spike_1_1a
from tests.test_thedoor_fetch import RUN_START, TOKEN, Clock, FakeApify
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.images.download import ImageResponse
from tlv_hunter.jobs.run_once import BOOTSTRAP_WINDOW, SQLITE_FILENAME, main
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.phones import extract_phones

JPEG = ImageResponse(200, "image/jpeg", b"\xff\xd8\xff\xe0" + b"jpeg body")
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def apify(clock: Clock) -> FakeApify:
    return FakeApify(clock=clock, items=load_spike_1_1a(), run=load_spike_1_1a("_run"))


def _main(
    tmp_path: Path,
    apify: FakeApify,
    clock: Clock,
    *argv: str,
    environ: dict[str, str] | None = None,
) -> tuple[int, list[dict[str, Any]], str]:
    stream = io.StringIO()
    code = main(
        list(argv),
        environ={"APIFY_TOKEN": TOKEN} if environ is None else environ,
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        transport=apify,
        image_transport=lambda url: JPEG,
        clock=clock,
        stream=stream,
    )
    text = stream.getvalue()
    return code, [json.loads(line) for line in text.splitlines()], text


def test_the_bootstrap_window_is_24_hours() -> None:
    assert BOOTSTRAP_WINDOW == timedelta(hours=24)  # #79 D1


def test_bootstrap_creates_the_store_under_the_repo_root_and_stores_the_run(
    tmp_path: Path, apify: FakeApify, clock: Clock
) -> None:
    code, lines, _ = _main(tmp_path, apify, clock, "--bootstrap")

    assert code == 0
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    assert database.is_file()
    assert len(SqliteRepository(database).query()) == 105
    records = SqliteWatermarkStore(database).get_all()
    assert len(records) == 6 and {r.last_success_at for r in records} == {RUN_START}
    run_input = apify.calls[0][2]
    assert run_input is not None and run_input["postsNewerThan"] == "1440 minutes"
    assert lines[-1]["msg"].startswith("run done: 105 rows fetched")


def test_every_log_line_is_json_with_this_run_id(
    tmp_path: Path, apify: FakeApify, clock: Clock
) -> None:
    _, first, _ = _main(tmp_path, apify, clock, "--bootstrap")
    clock.now += timedelta(minutes=40)
    code, second, _ = _main(tmp_path, apify, clock)

    assert code == 0
    for lines in (first, second):
        assert lines
        assert all(set(line) == {"ts", "level", "logger", "run_id", "msg"} for line in lines)
        run_ids = {line["run_id"] for line in lines}
        assert len(run_ids) == 1 and len(run_ids.pop()) == 12
    assert first[0]["run_id"] != second[0]["run_id"]
    assert any(line["msg"].startswith("apify_run ") for line in second)


def test_a_normal_run_without_a_store_is_refused_and_creates_nothing(
    tmp_path: Path, apify: FakeApify, clock: Clock
) -> None:
    code, lines, _ = _main(tmp_path, apify, clock)
    assert code == 1
    assert lines[-1]["level"] == "ERROR" and "needs --bootstrap" in lines[-1]["msg"]
    assert not (tmp_path / STORE_ROOT).exists()
    assert apify.calls == []


@pytest.mark.parametrize("environ", [{}, {"APIFY_TOKEN": "  "}])
def test_a_missing_token_is_refused_before_anything(
    tmp_path: Path, apify: FakeApify, clock: Clock, environ: dict[str, str]
) -> None:
    code, lines, _ = _main(tmp_path, apify, clock, "--bootstrap", environ=environ)
    assert code == 1
    assert [line["msg"] for line in lines] == ["APIFY_TOKEN is not set"]
    assert not (tmp_path / STORE_ROOT).exists()
    assert apify.calls == []


def test_a_failed_run_exits_1_and_logs_no_token(
    tmp_path: Path, apify: FakeApify, clock: Clock
) -> None:
    apify.statuses = ["FAILED"]
    code, lines, text = _main(tmp_path, apify, clock, "--bootstrap")

    assert code == 1
    assert any(line["msg"] == "run failed at step fetch (ProviderRunError)" for line in lines)
    failure = lines[-1]["msg"]
    run_id = apify.run["id"]
    assert failure.startswith(f"run failed: ProviderRunError: apify_run {run_id} ended FAILED")
    assert TOKEN not in text
    assert SqliteWatermarkStore(tmp_path / STORE_ROOT / SQLITE_FILENAME).get_all() == []


def test_the_token_never_reaches_the_log(tmp_path: Path, apify: FakeApify, clock: Clock) -> None:
    _, _, text = _main(tmp_path, apify, clock, "--bootstrap")
    assert text and TOKEN not in text


def test_the_log_carries_no_post_text_or_phone_numbers(
    tmp_path: Path, apify: FakeApify, clock: Clock
) -> None:
    _, _, text = _main(tmp_path, apify, clock, "--bootstrap")
    texts = [item["text"] for item in apify.items if item["text"].strip()]
    phones = {phone for item_text in texts for phone in extract_phones(item_text)}
    assert texts and phones
    assert not any(json.dumps(item_text, ensure_ascii=False)[1:-1] in text for item_text in texts)
    assert not any(phone in text.replace("-", "") for phone in phones)
