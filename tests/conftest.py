import json
import socket
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tlv_hunter.contracts.field_correction import FIELD_CORRECTION_SCHEMA_VERSION, FieldCorrection
from tlv_hunter.contracts.listing import LISTING_SCHEMA_VERSION, Listing
from tlv_hunter.contracts.post_lifecycle import PostLifecycle
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.store.base import Repository
from tlv_hunter.store.local_json import LocalJsonRepository
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.textnorm.annotate import annotate

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_ROOT = REPO_ROOT / "config"
THEDOOR_20 = REPO_ROOT / "data" / "raw" / "thedoor_20posts_2026-09-13.json"
SPIKE_1_1A_PREFIX = REPO_ROOT / "data" / "raw" / "thedoor_spike_1_1a_2026-10-04"
# Spike 2.1's raw OpenAI responses and its 20 posts (DECISIONS.md #156). The answers predate #167
# and carry no `areas`: a test that needs a version-1 answer adds it in memory, never in the file.
OPENAI_SPIKE = REPO_ROOT / "data" / "raw" / "openai_spike_2026-10-05"
OPENAI_SPIKE_POSTS = REPO_ROOT / "data" / "spike_openai_2026-10-05" / "posts.json"

FETCHED_AT = datetime(2026, 9, 14, 12, 0, tzinfo=UTC)

KNOWN_DUPLICATE_PAIRS = {
    frozenset({"10163683432542695", "10163683412257695"}),
    frozenset({"2178554076041449", "2178430789387111"}),
    frozenset({"2178092279420962", "2177447349485455"}),
}


class NetworkBlockedError(RuntimeError):
    pass


def _refuse_network(*args: Any, **kwargs: Any) -> None:
    raise NetworkBlockedError("tests must not open network connections")


class RealSleepError(RuntimeError):
    pass


def _refuse_sleep(seconds: float) -> None:
    raise RealSleepError(f"tests must not really sleep ({seconds} s); inject a sleep")


@pytest.fixture(autouse=True)
def _block_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """The network waits of the photo download (DECISIONS.md #80) go through an injected sleep."""
    monkeypatch.setattr(time, "sleep", _refuse_sleep)


@pytest.fixture(autouse=True)
def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket.socket, "connect", _refuse_network)
    monkeypatch.setattr(socket.socket, "connect_ex", _refuse_network)
    monkeypatch.setattr(socket, "create_connection", _refuse_network)
    monkeypatch.setattr(socket, "getaddrinfo", _refuse_network)


def _load_fixture(path: Path) -> Any:
    if not path.is_file():
        pytest.fail(f"fixture missing: {path}. data/ is gitignored; tests fail, never skip.")
    return json.loads(path.read_text(encoding="utf-8"))


def load_thedoor_items() -> list[dict[str, Any]]:
    return _load_fixture(THEDOOR_20)


def load_openai_spike(name: str) -> Any:
    """One file of spike 2.1, by its name without `.json` (`none_t0_p1_01`, `probe_incomplete`)."""
    return _load_fixture(OPENAI_SPIKE / f"{name}.json")


def spike_answer(name: str) -> dict[str, Any]:
    """The JSON answer of one spike response, from its message item (a reasoning item can come
    first at effort `low`)."""
    response = load_openai_spike(name)["response"]
    (message,) = [item for item in response["output"] if item["type"] == "message"]
    return json.loads(message["content"][0]["text"])


def load_openai_spike_posts() -> list[dict[str, Any]]:
    return _load_fixture(OPENAI_SPIKE_POSTS)


def post_with_text(base: RawPost, text: str, **changes: Any) -> RawPost:
    """`base` with another text, annotated again (hash, phones), as a pending canonical."""
    fresh = base.with_changes(
        text=text,
        text_source="text",
        no_text=None,
        text_hash=None,
        phones=None,
        is_canonical=None,
        duplicate_of=None,
        **changes,
    )
    return annotate(fresh).with_changes(is_canonical=True)


def load_spike_1_1a(suffix: str = "") -> Any:
    """Spike 1.1a: run 1's dataset (no suffix), `_run` (run object), `_input` (its INPUT), or
    `_control` (the control run's dataset)."""
    return _load_fixture(SPIKE_1_1A_PREFIX.with_name(SPIKE_1_1A_PREFIX.name + suffix + ".json"))


NOT_WRITTEN = {"state": "not_written", "value": None}
CLASSIFIED_AT = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


