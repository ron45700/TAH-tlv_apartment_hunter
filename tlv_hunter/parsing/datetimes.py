from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime


def parse_rfc2822_utc(value: str) -> datetime:
    parsed = parsedate_to_datetime(value)
    # RFC 2822 "-0000" means "zone unknown"; the stdlib returns a naive datetime for it.
    if parsed.tzinfo is None:
        raise ValueError(f"RFC 2822 datetime carries no usable timezone: {value!r}")
    return parsed.astimezone(UTC)


def require_utc(value: datetime) -> datetime:
    """The single UTC check for every stored record's datetimes."""
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("must be a tz-aware UTC datetime")
    return value


def nearest_occurrence(day: int, month: int, reference: date) -> date | None:
    """The date with this day and month nearest to `reference`, the year before, the same year or
    the year after; a tie goes to the later one. None when the day exists in none of the three
    years (31.11). DECISIONS.md #115, #179."""
    candidates = []
    for year in (reference.year - 1, reference.year, reference.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(
        candidates, key=lambda candidate: (abs(candidate - reference), -candidate.toordinal())
    )
