import copy
import io
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.conftest import CONFIG_ROOT, NetworkBlockedError, load_spike_1_1a
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.providers.thedoor import (
    API_BASE,
    ApifyApiError,
    ProviderRunError,
    ThedoorProvider,
    build_actor_input,
    posts_newer_than,
    urllib_transport,
)
from tlv_hunter.textnorm.phones import extract_phones

TOKEN = "test-token-not-real"
# Spike 1.1a run 1 started at this instant with postsNewerThan "1440 minutes".
RUN_START = datetime(2026, 10, 3, 21, 32, 6, tzinfo=UTC)
SINCE = RUN_START - timedelta(minutes=1440)
ZERO_ROW_GROUP = "5612809662118963"
MAX_POSTS_GROUP = "101875683484689"


@pytest.fixture
def config():
    # The repo config with the spike's maxPosts, so that the spike fixtures stay valid as captured.
    spike_max_posts = load_spike_1_1a("_input")["maxPosts"]
    return YamlConfig(CONFIG_ROOT).collection().model_copy(update={"max_posts": spike_max_posts})


@dataclass
class Clock:
    now: datetime = RUN_START

    def __call__(self) -> datetime:
        return self.now


@dataclass
class FakeApify:
    """Serves the spike 1.1a run object and dataset. Each poll advances the clock by its wait."""

    clock: Clock
    items: list[dict[str, Any]]
    run: dict[str, Any]
    statuses: list[str] = field(default_factory=lambda: ["SUCCEEDED"])
    fail_abort: bool = False
    calls: list[tuple[str, str, dict[str, Any] | None]] = field(default_factory=list)

    def __call__(
        self, method: str, url: str, *, token: str, body: dict[str, Any] | None, timeout: float
    ) -> Any:
        assert token == TOKEN
        assert TOKEN not in url
        assert url.startswith(API_BASE)
        self.calls.append((method, url, body))
        parts = urlsplit(url)
        path, query = parts.path, parse_qs(parts.query)
        if method == "POST" and path.endswith("/runs"):
            return {"data": self._run(self.statuses[0])}
        if method == "GET" and "/actor-runs/" in path:
            self.clock.now += timedelta(seconds=int(query["waitForFinish"][0]))
            status = self.statuses[1] if len(self.statuses) > 1 else self.statuses[0]
            if len(self.statuses) > 1:
                self.statuses.pop(0)
            return {"data": self._run(status)}
        if method == "POST" and path.endswith("/abort"):
            if self.fail_abort:
                raise ApifyApiError(f"POST {path} -> HTTP 500")
            return {"data": self._run("ABORTING")}
        if method == "GET" and path == f"/v2/datasets/{self.run['defaultDatasetId']}/items":
            assert query == {"format": ["json"]}
            return copy.deepcopy(self.items)
        raise AssertionError(f"unexpected call {method} {url}")

    def _run(self, status: str) -> dict[str, Any]:
        return {**copy.deepcopy(self.run), "status": status}

    def paths(self, method: str, fragment: str) -> list[str]:
        return [url for m, url, _ in self.calls if m == method and fragment in url]


@pytest.fixture
def clock() -> Clock:
    return Clock()


@pytest.fixture
def apify(clock, spike_items) -> FakeApify:
    return FakeApify(clock=clock, items=spike_items, run=load_spike_1_1a("_run"))


def _fetch(config, apify, clock, since=SINCE, group_ids=None):
    provider = ThedoorProvider(config, TOKEN, transport=apify, clock=clock)
    return provider.fetch(config.group_ids if group_ids is None else group_ids, since)


# --- input -----------------------------------------------------------------------------------


def test_input_takes_max_posts_from_the_repo_config() -> None:
    repo_config = YamlConfig(CONFIG_ROOT).collection()
    built = build_actor_input(repo_config, repo_config.group_ids, SINCE, RUN_START)
    assert built["maxPosts"] == repo_config.max_posts


