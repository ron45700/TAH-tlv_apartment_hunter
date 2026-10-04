from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.conftest import CONFIG_ROOT, FETCHED_AT, SQLITE_FILENAME, load_spike_1_1a
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.contracts.group_watermark import GROUP_WATERMARK_SCHEMA_VERSION, GroupWatermark
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.providers.thedoor import to_raw_post
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.watermark.window import BUFFER, MissingWatermarkError, advance, run_since

# Spike 1.1a run 1 started at this instant with postsNewerThan "1440 minutes" and maxPosts 30.
RUN_START = datetime(2026, 10, 3, 21, 32, 6, tzinfo=UTC)
SPIKE_SINCE = RUN_START - timedelta(minutes=1440)
SPIKE_MAX_POSTS = 30
GROUPS = YamlConfig(CONFIG_ROOT).collection().group_ids
ZERO_ROW_GROUP = "5612809662118963"
MAX_POSTS_GROUP = "101875683484689"
LAST_SUCCESS = RUN_START - timedelta(minutes=30)


def _posts(suffix: str = "") -> list[RawPost]:
    return [to_raw_post(item, FETCHED_AT) for item in load_spike_1_1a(suffix)]


def _mark(group_id: str, **changes) -> GroupWatermark:
    fields = {
        "schema_version": GROUP_WATERMARK_SCHEMA_VERSION,
        "group_id": group_id,
        "watermark": RUN_START - timedelta(hours=2),
        "last_success_at": LAST_SUCCESS,
        "consecutive_failures": 0,
    }
    return GroupWatermark(**{**fields, **changes})


def _marks(**per_group: dict) -> list[GroupWatermark]:
    return [_mark(group_id, **per_group.get(group_id, {})) for group_id in GROUPS]


def _advance(records, posts, **overrides):
    arguments = {"run_started_at": RUN_START, "since": SPIKE_SINCE, "max_posts": SPIKE_MAX_POSTS}
    return advance(records, GROUPS, posts, **{**arguments, **overrides})


def _by_group(records) -> dict[str, GroupWatermark]:
    return {record.group_id: record for record in records}


def _newest(posts: list[RawPost], group_id: str) -> datetime:
    return max(post.posted_at for post in posts if post.group_id == group_id)


def _oldest(posts: list[RawPost], group_id: str) -> datetime:
    return min(post.posted_at for post in posts if post.group_id == group_id)


# --- W1: the window starts at the last successful run's start ----------------------------------


def test_since_is_the_earliest_last_success_minus_the_buffer() -> None:
    earliest = RUN_START - timedelta(hours=3)
    records = _marks(**{GROUPS[2]: {"last_success_at": earliest}})
    assert run_since(records, GROUPS) == earliest - BUFFER


def test_a_quiet_groups_old_watermark_does_not_widen_the_window() -> None:
    # The spike's quiet group had last posted 31 hours before the run.
    records = _marks(**{ZERO_ROW_GROUP: {"watermark": RUN_START - timedelta(hours=31)}})
    assert run_since(records, GROUPS) == LAST_SUCCESS - BUFFER


def test_a_failed_run_writes_nothing_so_the_next_window_covers_it() -> None:
    records = _marks()
    since = run_since(records, GROUPS)
    # A failed run: 1.14 neither calls advance nor saves, so the next run asks for the same start.
    assert run_since(records, GROUPS) == since
    later = RUN_START + timedelta(hours=5)
    result = _advance(records, _posts(), run_started_at=later, since=since)
    assert run_since(result.records, GROUPS) == later - BUFFER


# --- W2: the buffer ------------------------------------------------------------------------------


def test_the_buffer_is_fifteen_minutes() -> None:
    assert BUFFER == timedelta(minutes=15)


# --- W3: max_posts 50, and a group at max_posts --------------------------------------------------


def test_max_posts_for_every_group_stays_below_the_caps_max_items() -> None:
    config = YamlConfig(CONFIG_ROOT).collection()
    run = load_spike_1_1a("_run")
    # The spike ran with the same cap; the platform derived maxItems from it.
    assert run["options"]["maxTotalChargeUsd"] == config.max_total_charge_usd
    assert config.max_posts == 50
    assert len(config.group_ids) * config.max_posts < run["options"]["maxItems"]


