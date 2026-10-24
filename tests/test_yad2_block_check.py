"""The block check's command (DECISIONS.md #519, #521): no network, a fake transport. The pages are
copied into a temporary root, so the responses it saves never land in the real `data/raw/`."""

import io
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import REPO_ROOT
from tests.test_openai_classifier import FakeTransport
from tests.test_yad2_rules import answer
from tlv_hunter.jobs import yad2_block_check

pytestmark = pytest.mark.raw_fixtures

NOW = datetime(2026, 10, 24, 19, 0, tzinfo=UTC)
KEY = {"OPENAI_API_KEY": "k"}


def _root(tmp_path: Path) -> Path:
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    for name, _ in yad2_block_check.PAGES:
        source = REPO_ROOT / "data" / "raw" / name
        if not source.is_file():
            pytest.fail(f"fixture missing: {source}. data/ is gitignored; tests fail, never skip.")
        shutil.copy(source, raw / name)
    return tmp_path


def _response(**changes: Any) -> dict[str, Any]:
    text = json.dumps(answer(**changes), ensure_ascii=False)
    return {
        "status": "completed",
        "model": "gpt-6-luna",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        "usage": {"input_tokens": 4000, "output_tokens": 300},
    }


def _run(root: Path, transport: FakeTransport, out: io.StringIO) -> int:
    return yad2_block_check.main(
        [],
        environ=KEY,
        repo_root=root,
        make_transport=lambda key: transport,
        clock=lambda: NOW,
        out=out,
    )


def test_check_maps_the_pages_with_no_key_and_no_call(tmp_path: Path) -> None:
    out = io.StringIO()
    code = yad2_block_check.main(["--check"], environ={}, repo_root=_root(tmp_path), out=out)
    assert code == 0 and "3 pages mapped, prompt version 8" in out.getvalue()


def test_the_run_saves_each_response_and_prints_the_answer(tmp_path: Path) -> None:
    root = _root(tmp_path)
    transport = FakeTransport(*(_response(areas=[3]) for _ in range(3)))
    out = io.StringIO()
    assert _run(root, transport, out) == 0
    assert len(transport.requests) == 3
    for request in transport.requests:
        (user,) = [item for item in request["input"] if item["role"] == "user"]
        assert len(user["content"]) == 2
        assert user["content"][1]["text"].startswith("[Yad2 listing form")
    saved = sorted(path.name for path in (root / "data" / "raw").glob("yad2_block_check_*"))
    assert saved == [f"yad2_block_check_{n}_2026-10-24.json" for n in (1, 2, 3)]
    first = json.loads((root / "data" / "raw" / saved[0]).read_text(encoding="utf-8"))
    assert first["status"] == "completed"
    printed = out.getvalue()
    assert printed.count("accepted: yes") == 3 and "field_sources: form [" in printed
    assert "spent $" in printed and not list(root.glob("**/*.sqlite"))


def test_a_refused_call_is_reported_and_fails(tmp_path: Path) -> None:
    bad = {"status": "failed", "output": [], "usage": {}}
    out = io.StringIO()
    assert _run(_root(tmp_path), FakeTransport(bad, _response(), _response()), out) == 1
    assert "NOT accepted: invalid" in out.getvalue()


def test_no_key_no_call(tmp_path: Path) -> None:
    out = io.StringIO()
    assert yad2_block_check.main([], environ={}, repo_root=_root(tmp_path), out=out) == 1
    assert "OPENAI_API_KEY is not set" in out.getvalue()
