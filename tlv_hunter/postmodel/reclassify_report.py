"""The files of one `reclassify --run` and the page Ron reads before anything is replaced
(`PHASE_2.md` 2.9; DECISIONS.md #218, #219, #221). A plain module: it formats, reads and writes
files under the run's folder, and nothing else.

`<store_root>/reclassify/<run_id>/` holds `proposals.jsonl` (appended per post, so a killed run
keeps every paid answer), then at the end `allow_unchanged.txt`, `allow_state_changes.txt`,
`diff.html` and, last, `summary.json` with `complete` true. `apply_reclassify` refuses a folder
without that file: the report always exists before a `Listing` is replaced."""

import html
import json
import os
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from tlv_hunter.parsing.datetimes import require_utc
from tlv_hunter.postmodel.reclassify import (
    ALLOW_STATE_CHANGES_FILE,
    ALLOW_UNCHANGED_FILE,
    COMPARED_FIELDS,
    PROPOSALS_FILE,
    REPORT_FILE,
    SUMMARY_FILE,
    Proposal,
    status_text,
)
from tlv_hunter.postmodel.rejects import CityRuling

SUMMARY_FORMAT_VERSION = 1


class TripleCount(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_version: str
    schema_version: int
    model_name: str
    count: int


class Summary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    format_version: Literal[1]
    run_id: str
    started_at: datetime
    finished_at: datetime
    current_prompt_version: str
    current_schema_version: int
    current_model_name: str
    prompt_fingerprint: str
    cap: float
    spent: float
    calls: int
    tokens: dict[str, int]
    reported_models: list[str]
    selected_by_triple: list[TripleCount]
    """The posts this run was asked about, counted by the triple of their stored `Listing`."""
    selected: int
    attempted: int
    proposed: int
    failed: int
    not_attempted: int
    state_changes: int
    unchanged_apart_from_provenance: int
    stopped: str | None
    complete: bool

    @field_validator("started_at", "finished_at")
    @classmethod
    def _utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class RunRefused(Exception):
    """The folder cannot be applied; the message says why."""


# --- the proposals file ---


def append_proposal(path: Path, proposal: Proposal) -> None:
    """One JSON line, flushed to disk before the next post is asked about."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as file:
        file.write(proposal.model_dump_json() + "\n")
        file.flush()
        os.fsync(file.fileno())


def read_proposals(path: Path) -> list[Proposal]:
    proposals = [
        Proposal.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len({p.listing_id for p in proposals}) != len(proposals):
        raise ValueError(f"{path}: a listing_id appears twice")
    return proposals


# --- the allow lists (#218) ---


def allow_lists(proposals: Iterable[Proposal]) -> tuple[list[str], list[str]]:
    """The proposed posts whose status is unchanged, and those whose state or reason changes, by
    `listing_id`. A failed post is in neither."""
    unchanged, changed = [], []
    for proposal in sorted(proposals, key=lambda p: p.listing_id):
        if proposal.new is None:
            continue
        (changed if proposal.status_changed else unchanged).append(proposal.listing_id)
    return unchanged, changed


def read_allow_file(path: Path) -> list[str]:
    """One `listing_id` (or a prefix) per line; blank lines and `#` lines are ignored."""
    entries = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def _write_allow_file(path: Path, ids: Sequence[str], what: str, run_id: str) -> None:
    lines = [
        f"# reclassify run {run_id}: {what} ({len(ids)} posts).",
        "# For: apply_reclassify <run_id> --apply --allow-file <this file>. Delete the lines you "
        "do not accept.",
        *ids,
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# --- the run folder ---


Cities = Mapping[str, tuple[CityRuling, CityRuling]]
"""Per post, the city ruling (#214) of its old and of its new `Listing`: the name to show and where
it came from. Derived by the command from the stored `RawPost`; the report only formats it."""


def write_run_files(
    folder: Path,
    summary: Summary,
    proposals: Sequence[Proposal],
    texts: Mapping[str, str],
    cities: Cities | None = None,
) -> None:
    """The lists, the page, then `summary.json`: it is written last and says `complete`."""
    if not summary.complete:
        raise ValueError("write_run_files writes the final summary")
    unchanged, changed = allow_lists(proposals)
    _write_allow_file(
        folder / ALLOW_UNCHANGED_FILE,
        unchanged,
        "proposed, the status is unchanged",
        summary.run_id,
    )
    _write_allow_file(
        folder / ALLOW_STATE_CHANGES_FILE,
        changed,
        "proposed, the state or the reason changes",
        summary.run_id,
    )
    (folder / REPORT_FILE).write_text(
        render_diff(summary, proposals, texts, cities), encoding="utf-8", newline="\n"
    )
    temporary = folder / (SUMMARY_FILE + ".tmp")
    temporary.write_text(summary.model_dump_json(indent=1) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(folder / SUMMARY_FILE)


@dataclass(frozen=True)
class FinishedRun:
    folder: Path
    summary: Summary
    proposals: list[Proposal]


def read_finished_run(folder: Path) -> FinishedRun:
    """The run, if its report is complete: `summary.json` says so and `diff.html` exists."""
    if not folder.is_dir():
        raise RunRefused(f"no run at {folder}")
    summary_path = folder / SUMMARY_FILE
    if not summary_path.is_file():
        raise RunRefused(f"{folder}: no {SUMMARY_FILE}; the report was not finished")
    summary = Summary.model_validate_json(summary_path.read_text(encoding="utf-8"))
    if not summary.complete or not (folder / REPORT_FILE).is_file():
        raise RunRefused(f"{folder}: the report is not complete; nothing is applied before it")
    proposals_path = folder / PROPOSALS_FILE
    if not proposals_path.is_file():
        raise RunRefused(f"{folder}: no {PROPOSALS_FILE}")
    return FinishedRun(folder, summary, read_proposals(proposals_path))


# --- the page ---

_STYLE = """
body { font-family: system-ui, sans-serif; margin: 1.5rem auto; max-width: 62rem; padding: 0 1rem;
  line-height: 1.4; }
table { border-collapse: collapse; margin: .5rem 0 1rem; }
th, td { border: 1px solid #bbb; padding: .25rem .6rem; text-align: start; vertical-align: top; }
.card { border: 1px solid #bbb; border-radius: 6px; margin: 1rem 0; padding: .6rem .9rem; }
.card.changed { border-color: #c60; }
.card.failed { border-color: #b00; }
.text { white-space: pre-wrap; background: #f6f6f6; padding: .5rem; border-radius: 4px; }
.old { color: #900; } .new { color: #060; } .muted { color: #666; }
.caution { background: #fff4d6; border: 1px solid #d9b44a; padding: .6rem .9rem; }
button { margin-inline-end: .4rem; }
@media (prefers-color-scheme: dark) {
  body { background: #1b1b1b; color: #e6e6e6; }
  th, td, .card { border-color: #555; } .text { background: #2a2a2a; }
  .caution { background: #3a3220; border-color: #8a7330; }
  .old { color: #f08080; } .new { color: #7fd17f; } .muted { color: #aaa; }
}
"""

_SCRIPT = """
function show(test) {
  for (const card of document.querySelectorAll('.card')) {
    card.style.display = test(card.dataset) ? '' : 'none';
  }
}
document.getElementById('f-all').onclick = () => show(() => true);
document.getElementById('f-state').onclick = () => show(d => d.state === '1');
document.getElementById('f-failed').onclick = () => show(d => d.failed === '1');
document.getElementById('f-field').onchange = (e) => {
  const name = e.target.value;
  show(d => name === '' || d.fields.split(' ').includes(name));
};
"""


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _value(listing, name: str) -> str:
    return json.dumps(listing.model_dump(mode="json")[name], ensure_ascii=False)


def _field_counts(proposals: Sequence[Proposal]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for proposal in proposals:
        counts.update(proposal.fields_changed)
    return counts


def _area_moves(proposals: Sequence[Proposal]) -> tuple[int, int]:
    """Posts that gained an area number, and posts that lost one."""
    gained = lost = 0
    for proposal in proposals:
        if proposal.new is None:
            continue
        before, after = set(proposal.old.listing.areas), set(proposal.new.listing.areas)
        gained += bool(after - before)
        lost += bool(before - after)
    return gained, lost


def render_diff(
    summary: Summary,
    proposals: Sequence[Proposal],
    texts: Mapping[str, str],
    cities: Cities | None = None,
) -> str:
    """The page Ron reads. Static: no network, no external file. Post text is set as escaped text.
    What he reads first are the header and the state changes."""
    ordered = sorted(proposals, key=lambda p: p.listing_id)
    proposed = [p for p in ordered if p.new is not None]
    failed = [p for p in ordered if p.new is None]
    state_changes = [p for p in proposed if p.status_changed]
    unchanged, changed = allow_lists(ordered)
    out: list[str] = []
    add = out.append

    add("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    add("<meta name='viewport' content='width=device-width, initial-scale=1'>")
    add(f"<title>Reclassify {_e(summary.run_id)}</title><style>{_STYLE}</style></head><body>")
    add(f"<h1>Reclassify run {_e(summary.run_id)}</h1>")
    add(
        "<p class='caution'>The same prompt and model give a different answer on many posts "
        "(20 of 46 posts changed between the two passes of the version 3 regression run), so this "
        "diff shows the model's variation as well as the effect of the change, and it cannot tell "
        "them apart. Every post you apply is replaced, even one that needed nothing: its "
        "provenance has to move, or it would be selected again. Nothing has been replaced "
        "yet.</p>"
    )

    add("<h2>This run</h2><table>")
    current = (
        f"prompt {summary.current_prompt_version}, schema {summary.current_schema_version}, "
        f"{summary.current_model_name}"
    )
    rows = [
        ("Current", current),
        (
            "Stored Listings asked about",
            "; ".join(
                f"prompt {t.prompt_version}, schema {t.schema_version}, {t.model_name}: {t.count}"
                for t in summary.selected_by_triple
            )
            or "none",
        ),
        (
            "Posts",
            f"{summary.selected} selected, {summary.attempted} attempted, {summary.proposed} "
            f"proposed, {summary.failed} failed, {summary.not_attempted} not attempted",
        ),
        ("Unchanged apart from the provenance", summary.unchanged_apart_from_provenance),
        (
            "Calls, cost",
            f"{summary.calls} calls, ${summary.spent:.6f} of the ${summary.cap:.2f} cap",
        ),
        ("Reported models", ", ".join(summary.reported_models) or "-"),
        ("Stopped", summary.stopped or "no"),
        ("Fingerprint", summary.prompt_fingerprint),
    ]
    for label, value in rows:
        add(f"<tr><th>{_e(label)}</th><td>{_e(value)}</td></tr>")
    add("</table>")

    add(f"<h2>State changes ({len(state_changes)})</h2>")
    if not state_changes:
        add("<p>No post changes state.</p>")
    else:
        add(
            "<table><tr><th>Post</th><th>Was</th><th>Becomes</th><th>City</th>"
            "<th>Reviewed by Ron</th></tr>"
        )
        for p in state_changes:
            add(
                f"<tr><td>{_e(p.listing_id[:12])}</td>"
                f"<td class='old'>{_e(status_text(p.old_status))}</td>"
                f"<td class='new'>{_e(status_text(p.new_status))}</td>"
                f"<td dir='auto'>{_e(_city_text(p, cities))}</td>"
                f"<td>{_e(_reviewed_text(p))}</td></tr>"
            )
        add("</table>")

    counts = _field_counts(proposed)
    add(f"<h2>Fields changed (of {len(proposed)} proposed posts)</h2><table>")
    add("<tr><th>Field</th><th>Posts changed</th></tr>")
    for name, count in counts.most_common():
        extra = ""
        if name == "areas":
            gained, lost = _area_moves(proposed)
            extra = f" ({gained} gained a number, {lost} lost one)"
        add(f"<tr><td>{_e(name)}</td><td>{count}{_e(extra)}</td></tr>")
    if not counts:
        add("<tr><td colspan='2'>no field differs</td></tr>")
    add("</table>")

    add(f"<h2>Failed ({len(failed)}) and not attempted ({summary.not_attempted})</h2>")
    if failed:
        add("<table><tr><th>Post</th><th>Why</th><th>Attempts</th></tr>")
        for p in failed:
            add(
                f"<tr><td>{_e(p.listing_id[:12])}</td><td>{_e(p.error)}</td>"
                f"<td>{p.attempts}</td></tr>"
            )
        add("</table>")
    else:
        add("<p>No post failed.</p>")

    reviewed = [p for p in proposed if p.reviewed]
    add(f"<h2>Posts with a reviewed correction on file ({len(reviewed)})</h2>")
    if reviewed:
        add(
            "<p>The replacement leaves Ron's correction attached to the old classification "
            "(DECISIONS.md #222); the new card shows the new answer.</p><ul>"
        )
        for p in reviewed:
            add(f"<li>{_e(p.listing_id[:12])}: {_e(_reviewed_text(p))}</li>")
        add("</ul>")
    else:
        add("<p>None.</p>")

    add("<h2>To apply</h2><p>")
    add(
        f"<code>{_e(ALLOW_UNCHANGED_FILE)}</code>: {len(unchanged)} posts whose status is "
        f"unchanged. <code>{_e(ALLOW_STATE_CHANGES_FILE)}</code>: {len(changed)} posts whose state "
        "or reason changes. In this run's folder; use "
        f"<code>apply_reclassify {_e(summary.run_id)} --apply --allow-file &lt;file&gt;</code>. "
        "Copy a file and delete the lines you do not accept.</p>"
    )

    add("<h2>Posts</h2><p>")
    add(
        "<button id='f-all'>all</button><button id='f-state'>state changed</button>"
        "<button id='f-failed'>failed</button> field: <select id='f-field'><option value=''>any"
        "</option>"
    )
    for name in COMPARED_FIELDS:
        add(f"<option>{_e(name)}</option>")
    add("</select></p>")
    for p in ordered:
        add(_card(p, texts.get(p.listing_id, "")))
    add(f"<script>{_SCRIPT}</script></body></html>")
    return "\n".join(out) + "\n"


def _city_text(proposal: Proposal, cities: Cities | None) -> str:
    """The city of a row where the old or the new status is `other_city` (#214): the name and its
    source, before and after. Empty for any other row."""
    statuses = (proposal.old_status, proposal.new_status)
    if all(status is None or status[1] != "other_city" for status in statuses):
        return ""
    if cities is None or proposal.listing_id not in cities:
        return "-"
    before, after = cities[proposal.listing_id]

    def show(ruling: CityRuling) -> str:
        return "none" if ruling.name is None else f"{ruling.name} ({ruling.source})"

    return f"was {show(before)}; becomes {show(after)}"


def _reviewed_text(proposal: Proposal) -> str:
    if not proposal.reviewed:
        return "no"
    if proposal.corrected_fields:
        return "corrected: " + ", ".join(proposal.corrected_fields)
    return "reviewed, nothing corrected"


def _card(p: Proposal, text: str) -> str:
    classes = (
        "card" + (" changed" if p.status_changed else "") + (" failed" if p.new is None else "")
    )
    out = [
        f"<div class='{classes}' data-state='{int(p.status_changed)}' "
        f"data-failed='{int(p.new is None)}' data-fields='{_e(' '.join(p.fields_changed))}'>",
        f"<h3>{_e(p.listing_id[:12])}</h3>",
        f"<p>Status: <span class='old'>{_e(status_text(p.old_status))}</span> &rarr; "
        f"<span class='new'>{_e(status_text(p.new_status))}</span>"
        + (" (flagged: kept)" if p.old.flagged else "")
        + f". {p.attempts} attempts, ${p.cost:.6f}. Reviewed by Ron: {_e(_reviewed_text(p))}.</p>",
        f"<div class='text' dir='auto'>{_e(text)}</div>",
    ]
    if p.new is None:
        out.append(f"<p>Failed: {_e(p.error)}. The old Listing stays.</p>")
    else:
        out.append("<table><tr><th>Field</th><th>Was</th><th>Becomes</th></tr>")
        for name in p.fields_changed:
            out.append(
                f"<tr><td>{_e(name)}</td><td class='old'>{_e(_value(p.old.listing, name))}</td>"
                f"<td class='new'>{_e(_value(p.new.listing, name))}</td></tr>"
            )
        if not p.fields_changed:
            out.append("<tr><td colspan='3'>no field differs</td></tr>")
        out.append("</table>")
        unchanged = [n for n in COMPARED_FIELDS if n not in p.fields_changed]
        out.append(
            f"<details><summary>{len(unchanged)} fields unchanged</summary>"
            f"<p class='muted'>{_e(', '.join(unchanged))}</p></details>"
        )
        dropped = p.dropped
        if dropped.streets or dropped.area_names or dropped.other_city:
            out.append(
                "<p class='muted'>Dropped from the new answer (#162, #180): "
                f"streets {_e(dropped.streets)}, area names {_e(dropped.area_names)}, "
                f"city {_e(dropped.other_city)}.</p>"
            )
    out.append("</div>")
    return "".join(out)
