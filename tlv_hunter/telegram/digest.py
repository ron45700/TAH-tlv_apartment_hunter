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
- Facebook's runs: how many, the failed ones with their reason, the rows fetched and skipped
  (#71 D);
- the Apify cost (#450): the runs settled by `settle_costs`, and how many are not yet;
- **Yad2 (#535)**, when it ran in the window: its runs, the failed ones and how many were blocks
  (`failure_kind` "blocked: …"), the listings read on its list pages (`rows_fetched`), the new
  listings (first stored in the window), the bumped ones (a stored `last_published_at` in the
  window, later than the post's own `posted_at`: listings, not bump events). No record holds a
  list page count or a bump (Gate G unchanged);
- the silent groups: only a suspect one or one over its threshold (point 9 B; the thresholds are
  not printed, #482), and the problems that stand.

The layout (#482, amended by #488): section headings bold and between dashes ("<b>-עלות-</b>"),
one value a line, number first, opened by "• "; the colours four lines with their meaning (#359);
per group its name from the config (an id with no name, the id), as a heading, then two lines of
counts, a blank line before the next group; every non-empty line opened by U+200F.

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
from tlv_hunter.notify.alert import rtl_lines
from tlv_hunter.parsing.ids import YAD2_SOURCE
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.postmodel.seen import SeenListing
from tlv_hunter.telegram.health import GroupSilence, Problem
from tlv_hunter.web.grouping import Snapshot

DIGEST_AT = day_time(8, 0)
DEFAULT_WINDOW = timedelta(hours=24)
MESSAGE_LIMIT = 4096
FAILED_LISTED = 10
BULLET = "• "  # every value line inside a section (#488)
BLOCKED = "blocked:"  # a Yad2 block's failure_kind (`yad2/block.py`)


@dataclass
class GroupCounts:
    collected: int = 0
    duplicates: int = 0
    classified: int = 0
    rejected: int = 0
    alerted: int = 0


@dataclass(frozen=True)
class Yad2Counts:
    runs: int = 0
    failed: int = 0
    blocked: int = 0
    listings_read: int = 0
    new: int = 0
    bumped: int = 0


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
    group_names: Mapping[str, str] = field(default_factory=dict)
    yad2: Yad2Counts = field(default_factory=Yad2Counts)
    """`runs`, `failed`, the rows and the cost above are Facebook's; Yad2's are here (#535)."""


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
    *,
    group_names: Mapping[str, str] | None = None,
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
    window_runs = [run for run in runs if within(run.started_at)]
    in_window = [run for run in window_runs if run.source == "facebook"]
    settled = [run for run in in_window if run.cost_usd is not None]
    yad2_runs = [run for run in window_runs if run.source == "yad2"]
    yad2_failed = [run for run in yad2_runs if run.status == "failed"]
    yad2_posts = [post for post, _, _ in canonicals if post.source == YAD2_SOURCE]
    yad2_posts += [
        duplicate
        for duplicates in snapshot.duplicates.values()
        for duplicate in duplicates
        if duplicate.source == YAD2_SOURCE
    ]
    clocks = [(member.post, member.lifecycle) for member in snapshot.members.values()]
    clocks += [(other.post, other.lifecycle) for other in snapshot.others.values()]
    yad2 = Yad2Counts(
        runs=len(yad2_runs),
        failed=len(yad2_failed),
        blocked=sum(1 for run in yad2_failed if (run.failure_kind or "").startswith(BLOCKED)),
        listings_read=sum(run.rows_fetched or 0 for run in yad2_runs),
        new=sum(1 for post in yad2_posts if within(post.fetched_at)),
        bumped=sum(
            1
            for post, lifecycle in clocks
            if post.source == YAD2_SOURCE
            and within(lifecycle.last_published_at)
            and lifecycle.last_published_at > post.posted_at
        ),
    )
    return Digest(
        start=start,
        end=end,
        runs=len(in_window),
        failed=tuple(run for run in window_runs if run.status == "failed"),
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
        group_names=dict(group_names or {}),
        yad2=yad2,
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
        _heading("ריצות פייסבוק"),
        f"{BULLET}{digest.runs} ריצות",
        f"{BULLET}{sum(1 for run in digest.failed if run.source == 'facebook')} נכשלו",
        f"{BULLET}{digest.rows_fetched} שורות",
        f"{BULLET}{digest.rows_skipped} דולגו",
        "",
        _heading("עלות"),
        f"{BULLET}${digest.cost_usd:.4f} ב-Apify",
        f"{BULLET}{digest.settled} ריצות סופיות",
    ]
    if digest.unsettled:
        lines.append(f"{BULLET}{digest.unsettled} עוד לא סופיות")
    yad2 = digest.yad2
    if yad2.runs:
        blocked = f" ({yad2.blocked} חסימות)" if yad2.blocked else ""
        lines += [
            "",
            _heading("יד2"),
            f"{BULLET}{yad2.runs} ריצות",
            f"{BULLET}{yad2.failed} נכשלו{blocked}",
            f"{BULLET}{yad2.listings_read} מודעות נקראו ברשימה",
            f"{BULLET}{yad2.new} מודעות חדשות",
            f"{BULLET}{yad2.bumped} הוקפצו",
        ]
    lines += [
        "",
        _heading("מודעות"),
        f"{BULLET}{total.collected} נאספו",
        f"{BULLET}{total.duplicates} כפולות",
        f"{BULLET}{total.classified} סווגו",
        f"{BULLET}{total.rejected} נדחו",
        f"{BULLET}{digest.alerted} התראות",
        # #359's three colours, each with its meaning (#488); the circle opens the line.
        f"🟢 {colours.get('green', 0)} פעילות, מחיר, מיקום וסוג ברורים",
        f"🟠 {colours.get('orange', 0)} פעילות, חסר מחיר, מיקום או סוג",
        f"🔴 {colours.get('red', 0)} נדחו",
        f"{BULLET}{colours.get('pending', 0)} ממתינות לסיווג",
    ]
    if digest.matches is not None:
        lines.append(f"{BULLET}{digest.matches} תואמות להעדפות שלך")
    lines.append(f"{BULLET}{digest.price_mismatches} מחיר בפייסבוק שונה מהטקסט")
    if digest.by_group:
        lines += ["", _heading("לפי קבוצה")]
        for at, group_id in enumerate(_group_order(digest)):
            counts = digest.by_group[group_id]
            lines += [""] if at else []
            lines += [
                _heading(_name(digest, group_id)),
                f"{BULLET}{counts.collected} נאספו | {counts.classified} סווגו",
                f"{BULLET}{counts.duplicates} כפולות | {counts.rejected} נדחו | "
                f"{counts.alerted} התראות",
            ]
    if digest.failed:
        lines += ["", _heading("ריצות שנכשלו")]
        for run in digest.failed[:FAILED_LISTED]:
            source = "יד2 · " if run.source == "yad2" else ""
            lines.append(
                f"{BULLET}{when(run.started_at, '%H:%M')} · {source}"
                f"{html.escape(run.failure_kind or '')}"
            )
        if len(digest.failed) > FAILED_LISTED:
            lines.append(f"{BULLET}ועוד {len(digest.failed) - FAILED_LISTED}")
    quiet = [g for g in digest.silences if g.suspect]
    if quiet:
        lines.append("")
        for group in quiet:
            name = html.escape(group.name or _name(digest, group.group_id), quote=False)
            lines.append(f"⚠️ {name} שקטה כבר {group.runs} ריצות")
    if digest.problems:
        lines += ["", "⚠️ " + _heading("בעיות פתוחות")]
        lines += [f"{BULLET}{html.escape(problem.text)}" for problem in digest.problems]
    return _split(rtl_lines("\n".join(lines)).split("\n"))


def _heading(words: str) -> str:
    """A section's heading, or a group's name: bold, and between dashes for a screen that shows no
    bold (#488)."""
    return f"<b>-{html.escape(words, quote=False)}-</b>"


def _name(digest: Digest, group_id: str) -> str:
    return digest.group_names.get(group_id, group_id)


def _group_order(digest: Digest) -> list[str]:
    """The groups in the config's order; any other (a group no longer configured) after, by id."""
    named = [group_id for group_id in digest.group_names if group_id in digest.by_group]
    return named + [group_id for group_id in digest.by_group if group_id not in named]


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
