"""The bot's watch over collection (`PHASE_5.md` points 7, 9 B, 10 A; DECISIONS.md #471): the
silent-group thresholds and the problems (`telegram/health.py`), the digest's counts and its Hebrew
messages (`telegram/digest.py`), the bot sending the failure alert once per problem and the digest
once a day to the admin's chat only, and `send_test_digest` (writes nothing). Temporary stores
(`test_telegram_bot.py`'s); every request goes to `FakeTelegram`."""

import io
from datetime import UTC, datetime, timedelta
from datetime import time as day_time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tests.test_gate_d import T0
from tests.test_gate_g import run_record, settings
from tests.test_telegram_bot import (  # noqa: F401  (fixtures)
    CHAT,
    SITE,
    Harness,
    TiedStore,
    _event_loop_self_pipe,
    environ,
    linked_ron,
    repo_of,
    store,
)
from tests.test_telegram_client import TOKEN, FakeTelegram
from tlv_hunter.contracts.group_watermark import GroupWatermark
from tlv_hunter.jobs import send_test_digest
from tlv_hunter.jobs.bot import watch_over
from tlv_hunter.notify.alert import RLM, reference_area_words
from tlv_hunter.schedule import Rhythm
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram.bot import FAILURE_HEAD, Bot
from tlv_hunter.telegram.client import TelegramClient
from tlv_hunter.telegram.digest import (
    MESSAGE_LIMIT,
    Digest,
    GroupCounts,
    build_digest,
    digest_due,
    digest_messages,
    window_start,
)
from tlv_hunter.telegram.health import (
    MIN_SILENT_RUNS,
    GroupSilence,
    problems,
    silent_threshold,
)
from tlv_hunter.web.grouping import Grouping

ZONE = ZoneInfo("Asia/Jerusalem")
RHYTHM = Rhythm(timedelta(minutes=30), day_time(0, 0), day_time(7, 0))


def israel(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, day, hour, minute, tzinfo=ZONE).astimezone(UTC)


# --- silent groups (point 9 B) ---


def test_a_groups_threshold_is_its_longest_active_silence_times_1_5_never_below_48() -> None:
    busy = [israel(18, 8) + timedelta(minutes=20 * n) for n in range(30)]
    assert silent_threshold(busy, RHYTHM, ZONE) == MIN_SILENT_RUNS
    # 08:00 to the next day's 22:00 is 38 hours, 31 of them outside the quiet hours: 62
    # intervals, times 1.5.
    quiet_group = [israel(18, 8), israel(19, 22)]
    assert silent_threshold(quiet_group, RHYTHM, ZONE) == 93
    assert silent_threshold([], RHYTHM, ZONE) == MIN_SILENT_RUNS


def test_a_group_is_suspect_from_half_its_threshold_and_silent_at_it() -> None:
    assert not GroupSilence("g", 23, 48).suspect
    assert GroupSilence("g", 24, 48).suspect and not GroupSilence("g", 24, 48).silent
    assert GroupSilence("g", 48, 48).silent


# --- the problems (point 10 A) ---


def finished(n: int, at: datetime, *, failed: bool = False):
    return run_record(
        run_id=f"r{n}",
        started_at=at,
        finished_at=at + timedelta(minutes=2),
        status="failed" if failed else "succeeded",
        failure_kind="ProviderRunError: boom" if failed else None,
    )


def keys(found) -> list[str]:
    return [problem.key for problem in found]


def test_a_healthy_collection_has_no_problem() -> None:
    now = israel(18, 10, 10)
    runs = [finished(2, israel(18, 10, 0)), finished(1, israel(18, 9, 30))]
    assert problems(runs, RHYTHM, ZONE, now, [now - timedelta(minutes=30)], []) == []
    assert problems([], RHYTHM, ZONE, now, [], []) == []  # a fresh store: nothing yet


