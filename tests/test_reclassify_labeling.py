"""What a reclassify does to `data/labeling` (`PHASE_2.md` 2.9 section 7; DECISIONS.md #222): a
reviewed post is still found by the regression runner after the store holds a new classification,
because `find_reviewed` also reads the `Listing`s kept in `reclassify/*/proposals.jsonl`."""

import io
import json
from datetime import UTC, datetime
from pathlib import Path

from tests.conftest import CONFIG_ROOT, make_listing
from tests.test_classification_run import lifecycle
from tests.test_reclassify_select import proposal
from tests.test_regression_runner import STORE_ROOT, _repo
from tlv_hunter.jobs.regression_run import main as regression_main
from tlv_hunter.labeling.corrections import (
    CORRECTIONS_FILE,
    Correction,
    find_reviewed,
    reclassified_listings,
)
from tlv_hunter.labeling.regression import prepare
from tlv_hunter.labeling.regression_set import LABELING_DIR, text_sha256
from tlv_hunter.postmodel.reclassify import PROPOSALS_FILE, RECLASSIFY_DIRECTORY, NewSide, OldSide
from tlv_hunter.postmodel.reclassify_report import append_proposal
from tlv_hunter.store.sqlite import SqliteRepository

ID = "a" * 64


def correction_for(listing, text: str = "x") -> Correction:
    return Correction(
        text_sha256=text_sha256(text),
        prompt_version=listing.prompt_version,
        model_name=listing.model_name,
        classified_at=listing.classified_at,
        reviewed=True,
        fields={},
        note="",
    )


def with_old_listing(listing_id: str, old) -> object:
    return proposal(
        listing_id,
        old=OldSide(listing=old, state="active", rejection_reason=None, flagged=False),
        new=NewSide(
            listing=make_listing(listing_id, prompt_version="3"),
            state="active",
            rejection_reason=None,
        ),
    )


def test_the_old_listings_of_every_run_are_read_and_a_cut_line_is_skipped(tmp_path: Path) -> None:
    old = make_listing(ID, prompt_version="2")
    folder = tmp_path / "0123456789ab"
    append_proposal(folder / PROPOSALS_FILE, with_old_listing(ID, old))
    with (folder / PROPOSALS_FILE).open("a", encoding="utf-8") as file:
        file.write('{"listing_id": "b", "old": {"listing"')  # a run killed mid-line
    assert list(reclassified_listings(tmp_path)) == [old]
    assert list(reclassified_listings(tmp_path / "none")) == []


def test_find_reviewed_falls_back_to_the_replaced_listing(tmp_path: Path) -> None:
    old = make_listing(ID, prompt_version="2")
    new = make_listing(ID, prompt_version="3", classified_at=datetime(2026, 10, 8, tzinfo=UTC))
    record = correction_for(old)
    folder = tmp_path / "0123456789ab"
    append_proposal(folder / PROPOSALS_FILE, with_old_listing(ID, old))

    assert find_reviewed(ID, record, new, tmp_path / "runs") is None  # without #222
    assert find_reviewed(ID, record, new, tmp_path / "runs", tmp_path) == old
    assert (
        find_reviewed(ID, record, old, tmp_path / "runs", tmp_path / "none") == old
    )  # the store's
    other = correction_for(make_listing(ID, prompt_version="9"))
    assert find_reviewed(ID, other, new, tmp_path / "runs", tmp_path) is None


def reviewed_world(tmp_path: Path, posts):
    """A store, a regression set of one `truth: "review"` post and Ron's correction of it."""
    database, chosen = _repo(tmp_path, posts, count=1)
    post = chosen[0]
    store = SqliteRepository(database)
    store.upsert_with_lifecycle(post, lifecycle(post))
    old = make_listing(post.listing_id, prompt_version="2", post_nature="for_sale")
    store.save_classification(old, lifecycle(post, state="rejected", rejection_reason="for_sale"))
    labeling = tmp_path / LABELING_DIR
    (labeling / "regression_set.json").write_text(
        json.dumps(
            {
                "format_version": 1,
                "posts": [
                    {
                        "listing_id": post.listing_id,
                        "case": "c",
                        "source": "store",
                        "truth": "review",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    record = correction_for(old, post.text).model_dump(mode="json")
    record["fields"] = {"rooms": {"state": "written", "value": 3.0}}
    (labeling / CORRECTIONS_FILE).write_text(
        json.dumps(
            {
                "format_version": 1,
                "exported_at": "2026-10-08T08:00:00Z",
                "corrections": {post.listing_id: record},
            }
        ),
        encoding="utf-8",
    )
    return database, post, old, store, tmp_path / STORE_ROOT / RECLASSIFY_DIRECTORY


def test_the_runner_keeps_the_truth_of_a_reviewed_post_after_a_reclassify(
    tmp_path: Path, posts
) -> None:
    """The break that motivated #222, end to end on a temporary store."""
    database, post, old, store, reclassify_dir = reviewed_world(tmp_path, posts)

    def prepared(with_dir: bool):
        read_only = SqliteRepository(database, read_only=True)
        return prepare(tmp_path, read_only, reclassify_dir if with_dir else None)

    assert prepared(False).refusals == [] and prepared(True).refusals == []

    # A reclassify replaced the classification: the store now holds another one.
    new = make_listing(
        post.listing_id,
        prompt_version="3",
        post_nature="rental_offer",
        classified_at=datetime(2026, 10, 9, tzinfo=UTC),
    )
    store.save_classification(new, lifecycle(post, state="active"))

    assert prepared(False).refusals == ["position 1: the reviewed classification is not found"]

    append_proposal(
        reclassify_dir / "0123456789ab" / PROPOSALS_FILE, with_old_listing(post.listing_id, old)
    )
    ready = prepared(True)
    assert ready.refusals == []
    (truth,) = ready.truths
    assert truth.values["post_nature"] == "for_sale"  # Ron's reviewed classification, not the new
    assert truth.values["rooms"].value == 3.0


def test_the_runner_command_reads_the_replaced_listings_from_the_store_root(
    tmp_path: Path, posts
) -> None:
    database, post, old, store, reclassify_dir = reviewed_world(tmp_path, posts)
    store.save_classification(
        make_listing(
            post.listing_id, prompt_version="3", classified_at=datetime(2026, 10, 9, tzinfo=UTC)
        ),
        lifecycle(post, state="active"),
    )

    def check() -> int:
        return regression_main(
            ["--check"],
            environ={},
            config_root=CONFIG_ROOT,
            repo_root=tmp_path,
            stream=io.StringIO(),
        )

    assert check() == 1  # the reviewed classification is gone from the store
    append_proposal(
        reclassify_dir / "0123456789ab" / PROPOSALS_FILE, with_old_listing(post.listing_id, old)
    )
    assert check() == 0