def test_input_is_the_spike_input(config) -> None:
    built = build_actor_input(config, config.group_ids, SINCE, RUN_START)
    assert built == load_spike_1_1a("_input")
    assert built["fetchAllComments"] is False
    assert built["includeTopComment"] is False
    assert built["sortingOrder"] == "newest_posts"


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(1, "1 minutes"), (60, "1 minutes"), (61, "2 minutes"), (90 * 60, "90 minutes")],
)
def test_posts_newer_than_is_relative_minutes_rounded_up(seconds: int, expected: str) -> None:
    assert posts_newer_than(RUN_START - timedelta(seconds=seconds), RUN_START) == expected


@pytest.mark.parametrize("since", [RUN_START, RUN_START + timedelta(minutes=1)])
def test_since_not_in_the_past_raises(since: datetime) -> None:
    with pytest.raises(ValueError):
        posts_newer_than(since, RUN_START)


def test_naive_since_raises(config, apify, clock) -> None:
    with pytest.raises(ValueError):
        _fetch(config, apify, clock, since=SINCE.replace(tzinfo=None))
    assert apify.calls == []


@pytest.mark.parametrize("group_ids", [[], ["35819517694", "35819517694"]])
def test_empty_or_duplicate_group_ids_raise(config, group_ids: list[str]) -> None:
    with pytest.raises(ValueError):
        build_actor_input(config, group_ids, SINCE, RUN_START)


def test_empty_token_is_refused(config) -> None:
    with pytest.raises(ValueError):
        ThedoorProvider(config, "")


# --- the run ---------------------------------------------------------------------------------


def test_fetch_returns_every_spike_row(config, apify, clock, spike_items) -> None:
    posts = _fetch(config, apify, clock)
    assert [post.source_post_id for post in posts] == [item["post_id"] for item in spike_items]
    assert {post.fetched_at for post in posts} == {RUN_START}


def test_run_is_started_with_the_input_and_the_charge_cap(config, apify, clock) -> None:
    _fetch(config, apify, clock)
    method, url, body = apify.calls[0]
    assert method == "POST"
    parts = urlsplit(url)
    assert parts.path == "/v2/actors/thedoor~facebook-group-post-scraper/runs"
    assert parse_qs(parts.query) == {"maxTotalChargeUsd": ["0.5"]}
    assert body == load_spike_1_1a("_input")


def test_polls_until_a_terminal_status(config, apify, clock) -> None:
    apify.statuses = ["READY", "RUNNING", "SUCCEEDED"]
    posts = _fetch(config, apify, clock)
    polls = apify.paths("GET", "/actor-runs/")
    assert len(polls) == 2
    assert all(url.endswith("?waitForFinish=60") for url in polls)
    assert len(posts) == 105


@pytest.mark.parametrize("status", ["FAILED", "ABORTED", "TIMED-OUT"])
def test_a_run_that_did_not_succeed_raises(config, apify, clock, status: str) -> None:
    apify.statuses = ["RUNNING", status]
    with pytest.raises(ProviderRunError, match=status):
        _fetch(config, apify, clock)
    assert apify.paths("GET", "/datasets/") == []


def test_deadline_aborts_the_run_and_raises(config, apify, clock) -> None:
    apify.statuses = ["RUNNING"]
    with pytest.raises(ProviderRunError, match="aborted"):
        _fetch(config, apify, clock)
    waits = [int(parse_qs(urlsplit(u).query)["waitForFinish"][0]) for u in apify.paths("GET", "")]
    assert sum(waits) == config.run_timeout_secs
    assert max(waits) == 60
    run_id = apify.run["id"]
    assert apify.paths("POST", "/abort") == [f"{API_BASE}/actor-runs/{run_id}/abort"]
    assert apify.paths("GET", "/datasets/") == []


