from pathlib import Path

import pytest

import tests.conftest as conftest


def test_missing_fixture_fails_instead_of_skipping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(conftest, "THEDOOR_20", tmp_path / "absent.json")
    with pytest.raises(pytest.fail.Exception):
        conftest.load_thedoor_items()


def test_missing_spike_fixture_fails_instead_of_skipping(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(conftest, "SPIKE_1_1A_PREFIX", tmp_path / "absent")
    with pytest.raises(pytest.fail.Exception):
        conftest.load_spike_1_1a()
