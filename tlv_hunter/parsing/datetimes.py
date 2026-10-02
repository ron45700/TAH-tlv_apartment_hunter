from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def parse_rfc2822_utc(value: str) -> datetime:
    parsed = parsedate_to_datetime(value)
    # RFC 2822 "-0000" means "zone unknown"; the stdlib returns a naive datetime for it.
    if parsed.tzinfo is None:
        raise ValueError(f"RFC 2822 datetime carries no usable timezone: {value!r}")
    return parsed.astimezone(UTC)
