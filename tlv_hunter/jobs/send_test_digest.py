"""The daily digest, now, to the admin's chat (`PHASE_5.md` point 7; DECISIONS.md #471): so Ron
judges the Hebrew text before the bot sends it each morning. Free: Telegram's Bot API costs nothing.

    python -m tlv_hunter.jobs.send_test_digest          # the window since the last digest (or 24 h)
    python -m tlv_hunter.jobs.send_test_digest --hours 6

Built exactly as the bot builds it (`telegram/watch.py`, `telegram/digest.py`), and also printed.
**Writes nothing:** no record, not `last_digest_at` (the morning's digest still comes). Run it in
the `bot` service's container (the token, #452). Exit codes: 0, sent; 1, refused or failed.
"""

import argparse
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO

from tlv_hunter.config.yaml_config import YamlConfig
from tlv_hunter.jobs.bot import Refused, store_paths, telegram_settings, watch_over
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, describe
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram.client import TelegramClient, Transport, urllib_transport
from tlv_hunter.telegram.digest import digest_messages, window_start
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.grouping import Grouping

EXIT_DONE, EXIT_FAILED = 0, 1


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    transport: Transport = urllib_transport,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.send_test_digest")
    parser.add_argument("--hours", type=int, help="the window: this many hours back from now")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        if args.hours is not None and not 1 <= args.hours <= 24 * 14:
            raise Refused("--hours must be from 1 to 336")
        token, _ = telegram_settings(environ)
        store_root, database = store_paths(config_root, repo_root)
        userdata = SqliteUserDataStore(database)
        grouping = Grouping(
            SqliteRepository(database, read_only=True), userdata.find_corrections, store_root
        )
        watch = watch_over(
            database, grouping, userdata, clock, YamlConfig(config_root).collection().group_names
        )
        chat = watch.admin_chat()
        if chat is None:
            raise Refused("the admin is not linked to Telegram")
        now = clock()
        settings = watch.settings()
        start = (
            now - timedelta(hours=args.hours)
            if args.hours is not None
            else window_start(None if settings is None else settings.last_digest_at, now)
        )
        messages = digest_messages(watch.digest(start, now), watch.zone)
        client = TelegramClient(token, transport=transport)
        for text in messages:
            print(text, file=out)
            client.send_message(chat, text)
        print(f"sent to the admin's chat: {len(messages)} message(s); nothing written", file=out)
        return EXIT_DONE
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