def test_a_failed_abort_still_raises(config, apify, clock, caplog) -> None:
    apify.statuses = ["RUNNING"]
    apify.fail_abort = True
    with caplog.at_level(logging.ERROR), pytest.raises(ProviderRunError, match="aborted"):
        _fetch(config, apify, clock)
    assert f"apify_run {apify.run['id']}: abort failed" in caplog.text


def test_rows_at_the_cap_raise(config, apify, clock) -> None:
    apify.run["options"]["maxItems"] = 105
    with pytest.raises(ProviderRunError, match="maxItems"):
        _fetch(config, apify, clock)


def test_rows_below_the_cap_pass(config, apify, clock) -> None:
    apify.run["options"]["maxItems"] = 106
    assert len(_fetch(config, apify, clock)) == 105


# --- rows ------------------------------------------------------------------------------------


def test_a_broken_row_is_skipped_and_counted(config, apify, clock, caplog) -> None:
    missing_key, invalid = apify.items[3], apify.items[40]
    del missing_key["creation_time"]
    invalid["post_url"] = None
    with caplog.at_level(logging.INFO):
        posts = _fetch(config, apify, clock)
    assert len(posts) == 103
    returned = {post.source_post_id for post in posts}
    assert missing_key["post_id"] not in returned
    assert invalid["post_id"] not in returned
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 2
    assert missing_key["post_id"] in errors[0] and missing_key["group_id"] in errors[0]
    assert "creation_time" in errors[0]
    assert invalid["post_id"] in errors[1] and "permalink" in errors[1]
    assert "skipped 2" in caplog.text


def _break(items: list[dict[str, Any]]) -> None:
    for item in items:
        item["post_url"] = None


def test_every_row_broken_raises(config, apify, clock) -> None:
    _break(apify.items)
    with pytest.raises(ProviderRunError, match=r"apify_run \S+: 105 of 105 rows failed to map"):
        _fetch(config, apify, clock)


def test_two_broken_rows_of_three_do_not_raise(config, apify, clock) -> None:
    apify.items = apify.items[:3]
    _break(apify.items[:2])
    assert len(_fetch(config, apify, clock)) == 1


def test_three_broken_rows_of_five_raise(config, apify, clock) -> None:
    apify.items = apify.items[:5]
    _break(apify.items[:3])
    with pytest.raises(ProviderRunError, match="3 of 5 rows failed to map"):
        _fetch(config, apify, clock)


def test_dropped_rows_are_not_counted_against_the_ceiling(config, apify, clock) -> None:
    apify.items = apify.items[:7]
    _break(apify.items[:3])
    for item in apify.items[3:]:
        item["group_id"] = "999"
    # 3 of 7 would pass; with the 4 dropped rows excluded it is 3 of 3.
    with pytest.raises(ProviderRunError, match="3 of 3 rows failed to map"):
        _fetch(config, apify, clock)


def test_logs_carry_no_post_text_or_phone_numbers(config, apify, clock, caplog) -> None:
    for item in apify.items[:10]:
        item["post_url"] = None
    with caplog.at_level(logging.DEBUG):
        _fetch(config, apify, clock)
    texts = [item["text"] for item in apify.items if item["text"].strip()]
    texts += [item["sharedPost"]["text"] for item in apify.items if item["sharedPost"]]
    phones = {phone for text in texts for phone in extract_phones(text)}
    assert texts and phones
    logged = caplog.text
    assert not any(text in logged for text in texts)
    assert not any(phone in logged.replace("-", "") for phone in phones)


def test_a_row_from_an_unrequested_group_is_dropped(config, apify, clock, caplog) -> None:
    stray = apify.items[0]
    stray["group_id"] = "999"
    with caplog.at_level(logging.INFO):
        posts = _fetch(config, apify, clock)
    assert len(posts) == 104
    assert stray["post_id"] not in {post.source_post_id for post in posts}
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("999" in w and stray["post_id"] in w for w in warnings)
    assert "dropped 1" in caplog.text


