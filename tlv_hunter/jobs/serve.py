"""Serves the site on this machine, over a dated copy of the store (`PHASE_3.md` 3.7, build step 2;
DECISIONS.md #331). Free: no model, no network beyond 127.0.0.1.

    uv run python -m tlv_hunter.jobs.serve --copy    # a new dated copy of the store, then serve it
    uv run python -m tlv_hunter.jobs.serve           # serve the newest copy made before

**Never the production file** (#331): until task 3.9 the site runs on a copy, so anything saved
through it stays in the copy. `--copy` copies the store into `<store_root>/site/` as
`tlv_hunter.<date>.site.sqlite3` (a second one the same day gets the time) with SQLite's online
backup from a read-only connection: a consistent copy, and the store itself is only read. Without
`--copy` it serves the newest copy there and refuses when there is none. The photos are read in
place from `<store_root>/images/`, read-only.

uvicorn listens on 127.0.0.1 only. It serves the API (3.7 (g)) and the built pages, `frontend/dist`,
when they are built (`npm run build` in `frontend/`); without them it serves the API alone and says
so. From build step 5 the site writes the copy's user-data tables (sessions, users, profiles, #331),
never the store itself; it opens no file but the copy for its records. Sign in at `/sign-in`: the
session cookie is `Secure`, which Chrome sends over `http://127.0.0.1` (`ASSUMPTIONS.md` I24).

Exit codes: 0, stopped; 1, refused or failed.
"""

import argparse
import sqlite3
import sys
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import uvicorn

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, describe
from tlv_hunter.sqlite_busy import BUSY_TIMEOUT_SECONDS
from tlv_hunter.web.app import create_app, site_over

EXIT_DONE, EXIT_FAILED = 0, 1
HOST = "127.0.0.1"
DEFAULT_PORT = 8000
COPIES_DIR = "site"
PAGES = Path("frontend") / "dist"


class Refused(Exception):
    """Nothing to serve, or a path that is the store itself."""


def main(
    argv: Sequence[str] | None = None,
    *,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
    run: Callable[..., None] = uvicorn.run,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.serve")
    parser.add_argument("--copy", action="store_true", help="make a new dated copy, serve it")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        config = YamlConfig(config_root).collection()
        store_root = repo_root / config.store_root
        database = store_root / SQLITE_FILENAME
        copy = make_copy(database, clock()) if args.copy else newest_copy(database)
        pages = repo_root / PAGES
        built = (pages / "index.html").is_file()
        print(f"serving the copy: {copy}", file=out)
        if built:
            print(f"open: http://{HOST}:{args.port}/", file=out)
        else:
            print(f"the pages are not built ({pages}): the API only", file=out)
            print(f"open: http://{HOST}:{args.port}/api/cards", file=out)
        site = site_over(copy, store_root, pages=pages if built else None, clock=clock)
        app = create_app(site)
        run(app, host=HOST, port=args.port)
        return EXIT_DONE
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def copies_dir(database: Path) -> Path:
    return database.parent / COPIES_DIR


def make_copy(database: Path, now: datetime) -> Path:
    """A dated, consistent copy of the store in `site/`; the store is opened read-only."""
    if not database.is_file():
        raise Refused(f"no store at {database}")
    folder = copies_dir(database)
    folder.mkdir(exist_ok=True)
    target = folder / f"{database.stem}.{now.date().isoformat()}.site{database.suffix}"
    if target.exists():
        target = folder / f"{database.stem}.{now.strftime('%Y-%m-%dT%H%M%S')}.site{database.suffix}"
    if target.exists():
        raise Refused(f"{target} exists: not overwritten")
    source = sqlite3.connect(
        f"file:{database.resolve().as_posix()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_SECONDS
    )
    with closing(source), closing(sqlite3.connect(target)) as destination:
        source.backup(destination)
    return _not_the_store(target, database)


def newest_copy(database: Path) -> Path:
    found = sorted(copies_dir(database).glob(f"{database.stem}.*.site{database.suffix}"))
    if not found:
        raise Refused(f"no copy in {copies_dir(database)}: run with --copy first")
    newest = max(found, key=lambda path: path.stat().st_mtime_ns)
    return _not_the_store(newest, database)


def _not_the_store(copy: Path, database: Path) -> Path:
    if copy.resolve() == database.resolve():
        raise Refused("the site never serves the store itself (#331)")
    return copy


if __name__ == "__main__":
    sys.exit(main())
