"""Writes the review report (task 2.7): `data/labeling/review.html`. Free: no model, no network.

    uv run python -m tlv_hunter.jobs.review_page                  # the store's classifications
    uv run python -m tlv_hunter.jobs.review_page --run <folder>   # a regression run's pass 1

`--run` names a folder under `data/labeling/runs/`: reviewing a run's pass 1 gives the truth of the
fields not labelled blind (DECISIONS.md #193). The store is opened read-only. When
`data/labeling/corrections.json` exists, it is checked, its errors per field are printed and shown
(#172), and every reviewed, corrected post the regression set does not hold joins it (#195): that
is the only write besides the page. Exit codes: 0, written; 1, failed, with nothing written.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.areas.reference import load_areas
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.classify_pending import RUNS_DIRECTORY
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, describe
from tlv_hunter.labeling.corrections import CORRECTIONS_FILE, RUNS_DIR, read_corrections
from tlv_hunter.labeling.regression_set import (
    LABELING_DIR,
    REGRESSION_SET_FILE,
    load_regression_set,
    regression_posts,
)
from tlv_hunter.labeling.review import (
    REVIEW_PAGE_FILE,
    add_corrected_to_set,
    render_review_page,
    run_cards,
    store_cards,
)
from tlv_hunter.store.sqlite import SqliteRepository

EXIT_DONE, EXIT_FAILED = 0, 1


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.review_page")
    parser.add_argument("--run", help="a folder under data/labeling/runs/: review its pass 1")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        return _run(args.run, config_root, repo_root, clock, out)
    except Exception as error:
        # describe(): a pydantic message would carry the input, which can be a post's text.
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def _run(
    run: str | None,
    config_root: Path,
    repo_root: Path,
    clock: Callable[[], datetime],
    out: TextIO,
) -> int:
    labeling = repo_root / LABELING_DIR
    config = YamlConfig(config_root).collection()
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    store = SqliteRepository(database, read_only=True)
    set_path = labeling / REGRESSION_SET_FILE
    regression_set = load_regression_set(set_path)
    positions = {entry.listing_id: i for i, entry in enumerate(regression_set.posts, 1)}
    corrections = read_corrections(labeling / CORRECTIONS_FILE)

    if run is None:
        cards = store_cards(store, store_root / RUNS_DIRECTORY)
        source = "the store's classifications"
    else:
        run_dir = labeling / RUNS_DIR / run
        if not run_dir.is_dir():
            raise FileNotFoundError(f"no run at {run_dir}")
        posts = regression_posts(regression_set.posts, store, repo_root)
        cards = run_cards(run_dir, {post.listing_id: post.text for post in posts})
        source = f"pass 1 of regression run {run}"

    if corrections is not None:
        texts = {card.listing_id: card.text for card in cards}
        stale = corrections.stale(texts)
        if stale:
            raise ValueError(f"{CORRECTIONS_FILE}: the text changed for {', '.join(stale)}")
        stored = {post.listing_id for post in store.query()}
        added = add_corrected_to_set(set_path, corrections, stored)
        reviewed = len(corrections.reviewed())
        print(f"{CORRECTIONS_FILE}: {reviewed} posts reviewed; errors per field:", file=out)
        for name, count in corrections.errors_per_field().items():
            if count:
                print(f"  {name}: {count} of {reviewed}", file=out)
        for listing_id in added:
            print(f"joined the regression set: {listing_id}", file=out)

    html = render_review_page(
        cards,
        load_areas(),
        set_positions=positions,
        corrections=corrections,
        source=source,
        generated_at=clock(),
    )
    path = labeling / REVIEW_PAGE_FILE
    path.write_text(html, encoding="utf-8", newline="")
    print(f"wrote {path} ({len(cards)} posts)", file=out)
    return EXIT_DONE


if __name__ == "__main__":
    sys.exit(main())
