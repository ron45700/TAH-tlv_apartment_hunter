"""The bot service's command (`PHASE_4.md` 4.3, point 2 A; DECISIONS.md #452). Free: Telegram's
Bot API costs nothing; no model, no Apify.

    python -m tlv_hunter.jobs.bot      # what the `bot` service runs (restart unless-stopped)

**The only code that reads `TELEGRAM_BOT_TOKEN`**, with the two admin commands that send through the
bot (`send_test_alert`, `telegram_menu`); it is passed to the `bot` service only (#444, #452 point
2), never logged, printed or put in an error (#356). `SITE_URL` is the site's `https://` address,
which the alerts' buttons open. Telegram allows one `getUpdates` consumer per bot: **never run two
bots with the same token** (the laptop's and the server's, #452 point 14).

It opens the store as the site does, beside it and the job commands (#260): a read-only Repository
for the grouping, a writable one for the report button's flag and report, and the user-data tables.
A stop (SIGTERM, Ctrl+C) ends the poll in progress and the alert pass between two sends. Logs are
JSON lines on stderr. Exit codes: 0, stopped; 1, refused or failed.
"""

import argparse
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, SQLITE_FILENAME, job_logging, log_failure
from tlv_hunter.notify.alert import reference_area_words
from tlv_hunter.schedule import ZONE
from tlv_hunter.state.runs import SqliteRunStore
from tlv_hunter.state.sqlite import SqliteWatermarkStore
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram.bot import Bot, site_url_or_refusal
from tlv_hunter.telegram.client import TelegramClient, Transport, urllib_transport
from tlv_hunter.telegram.watch import Watch
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.grouping import Grouping
from tlv_hunter.yad2.mapping import GROUP_ID, GROUP_TITLE

TOKEN_VARIABLE = "TELEGRAM_BOT_TOKEN"
SITE_VARIABLE = "SITE_URL"
EXIT_DONE, EXIT_FAILED = 0, 1

logger = logging.getLogger(__name__)


class Refused(Exception):
    """A setting missing or wrong, or no store."""


def telegram_settings(environ: Mapping[str, str]) -> tuple[str, str]:
    """The token and the site's address, or `Refused` naming the variable only."""
    token = environ.get(TOKEN_VARIABLE, "").strip()
    if not token:
        raise Refused(f"{TOKEN_VARIABLE} is not set")
    try:
        site_url = site_url_or_refusal(environ.get(SITE_VARIABLE, ""))
    except ValueError as error:
        raise Refused(str(error)) from None
    return token, site_url


def store_paths(config_root: Path, repo_root: Path) -> tuple[Path, Path]:
    """The store root and the database, which must exist (SQLite would create an empty one)."""
    config = YamlConfig(config_root).collection()
    store_root = repo_root / config.store_root
    database = store_root / SQLITE_FILENAME
    if not database.is_file():
        raise Refused(f"no store at {database}")
    return store_root, database


def watch_over(
    database: Path,
    grouping: Grouping,
    userdata: SqliteUserDataStore,
    clock: Callable[[], datetime],
    group_names: Mapping[str, str] | None = None,
) -> Watch:
    """The digest's and the failure alert's reads (Phase 5, #471), over the bot's own grouping;
    the groups named as the config names them (#482)."""
    return Watch(
        SqliteRunStore(database),
        SqliteWatermarkStore(database),
        grouping,
        userdata,
        clock=clock,
        zone=ZoneInfo(ZONE),
        group_names=group_names,
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    transport: Transport = urllib_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    sleep: Callable[[float], None] = time.sleep,
    stream: TextIO | None = None,
    stop: threading.Event | None = None,
) -> int:
    argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.bot").parse_args(argv)
    with job_logging(stream):
        try:
            token, site_url = telegram_settings(environ)
            store_root, database = store_paths(config_root, repo_root)
            client = TelegramClient(token, transport=transport, sleep=sleep)
            userdata = SqliteUserDataStore(database)
            grouping = Grouping(
                SqliteRepository(database, read_only=True), userdata.find_corrections, store_root
            )
            bot = Bot(
                client,
                SqliteRepository(database),
                userdata,
                grouping,
                reference_area_words(),
                site_url=site_url,
                store_root=store_root,
                clock=clock,
                sleep=sleep,
                watch=watch_over(
                    database,
                    grouping,
                    userdata,
                    clock,
                    # Yad2's one group by its own title (#496, #535), beside the config's.
                    {**YamlConfig(config_root).collection().group_names, GROUP_ID: GROUP_TITLE},
                ),
            )
            bot.start()
            stopping = threading.Event() if stop is None else stop
            if stop is None:
                for signum in (signal.SIGTERM, signal.SIGINT):
                    signal.signal(signum, lambda *_: stopping.set())
            bot.run(stopping.is_set)
            return EXIT_DONE
        except Refused as refusal:
            logger.error("refused: %s", refusal)
            return EXIT_FAILED
        except Exception as error:
            log_failure(logger, error)
            return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
