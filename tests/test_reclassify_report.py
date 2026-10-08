"""The files of a reclassify run and its page (`PHASE_2.md` 2.9; DECISIONS.md #218, #219, #221):
`tlv_hunter/postmodel/reclassify_report.py`. No model, no network; temporary folders."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import make_listing
from tests.test_reclassify_select import proposal
from tlv_hunter.postmodel.reclassify import (
    ALLOW_STATE_CHANGES_FILE,
    ALLOW_UNCHANGED_FILE,
    PROPOSALS_FILE,
    REPORT_FILE,
    SUMMARY_FILE,
    NewSide,
)
from tlv_hunter.postmodel.reclassify_report import (
    RunRefused,
    Summary,
    TripleCount,
    allow_lists,
    append_proposal,
    read_allow_file,
    read_finished_run,
    read_proposals,
    render_diff,
    write_run_files,
)
from tlv_hunter.postmodel.rejects import CityRuling

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=UTC)
ID_A, ID_B, ID_C, ID_D = "a" * 64, "b" * 64, "c" * 64, "d" * 64


def summary(**changes: Any) -> Summary:
    fields: dict[str, Any] = {
        "format_version": 1,
        "run_id": "0123456789ab",
        "started_at": NOW,
        "finished_at": NOW,
        "current_prompt_version": "3",
        "current_schema_version": 1,
        "current_model_name": "gpt-6-luna",
        "prompt_fingerprint": "f" * 64,
        "cap": 0.1,
        "spent": 0.0004,
        "calls": 2,
        "tokens": {"input": 10},
        "reported_models": ["gpt-6-luna"],
        "selected_by_triple": [
            TripleCount(prompt_version="2", schema_version=1, model_name="gpt-6-luna", count=4)
        ],
        "selected": 4,
        "attempted": 3,
        "proposed": 2,
        "failed": 1,
        "not_attempted": 1,
        "state_changes": 1,
        "unchanged_apart_from_provenance": 1,
        "stopped": None,
        "complete": True,
    }
    return Summary(**{**fields, **changes})


def unchanged_proposal(listing_id: str) -> Any:
    listing = make_listing(listing_id, prompt_version="2")
    new = listing.model_copy(update={"prompt_version": "3"})
    return proposal(
        listing_id,
        new=NewSide(listing=new, state="active", rejection_reason=None),
        fields_changed=[],
    )


def set_of_proposals() -> list[Any]:
    changed = proposal(ID_B)  # active -> rejected: seeking
    failed = proposal(ID_C, new=None, error="refusal", fields_changed=[], attempts=1)
    return [unchanged_proposal(ID_A), changed, failed]


# --- the lists ---


def test_the_allow_lists_split_unchanged_from_state_changes_and_leave_the_failed_out() -> None:
    unchanged, changed = allow_lists(set_of_proposals())
    assert unchanged == [ID_A] and changed == [ID_B]


def test_an_allow_file_ignores_comments_and_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "list.txt"
    path.write_text(f"# a comment\n\n  {ID_A}  \n{ID_B[:12]}\n# {ID_C}\n", encoding="utf-8")
    assert read_allow_file(path) == [ID_A, ID_B[:12]]


# --- the proposals file ---


def test_proposals_are_appended_one_line_each_and_read_back(tmp_path: Path) -> None:
    path = tmp_path / "run" / PROPOSALS_FILE
    items = set_of_proposals()
    for item in items:
        append_proposal(path, item)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3 and all(json.loads(line)["listing_id"] for line in lines)
    assert read_proposals(path) == items


def test_a_listing_id_twice_in_a_proposals_file_is_refused(tmp_path: Path) -> None:
    path = tmp_path / PROPOSALS_FILE
    append_proposal(path, proposal(ID_A))
    append_proposal(path, proposal(ID_A))
    with pytest.raises(ValueError, match="appears twice"):
        read_proposals(path)


# --- the run folder ---


def finished_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "reclassify" / "0123456789ab"
    items = set_of_proposals()
    for item in items:
        append_proposal(folder / PROPOSALS_FILE, item)
    write_run_files(folder, summary(), items, {ID_A: "a", ID_B: "b", ID_C: "c"})
    return folder


def test_a_finished_run_has_the_page_the_lists_and_the_summary_last(tmp_path: Path) -> None:
    folder = finished_folder(tmp_path)
    assert sorted(p.name for p in folder.iterdir()) == sorted(
        [
            PROPOSALS_FILE,
            SUMMARY_FILE,
            REPORT_FILE,
            ALLOW_UNCHANGED_FILE,
            ALLOW_STATE_CHANGES_FILE,
        ]
    )
    assert read_allow_file(folder / ALLOW_UNCHANGED_FILE) == [ID_A]
    assert read_allow_file(folder / ALLOW_STATE_CHANGES_FILE) == [ID_B]
    first = (folder / ALLOW_UNCHANGED_FILE).read_text(encoding="utf-8").splitlines()[0]
    assert first.startswith("# reclassify run 0123456789ab")
    run = read_finished_run(folder)
    assert run.summary == summary() and len(run.proposals) == 3


def test_summary_is_written_after_the_page_so_a_killed_run_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tlv_hunter.postmodel.reclassify_report as module

    folder = tmp_path / "run"
    append_proposal(folder / PROPOSALS_FILE, proposal(ID_A))

    def broken(*args: Any, **kwargs: Any) -> str:
        raise RuntimeError("killed while rendering")

    monkeypatch.setattr(module, "render_diff", broken)
    with pytest.raises(RuntimeError):
        write_run_files(folder, summary(), [proposal(ID_A)], {ID_A: "a"})
    assert not (folder / SUMMARY_FILE).exists()
    with pytest.raises(RunRefused, match="no summary.json"):
        read_finished_run(folder)


def test_write_run_files_writes_only_a_final_summary(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="final summary"):
        write_run_files(tmp_path, summary(complete=False), [], {})


@pytest.mark.parametrize("what", ["no_folder", "incomplete", "no_page", "no_proposals"])
def test_an_unfinished_run_is_refused(tmp_path: Path, what: str) -> None:
    folder = finished_folder(tmp_path)
    if what == "no_folder":
        folder = tmp_path / "nowhere"
    elif what == "incomplete":
        (folder / SUMMARY_FILE).write_text(
            summary(complete=False).model_dump_json(), encoding="utf-8"
        )
    elif what == "no_page":
        (folder / REPORT_FILE).unlink()
    else:
        (folder / PROPOSALS_FILE).unlink()
    with pytest.raises(RunRefused):
        read_finished_run(folder)


# --- the page ---


def page(proposals=None, texts=None, **changes: Any) -> str:
    items = set_of_proposals() if proposals is None else proposals
    return render_diff(summary(**changes), items, texts or {ID_A: "a", ID_B: "b", ID_C: "c"})


def test_the_state_changes_come_first_after_the_header() -> None:
    html = page()
    header = html.index("This run")
    states = html.index("State changes (1)")
    fields = html.index("Fields changed")
    failed = html.index("Failed (1)")
    reviewed = html.index("Posts with a reviewed correction")
    cards = html.index("<h2>Posts</h2>")
    assert header < states < fields < failed < reviewed < cards
    states_block = html[states:fields]
    assert (
        ID_B[:12] in states_block
        and "active" in states_block
        and "rejected: seeking" in states_block
    )
    assert ID_A[:12] not in states_block


def test_it_says_nothing_has_been_replaced_and_why_the_diff_is_noisy() -> None:
    html = page()
    assert "Nothing has been replaced yet" in html
    assert "20 of 46 posts changed between the two passes" in html


def test_it_counts_the_fields_changed_and_the_areas_gained_and_lost() -> None:
    gained = proposal(
        ID_D,
        new=NewSide(
            listing=make_listing(ID_D, prompt_version="3", areas=[30, 31]),
            state="active",
            rejection_reason=None,
        ),
        fields_changed=["areas"],
    )
    lost = proposal(
        ID_A,
        old=proposal(ID_A).old.model_copy(
            update={"listing": make_listing(ID_A, prompt_version="2", areas=[30, 31])}
        ),
        new=NewSide(
            listing=make_listing(ID_A, prompt_version="3", areas=[30]),
            state="active",
            rejection_reason=None,
        ),
        fields_changed=["areas"],
    )
    html = page([gained, lost])
    assert "2 (1 gained a number, 1 lost one)" in html


def test_it_lists_the_failed_the_reviewed_and_the_empty_cases() -> None:
    html = page()
    assert "refusal" in html and "The old Listing stays" in html
    assert "None.</p>" in html  # no reviewed correction
    empty = page([], {}, selected=0, attempted=0, proposed=0, failed=0, not_attempted=0)
    assert "No post changes state." in empty and "No post failed." in empty
    assert "no field differs" in empty
    reviewed = page([proposal(ID_A, reviewed=True, corrected_fields=["price"])])
    assert (
        "corrected: price" in reviewed
        and "Posts with a reviewed correction on file (1)" in reviewed
    )


def test_post_text_is_escaped_never_parsed() -> None:
    hostile = '<script>alert(1)</script> & "quotes" דירה'
    html = page(texts={ID_A: hostile, ID_B: "b", ID_C: "c"})
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;quotes&quot; דירה" in html
    assert html.count("<script>") == 1  # the page's own filter script


def test_the_page_is_static_and_names_the_lists() -> None:
    html = page()
    for forbidden in ("http://", "https://", "src=", "<link", "@import"):
        assert forbidden not in html
    assert ALLOW_UNCHANGED_FILE in html and ALLOW_STATE_CHANGES_FILE in html
    assert "--allow-file" in html


def test_a_card_shows_old_and_new_values_and_collapses_the_unchanged() -> None:
    html = page()
    assert "&quot;rental_offer&quot;" in html and "&quot;seeking&quot;" in html
    assert "fields unchanged" in html
    assert "(flagged: kept)" not in html
    flagged = proposal(ID_A, old=proposal(ID_A).old.model_copy(update={"flagged": True}))
    assert "(flagged: kept)" in page([flagged])


# --- the city of an other-city row (#214) ---


def other_city_proposal(listing_id: str, *, old_reason: str | None, new_reason: str | None):
    old_state = "active" if old_reason is None else "rejected"
    new_state = "active" if new_reason is None else "rejected"
    base = proposal(listing_id)
    return proposal(
        listing_id,
        old=base.old.model_copy(update={"state": old_state, "rejection_reason": old_reason}),
        new=NewSide(
            listing=make_listing(listing_id, prompt_version="3"),
            state=new_state,
            rejection_reason=new_reason,
        ),
    )


def state_changes_block(html: str) -> str:
    return html[html.index("State changes") : html.index("Fields changed")]


def test_a_state_change_to_other_city_shows_the_city_and_its_source() -> None:
    row = other_city_proposal(ID_A, old_reason=None, new_reason="other_city")
    cities = {ID_A: (CityRuling(None, None), CityRuling("חולון", "native_location"))}
    block = state_changes_block(render_diff(summary(), [row], {ID_A: "a"}, cities))
    assert "<th>City</th>" in block
    assert "was none; becomes חולון (native_location)" in block


def test_a_state_change_out_of_other_city_shows_both_cities_and_their_sources() -> None:
    row = other_city_proposal(ID_A, old_reason="other_city", new_reason=None)
    cities = {ID_A: (CityRuling("רמת גן", "model"), CityRuling(None, None))}
    block = state_changes_block(render_diff(summary(), [row], {ID_A: "a"}, cities))
    assert "was רמת גן (model); becomes none" in block


def test_a_state_change_that_is_not_about_a_city_has_an_empty_city_cell() -> None:
    row = other_city_proposal(ID_A, old_reason=None, new_reason="seeking")
    cities = {ID_A: (CityRuling("חולון", "model"), CityRuling("חולון", "model"))}
    block = state_changes_block(render_diff(summary(), [row], {ID_A: "a"}, cities))
    assert "חולון" not in block and "<td dir='auto'></td>" in block


def test_an_other_city_row_with_no_city_given_shows_a_dash_not_an_error() -> None:
    row = other_city_proposal(ID_A, old_reason=None, new_reason="other_city")
    assert "<td dir='auto'>-</td>" in state_changes_block(render_diff(summary(), [row], {}))
    assert "<td dir='auto'>-</td>" in state_changes_block(render_diff(summary(), [row], {}, {}))


def test_the_city_is_escaped() -> None:
    row = other_city_proposal(ID_A, old_reason=None, new_reason="other_city")
    cities = {ID_A: (CityRuling(None, None), CityRuling("<b>x</b>", "model"))}
    block = state_changes_block(render_diff(summary(), [row], {ID_A: "a"}, cities))
    assert "<b>x</b>" not in block and "&lt;b&gt;x&lt;/b&gt; (model)" in block
