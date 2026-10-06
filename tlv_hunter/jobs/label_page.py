"""Writes the regression set's labelling page (task 2.6): `data/labeling/label_posts.html`. Free: no
model, no network.

    uv run python -m tlv_hunter.jobs.label_page

Reads `data/labeling/regression_set.json`, the texts from the store and from
`data/raw/test_posts.json`, and the 71 areas. The store is opened read-only (`SqliteRepository`'s
`read_only`): nothing in it is created or changed. Never run it beside `run_once` or
`classify_pending`, whose writes it could read half done. Exit codes: 0, written; 1, failed, with
nothing written.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.areas.reference import load_areas
from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, describe
from tlv_hunter.labeling.page import LABEL_PAGE_FILE, render_label_page
from tlv_hunter.labeling.regression_set import (
    LABELING_DIR,
    REGRESSION_SET_FILE,
    load_regression_set,
    post_texts,
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
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.label_page").parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        path, count = _run(config_root, repo_root, clock)
    except Exception as error:
        # describe(): a pydantic message would carry the input, which can be a post's text.
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED
    print(f"wrote {path} ({count} posts)", file=out)
    return EXIT_DONE


def _run(config_root: Path, repo_root: Path, clock: Callable[[], datetime]) -> tuple[Path, int]:
    labeling = repo_root / LABELING_DIR
    regression_set = load_regression_set(labeling / REGRESSION_SET_FILE)
    config = YamlConfig(config_root).collection()
    # A relative store_root resolves against the repo root, as in the job commands (#79 O6).
    database = repo_root / config.store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    store = SqliteRepository(database, read_only=True)
    # A post that joined from the review has its truth there, not a blind label (#195).
    blind = [entry for entry in regression_set.posts if entry.truth == "blind"]
    texts = post_texts(blind, store, repo_root)
    html = render_label_page(texts, load_areas(), clock())
    path = labeling / LABEL_PAGE_FILE
    path.write_text(html, encoding="utf-8", newline="")
    return path, len(texts)


if __name__ == "__main__":
    sys.exit(main())