def test_three_failed_runs_in_a_row_is_a_problem() -> None:
    now = israel(18, 10, 10)
    runs = [finished(n, israel(18, 10, 0) - timedelta(minutes=30 * i), failed=True)
            for i, n in enumerate((3, 2, 1))]  # fmt: skip
    (found,) = problems(runs, RHYTHM, ZONE, now, [], [])
    assert found.key == "failed_runs" and "ProviderRunError: boom" in found.text
    assert problems(runs[:2] + [finished(0, israel(18, 9, 0))], RHYTHM, ZONE, now, [], []) == []


def test_no_run_for_two_intervals_of_active_time_or_a_run_stuck_is_a_problem() -> None:
    last = [finished(1, israel(18, 9, 0))]
    assert keys(problems(last, RHYTHM, ZONE, israel(18, 9, 59), [], [])) == []
    assert keys(problems(last, RHYTHM, ZONE, israel(18, 10, 3), [], [])) == ["no_run"]
    night = [finished(1, israel(18, 23, 40))]  # the quiet hours do not count
    assert keys(problems(night, RHYTHM, ZONE, israel(19, 7, 15), [], [])) == []
    stuck = [
        run_record(run_id="live", status="running", finished_at=None, started_at=israel(18, 9))
    ]
    assert keys(problems(stuck, RHYTHM, ZONE, israel(18, 10, 31), [], [])) == ["stuck:live"]
    assert keys(problems(stuck, RHYTHM, ZONE, israel(18, 10, 29), [], [])) == []


def test_pending_posts_older_than_two_hours_and_a_silent_group_are_problems() -> None:
    now = israel(18, 12)
    found = problems(
        [finished(1, now - timedelta(minutes=5))],
        RHYTHM,
        ZONE,
        now,
        [now - timedelta(hours=3), now - timedelta(minutes=30)],
        [GroupSilence("101", 50, 48), GroupSilence("202", 30, 48)],
    )
    assert keys(found) == ["pending", "silent:101"]
    named = problems([], RHYTHM, ZONE, now, [], [GroupSilence("101", 50, 48, "דירות בתל אביב")])
    assert named[0].text.startswith("הקבוצה דירות בתל אביב לא החזירה")
    assert found[0].text.startswith("1 מודעות ממתינות")


# --- the digest (point 7) ---


def snapshot_of(store: TiedStore):  # noqa: F811
    grouping = Grouping(
        SqliteRepository(store.db, read_only=True), store.userdata.find_corrections, store.root
    )
    return grouping.current().snapshot


