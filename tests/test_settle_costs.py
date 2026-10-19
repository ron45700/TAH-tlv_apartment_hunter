"""The real Apify cost (`PHASE_5.md` point 6 A; DECISIONS.md #450): `providers.thedoor.run_charges`
(Σ charged events × each event's flat price, `usageTotalUsd` beside it as the check), and the
`settle_costs` command: only the runs that ended 15 minutes ago or more, by compare and set;
`--show` writes nothing; the token never printed. A fake Apify; no network."""

import copy
import io
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import CONFIG_ROOT, SQLITE_FILENAME
from tests.test_gate_g import NOW, run_record
from tlv_hunter.jobs import settle_costs
from tlv_hunter.providers.thedoor import UnpricedEvent, run_charges
from tlv_hunter.state.runs import SqliteRunStore

TOKEN = "apify_api_test_token_never_printed"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

PRICING = {
    "pricingModel": "PAY_PER_EVENT",
    "pricingPerEvent": {
        "actorChargeEvents": {
            "apify-default-dataset-item": {"eventTitle": "result", "eventPriceUsd": 0.0015},
            "apify-actor-start": {"eventTitle": "Actor Start", "eventPriceUsd": 0.005},
        }
    },
}


def apify_run(rows: int, **changes: Any) -> dict[str, Any]:
    run = {
        "id": "AbCdEf",
        "status": "SUCCEEDED",
        "startedAt": "2026-10-20T07:00:00.000Z",
        "finishedAt": "2026-10-20T07:01:00.000Z",
        "chargedEventCounts": {"apify-default-dataset-item": rows, "apify-actor-start": 1},
        "pricingInfo": copy.deepcopy(PRICING),
        "usageTotalUsd": round(rows * 0.0015 + 0.005, 6),
        "usageUsd": None,
        "platformUsageBillingModel": "DEVELOPER",
    }
    return {**run, **changes}


class FakeApify:
    """Answers `GET /v2/actor-runs/{id}` from `runs`; records every call."""

    def __init__(self, runs: dict[str, dict[str, Any]]) -> None:
        self.runs = runs
        self.calls: list[str] = []

    def __call__(self, method: str, url: str, *, token: str, body: Any, timeout: float) -> Any:
        assert method == "GET" and body is None and token == TOKEN and TOKEN not in url
        self.calls.append(url)
        return {"data": self.runs[url.rsplit("/", 1)[1]]}


def test_the_cost_is_the_charged_events_times_their_prices() -> None:
    charges = run_charges(apify_run(99))
    assert charges.cost_usd == pytest.approx(0.1535)
    assert charges.usage_total_usd == pytest.approx(0.1535)
    assert charges.prices == {"apify-default-dataset-item": 0.0015, "apify-actor-start": 0.005}
    assert charges.pricing_model == "PAY_PER_EVENT"
    # usageTotalUsd is the check only: a different value changes nothing.
    assert run_charges(apify_run(99, usageTotalUsd=0.302)).cost_usd == pytest.approx(0.1535)


def test_an_event_with_no_flat_price_is_not_settled() -> None:
    run = apify_run(10)
    events = run["pricingInfo"]["pricingPerEvent"]["actorChargeEvents"]
    events["apify-default-dataset-item"] = {"eventTieredPricingUsd": {"FREE": 0.002}}
    with pytest.raises(UnpricedEvent):
        run_charges(run)


@pytest.mark.raw_fixtures
@pytest.mark.parametrize("name", ["_run", "_control_run"])
def test_the_saved_runs_usage_total_is_the_events_sum(name: str) -> None:
    """`PHASE_5.md` §5.1: in both runs saved on 2026-10-04 `usageTotalUsd` equals the formula."""
    path = RAW / f"thedoor_spike_1_1a_2026-10-04{name}.json"
    run = json.loads(path.read_text(encoding="utf-8"))
    run = run.get("data", run)
    charges = run_charges(run)
    assert charges.cost_usd == pytest.approx(run["usageTotalUsd"])
    assert charges.platform_usage_billing_model == "DEVELOPER"


