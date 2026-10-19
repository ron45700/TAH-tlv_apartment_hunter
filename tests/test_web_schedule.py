"""The admin's schedule page's API (Phase 5; DECISIONS.md #61, #471 points 8 and 11; Gate G, #472):
the settings read with their defaults, saved against the version the page showed, a value out of
range refused; "run now" written for the scheduler, refused while a run is in progress or a request
waits; the admin only, every write with its `Origin`. Temporary stores (`test_web_admin.py`'s)."""

from datetime import timedelta

from fastapi.testclient import TestClient

from tests.test_gate_g import run_record
from tests.test_web_accounts import Clock, write
from tests.test_web_admin import (  # noqa: F401  (fixtures)
    AdminStore,
    _event_loop_self_pipe,  # #344: the same one exception
    client_of,
    clock,
    dana,
    ron,
    site,
    store,
)
from tlv_hunter.state.runs import SqliteRunStore


def schedule(client: TestClient) -> dict:
    response = client.get("/api/admin/schedule")
    assert response.status_code == 200, response.text
    return response.json()


def test_the_admin_only(site, ron: TestClient, dana: TestClient) -> None:  # noqa: F811
    assert client_of(site).get("/api/admin/schedule").status_code == 401
    assert dana.get("/api/admin/schedule").status_code == 403
    assert write(dana, "POST", "/api/admin/schedule/run-now").status_code == 403
    assert ron.post("/api/admin/schedule/run-now", json={}).status_code == 403  # no Origin


def test_before_any_row_the_page_shows_the_defaults_and_the_next_run_is_now(
    ron: TestClient,  # noqa: F811
    clock: Clock,  # noqa: F811
) -> None:
    answer = schedule(ron)
    assert answer["stored"] is False and answer["version"] == "none"
    assert (answer["interval_minutes"], answer["quiet_from"], answer["quiet_until"]) == (
        30,
        "00:00",
        "07:00",
    )
    assert answer["running"] is None and answer["runs"] == []


def test_a_save_writes_the_row_against_the_version_shown(
    ron: TestClient,  # noqa: F811
    store: AdminStore,  # noqa: F811
    clock: Clock,  # noqa: F811
) -> None:
    body = {"interval_minutes": 45, "quiet_from": "23:30", "quiet_until": "06:30"}
    saved = write(ron, "POST", "/api/admin/schedule", {**body, "version": "none"})
    assert saved.status_code == 200, saved.text
    answer = saved.json()
    assert answer["stored"] and answer["interval_minutes"] == 45 and answer["updated_by"] == "ron"
    stored = SqliteRunStore(store.db).get_settings()
    assert stored is not None and (stored.quiet_from, stored.quiet_until) == ("23:30", "06:30")
    stale = write(ron, "POST", "/api/admin/schedule", {**body, "version": "none"})
    assert stale.status_code == 409 and stale.json() == {"refusal": "changed"}
    # The bot's digest time does not make the form stale.
    SqliteRunStore(store.db).set_last_digest(clock.now)
    again = write(
        ron,
        "POST",
        "/api/admin/schedule",
        {**body, "interval_minutes": 60, "version": answer["version"]},
    )
    assert again.status_code == 200 and again.json()["interval_minutes"] == 60


def test_a_value_out_of_range_is_refused(ron: TestClient) -> None:  # noqa: F811
    for body in (
        {"interval_minutes": 4, "quiet_from": "00:00", "quiet_until": "07:00"},
        {"interval_minutes": 30, "quiet_from": "7am", "quiet_until": "07:00"},
    ):
        refused = write(ron, "POST", "/api/admin/schedule", {**body, "version": "none"})
        assert refused.status_code == 422
        assert refused.json() == {"refusal": "invalid_schedule"}
    assert schedule(ron)["stored"] is False


def test_run_now_is_written_once_and_refused_while_a_run_is_in_progress(
    ron: TestClient,  # noqa: F811
    store: AdminStore,  # noqa: F811
    clock: Clock,  # noqa: F811
) -> None:
    asked = write(ron, "POST", "/api/admin/schedule/run-now")
    assert asked.status_code == 200 and asked.json()["run_now_waiting"] is True
    stored = SqliteRunStore(store.db).get_settings()
    assert stored is not None and stored.run_now_requested_at == clock.now
    again = write(ron, "POST", "/api/admin/schedule/run-now")
    assert again.status_code == 409 and again.json() == {"refusal": "already_asked"}
    runs = SqliteRunStore(store.db)
    runs.add_run(
        run_record(trigger="manual", status="running", finished_at=None, started_at=clock.now)
    )
    clock.now += timedelta(minutes=1)
    busy = write(ron, "POST", "/api/admin/schedule/run-now")
    assert busy.status_code == 409 and busy.json() == {"refusal": "run_in_progress"}
    answer = schedule(ron)
    assert answer["running"]["trigger"] == "manual" and answer["next_run"] is None
    assert answer["run_now_waiting"] is False  # the manual run followed the request


def test_the_page_lists_the_last_runs_newest_first_with_their_cost(
    ron: TestClient,  # noqa: F811
    store: AdminStore,  # noqa: F811
    clock: Clock,  # noqa: F811
) -> None:
    runs = SqliteRunStore(store.db)
    first = clock.now - timedelta(hours=1)
    runs.add_run(
        run_record(
            run_id="one",
            started_at=first,
            finished_at=first + timedelta(minutes=2),
            cost_usd=0.023,
            cost_settled_at=first + timedelta(minutes=20),
        )
    )
    runs.add_run(
        run_record(
            run_id="two",
            started_at=clock.now - timedelta(minutes=10),
            finished_at=clock.now - timedelta(minutes=8),
            status="failed",
            failure_kind="ProviderRunError: apify_run x ended FAILED",
        )
    )
    answer = schedule(ron)
    assert [r["run_id"] for r in answer["runs"]] == ["two", "one"]
    assert answer["runs"][1]["cost_usd"] == 0.023 and answer["runs"][0]["cost_usd"] is None
    assert answer["next_run"] is not None
