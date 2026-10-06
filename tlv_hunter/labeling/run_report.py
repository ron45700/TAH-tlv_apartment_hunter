"""A regression run's report (`PHASE_2.md` 2.6): one folder per run under `data/labeling/runs/`,
named for the prompt version, its fingerprint and the run id.

- `results.json`: per pass and post, the completed `Listing` (the review report reads pass 1 from
  here, #193), the dropped names, the attempts and the calls' usage and cost; per pass, the bar per
  field and every mismatch; the overrides applied, verbatim.
- `report.html`: the same, readable, with each mismatched post's text. Static: no script, nothing
  loaded from outside; every text is escaped.

Both are under `data/`, gitignored: they hold post texts.
"""

import html
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tlv_hunter.classify.complete import Completed
from tlv_hunter.classify.cost import CallRecord
from tlv_hunter.labeling.compare import FIELDS, PassResult, same, shown
from tlv_hunter.labeling.corrections import RESULTS_FILE
from tlv_hunter.labeling.regression import Prepared
from tlv_hunter.labeling.regression_set import text_sha256

REPORT_FILE = "report.html"


@dataclass(frozen=True)
class PostRun:
    """One post in one pass."""

    listing_id: str
    outcome: str
    """"ok", or "failed: <kind>"."""
    attempts: int
    completed: Completed | None
    calls: tuple[CallRecord, ...]
    error: str | None = None
    """The last attempt's error detail: field paths and types, never post content (#139)."""


@dataclass(frozen=True)
class RunMeta:
    run_id: str
    started_at: datetime
    finished_at: datetime
    model: str
    prompt_version: str
    prompt_fingerprint: str
    reasoning_effort: str
    temperature: float | None
    cap: float
    spent: float
    stopped: str | None


def folder_name(meta: RunMeta) -> str:
    return (
        f"v{meta.prompt_version}-{meta.reasoning_effort}-{meta.prompt_fingerprint[:8]}"
        f"-{meta.run_id}"
    )


def changed_posts(flipped: Sequence[tuple[int, str, str, str]]) -> int:
    """The posts with at least one answer that changed between the passes."""
    return len({position for position, *_ in flipped})


def write_run(
    runs_dir: Path,
    meta: RunMeta,
    prepared: Prepared,
    passes: Sequence[list[PostRun]],
    results: Sequence[PassResult],
) -> Path:
    folder = runs_dir / folder_name(meta)
    folder.mkdir(parents=True, exist_ok=False)
    data = _results(meta, prepared, passes, results)
    (folder / RESULTS_FILE).write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (folder / REPORT_FILE).write_text(
        _html(meta, prepared, passes, results), encoding="utf-8", newline=""
    )
    return folder


def flips(prepared: Prepared, passes: Sequence[list[PostRun]]) -> list[tuple[int, str, str, str]]:
    """Every compared field whose answer changed between pass 1 and pass 2 (O12): position,
    field, pass 1's value, pass 2's."""
    if len(passes) < 2:
        return []
    second = {run.listing_id: run for run in passes[1]}
    found = []
    for run in passes[0]:
        other = second.get(run.listing_id)
        if run.completed is None or other is None or other.completed is None:
            continue
        for name in FIELDS:
            one = getattr(run.completed.listing, name)
            two = getattr(other.completed.listing, name)
            if not same(name, one, two):
                found.append((prepared.positions[run.listing_id], name, shown(one), shown(two)))
    return found


# --- results.json ---


def _call(call: CallRecord) -> dict[str, Any]:
    usage = call.usage
    return {
        "outcome": call.outcome,
        "status": call.status,
        "reported_model": call.reported_model,
        "seconds": call.seconds,
        "cost": call.cost,
        "input_tokens": usage.input_tokens,
        "cached_tokens": usage.cached_tokens,
        "cache_write_tokens": usage.cache_write_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
    }


