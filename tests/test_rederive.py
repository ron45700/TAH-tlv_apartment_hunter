"""Re-deriving the stored rejections with the native-location rule (DECISIONS.md #214):
`tlv_hunter/postmodel/rederive.py` and the command `tlv_hunter/jobs/rederive_rejections.py`. No
model, no network; the store is a temporary one."""

import hashlib
import io
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT, make_listing, post_with_text
from tests.test_classification_run import lifecycle
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.jobs import rederive_rejections
from tlv_hunter.jobs.common import SQLITE_FILENAME
from tlv_hunter.jobs.rederive_rejections import main
from tlv_hunter.postmodel.rederive import plan_rederivation, rederived_lifecycle
from tlv_hunter.store.sqlite import SqliteRepository

STORE_ROOT = YamlConfig(CONFIG_ROOT).collection().store_root
CLOCK = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
TLV = "תל אביב - יפו, תל אביב"

# (name, native location, model city, model nature, state, reason) and what the rule makes of it.
CASES = {
    "cleared": (TLV, "עין ורד", "rental_offer", "rejected", "other_city"),
    "caught": ("רמת גן, תל אביב", None, "rental_offer", "active", None),
    "relabelled": ("באר שבע, ישראל", None, "not_listing", "rejected", "not_listing"),
    "same": ("חולון, תל אביב", "חולון", "rental_offer", "rejected", "other_city"),
    "nolocation": (None, None, "rental_offer", "active", None),
    "sale": (TLV, None, "for_sale", "rejected", "for_sale"),
}
CHANGED = {"cleared", "caught", "relabelled"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(tmp_path: Path, posts: list[RawPost]) -> tuple[Path, dict[str, RawPost]]:
    database = tmp_path / STORE_ROOT / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    repository = SqliteRepository(database)
    named: dict[str, RawPost] = {}
    for i, (name, (location, city, nature, state, reason)) in enumerate(CASES.items()):
        text = f"דירה מספר {i} {city or ''}".strip()
        post = post_with_text(posts[i], text, native_location=location)
        repository.upsert_with_lifecycle(post, lifecycle(post))
        answer = make_listing(post.listing_id, post_nature=nature, other_city=city)
        repository.save_classification(
            answer, lifecycle(post, state=state, rejection_reason=reason)
        )
        named[name] = post
    # A pre-model reject with a Holon location, a flagged post, and a pending one: never touched.
    pre = post_with_text(posts[6], "בלי תמונות", native_location="חולון, תל אביב")
    repository.upsert_with_lifecycle(
        pre, lifecycle(pre, state="rejected", rejection_reason="no_images")
    )
    named["premodel"] = pre
    pending = post_with_text(posts[7], "ממתין", native_location="חולון, תל אביב")
    repository.upsert_with_lifecycle(pending, lifecycle(pending))
    named["pending"] = pending
    return database, named


def run(tmp_path: Path, *argv: str) -> tuple[int, str]:
    stream = io.StringIO()
    code = main(
        list(argv), config_root=CONFIG_ROOT, repo_root=tmp_path, clock=lambda: CLOCK, stream=stream
    )
    return code, stream.getvalue()


def status(database: Path, post: RawPost) -> tuple[str, str | None]:
    record = SqliteRepository(database, read_only=True).get_lifecycle(post.listing_id)
    return record.state, record.rejection_reason


# --- the plan ---


def test_the_plan_lists_exactly_the_posts_whose_status_changes(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    before = sha(database)
    plan = plan_rederivation(SqliteRepository(database, read_only=True))
    assert {c.listing_id for c in plan.changes} == {named[n].listing_id for n in CHANGED}
    by_id = {c.listing_id: c for c in plan.changes}
    assert by_id[named["cleared"].listing_id].old == ("rejected", "other_city")
    assert by_id[named["cleared"].listing_id].new == ("active", None)
    assert by_id[named["caught"].listing_id].new == ("rejected", "other_city")
    assert by_id[named["caught"].listing_id].locality == "רמת גן"
    assert by_id[named["relabelled"].listing_id].old == ("rejected", "not_listing")
    assert by_id[named["relabelled"].listing_id].new == ("rejected", "other_city")
    assert plan.considered == 6  # not the pre-model reject, not the pending post
    assert plan.native_present == 5
    assert (
        plan.before[("rejected", "other_city")] == 2 and plan.after[("rejected", "other_city")] == 3
    )
    assert sha(database) == before  # the plan writes nothing


def test_a_second_plan_after_the_rule_has_nothing_to_change(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    repository = SqliteRepository(database)
    for name in CHANGED:
        post = named[name]
        record = repository.get_lifecycle(post.listing_id)
        repository.save_lifecycle(
            rederived_lifecycle(record, repository.get_listing(post.listing_id), post)
        )
    assert plan_rederivation(repository).changes == ()


def test_a_record_that_is_not_model_classified_is_refused(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    repository = SqliteRepository(database, read_only=True)
    record = repository.get_lifecycle(named["premodel"].listing_id)
    with pytest.raises(ValueError, match="not a model-classified record"):
        rederived_lifecycle(record, make_listing(record.listing_id), named["premodel"])


# --- the command: the dry run ---


def test_the_dry_run_lists_the_changes_and_writes_nothing(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    before = sha(database)
    code, output = run(tmp_path)
    assert code == 0
    assert "3 change" in output and "dry run: nothing written" in output
    for name in CHANGED:
        assert named[name].listing_id[:12] in output
    assert named["same"].listing_id[:12] not in output
    assert "רמת גן" in output and "באר שבע" in output
    assert sha(database) == before
    assert [p.name for p in database.parent.iterdir()] == [SQLITE_FILENAME]  # no backup


def test_with_no_store_the_command_fails(tmp_path: Path) -> None:
    code, output = run(tmp_path)
    assert code == 1 and "no store" in output


# --- the command: --apply ---


def allow(named: dict[str, RawPost], *names: str) -> str:
    return ",".join(named[n].listing_id[:12] for n in names)


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        ((), "needs --allow"),
        (("--allow", "2bac260"), "at least 8 characters"),
    ],
)
def test_apply_refuses_without_a_proper_allow(
    tmp_path: Path, posts, argv: tuple[str, ...], message: str
) -> None:
    database, _ = build(tmp_path, posts)
    before = sha(database)
    code, output = run(tmp_path, "--apply", *argv)
    assert code == 1 and message in output
    assert sha(database) == before
    assert [p.name for p in database.parent.iterdir()] == [SQLITE_FILENAME]


def test_apply_refuses_when_the_plan_goes_beyond_the_allowed_posts(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    before = sha(database)
    code, output = run(tmp_path, "--apply", "--allow", allow(named, "cleared", "caught"))
    assert code == 1 and "the plan and --allow differ" in output
    assert named["relabelled"].listing_id[:12] in output
    assert sha(database) == before
    assert [p.name for p in database.parent.iterdir()] == [SQLITE_FILENAME]


def test_apply_refuses_an_allowed_post_that_is_not_in_the_plan(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    before = sha(database)
    code, output = run(tmp_path, "--apply", "--allow", allow(named, *CHANGED, "same"))
    assert code == 1 and "Not in the plan" in output
    assert sha(database) == before


def test_apply_backs_up_writes_the_three_and_leaves_everything_else(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    before = sha(database)
    raw_before = _raw(database)
    lifecycles = {
        n: SqliteRepository(database, read_only=True).get_lifecycle(p.listing_id)
        for n, p in named.items()
    }
    listings = {
        n: SqliteRepository(database, read_only=True).get_listing(p.listing_id)
        for n, p in named.items()
    }
    code, output = run(tmp_path, "--apply", "--allow", allow(named, *CHANGED))
    assert code == 0, output

    backup = database.with_name("tlv_hunter.2026-10-08.backup.sqlite3")
    assert backup.is_file() and sha(backup) == before
    assert f"backup SHA-256: {before}" in output and str(backup) in output
    assert "stored RawPost documents identical to the backup's: True" in output
    assert _raw(database) == raw_before

    assert status(database, named["cleared"]) == ("active", None)
    assert status(database, named["caught"]) == ("rejected", "other_city")
    assert status(database, named["relabelled"]) == ("rejected", "other_city")
    repository = SqliteRepository(database, read_only=True)
    for name, post in named.items():
        assert repository.get_listing(post.listing_id) == listings[name]  # no Listing edited
        if name not in CHANGED:
            assert repository.get_lifecycle(post.listing_id) == lifecycles[name]
    for name in CHANGED:  # only the state and the reason differ
        now = repository.get_lifecycle(named[name].listing_id)
        was = lifecycles[name]
        assert (
            now.model_copy(update={"state": was.state, "rejection_reason": was.rejection_reason})
            == was
        )

    # Idempotent: the rule has nothing left to change.
    code, output = run(tmp_path)
    assert code == 0 and "0 change" in output


def test_a_second_backup_on_the_same_day_gets_a_time_in_its_name(tmp_path: Path, posts) -> None:
    database, named = build(tmp_path, posts)
    (database.with_name("tlv_hunter.2026-10-08.backup.sqlite3")).write_bytes(b"earlier")
    code, _ = run(tmp_path, "--apply", "--allow", allow(named, *CHANGED))
    assert code == 0
    names = sorted(p.name for p in database.parent.iterdir())
    assert "tlv_hunter.2026-10-08T090000.backup.sqlite3" in names
    assert (database.parent / "tlv_hunter.2026-10-08.backup.sqlite3").read_bytes() == b"earlier"


def test_a_record_that_changed_since_the_plan_is_not_written(
    tmp_path: Path, posts, monkeypatch: pytest.MonkeyPatch
) -> None:
    database, named = build(tmp_path, posts)
    real = rederive_rejections.plan_rederivation

    def stale_plan(repository: Any):
        plan = real(repository)
        changes = tuple(
            c.__class__(c.listing_id, ("active", None), c.new, c.locality)
            if c.listing_id == named["cleared"].listing_id
            else c
            for c in plan.changes
        )
        return plan.__class__(
            plan.considered, plan.native_present, changes, plan.before, plan.after
        )

    monkeypatch.setattr(rederive_rejections, "plan_rederivation", stale_plan)
    code, output = run(tmp_path, "--apply", "--allow", allow(named, *CHANGED))
    assert code == 1 and "changed since the plan" in output
    assert status(database, named["cleared"]) == ("rejected", "other_city")


def _raw(database: Path) -> list[tuple]:
    connection = sqlite3.connect(f"file:{database.resolve().as_posix()}?mode=ro", uri=True)
    try:
        return connection.execute(
            "SELECT listing_id, doc, text_hash FROM raw_posts ORDER BY listing_id"
        ).fetchall()
    finally:
        connection.close()