def test_a_group_at_max_posts_short_of_its_window_is_reported_and_still_advances() -> None:
    control = _posts("_control")
    oldest = _oldest(control, MAX_POSTS_GROUP)
    # The group's own window starts an hour before the oldest post it returned.
    records = _marks(**{MAX_POSTS_GROUP: {"watermark": oldest - timedelta(hours=1) + BUFFER}})
    result = _advance(records, control, since=oldest - timedelta(hours=5))
    assert [gap.group_id for gap in result.cut_off] == [MAX_POSTS_GROUP]
    gap = result.cut_off[0]
    assert gap.rows == 30
    assert gap.window_start == oldest - timedelta(hours=1)
    assert gap.oldest_posted_at == oldest
    record = _by_group(result.records)[MAX_POSTS_GROUP]
    assert record.watermark == _newest(control, MAX_POSTS_GROUP)
    assert record.last_success_at == RUN_START


def test_a_group_at_max_posts_that_reached_its_window_is_not_reported() -> None:
    control = _posts("_control")
    oldest = _oldest(control, MAX_POSTS_GROUP)
    # The returned posts reach back to the group's own window start: nothing is missing.
    records = _marks(**{MAX_POSTS_GROUP: {"watermark": oldest + BUFFER}})
    result = _advance(records, control, since=oldest - timedelta(hours=5))
    assert MAX_POSTS_GROUP not in {gap.group_id for gap in result.cut_off}


def test_the_window_start_is_never_before_the_runs_since() -> None:
    control = _posts("_control")
    oldest = _oldest(control, MAX_POSTS_GROUP)
    # A watermark far older than the run's window: the gap starts at since, not before it.
    records = _marks(**{MAX_POSTS_GROUP: {"watermark": oldest - timedelta(days=3)}})
    since = oldest - timedelta(minutes=1)
    gaps = {gap.group_id: gap for gap in _advance(records, control, since=since).cut_off}
    assert gaps[MAX_POSTS_GROUP].window_start == since


def test_below_max_posts_no_group_is_reported() -> None:
    assert _advance(_marks(), _posts("_control"), max_posts=50).cut_off == ()


# --- W5a: last_success_at -----------------------------------------------------------------------


def test_last_success_at_is_the_run_start_for_every_group() -> None:
    result = _advance(_marks(), _posts())
    assert {record.last_success_at for record in result.records} == {RUN_START}


def test_a_run_that_started_before_the_last_success_is_refused() -> None:
    records = _marks(**{GROUPS[0]: {"last_success_at": RUN_START + timedelta(minutes=1)}})
    with pytest.raises(ValueError, match=GROUPS[0]):
        _advance(records, _posts())


# --- W5b: consecutive_failures counts zero-row successful runs ---------------------------------


def test_a_zero_row_group_counts_up_and_a_group_with_rows_resets() -> None:
    posts = _posts()
    assert ZERO_ROW_GROUP not in {post.group_id for post in posts}
    records = _marks(**{group_id: {"consecutive_failures": 4} for group_id in GROUPS})
    result = _by_group(_advance(records, posts).records)
    assert result[ZERO_ROW_GROUP].consecutive_failures == 5
    assert result[ZERO_ROW_GROUP].watermark == _by_group(records)[ZERO_ROW_GROUP].watermark
    assert {
        record.consecutive_failures for gid, record in result.items() if gid != ZERO_ROW_GROUP
    } == {0}


# --- the watermark: the highest posted_at seen ---------------------------------------------------


def test_the_watermark_is_the_newest_posted_at_of_the_group() -> None:
    posts = _posts()
    records = _marks(**{group_id: {"watermark": SPIKE_SINCE} for group_id in GROUPS})
    result = _by_group(_advance(records, posts).records)
    for group_id in GROUPS:
        if group_id != ZERO_ROW_GROUP:
            assert result[group_id].watermark == _newest(posts, group_id)


def test_the_watermark_never_moves_backwards() -> None:
    later = RUN_START + timedelta(days=1)
    records = _marks(**{group_id: {"watermark": later} for group_id in GROUPS})
    result = _advance(records, _posts())
    assert {record.watermark for record in result.records} == {later}


# --- W6: no per-group filter; every fetched post counts ------------------------------------------


def test_posts_older_than_a_groups_own_window_still_count() -> None:
    posts = _posts()
    group_id = GROUPS[0]
    above = _newest(posts, group_id) + timedelta(hours=1)
    # Every post of this group is older than its watermark minus the buffer.
    records = _marks(**{group_id: {"watermark": above, "consecutive_failures": 2}})
    record = _by_group(_advance(records, posts).records)[group_id]
    assert record.consecutive_failures == 0
    assert record.watermark == above


# --- W7: a configured group with no record; groups no longer configured -------------------------


