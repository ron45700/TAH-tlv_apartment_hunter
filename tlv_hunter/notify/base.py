"""The `notify/` seam (`CLAUDE.md`): sends an alert to one user. Built in Phase 4 (`PHASE_4.md` 4.6;
DECISIONS.md #452): `notify.telegram.TelegramNotifier` over the bot's client. It sends; it decides
nothing (who is alerted is `telegram/alerts.py`'s, by `policy.alert`) and writes nothing."""

from typing import Protocol, runtime_checkable

from tlv_hunter.notify.alert import Alert


@runtime_checkable
class Notifier(Protocol):
    def send(self, chat_id: int, alert: Alert) -> int:
        """Sends the alert to the chat; returns the sent message's `message_id`."""
        ...
