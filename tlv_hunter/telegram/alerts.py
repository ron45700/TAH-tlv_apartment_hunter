"""Who is alerted, and when (`PHASE_4.md` 4.5, points 3, 6, 10; `BASELINE.md` §9; DECISIONS.md
#230–#232, #357, #360, #452). Wiring, like `pipeline.py`: the held grouping (the cards), the
profiles and the sent-alert records in; the alerts sent through `notify/`, one `SentAlert` written
for each.

A card alerts a linked user when all of these hold:
- **Its shown post is new for the user:** first stored (`RawPost.fetched_at`, kept by every later
  upsert) after the user's `telegram_linked_at` (point 10). The shown post is the card's earliest
  publication (#297), so a post the Gate D key ties to an earlier one never alerts, and neither
  does a repost (dedup A's duplicates are inside the card); a bootstrap run's posts are stored
  before anyone is linked (`BASELINE.md` §4, #357).
- **Nothing of the card was alerted to the user:** no `SentAlert` on any of its posts (#453 point 4:
  a card whose members include an alerted post does not alert again).
- **Its shown post was published within 24 hours of the pass** (`policy.alert.PUBLISHED_WINDOW`,
  point 12 B, #473): after a pause the run brings older posts, which are stored but never alert.
- **Its classification is recent:** `Listing.classified_at` within `ALERT_WINDOW` of the pass. The
  pass looks at "the posts classified since its last pass" (point 3) without a record of its own:
  after a restart it catches up on the window, and an old post a later profile change would admit
  is not sent.
- **`policy.alert.no_alert_reason` is `None`** against the user's saved profile (§9, #360).

Sent in publication order, at most one message a second per chat (point 6). A send that fails
leaves no record: the next pass tries again. Disabled users get nothing.
"""

import logging
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from tlv_hunter.contracts.profile import Profile
from tlv_hunter.contracts.sent_alert import SENT_ALERT_SCHEMA_VERSION, SentAlert
from tlv_hunter.contracts.user import User
from tlv_hunter.dedup.stage_b import Card
from tlv_hunter.notify.alert import AreaWords, build_alert
from tlv_hunter.notify.base import Notifier
from tlv_hunter.policy.alert import no_alert_reason, published_too_long_ago
from tlv_hunter.policy.base import Evaluation
from tlv_hunter.policy.evaluate import evaluate
from tlv_hunter.telegram.client import TelegramError
from tlv_hunter.userdata.base import UserDataStore

ALERT_WINDOW = timedelta(hours=24)
SEND_GAP_SECONDS = 1.0  # "in a single chat, avoid sending more than one message per second"

logger = logging.getLogger(__name__)


def is_linked(user: User) -> bool:
    return user.telegram_chat_id is not None and user.disabled_at is None


def due_alerts(
    user: User,
    profile: Profile,
    cards: Iterable[Card],
    sent_ids: set[str],
    now: datetime,
) -> list[tuple[Card, Evaluation]]:
    """The cards to alert this user now, in publication order. Pure."""
    linked_at = user.telegram_linked_at
    if not is_linked(user) or linked_at is None:
        return []
    due = []
    for card in cards:
        shown = card.shown
        if shown.post.fetched_at <= linked_at:
            continue
        if shown.seen.listing.classified_at < now - ALERT_WINDOW:
            continue
        if published_too_long_ago(shown.post.posted_at, now):
            continue
        if card.post_ids & sent_ids:
            continue
        evaluation = evaluate(shown.seen, profile, now)
        if no_alert_reason(shown.seen, evaluation) is None:
            due.append((card, evaluation))
    return sorted(due, key=lambda entry: (entry[0].shown.post.posted_at, entry[0].shown_id))


@dataclass(frozen=True)
class PassResult:
    sent: int
    failed_users: tuple[str, ...]


class AlertPass:
    def __init__(
        self,
        userdata: UserDataStore,
        notifier: Notifier,
        areas: AreaWords,
        *,
        site_url: str,
        store_root: Path,
        clock: Callable[[], datetime],
        sleep: Callable[[float], None],
    ) -> None:
        self._userdata = userdata
        self._notifier = notifier
        self._areas = areas
        self._site_url = site_url
        self._store_root = Path(store_root)
        self._clock = clock
        self._sleep = sleep

    def run(
        self, cards: Sequence[Card], should_stop: Callable[[], bool] = lambda: False
    ) -> PassResult:
        sent = 0
        failed: list[str] = []
        for user in self._userdata.list_users():
            if not is_linked(user) or should_stop():
                continue
            profile = self._userdata.get_profile(user.user_id)
            if profile is None:
                continue
            due = due_alerts(
                user, profile, cards, self._userdata.sent_listing_ids(user.user_id), self._clock()
            )
            for card, evaluation in due:
                if should_stop():
                    break
                if not self._send(user, profile, card, evaluation):
                    failed.append(user.user_id)
                    break
                sent += 1
                self._sleep(SEND_GAP_SECONDS)
        if sent or failed:
            logger.info("alert pass: %d sent, %d users failed", sent, len(failed))
        return PassResult(sent, tuple(failed))

    def _send(self, user: User, profile: Profile, card: Card, evaluation: Evaluation) -> bool:
        assert user.telegram_chat_id is not None
        alert = build_alert(
            card,
            evaluation,
            profile,
            self._areas,
            site_url=self._site_url,
            store_root=self._store_root,
            now=self._clock(),
        )
        try:
            self._notifier.send(user.telegram_chat_id, alert)
        except TelegramError as error:
            # 403: the user blocked the bot or never started it; the alert waits for a later pass.
            logger.warning("alert to user %s not sent: %s", user.user_id, error)
            return False
        self._userdata.add_sent_alert(
            SentAlert(
                schema_version=SENT_ALERT_SCHEMA_VERSION,
                user_id=user.user_id,
                listing_id=card.shown_id,
                sent_at=self._clock(),
            )
        )
        logger.info("alert sent: user %s, post %s", user.user_id, card.shown_id)
        return True
