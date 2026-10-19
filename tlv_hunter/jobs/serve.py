"""Serves the site (`PHASE_3.md` 3.7, build step 2; 3.9; DECISIONS.md #331, #417, #424). Free: no
model, no network beyond the address it listens on.

    python -m tlv_hunter.jobs.serve --store    # the production store itself (what the image runs)
    python -m tlv_hunter.jobs.serve --copy     # a new dated copy of the store, then serve it
    python -m tlv_hunter.jobs.serve            # serve the newest copy made before

**`--store`** (3.9, #424 point 88) serves the production store itself: from the move into the
Docker volume (#416) what is saved through the site is real, and moves to the server with the
store. It refuses when there is no store, and names the file it serves. **Never run it on Windows
before the move** (3.9 (f)): it would write the Windows store that the move then copies.

**`--copy` and the bare form** serve a copy, for trying a change (#331): anything saved through
the site stays in the copy. `--copy` copies the store into `<store_root>/site/` as
`tlv_hunter.<date>.site.sqlite3` (a second one the same day gets the time) with SQLite's online
backup from a read-only connection (`jobs.common.online_copy`): a consistent copy, and the store
itself is only read. Without a flag it serves the newest copy there and refuses when there is none;
a copy is never the store itself. The photos are read in place from `<store_root>/images/`.

uvicorn listens on 127.0.0.1 by default. **`--host 0.0.0.0`** is for the container only (3.9 (c)):
a process listening on 127.0.0.1 inside a container cannot be reached through Docker's port
publishing, so inside it listens on the container's own interface and the compose file publishes the
port on the machine's 127.0.0.1 only. No other address is accepted. It serves the API (3.7 (g))
and the built pages, `frontend/dist`, when they are built (`npm run build` in `frontend/`);
without them it serves the API alone and says so. The site writes the user-data tables and a
post's lifecycle record (3.7, 3.8), never a `RawPost` or a `Listing`. Sign in at `/sign-in`: the
session cookie is `Secure`, which Chrome sends over `http://127.0.0.1` (`ASSUMPTIONS.md` I24).

Exit codes: 0, stopped; 1, refused or failed.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

import uvicorn

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import (
    CONFIG_ROOT,
    REPO_ROOT,
    SQLITE_FILENAME,
    describe,
    job_logging,
    online_copy,
)
from tlv_hunter.web.app import create_app, site_over

EXIT_DONE, EXIT_FAILED = 0, 1
HOST = "127.0.0.1"
CONTAINER_HOST = "0.0.0.0"  # in a container only; the compose file publishes 127.0.0.1 (3.9 (c))
HOSTS = (HOST, CONTAINER_HOST)
DEFAULT_PORT = 8000
COPIES_DIR = "site"
PAGES = Path("frontend") / "dist"


class Refused(Exception):
    """Nothing to serve, or a copy that is the store itself."""


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
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--store", action="store_true", help="serve the production store itself")
    which.add_argument("--copy", action="store_true", help="make a new dated copy, serve it")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--host", choices=HOSTS, default=HOST, help="0.0.0.0 inside the container only"
    )
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        config = YamlConfig(config_root).collection()
        store_root = repo_root / config.store_root
        database = store_root / SQLITE_FILENAME
        if args.store:
            served = the_store(database)
            print(f"serving the store itself: {served}", file=out)
        else:
            served = make_copy(database, clock()) if args.copy else newest_copy(database)
            print(f"serving the copy: {served}", file=out)
        pages = repo_root / PAGES
        built = (pages / "index.html").is_file()
        # In the container the address is the one the compose file publishes on the machine.
        if built:
            print(f"open: http://{HOST}:{args.port}/", file=out)
        else:
            print(f"the pages are not built ({pages}): the API only", file=out)
            print(f"open: http://{HOST}:{args.port}/api/cards", file=out)
        site = site_over(
            served, store_root, pages=pages if built else None, clock=clock, background=True
        )
        # The package's own log lines (the measurements of point 13, #471) as JSON on stderr.
        with job_logging():
            site.grouping.start()  # the first grouping begins now, before any visitor (#380)
            app = create_app(site)
            run(app, host=args.host, port=args.port)
        return EXIT_DONE
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def the_store(database: Path) -> Path:
    """The production store, for `--store` (#424 point 88); refused when it does not exist."""
    if not database.is_file():
        raise Refused(f"no store at {database}")
    return database


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
    online_copy(database, target)
    return _not_the_store(target, database)


def newest_copy(database: Path) -> Path:
    found = sorted(copies_dir(database).glob(f"{database.stem}.*.site{database.suffix}"))
    if not found:
        raise Refused(f"no copy in {copies_dir(database)}: run with --copy first")
    newest = max(found, key=lambda path: path.stat().st_mtime_ns)
    return _not_the_store(newest, database)


def _not_the_store(copy: Path, database: Path) -> Path:
    if copy.resolve() == database.resolve():
        raise Refused("a copy is never the store itself (#331); --store serves the store")
    return copy


if __name__ == "__main__":
    sys.exit(main())
