"""Gate D's evidence (task 2.10, `PHASE_2.md`; DECISIONS.md #145, #226, #227). Free: no model, no
network, no key.

    uv run python -m tlv_hunter.jobs.gate_d_pairs             # writes the page
    uv run python -m tlv_hunter.jobs.gate_d_pairs --dry-run   # prints the counts and the pairs
    uv run python -m tlv_hunter.jobs.gate_d_pairs --measure   # reads pair_verdicts.json; prints

The store is opened read-only (`SqliteRepository`'s `read_only`): nothing in it is created or
changed, and no post is marked a duplicate. The only file written is the page, and `--dry-run` and
`--measure` write none. It decides no Gate D key and no dedup B rule. No phone number or text is
printed: the page holds them, in the gitignored `data/`. Never run it beside `run_once` or
`classify_pending`, whose writes it could read half done. Exit codes: 0, done; 1, failed, with
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
from tlv_hunter.gate_d.candidates import (
    AGENT_PHONE_SAMPLE,
    FIELDS,
    PHONE,
    RULES_VERSION,
    WINDOW,
    Candidates,
    Population,
    find_candidates,
    load_population,
)
from tlv_hunter.gate_d.page import PAGE_FILE, render_pairs_page
from tlv_hunter.gate_d.verdicts import (
    GATE_D_DIR,
    VERDICTS_FILE,
    check_against,
    measure,
    read_verdicts,
)
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, describe
from tlv_hunter.labeling.regression_set import text_sha256
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
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.gate_d_pairs")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="print the counts and the pairs; write nothing"
    )
    mode.add_argument(
        "--measure", action="store_true", help=f"read {GATE_D_DIR}/{VERDICTS_FILE} and print"
    )
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        return _run(args.dry_run, args.measure, config_root, repo_root, clock, out)
    except Exception as error:
        # describe(): a pydantic message would carry the input, which can be a post's text.
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def _run(
    dry_run: bool,
    measuring: bool,
    config_root: Path,
    repo_root: Path,
    clock: Callable[[], datetime],
    out: TextIO,
) -> int:
    config = YamlConfig(config_root).collection()
    # A relative store_root resolves against the repo root, as in the job commands (#79 O6).
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        raise FileNotFoundError(f"no store at {database}")
    store = SqliteRepository(database, read_only=True)
    population = load_population(store)
    candidates = find_candidates(population.members)
    gate_d = repo_root / GATE_D_DIR

    if measuring:
        path = gate_d / VERDICTS_FILE
        if not path.is_file():
            raise FileNotFoundError(f"no {VERDICTS_FILE} in {gate_d}")
        verdicts = read_verdicts(path)
        hashes = {m.listing_id: text_sha256(m.post.text) for m in population.members}
        check_against(verdicts, {pair.key: pair for pair in candidates.pairs}, hashes)
        for line in measure(verdicts, population, len(candidates.pairs)):
            print(line, file=out)
        return EXIT_DONE

    for line in _counts(candidates, population):
        print(line, file=out)
    if dry_run:
        for pair in candidates.pairs:
            print(
                f"  {pair.first_id[:12]} {pair.second_id[:12]} "
                f"{'+'.join(pair.found_by)}; matched: {', '.join(pair.matched) or 'none'}; "
                f"{pair.gap_hours:.1f} h apart; {'same' if pair.same_group else 'different'} group",
                file=out,
            )
        print("dry run: nothing written", file=out)
        return EXIT_DONE

    html = render_pairs_page(
        candidates,
        population,
        load_areas(),
        store_root=store_root,
        page_dir=gate_d,
        generated_at=clock(),
    )
    gate_d.mkdir(parents=True, exist_ok=True)
    path = gate_d / PAGE_FILE
    path.write_text(html, encoding="utf-8", newline="")
    print(f"wrote {path} ({len(candidates.pairs)} pairs)", file=out)
    return EXIT_DONE


def _counts(candidates: Candidates, population: Population) -> list[str]:
    return [
        f"rules version {RULES_VERSION}; window {WINDOW.total_seconds() / 3600:.0f} hours",
        f"stored posts {population.total_posts}; duplicates {population.duplicates}; "
        f"compared (active canonicals with a Listing) {candidates.members}; "
        f"the posts span {population.span_hours:.1f} hours",
        f"pairs listed {len(candidates.pairs)}: "
        f"found by the fields rule {candidates.count(FIELDS)}, "
        f"by the phone rule {candidates.count(PHONE)}, "
        f"agent-number sample {candidates.count(AGENT_PHONE_SAMPLE)}",
        f"agent numbers {candidates.agent_numbers}; their pairs {candidates.agent_pairs} "
        "(not listed one by one)",
    ]


if __name__ == "__main__":
    sys.exit(main())