def test_the_digest_counts_the_window_and_names_failures_and_silences(store: TiedStore) -> None:  # noqa: F811
    failed = finished(9, T0, failed=True).model_copy(update={"failure_kind": "<boom & co>"})
    settled = finished(8, T0 - timedelta(minutes=30)).model_copy(
        update={"cost_usd": 0.023, "cost_settled_at": T0, "apify_run_id": "a8"}
    )
    unsettled = finished(7, T0 + timedelta(minutes=30)).model_copy(update={"apify_run_id": "a7"})
    outside = finished(6, T0 - timedelta(days=2)).model_copy(
        update={"cost_usd": 9.0, "cost_settled_at": T0, "rows_fetched": 999}
    )
    profile = store.userdata.get_profile(store.userdata.list_users()[0].user_id)
    digest = build_digest(
        snapshot_of(store),
        [unsettled, failed, settled, outside],
        [],
        profile,
        [GroupSilence("g1", 30, 48)],
        [],
        T0 - timedelta(hours=1),
        T0 + timedelta(hours=1),
    )
    group = digest.by_group["g1"]
    # Six canonical posts and one duplicate, all first stored at T0.
    assert (group.collected, group.duplicates) == (7, 1)
    assert digest.colours["red"] == 1 and digest.colours["pending"] == 1
    assert digest.colours.get("green", 0) + digest.colours.get("orange", 0) == 3
    assert digest.runs == 3 and [r.run_id for r in digest.failed] == ["r9"]
    # The failed run reached Apify too: its cost is not settled yet either.
    assert digest.cost_usd == pytest.approx(0.023) and (digest.settled, digest.unsettled) == (1, 2)
    assert digest.rows_fetched == 36  # three runs in the window, 12 rows each
    assert digest.matches is not None and digest.matches >= 1
    messages = digest_messages(digest, ZONE)
    lines = digest_lines(messages)
    text = "\n".join(lines)
    assert text.startswith("📊 <b>סיכום יומי</b>")
    assert "&lt;boom &amp; co&gt;" in text and "<boom" not in text
    assert "⚠️ g1 שקטה כבר 30 ריצות" in text and "סף" not in text
    cost = lines.index("<b>-עלות-</b>")
    assert lines[cost + 1 : cost + 4] == [
        "• $0.0230 ב-Apify",
        "• 1 ריצות סופיות",
        "• 2 עוד לא סופיות",
    ]
    runs = lines.index("<b>-ריצות איסוף-</b>")
    assert lines[runs + 1 : runs + 5] == ["• 3 ריצות", "• 1 נכשלו", "• 36 שורות", "• 0 דולגו"]
    posts = lines.index("<b>-מודעות-</b>")
    assert lines[posts + 1 : posts + 6] == [
        "• 7 נאספו",
        "• 1 כפולות",
        "• 0 סווגו",
        "• 1 נדחו",
        "• 0 התראות",
    ]
    green, orange = digest.colours.get("green", 0), digest.colours.get("orange", 0)
    assert lines[posts + 6 : posts + 10] == [
        f"🟢 {green} פעילות, מחיר, מיקום וסוג ברורים",
        f"🟠 {orange} פעילות, חסר מחיר, מיקום או סוג",
        "🔴 1 נדחו",
        "• 1 ממתינות לסיווג",
    ]
    assert "• 0 מחיר בפייסבוק שונה מהטקסט" in lines
    assert lines.index("<b>-ריצות שנכשלו-</b>") > 0


def digest_lines(messages: list[str]) -> list[str]:
    """The digest's lines, each one's opening right-to-left mark checked and removed (#488)."""
    lines = "\n".join(messages).split("\n")
    assert all(line.startswith(RLM) for line in lines if line)
    return [line.removeprefix(RLM) for line in lines]


def test_each_group_is_its_own_block_with_a_dashed_bold_name_and_bullets() -> None:
    """#488: a blank line between one group's block and the next."""
    digest = Digest(
        start=T0,
        end=T0,
        runs=0,
        failed=(),
        rows_fetched=0,
        rows_skipped=0,
        cost_usd=0.0,
        settled=0,
        unsettled=0,
        by_group={"g1": GroupCounts(89, 23, 50, 25, 2), "g2": GroupCounts(4, 0, 4, 1, 0)},
        colours={},
        matches=None,
        price_mismatches=0,
        silences=(),
        problems=(),
        group_names={"g1": 'דירות בת"א', "g2": "שותפים"},
    )
    lines = digest_lines(digest_messages(digest, ZONE))
    at = lines.index("<b>-לפי קבוצה-</b>")
    assert lines[at + 1 :] == [
        '<b>-דירות בת"א-</b>',
        "• 89 נאספו | 50 סווגו",
        "• 23 כפולות | 25 נדחו | 2 התראות",
        "",
        "<b>-שותפים-</b>",
        "• 4 נאספו | 4 סווגו",
        "• 0 כפולות | 1 נדחו | 0 התראות",
    ]


