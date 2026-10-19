"""The daily digest to the admin (`BASELINE.md` §11; DECISIONS.md #359, #450; `PHASE_5.md` point
7). Pure: the grouping's snapshot, the run records, the sent alerts, the admin's profile and the
health checks in; the Hebrew messages out. The bot sends them at `DIGEST_AT` Israel time and keeps
the time in `ScheduleSettings.last_digest_at`; `jobs/send_test_digest.py` sends one on demand.

The window is from the last digest to now (24 hours with none). Counted from the stored timestamps
(`RawPost.fetched_at`, `Listing.classified_at`, `SentAlert.sent_at`, the run records' start):
- per group: collected (the canonicals and the duplicates first stored in the window), duplicates,
  classified, rejected (of the collected canonicals, their state now), alerted;
- the collected canonicals by colour, independent of any profile (#359): green, active with the
  price, the location and the kind all written; orange, active with one of them not; red,
  rejected; and the pending ones;
- the collected canonicals the admin's saved profile shows (`policy.evaluate`);
- the price mismatches: a native price that is not among the text's prices;
- the runs: how many, the failed ones with their reason, the rows fetched and skipped (#71 D);
- the Apify cost (#450): the runs settled by `settle_costs`, and how many are not yet;
- the silent groups' state and every group's threshold (point 9 B), and the problems that stand.

Not in it (#471, a field outside Gate G): retention's last numbers, which no record holds.
"""

import html
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from datetime import time as day_time
from zoneinfo import ZoneInfo

from tlv_hunter.contracts.listing import Listing
from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.raw_post import RawPost
from tlv_hunter.contracts.run_record import RunRecord
from tlv_hunter.contracts.sent_alert import SentAlert
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.postmodel.seen import SeenListing
from tlv_hunter.telegram.health import GroupSilence, Problem
from tlv_hunter.web.grouping import Snapshot

DIGEST_AT = day_time(8, 0)
DEFAULT_WINDOW = timedelta(hours=24)
MESSAGE_LIMIT = 4096
FAILED_LISTED = 10
THRESHOLDS_PER_LINE = 8  # so no single line nears a message's limit


@dataclass
class GroupCounts:
    collected: int = 0
    duplicates: int = 0
    classified: int = 0
    rejected: int = 0
    alerted: int = 0


@dataclass(frozen=True)
class Digest:
    start: datetime
    end: datetime
    runs: int
    failed: tuple[RunRecord, ...]
    rows_fetched: int
    rows_skipped: int
    cost_usd: float
    settled: int
    unsettled: int
    by_group: Mapping[str, GroupCounts]
    colours: Mapping[str, int]
    matches: int | None
    price_mismatches: int
    silences: tuple[GroupSilence, ...]
    problems: tuple[Problem, ...]
    alerted: int = field(default=0)


def digest_due(last: datetime | None, now: datetime, zone: ZoneInfo) -> bool:
    """At `DIGEST_AT` Israel time or later, once a local day."""
    local = now.astimezone(zone)
    if local.time() < DIGEST_AT:
        return False
    return last is None or last.astimezone(zone).date() < local.date()


def window_start(last: datetime | None, now: datetime) -> datetime:
    return now - DEFAULT_WINDOW if last is None else min(last, now)


def build_digest(
    snapshot: Snapshot,
    runs: Sequence[RunRecord],
    sent: Sequence[SentAlert],
    profile: Profile | None,
    silences: Sequence[GroupSilence],
    problems: Sequence[Problem],
    start: datetime,
    end: datetime,
) -> Digest:
    def within(moment: datetime) -> bool:
        return start <= moment < end

    canonicals: list[tuple[RawPost, str, SeenListing | None]] = [
        (member.post, member.lifecycle.state, member.seen) for member in snapshot.members.values()
    ] + [(other.post, other.lifecycle.state, other.seen) for other in snapshot.others.values()]
    group_of = {post.listing_id: post.group_id for post, _, _ in canonicals}
    by_group: dict[str, GroupCounts] = defaultdict(GroupCounts)
    for duplicates in snapshot.duplicates.values():
        for duplicate in duplicates:
            group_of[duplicate.listing_id] = duplicate.group_id
            if within(duplicate.fetched_at):
                by_group[duplicate.group_id].collected += 1
                by_group[duplicate.group_id].duplicates += 1
    colours: Counter[str] = Counter()
    matches = 0
    mismatches = 0
    for post, state, seen in canonicals:
        counts = by_group[post.group_id]
        if seen is not None and within(seen.listing.classified_at):
            counts.classified += 1
        if not within(post.fetched_at):
            continue
        counts.collected += 1
        if state == "rejected":
            counts.rejected += 1
            colours["red"] += 1
        elif state == "pending":
            colours["pending"] += 1
        elif state == "active" and seen is not None:
            colours["green" if _clear(seen.listing) else "orange"] += 1
            if profile is not None and evaluate(seen, profile, end).shown:
                matches += 1
        if seen is not None and _price_mismatch(post, seen.listing):
            mismatches += 1
    alerted = 0
    for alert in sent:
        if within(alert.sent_at):
            alerted += 1
            group = group_of.get(alert.listing_id)
            if group is not None:
                by_group[group].alerted += 1
    in_window = [run for run in runs if within(run.started_at)]
    settled = [run for run in in_window if run.cost_usd is not None]
    return Digest(
        start=start,
        end=end,
        runs=len(in_window),
        failed=tuple(run for run in in_window if run.status == "failed"),
        rows_fetched=sum(run.rows_fetched or 0 for run in in_window),
        rows_skipped=sum(run.rows_skipped or 0 for run in in_window),
        cost_usd=round(sum(run.cost_usd or 0.0 for run in settled), 6),
        settled=len(settled),
        unsettled=sum(
            1 for run in in_window if run.cost_usd is None and run.apify_run_id is not None
        ),
        by_group=dict(sorted(by_group.items())),
        colours=dict(colours),
        matches=None if profile is None else matches,
        price_mismatches=mismatches,
        silences=tuple(silences),
        problems=tuple(problems),
        alerted=alerted,
    )


