"""The bot's menu button on one user's chat, for the Mini App spike (`PHASE_4.md` 4.8, point 9 A;
DECISIONS.md #365, #452; `ASSUMPTIONS.md` T5). Free. Since round 35 the bot service sets the same
button on every linked chat by itself (`Bot.sync_menus`, #470); this command stays for one chat.

    python -m tlv_hunter.jobs.telegram_menu --show [--user <username>]
    python -m tlv_hunter.jobs.telegram_menu --spike [--user <username>]    # SITE_URL in Telegram
    python -m tlv_hunter.jobs.telegram_menu --default [--user <username>]  # Telegram's default

`--spike` sets a `MenuButtonWebApp` on the linked user's chat only (the admin's by default) that
opens `SITE_URL` as a Web App; no `initData` is validated (the spike only asks whether the site
loads, and whether the sign-in holds, inside Telegram's view). `--default` puts back
`MenuButtonDefault`. Every other chat keeps the default menu: the commands, `/site` among them.
Writes no record. Run it in the `bot` service's container (the token, #452).
Exit codes: 0, done; 1, refused or failed.
"""

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO

from tlv_hunter.jobs.bot import Refused, store_paths, telegram_settings
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, describe
from tlv_hunter.jobs.send_test_alert import linked_user
from tlv_hunter.telegram.bot import DEFAULT_MENU, site_menu_button
from tlv_hunter.telegram.client import TelegramClient, Transport, urllib_transport
from tlv_hunter.userdata.sqlite import SqliteUserDataStore

EXIT_DONE, EXIT_FAILED = 0, 1


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: Mapping[str, str] = os.environ,
    config_root: Path = CONFIG_ROOT,
    repo_root: Path = REPO_ROOT,
    transport: Transport = urllib_transport,
    stream: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.telegram_menu")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--show", action="store_true", help="print the chat's menu button")
    which.add_argument("--spike", action="store_true", help="a Web App button opening SITE_URL")
    which.add_argument("--default", action="store_true", help="Telegram's default menu button")
    parser.add_argument("--user", help="the linked username; the admin by default")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        token, site_url = telegram_settings(environ)
        _, database = store_paths(config_root, repo_root)
        user = linked_user(SqliteUserDataStore(database), args.user)
        assert user.telegram_chat_id is not None
        client = TelegramClient(token, transport=transport)
        if args.spike:
            client.set_chat_menu_button(user.telegram_chat_id, site_menu_button(site_url))
            print(f"{user.username}'s menu button now opens {site_url}/ as a Web App", file=out)
        elif args.default:
            client.set_chat_menu_button(user.telegram_chat_id, DEFAULT_MENU)
            print(f"{user.username}'s menu button is Telegram's default again", file=out)
        found = client.get_chat_menu_button(user.telegram_chat_id)
        print(f"menu button: {json.dumps(found, ensure_ascii=False)}", file=out)
        return EXIT_DONE
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