def make_listing(listing_id: str, **changes: Any) -> Listing:
    """A valid Listing with every Marked field not written; `changes` override any field."""
    fields: dict[str, Any] = {
        "schema_version": LISTING_SCHEMA_VERSION,
        "listing_id": listing_id,
        "model_name": "gpt-6-luna",
        "prompt_version": "test-1",
        "classified_at": CLASSIFIED_AT,
        "post_nature": "rental_offer",
        "apartment_kind": NOT_WRITTEN,
        "price": NOT_WRITTEN,
        "price_source": None,
        "entry_date_written": None,
        "entry_date": NOT_WRITTEN,
        "rooms": NOT_WRITTEN,
        "floor": NOT_WRITTEN,
        "building_floors": NOT_WRITTEN,
        "size_sqm": NOT_WRITTEN,
        "room_size_sqm": NOT_WRITTEN,
        "broker": NOT_WRITTEN,
        "balcony": NOT_WRITTEN,
        "parking": NOT_WRITTEN,
        "elevator": NOT_WRITTEN,
        "air_conditioning": NOT_WRITTEN,
        "furnished": NOT_WRITTEN,
        "arnona": NOT_WRITTEN,
        "house_committee": NOT_WRITTEN,
        "gender": "no_restriction",
        "streets": [],
        "stated_area_names": [],
        "areas": [],
        "other_city": None,
        "phone_names": [],
    }
    return Listing.model_validate({**fields, **changes}, strict=False)


CORRECTED_AT = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)
ADMIN_ID = "a" * 32


def make_correction(
    listing: Listing, field: str, corrected_value: Any, *, removed: bool = False, n: int = 1
) -> FieldCorrection:
    """An admin's correction of one field of `listing` (Gate C): the model's value is the
    listing's own; `removed` makes it a removed one; `n` makes the id distinct."""
    return FieldCorrection(
        schema_version=FIELD_CORRECTION_SCHEMA_VERSION,
        correction_id=f"{n:032x}",
        listing_id=listing.listing_id,
        field=field,
        model_value=getattr(listing, field),
        corrected_value=corrected_value,
        corrected_by=ADMIN_ID,
        corrected_at=CORRECTED_AT,
        report_id=None,
        removed_by=ADMIN_ID if removed else None,
        removed_at=CORRECTED_AT if removed else None,
    )


@pytest.fixture
def thedoor_items() -> list[dict[str, Any]]:
    return load_thedoor_items()


@pytest.fixture
def spike_items() -> list[dict[str, Any]]:
    return load_spike_1_1a()


@pytest.fixture
def posts(thedoor_items: list[dict[str, Any]]) -> list[RawPost]:
    return [annotate(to_raw_post(item, FETCHED_AT)) for item in thedoor_items]


def overwrite_lifecycle(repository: Repository, record: PostLifecycle) -> PostLifecycle:
    """Test setup: replace a post's lifecycle record, whatever it holds now. Compare and set
    against the stored record (DECISIONS.md #260), so it never races another writer in a test."""
    return repository.save_lifecycle(record, expected=repository.get_lifecycle(record.listing_id))


def overwrite_classification(
    repository: Repository, listing: Listing, lifecycle: PostLifecycle
) -> None:
    """Test setup: `save_classification` against the stored lifecycle record, whatever it holds."""
    repository.save_classification(
        listing, lifecycle, expected=repository.get_lifecycle(lifecycle.listing_id)
    )


class AnotherWriterFirst:
    """A Repository whose first `times` lifecycle writes each meet another writer: right before
    the write, the stored record's `flag_note` is changed, as the site would change a field it
    owns (DECISIONS.md #260). Every other method passes through."""

    def __init__(self, inner: Repository, times: int = 1) -> None:
        self._inner = inner
        self.times = times
        self.interposed: list[str] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def _another_writer(self, listing_id: str) -> None:
        current = self._inner.get_lifecycle(listing_id)
        if self.times > 0 and current is not None:
            self.times -= 1
            self.interposed.append(listing_id)
            note = f"another writer {len(self.interposed)}"
            self._inner.save_lifecycle(
                current.model_copy(update={"flag_note": note}), expected=current
            )

    def save_lifecycle(
        self, record: PostLifecycle, *, expected: PostLifecycle | None
    ) -> PostLifecycle:
        self._another_writer(record.listing_id)
        return self._inner.save_lifecycle(record, expected=expected)

    def save_classification(
        self, listing: Listing, lifecycle: PostLifecycle, *, expected: PostLifecycle | None
    ) -> None:
        self._another_writer(lifecycle.listing_id)
        self._inner.save_classification(listing, lifecycle, expected=expected)


@pytest.fixture(params=["local_json", "sqlite"])
def make_repository(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[], Repository]:
    """Each call returns a fresh instance over the same storage, for every Repository."""
    if request.param == "local_json":
        return lambda: LocalJsonRepository(tmp_path)
    return lambda: SqliteRepository(tmp_path / SQLITE_FILENAME)