def test_a_group_at_max_posts_is_warned_about(config, apify, clock, caplog) -> None:
    with caplog.at_level(logging.WARNING):
        posts = _fetch(config, apify, clock)
    warnings = [r.getMessage() for r in caplog.records if "max_posts" in r.getMessage()]
    assert len(warnings) == 1
    assert MAX_POSTS_GROUP in warnings[0]
    assert len(posts) == 105


def test_a_group_above_max_posts_is_warned_about(config, apify, clock, caplog) -> None:
    config = config.model_copy(update={"max_posts": 28})
    with caplog.at_level(logging.WARNING):
        _fetch(config, apify, clock)
    warnings = [r.getMessage() for r in caplog.records if "max_posts" in r.getMessage()]
    # 101875683484689 returned 30 rows (> 28) and 295395253832427 returned 28 (= 28).
    assert len(warnings) == 2
    assert MAX_POSTS_GROUP in warnings[0] + warnings[1]
    assert "295395253832427" in warnings[0] + warnings[1]


def test_no_max_posts_warning_below_the_limit(config, apify, clock, caplog) -> None:
    config = config.model_copy(update={"max_posts": 31})
    with caplog.at_level(logging.WARNING):
        _fetch(config, apify, clock)
    assert "max_posts" not in caplog.text


def test_max_posts_count_is_taken_before_the_since_filter(config, apify, clock, caplog) -> None:
    later = SINCE + timedelta(hours=20)
    with caplog.at_level(logging.WARNING):
        posts = _fetch(config, apify, clock, since=later)
    assert all(post.posted_at >= later for post in posts)
    assert len(posts) < 105
    assert MAX_POSTS_GROUP in caplog.text


def test_run_log_line_counts_every_requested_group(config, apify, clock, caplog) -> None:
    with caplog.at_level(logging.INFO):
        _fetch(config, apify, clock)
    summary = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert len(summary) == 1
    line = summary[0]
    # Named apify_run, so that run_id in a log line is only ours (DECISIONS.md #79).
    assert line.startswith(f"apify_run {apify.run['id']}: SUCCEEDED, ")
    assert f"'{ZERO_ROW_GROUP}': 0" in line
    assert f"'{MAX_POSTS_GROUP}': 30" in line
    assert "105 rows" in line and "skipped 0" in line and "dropped 0" in line
    assert "usageTotalUsd 0.1535" in line


# --- the real transport, without a network -----------------------------------------------------


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_transport_sends_the_token_only_in_the_header(monkeypatch) -> None:
    seen: list[urllib.request.Request] = []

    def fake_urlopen(request, timeout):
        seen.append(request)
        return _Response(b'{"data": {}}')

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    urllib_transport("POST", f"{API_BASE}/x", token=TOKEN, body={"a": 1}, timeout=5)
    urllib_transport("POST", f"{API_BASE}/y/abort", token=TOKEN, body=None, timeout=5)
    urllib_transport("GET", f"{API_BASE}/z", token=TOKEN, body=None, timeout=5)
    for request in seen:
        assert request.get_header("Authorization") == f"Bearer {TOKEN}"
        assert TOKEN not in request.full_url
    assert seen[0].data == b'{"a": 1}'
    assert seen[0].get_header("Content-type") == "application/json"
    assert seen[1].data == b""
    assert seen[2].data is None


def test_transport_http_error_names_no_token(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApifyApiError, match="HTTP 401") as raised:
        urllib_transport("GET", f"{API_BASE}/actor-runs/r1", token=TOKEN, body=None, timeout=5)
    assert TOKEN not in str(raised.value)


def test_default_transport_is_stopped_by_the_network_guard(config) -> None:
    provider = ThedoorProvider(config, TOKEN, clock=Clock())
    with pytest.raises(NetworkBlockedError):
        provider.fetch(config.group_ids, SINCE)
