"""Sends an alert through the bot (`PHASE_4.md` 4.6; DECISIONS.md #452 point 13): the photo by a
multipart upload from the store with the lines as its caption, or a text message with the same
lines when the post has no photo Telegram takes. A photo Telegram refuses (400) is sent again as
the text message, so the alert still arrives."""

import logging

from tlv_hunter.notify.alert import Alert
from tlv_hunter.telegram.client import TelegramClient, TelegramError, Upload

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, client: TelegramClient) -> None:
        self._client = client

    def send(self, chat_id: int, alert: Alert) -> int:
        if alert.photo is not None:
            upload = Upload(
                field="photo",
                filename=alert.photo.path.name,
                content_type=alert.photo.content_type,
                data=alert.photo.path.read_bytes(),
            )
            try:
                sent = self._client.send_photo(chat_id, upload, alert.text, alert.keyboard)
                return int(sent["message_id"])
            except TelegramError as error:
                if error.error_code != 400:
                    raise
                logger.warning(
                    "photo of %s refused (%s): sent as text", alert.listing_id, error.description
                )
        sent = self._client.send_message(chat_id, alert.text, alert.keyboard)
        return int(sent["message_id"])