def store_with(tmp_path: Path, *records: Any) -> tuple[SqliteRunStore, Path]:
    database = tmp_path / "data" / "store" / SQLITE_FILENAME
    database.parent.mkdir(parents=True)
    store = SqliteRunStore(database)
    for record in records:
        store.add_run(record)
    return store, database


def test_only_runs_ended_15_minutes_ago_with_an_apify_run_are_settled(tmp_path: Path) -> None:
    old = run_record(run_id="old", apify_run_id="old1", finished_at=NOW + timedelta(minutes=2))
    young = run_record(
        run_id="young",
        apify_run_id="young1",
        started_at=NOW + timedelta(minutes=10),
        finished_at=NOW + timedelta(minutes=12),
    )
    none = run_record(
        run_id="none",
        apify_run_id=None,
        status="failed",
        failure_kind="no store",
        finished_at=NOW + timedelta(minutes=1),
    )
    running = run_record(run_id="busy", apify_run_id="busy1", status="running", finished_at=None)
    store, _ = store_with(tmp_path, old, young, none, running)
    apify = FakeApify({"old1": apify_run(12), "young1": apify_run(3)})
    settled, left = settle_costs.settle(store, TOKEN, NOW + timedelta(minutes=20), apify)
    assert (settled, left) == (1, 0)
    assert [url.rsplit("/", 1)[1] for url in apify.calls] == ["old1"]
    done = store.get_run("old")
    assert done is not None and done.cost_usd == pytest.approx(12 * 0.0015 + 0.005)
    assert done.cost_settled_at == NOW + timedelta(minutes=20)
    assert done.charged_events == {"apify-default-dataset-item": 12, "apify-actor-start": 1}
    assert store.get_run("young") == young
    # A settled run is never read again.
    assert settle_costs.settle(store, TOKEN, NOW + timedelta(hours=1), apify) == (1, 0)
    assert apify.calls[-1].endswith("/young1")


def test_a_run_apify_still_runs_or_cannot_price_is_left_for_later(tmp_path: Path) -> None:
    store, _ = store_with(
        tmp_path,
        run_record(run_id="a", apify_run_id="a1"),
        run_record(run_id="b", apify_run_id="b1"),
    )
    tiered = apify_run(4)
    tiered["pricingInfo"]["pricingPerEvent"]["actorChargeEvents"]["apify-actor-start"] = {}
    apify = FakeApify({"a1": apify_run(4, status="RUNNING"), "b1": tiered})
    assert settle_costs.settle(store, TOKEN, NOW + timedelta(hours=1), apify) == (0, 2)
    assert all(run.cost_usd is None for run in store.recent_runs())


def run_main(tmp_path: Path, *argv: str, environ: dict[str, str] | None = None, apify=None):
    out = io.StringIO()
    code = settle_costs.main(
        list(argv),
        environ={"APIFY_TOKEN": TOKEN} if environ is None else environ,
        config_root=CONFIG_ROOT,
        repo_root=tmp_path,
        transport=apify or FakeApify({}),
        clock=lambda: NOW + timedelta(hours=1),
        stream=out,
    )
    return code, out.getvalue()


def test_show_prints_one_run_and_writes_nothing(tmp_path: Path) -> None:
    store, database = store_with(tmp_path, run_record(apify_run_id="x1"))
    before = database.read_bytes()
    code, out = run_main(tmp_path, "--show", "x1", apify=FakeApify({"x1": apify_run(33)}))
    assert code == 0
    assert "the cost by the events: $0.0545" in out
    assert '"apify-actor-start": 1' in out and "usageTotalUsd 0.0545" in out
    assert database.read_bytes() == before
    assert TOKEN not in out


def test_the_command_settles_and_refuses_with_no_token(tmp_path: Path) -> None:
    store, _ = store_with(tmp_path, run_record(apify_run_id="x1"))
    code, out = run_main(tmp_path, apify=FakeApify({"x1": apify_run(2)}))
    assert code == 0 and TOKEN not in out
    (record,) = store.recent_runs()
    assert record.cost_usd == pytest.approx(0.008)
    code, out = run_main(tmp_path, environ={})
    assert code == 1 and out == "refused: APIFY_TOKEN is not set\n"