def test_the_digest_names_each_group_from_the_config_in_its_order(store: TiedStore) -> None:  # noqa: F811
    digest = build_digest(
        snapshot_of(store),
        [],
        [],
        None,
        [GroupSilence("g1", 10, 48, 'דירות בת"א'), GroupSilence("g2", 30, 48)],
        [],
        T0 - timedelta(hours=1),
        T0 + timedelta(hours=1),
        group_names={"g1": 'דירות בת"א'},
    )
    lines = digest_lines(digest_messages(digest, ZONE))
    at = lines.index("<b>-לפי קבוצה-</b>")
    assert lines[at + 1 : at + 4] == [
        '<b>-דירות בת"א-</b>',
        "• 7 נאספו | 0 סווגו",
        "• 1 כפולות | 1 נדחו | 0 התראות",
    ]
    # Only a suspect group (half its threshold) or a silent one; the id when it has no name.
    assert "⚠️ g2 שקטה כבר 30 ריצות" in lines
    assert not any("דירות בת" in line and "שקטה" in line for line in lines)
    assert not any(line.startswith("ספי שקט") for line in lines)


def test_a_long_digest_is_split_at_line_ends_under_the_limit(store: TiedStore) -> None:  # noqa: F811
    many = [GroupSilence(f"group{n:04d}" + "x" * 60, 40, 48) for n in range(120)]
    digest = build_digest(snapshot_of(store), [], [], None, many, [], T0, T0)
    messages = digest_messages(digest, ZONE)
    assert len(messages) >= 2 and all(len(m) <= MESSAGE_LIMIT for m in messages)
    assert "\n".join(messages).count("group0119") == 1  # its silence line; no thresholds


def test_the_digest_is_due_at_08_00_israel_time_once_a_local_day() -> None:
    assert not digest_due(None, israel(18, 7, 59), ZONE)
    assert digest_due(None, israel(18, 8, 0), ZONE)
    assert not digest_due(israel(18, 8, 1), israel(18, 21, 0), ZONE)
    assert digest_due(israel(18, 8, 1), israel(19, 8, 0), ZONE)
    assert window_start(None, israel(18, 8)) == israel(17, 8)
    assert window_start(israel(17, 8, 2), israel(18, 8)) == israel(17, 8, 2)


# --- the bot sends them (to the admin's chat only) ---


def watching_bot(store: TiedStore, clock) -> tuple[Bot, FakeTelegram]:  # noqa: F811
    fake = FakeTelegram()
    grouping = Grouping(
        SqliteRepository(store.db, read_only=True), store.userdata.find_corrections, store.root
    )
    bot = Bot(
        TelegramClient(TOKEN, transport=fake, sleep=lambda _: None),
        SqliteRepository(store.db),
        store.userdata,
        grouping,
        reference_area_words(),
        site_url=SITE,
        store_root=store.root,
        clock=clock,
        sleep=lambda _: None,
        watch=watch_over(store.db, grouping, store.userdata, clock),
    )
    return bot, fake


class Moment:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now


def test_the_failure_alert_goes_once_per_problem_and_again_when_it_returns(
    store: TiedStore,  # noqa: F811
) -> None:
    linked_ron(store)
    clock = Moment(israel(13, 7, 30))  # before the digest's hour
    runs = SqliteRunStore(store.db)
    for n in range(3):
        runs.add_run(finished(n, clock.now - timedelta(minutes=10 + n), failed=True))
    bot, fake = watching_bot(store, clock)
    bot.watch_collection()
    bot.watch_collection()
    alerts = [m for m in fake.of("sendMessage") if m["text"].startswith(FAILURE_HEAD)]
    assert len(alerts) == 1 and alerts[0]["chat_id"] == CHAT
    assert "3 ריצות איסוף אחרונות נכשלו" in alerts[0]["text"]
    assert "ממתינות לסיווג" in alerts[0]["text"]  # the store's pending post, days old
    runs.add_run(finished(3, clock.now - timedelta(minutes=1)))
    bot.watch_collection()  # cleared
    for n in range(4, 7):
        runs.add_run(finished(n, clock.now, failed=True))
    bot.watch_collection()
    alerts = [m for m in fake.of("sendMessage") if m["text"].startswith(FAILURE_HEAD)]
    assert len(alerts) == 2 and "נכשלו" in alerts[1]["text"]
    assert "ממתינות" not in alerts[1]["text"]  # still standing: not alerted again


