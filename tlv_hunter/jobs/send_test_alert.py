"""Sends one test alert (DECISIONS.md #456): free, to check the alert's layout without new posts.

    python -m tlv_hunter.jobs.send_test_alert --listing <id prefix> [--user <username>]

Builds the alert for an existing post exactly as a real one (`notify.alert.build_alert`: the photo,
the lines against the user's saved profile, the buttons, the report button included) and sends it
to a linked user's chat: the admin's by default. **Writes no sent-alert record and no record at
all:** the posts are read through a read-only Repository and the user-data tables are only read
(their opener lays out Gate F's empty tables on a store that has none yet, as every opener does).
It prints whether the post would alert that user, and why not (`policy.alert`), then sends it
either way. The prefix is any post of a current card, a dedup A duplicate's too; it must name one
card.

Run it in the `bot` service's container, which alone has `TELEGRAM_BOT_TOKEN` (#452):
`docker compose run --rm bot python -m tlv_hunter.jobs.send_test_alert --listing 3f9a12`.
Exit codes: 0, sent; 1, refused or failed.
"""

import argparse
import os
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from tlv_hunter.accounts.actions import find_admin
from tlv_hunter.areas.reference import load_areas
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.jobs.bot import Refused, store_paths, telegram_settings
from tlv_hunter.jobs.common import CONFIG_ROOT, REPO_ROOT, describe
from tlv_hunter.notify.alert import build_alert
from tlv_hunter.notify.telegram import TelegramNotifier
from tlv_hunter.policy.alert import no_alert_reason
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.store.sqlite import SqliteRepository
from tlv_hunter.telegram.client import TelegramClient, Transport, urllib_transport
from tlv_hunter.userdata.base import UserDataStore
from tlv_hunter.userdata.sqlite import SqliteUserDataStore
from tlv_hunter.web.grouping import Grouping

EXIT_SENT, EXIT_FAILED = 0, 1
MIN_PREFIX = 6


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
) -> int:
    parser = argparse.ArgumentParser(prog="python -m tlv_hunter.jobs.send_test_alert")
    parser.add_argument("--listing", required=True, help="the start of a post's listing_id")
    parser.add_argument("--user", help="the username to send to; the admin by default")
    args = parser.parse_args(argv)
    out = sys.stdout if stream is None else stream
    try:
        prefix = args.listing.strip().lower()
        if len(prefix) < MIN_PREFIX or any(c not in "0123456789abcdef" for c in prefix):
            raise Refused(f"--listing takes at least {MIN_PREFIX} hex characters of a listing_id")
        token, site_url = telegram_settings(environ)
        store_root, database = store_paths(config_root, repo_root)
        userdata = SqliteUserDataStore(database)
        user = linked_user(userdata, args.user)
        profile = userdata.get_profile(user.user_id)
        if profile is None:
            raise Refused(f"user {user.username} has no profile")
        repository = SqliteRepository(database, read_only=True)
        snapshot = Grouping(repository, userdata.find_corrections, store_root).current().snapshot
        card = _card(snapshot.card_of, prefix)
        now = clock()
        evaluation = evaluate(card.shown.seen, profile, now)
        reason = no_alert_reason(card.shown.seen, evaluation)
        print(f"post {card.shown_id} ({len(card.post_ids)} posts in its card)", file=out)
        print(
            "a real alert would be sent to this user"
            if reason is None
            else f"a real alert would NOT be sent to this user: {reason}",
            file=out,
        )
        alert = build_alert(
            card,
            evaluation,
            profile,
            {area.number: area.display_name for area in load_areas()},
            site_url=site_url,
            store_root=store_root,
            now=now,
        )
        client = TelegramClient(token, transport=transport, sleep=sleep)
        assert user.telegram_chat_id is not None
        message_id = TelegramNotifier(client).send(user.telegram_chat_id, alert)
        kind = "a photo" if alert.photo is not None else "a text message"
        print(f"sent to {user.username}: {kind}, message {message_id}; no record written", file=out)
        return EXIT_SENT
    except Refused as refusal:
        print(f"refused: {refusal}", file=out)
        return EXIT_FAILED
    except Exception as error:
        print(f"failed: {describe(error)}", file=out)
        return EXIT_FAILED


def linked_user(userdata: UserDataStore, username: str | None) -> User:
    """The user by username, or the admin; refused unless linked and enabled."""
    user = find_admin(userdata) if username is None else userdata.find_user_by_username(username)
    if user is None:
        raise Refused("no such user" if username else "no admin")
    if user.telegram_chat_id is None or user.disabled_at is not None:
        raise Refused(f"user {user.username} is not linked to Telegram")
    return user


def _card(card_of: Mapping[str, Card], prefix: str) -> Card:
    found = {id(c): c for listing_id, c in card_of.items() if listing_id.startswith(prefix)}
    if not found:
        raise Refused(f"no post of a current card starts with {prefix}")
    if len(found) > 1:
        raise Refused(f"{prefix} names {len(found)} cards: give more characters")
    return next(iter(found.values()))


if __name__ == "__main__":
    sys.exit(main())