def _results(
    meta: RunMeta,
    prepared: Prepared,
    passes: Sequence[list[PostRun]],
    results: Sequence[PassResult],
) -> dict[str, Any]:
    texts = {post.listing_id: post.text for post in prepared.posts}
    return {
        "run_id": meta.run_id,
        "started_at": meta.started_at.isoformat(),
        "finished_at": meta.finished_at.isoformat(),
        "model": meta.model,
        "prompt_version": meta.prompt_version,
        "prompt_fingerprint": meta.prompt_fingerprint,
        "reasoning_effort": meta.reasoning_effort,
        "temperature": meta.temperature,
        "cap": meta.cap,
        "spent": meta.spent,
        "stopped": meta.stopped,
        "labels_sha256": prepared.labels_sha256,
        "posts": len(prepared.truths),
        "removed_positions": prepared.removed,
        "ambiguous_positions": prepared.ambiguous,
        "overrides": None
        if prepared.overrides is None
        else prepared.overrides.model_dump(mode="json"),
        "passes": [
            {
                "number": result.number,
                "verdict": result.verdict,
                "areas_exact": None
                if result.areas_exact is None
                else {
                    "counted": result.areas_exact.counted,
                    "errors": result.areas_exact.errors,
                    "rate": result.areas_exact.rate,
                    "average_returned": result.areas_exact.average_returned,
                    "average_labelled": result.areas_exact.average_labelled,
                },
                "failed_positions": result.failed_posts,
                "missing_positions": result.missing_posts,
                "fields": [
                    {
                        "field": f.field,
                        "counted": f.counted,
                        "errors": f.errors,
                        "rate": f.rate,
                        "bar": f.bar,
                        "passed": f.passed,
                    }
                    for f in result.fields
                ],
                "mismatches": [vars(m) for m in result.mismatches],
                "posts": [
                    {
                        "position": prepared.positions[run.listing_id],
                        "listing_id": run.listing_id,
                        "text_sha256": text_sha256(texts[run.listing_id]),
                        "outcome": run.outcome,
                        "error": run.error,
                        "attempts": run.attempts,
                        "listing": None
                        if run.completed is None
                        else run.completed.listing.model_dump(mode="json"),
                        "dropped_streets": []
                        if run.completed is None
                        else list(run.completed.dropped_streets),
                        "dropped_area_names": []
                        if run.completed is None
                        else list(run.completed.dropped_area_names),
                        "dropped_other_city": None
                        if run.completed is None
                        else run.completed.dropped_other_city,
                        "calls": [_call(call) for call in run.calls],
                    }
                    for run in runs
                ],
            }
            for result, runs in zip(results, passes, strict=True)
        ],
        "changed_posts": changed_posts(flips(prepared, passes)),
        "flips": [
            {"position": p, "field": f, "pass_1": a, "pass_2": b}
            for p, f, a, b in flips(prepared, passes)
        ],
    }


# --- report.html ---

_STYLE = """
body { font: 14px/1.45 system-ui, "Segoe UI", Arial, sans-serif; margin: 16px; color: #1d1d1b;
  background: #fff; }
h1 { font-size: 20px; } h2 { font-size: 17px; margin-top: 28px; }
table { border-collapse: collapse; margin: 8px 0; }
th, td { border: 1px solid #ccc; padding: 3px 8px; text-align: left; vertical-align: top; }
.pass { color: #2e7d32; font-weight: 600; } .fail { color: #b3261e; font-weight: 600; }
.muted { color: #666; }
.text { white-space: pre-wrap; unicode-bidi: plaintext; max-width: 720px; }
details { margin: 2px 0; }
"""


def _e(value: object) -> str:
    return html.escape(str(value))


def _verdict_class(verdict: str) -> str:
    return "pass" if verdict.startswith("pass") else "fail"


