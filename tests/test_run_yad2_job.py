"""The Yad2 run command (`jobs/run_yad2.py`; `PHASE_6.md` build step 5; DECISIONS.md #529): the
first run bootstraps itself, the `RunRecord` with `source` `"yad2"` from the collection's counts or
a block's reason, no store refused. A temporary store under `repo_root`, a fake browser over
synthetic pages (`tests/yad2_synthetic.py`); no browser, no network."""

import io
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from tests.conftest import CONFIG_ROOT, SQLITE_FILENAME
from tests.yad2_synthetic import FakeBrowser, page_url, site, token
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.images.download import ImageResponse
from tlv_hunter.jobs import run_yad2
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.yad2.block import PageLoad
from tlv_hunter.yad2.mapping import GROUP_ID

NOW = datetime(2026, 10, 25, 9, 0, tzinfo=UTC)
STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root


def _pages(count: int) -> dict[int, list[str]]:
    return {n: [token(n * 10 + i) for i in range(3)] + [token(n, "a")] for n in range(1, count + 1)}


def _main(tmp_path: Path, pages, *args: str) -> tuple[int, list[Path]]:
    opened: list[Path] = []

    @contextmanager
    def browser(profile: Path):
        opened.append(profile)
        yield FakeBrowser(pages)

    code = run_yad2.main(
        list(args),
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        browser_factory=browser,
        image_transport=lambda url: ImageResponse(404, None, b""),
        clock=lambda: NOW,
        sleep=lambda seconds: None,
        stream=io.StringIO(),
    )
    return code, opened


def _database(tmp_path: Path) -> Path:
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    database.parent.mkdir(parents=True, exist_ok=True)
    SqliteRepository(database)  # the store Facebook's bootstrap made
    return database


def test_without_a_store_it_refuses_and_creates_nothing(tmp_path: Path) -> None:
    code, opened = _main(tmp_path, site(_pages(3)))
    assert code == 1 and opened == []
    assert not (tmp_path / STORE_ROOT / SQLITE_FILENAME).exists()


def test_the_first_run_is_the_bootstrap_and_records_its_run(tmp_path: Path) -> None:
    database = _database(tmp_path)
    code, opened = _main(tmp_path, site(_pages(5)), "--trigger", "scheduled")
    assert code == 0
    assert opened == [tmp_path / "data" / "yad2-profile"]
    (record,) = SqliteRunStore(database).recent_runs()
    assert (record.source, record.trigger, record.status) == ("yad2", "scheduled", "succeeded")
    assert (record.rows_fetched, record.rows_skipped) == (12, 0)  # 3 pages: the bootstrap
    assert record.window_since is None and record.apify_run_id is None
    assert record.started_at == record.finished_at == NOW
    assert len(SqliteRepository(database).query()) == 12
    watermark = SqliteWatermarkStore(database).get(GROUP_ID)
    assert watermark is not None and watermark.last_success_at == NOW


def test_with_the_record_a_run_is_not_a_bootstrap(tmp_path: Path) -> None:
    database = _database(tmp_path)
    pages = _pages(5)
    assert _main(tmp_path, site(pages))[0] == 0
    pages[4] = [token(99), *pages[4][1:]]  # a new private token on page 4 only
    assert _main(tmp_path, site(pages))[0] == 0
    newest = SqliteRunStore(database).recent_runs()[0]
    assert newest.trigger == "manual" and newest.status == "succeeded"
    # Not a bootstrap: pages 1-3 hold nothing new, so the run stops at the minimum.
    assert newest.rows_fetched == 12


def test_a_blocked_run_records_its_reason_and_stores_nothing(tmp_path: Path) -> None:
    database = _database(tmp_path)
    pages = site(_pages(3))
    pages[page_url(2)] = PageLoad(
        url=page_url(2),
        final_url="https://validate.perfdrive.com/x/?ssa=1",
        html="<html></html>",
        hosts=frozenset({"www.yad2.co.il", "validate.perfdrive.com"}),
    )
    code, _ = _main(tmp_path, pages)
    assert code == 1
    (record,) = SqliteRunStore(database).recent_runs()
    assert record.status == "failed"
    assert record.failure_kind == "blocked: the page moved to validate.perfdrive.com"
    assert record.rows_fetched is None
    assert SqliteRepository(database).query() == []
    assert SqliteWatermarkStore(database).get(GROUP_ID) is None  # the next run bootstraps again


def test_the_command_reads_no_key() -> None:
    source = Path(run_yad2.__file__).read_text(encoding="utf-8")
    for name in ("APIFY_TOKEN", "OPENAI_API_KEY", "TELEGRAM_BOT_TOKEN", "environ"):
        assert name not in source, name