def digest_messages(digest: Digest, zone: ZoneInfo) -> list[str]:
    """The Hebrew text (HTML parse mode, every value escaped), split at line ends into messages of
    at most `MESSAGE_LIMIT` characters."""

    def when(moment: datetime, form: str = "%d.%m %H:%M") -> str:
        return moment.astimezone(zone).strftime(form)

    total = GroupCounts()
    for counts in digest.by_group.values():
        for name in ("collected", "duplicates", "classified", "rejected"):
            setattr(total, name, getattr(total, name) + getattr(counts, name))
    colours = digest.colours
    lines = [
        "📊 <b>סיכום יומי</b>",
        f"{when(digest.start)} – {when(digest.end)}",
        "",
        f"ריצות איסוף: {digest.runs}, נכשלו {len(digest.failed)} · שורות {digest.rows_fetched}"
        f", דולגו {digest.rows_skipped}",
        f"עלות Apify: ${digest.cost_usd:.4f} ב-{digest.settled} ריצות סופיות"
        + (f" · {digest.unsettled} עוד לא סופיות" if digest.unsettled else ""),
        f"מודעות שנאספו: {total.collected} (כפולות {total.duplicates}) · סווגו "
        f"{total.classified} · נדחו {total.rejected} · התראות {digest.alerted}",
        f"🟢 {colours.get('green', 0)} · 🟠 {colours.get('orange', 0)} · 🔴 "
        f"{colours.get('red', 0)} · ממתינות {colours.get('pending', 0)}",
    ]
    if digest.matches is not None:
        lines.append(f"תואמות להעדפות שלך: {digest.matches}")
    lines.append(f"מחיר בפייסבוק שאינו בין מחירי הטקסט: {digest.price_mismatches}")
    if digest.by_group:
        lines += ["", "<b>לפי קבוצה</b>"]
        for group_id, counts in digest.by_group.items():
            lines.append(
                f"• {html.escape(group_id)}: נאספו {counts.collected} · כפולות "
                f"{counts.duplicates} · סווגו {counts.classified} · נדחו {counts.rejected} · "
                f"התראות {counts.alerted}"
            )
    if digest.failed:
        lines += ["", "<b>ריצות שנכשלו</b>"]
        for run in digest.failed[:FAILED_LISTED]:
            lines.append(
                f"• {when(run.started_at, '%H:%M')} · {html.escape(run.failure_kind or '')}"
            )
        if len(digest.failed) > FAILED_LISTED:
            lines.append(f"• ועוד {len(digest.failed) - FAILED_LISTED}")
    quiet = [g for g in digest.silences if g.suspect]
    if quiet:
        lines += ["", "<b>קבוצות שקטות</b>"]
        for group in quiet:
            state = "שקטה מדי" if group.silent else "חשודה"
            lines.append(
                f"• {html.escape(group.group_id)}: {group.runs} ריצות בלי פוסט "
                f"(סף {group.threshold}) · {state}"
            )
    if digest.problems:
        lines += ["", "<b>⚠️ בעיות פתוחות</b>"]
        lines += [f"• {html.escape(problem.text)}" for problem in digest.problems]
    if digest.silences:
        entries = [f"{html.escape(g.group_id)} {g.threshold}" for g in digest.silences]
        lines += ["", "ספי שקט בריצות: " + " · ".join(entries[:THRESHOLDS_PER_LINE])]
        for at in range(THRESHOLDS_PER_LINE, len(entries), THRESHOLDS_PER_LINE):
            lines.append(" · ".join(entries[at : at + THRESHOLDS_PER_LINE]))
    return _split(lines)


def _clear(listing: Listing) -> bool:
    """#359's green: the price, the location and the kind all written."""
    return (
        listing.price.state == "written"
        and bool(listing.areas)
        and listing.apartment_kind.state == "written"
    )


def _price_mismatch(post: RawPost, listing: Listing) -> bool:
    """A native price the text's prices do not include (the text decides, #114)."""
    if post.native_price is None or listing.price.state != "written":
        return False
    if listing.price_source != "text":
        return False
    return post.native_price not in (listing.price.value or [])


def _split(lines: Sequence[str]) -> list[str]:
    messages: list[str] = []
    current = ""
    for line in lines:
        candidate = line if not current else f"{current}\n{line}"
        if len(candidate) > MESSAGE_LIMIT and current:
            messages.append(current)
            current = line[:MESSAGE_LIMIT]
        else:
            current = candidate[:MESSAGE_LIMIT]
    if current:
        messages.append(current)
    return messages