def _html(
    meta: RunMeta,
    prepared: Prepared,
    passes: Sequence[list[PostRun]],
    results: Sequence[PassResult],
) -> str:
    texts = {post.listing_id: post.text for post in prepared.posts}
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        f"<title>Regression run {_e(meta.run_id)}</title><style>{_STYLE}</style></head><body>",
        f"<h1>Regression run {_e(meta.run_id)}</h1>",
        "<table>",
        f"<tr><th>Model</th><td>{_e(meta.model)}</td></tr>",
        f"<tr><th>Prompt</th><td>version {_e(meta.prompt_version)}, fingerprint "
        f"{_e(meta.prompt_fingerprint[:16])}…</td></tr>",
        f"<tr><th>Setting</th><td>effort {_e(meta.reasoning_effort)}, temperature "
        f"{_e(meta.temperature)}</td></tr>",
        f"<tr><th>Posts</th><td>{len(prepared.truths)}; removed positions "
        f"{_e(prepared.removed)}; ambiguous {_e(prepared.ambiguous)}</td></tr>",
        f"<tr><th>Cost</th><td>${meta.spent:.6f} of the ${meta.cap:.2f} cap, by the usage "
        "metadata</td></tr>",
        f"<tr><th>Stopped</th><td>{_e(meta.stopped or 'no')}</td></tr>",
        f"<tr><th>Time</th><td>{_e(meta.started_at.isoformat())} to "
        f"{_e(meta.finished_at.isoformat())} (UTC)</td></tr>",
        "</table>",
    ]
    for result in results:
        parts.append(
            f"<h2>Pass {result.number}: <span class='{_verdict_class(result.verdict)}'>"
            f"{_e(result.verdict)}</span></h2>"
        )
        if result.failed_posts or result.missing_posts:
            parts.append(
                f"<p>Failed positions {_e(result.failed_posts)}; not attempted "
                f"{_e(result.missing_posts)}.</p>"
            )
        parts.append(
            "<table><tr><th>Field</th><th>Counted</th><th>Errors</th><th>Rate</th>"
            "<th>Bar</th><th>Result</th></tr>"
        )
        for f in result.fields:
            rate = "—" if f.rate is None else f"{f.rate:.1%}"
            bar = "no error" if f.bar == 1.0 else f"{f.bar:.0%}"
            state = {True: "pass", False: "fail", None: "not measured"}[f.passed]
            css = {True: "pass", False: "fail", None: "muted"}[f.passed]
            parts.append(
                f"<tr><td>{_e(f.field)}</td><td>{f.counted}</td><td>{f.errors}</td>"
                f"<td>{rate}</td><td>{bar}</td><td class='{css}'>{state}</td></tr>"
            )
        parts.append("</table>")
        exact = result.areas_exact
        if exact is not None and exact.counted:
            parts.append(
                f"<p>Areas, as information (not a bar): exact match {exact.rate:.1%} "
                f"({exact.counted - exact.errors} of {exact.counted}); the model returned "
                f"{exact.average_returned:.2f} areas a post, the labels hold "
                f"{exact.average_labelled:.2f}.</p>"
            )
        parts.append(
            f"<p>Values filled in where the truth says not written: {len(result.filled_in)}.</p>"
        )
        if result.mismatches:
            parts.append(
                "<table><tr><th>Position</th><th>Field</th><th>Truth</th><th>Model</th>"
                "<th>Filled in</th><th>Post</th></tr>"
            )
            for m in sorted(result.mismatches, key=lambda m: (m.position, m.field)):
                parts.append(
                    f"<tr><td>{m.position}</td><td>{_e(m.field)}</td><td>{_e(m.truth)}</td>"
                    f"<td>{_e(m.answer)}</td><td>{'yes' if m.filled_in else ''}</td>"
                    f"<td><details><summary>text</summary><div class='text' dir='auto'>"
                    f"{_e(texts[m.listing_id])}</div></details></td></tr>"
                )
            parts.append("</table>")
    found = flips(prepared, passes)
    parts.append(
        f"<h2>Answers that changed between the passes: {len(found)}, in "
        f"{changed_posts(found)} posts</h2>"
    )
    if found:
        parts.append(
            "<table><tr><th>Position</th><th>Field</th><th>Pass 1</th><th>Pass 2</th></tr>"
        )
        for position, name, one, two in found:
            parts.append(
                f"<tr><td>{position}</td><td>{_e(name)}</td><td>{_e(one)}</td><td>{_e(two)}</td></tr>"
            )
        parts.append("</table>")
    parts.append("<h2>Overrides applied on top of labels.json</h2>")
    overrides = prepared.overrides
    if overrides is None:
        parts.append("<p>None.</p>")
    else:
        parts.append(
            f"<p>Approved {_e(overrides.approved)}. Nature only: "
            f"{_e(', '.join(overrides.nature_only.natures))} ({_e(overrides.nature_only.reason)})."
            "</p><table><tr><th>Kind</th><th>Position</th><th>Field</th><th>Value</th>"
            "<th>Reason</th></tr>"
        )
        for item in overrides.removed:
            parts.append(
                f"<tr><td>removed</td><td>{item.position}</td><td></td><td></td>"
                f"<td>{_e(item.reason)}</td></tr>"
            )
        for item in overrides.label_changes:
            parts.append(
                f"<tr><td>label changed</td><td>{item.position}</td><td>{_e(item.field)}</td>"
                f"<td>{_e(json.dumps(item.value, ensure_ascii=False))}</td>"
                f"<td>{_e(item.reason)}</td></tr>"
            )
        for item in overrides.not_compared:
            parts.append(
                f"<tr><td>not compared</td><td>{item.position}</td><td>{_e(item.field)}</td>"
                f"<td></td><td>{_e(item.reason)}</td></tr>"
            )
        parts.append("</table>")
    parts.append("</body></html>\n")
    return "".join(parts)