def test_the_digest_goes_at_08_00_once_and_records_its_time(store: TiedStore) -> None:  # noqa: F811
    linked_ron(store)
    clock = Moment(israel(13, 7, 59))
    runs = SqliteRunStore(store.db)
    runs.save_settings(settings(), expected=None)
    runs.add_run(finished(1, clock.now - timedelta(minutes=5)))
    bot, fake = watching_bot(store, clock)
    bot.watch_collection()
    assert not any("סיכום יומי" in m["text"] for m in fake.of("sendMessage"))
    clock.now = israel(13, 8, 0)
    bot.watch_collection()
    bot.watch_collection()
    digests = [m for m in fake.of("sendMessage") if "סיכום יומי" in m["text"]]
    assert len(digests) == 1 and digests[0]["chat_id"] == CHAT
    stored = runs.get_settings()
    assert stored is not None and stored.last_digest_at == israel(13, 8, 0)
    # A restart does not send it again the same day.
    again, fake_again = watching_bot(store, clock)
    again.watch_collection()
    assert not any("סיכום יומי" in m["text"] for m in fake_again.of("sendMessage"))


def test_nothing_is_sent_while_the_admin_is_not_linked(store: TiedStore) -> None:  # noqa: F811
    clock = Moment(israel(13, 9, 0))
    bot, fake = watching_bot(store, clock)
    bot.watch_collection()
    assert fake.calls == []


def test_a_bot_with_no_watch_does_nothing_more(store: TiedStore) -> None:  # noqa: F811
    harness = Harness(store, Moment(israel(13, 9, 0)))
    harness.bot.watch_collection()
    assert harness.fake.calls == []


# --- send_test_digest (writes nothing) ---


def run_send(store: TiedStore, *args: str):  # noqa: F811
    fake, out = FakeTelegram(), io.StringIO()
    code = send_test_digest.main(
        list(args),
        environ=environ(),
        repo_root=repo_of(store),
        transport=fake,
        clock=lambda: T0 + timedelta(hours=1),
        stream=out,
    )
    return code, out.getvalue(), fake


def test_send_test_digest_sends_to_the_admin_and_writes_nothing(store: TiedStore) -> None:  # noqa: F811
    code, out, _ = run_send(store)
    assert code == 1 and out == "refused: the admin is not linked to Telegram\n"
    linked_ron(store)
    SqliteWatermarkStore(store.db).save_all(
        [
            GroupWatermark(
                schema_version=1,
                group_id="g1",
                watermark=T0,
                last_success_at=T0,
                consecutive_failures=3,
            )
        ]
    )
    before = Path(store.db).read_bytes()
    code, out, fake = run_send(store, "--hours", "2")
    assert code == 0, out
    (sent,) = fake.of("sendMessage")
    assert sent["chat_id"] == CHAT and "סיכום יומי" in sent["text"]
    assert "<b>-g1-</b>" in sent["text"] and "• 7 נאספו | 0 סווגו" in sent["text"]
    assert "שקטה" not in sent["text"]  # 3 of 48: not suspect
    assert Path(store.db).read_bytes() == before
    assert TOKEN not in out
    assert run_send(store, "--hours", "0")[1] == "refused: --hours must be from 1 to 336\n"


# --- point 13: the recompute's time against the store's size ---


def test_each_grouping_recompute_logs_its_time_and_the_store_s_size(
    store: TiedStore,  # noqa: F811
    caplog: pytest.LogCaptureFixture,  # noqa: F811
) -> None:
    import logging

    with caplog.at_level(logging.INFO, logger="tlv_hunter.web.grouping"):
        snapshot_of(store)
    (line,) = [r.message for r in caplog.records if r.message.startswith("grouping recomputed")]
    assert " ms: generation " in line and "6 canonical posts" in line and "cards" in line