def test_a_configured_group_with_no_record_raises_naming_it() -> None:
    records = [record for record in _marks() if record.group_id != GROUPS[4]]
    with pytest.raises(MissingWatermarkError, match=GROUPS[4]) as raised:
        run_since(records, GROUPS)
    assert raised.value.group_ids == (GROUPS[4],)


def test_a_record_with_no_success_yet_counts_as_missing() -> None:
    records = _marks(**{GROUPS[1]: {"last_success_at": None}})
    with pytest.raises(MissingWatermarkError, match=GROUPS[1]):
        run_since(records, GROUPS)


def test_a_group_no_longer_configured_does_not_count_and_is_not_returned() -> None:
    records = [*_marks(), _mark("999", last_success_at=RUN_START - timedelta(days=30))]
    assert run_since(records, GROUPS) == LAST_SUCCESS - BUFFER
    assert [record.group_id for record in _advance(records, _posts()).records] == list(GROUPS)


def test_save_all_leaves_a_group_no_longer_configured_untouched(tmp_path: Path) -> None:
    store = SqliteWatermarkStore(tmp_path / SQLITE_FILENAME)
    old = _mark("999", last_success_at=RUN_START - timedelta(days=30))
    store.save_all([*_marks(), old])
    store.save_all(_advance(store.get_all(), _posts()).records)
    assert store.get("999") == old
    assert run_since(store.get_all(), GROUPS) == RUN_START - BUFFER


# --- bootstrap: the records are created ----------------------------------------------------------


def test_a_bootstrap_run_creates_a_record_for_every_group() -> None:
    posts = _posts()
    result = _by_group(_advance([], posts).records)
    assert list(result) == list(GROUPS)
    assert {record.schema_version for record in result.values()} == {GROUP_WATERMARK_SCHEMA_VERSION}
    assert result[ZERO_ROW_GROUP].watermark is None
    assert result[ZERO_ROW_GROUP].consecutive_failures == 1
    assert result[MAX_POSTS_GROUP].watermark == _newest(posts, MAX_POSTS_GROUP)
    assert result[MAX_POSTS_GROUP].consecutive_failures == 0


def test_a_bootstrap_run_reports_the_spikes_capped_group() -> None:
    # Spike run 1: 101875683484689 hit maxPosts 30 about ten hours into a 24-hour window.
    result = _advance([], _posts())
    assert [gap.group_id for gap in result.cut_off] == [MAX_POSTS_GROUP]
    assert result.cut_off[0].window_start == SPIKE_SINCE


# --- a row skipped under #71 D: no change --------------------------------------------------------


def test_the_watermark_advances_past_a_row_that_was_never_mapped() -> None:
    posts = _posts()
    in_group = sorted(
        (post for post in posts if post.group_id == GROUPS[0]), key=lambda post: post.posted_at
    )
    skipped = in_group[-1]
    kept = [post for post in posts if post is not skipped]
    record = _by_group(_advance([], kept).records)[GROUPS[0]]
    assert record.watermark == in_group[-2].posted_at
    assert record.watermark < skipped.posted_at


# --- round trip and guards -----------------------------------------------------------------------


def test_round_trip_through_the_sqlite_watermark_store(tmp_path: Path) -> None:
    store = SqliteWatermarkStore(tmp_path / SQLITE_FILENAME)
    result = _advance([], _posts())
    store.save_all(result.records)
    assert store.get_all() == sorted(result.records, key=lambda record: record.group_id)
    assert run_since(store.get_all(), GROUPS) == RUN_START - BUFFER


def test_advance_refuses_a_since_not_before_the_run_start() -> None:
    with pytest.raises(ValueError, match="not before"):
        _advance([], [], since=RUN_START)


@pytest.mark.parametrize("field", ["run_started_at", "since"])
def test_advance_refuses_a_datetime_that_is_not_utc(field: str) -> None:
    israel = timezone(timedelta(hours=3))
    times = {"run_started_at": RUN_START, "since": SPIKE_SINCE}
    with pytest.raises(ValueError, match="UTC"):
        _advance([], [], **{field: times[field].astimezone(israel)})


def test_advance_refuses_a_post_from_a_group_not_configured() -> None:
    posts = _posts()
    with pytest.raises(ValueError, match="not configured"):
        advance([], GROUPS[:5], posts, run_started_at=RUN_START, since=SPIKE_SINCE, max_posts=50)


def test_duplicate_records_or_groups_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicate watermark record"):
        run_since([*_marks(), _mark(GROUPS[0])], GROUPS)
    with pytest.raises(ValueError, match="duplicates"):
        run_since(_marks(), [*GROUPS, GROUPS[0]])
    with pytest.raises(ValueError, match="empty"):
        run_since(_marks(), [])
