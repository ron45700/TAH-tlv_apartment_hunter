from datetime import UTC, date, datetime, timedelta
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

ISRAEL_ZONE = ZoneInfo("Asia/Jerusalem")


def parse_rfc2822_utc(value: str) -> datetime:
    parsed = parsedate_to_datetime(value)
    # RFC 2822 "-0000" means "zone unknown"; the stdlib returns a naive datetime for it.
    if parsed.tzinfo is None:
        raise ValueError(f"RFC 2822 datetime carries no usable timezone: {value!r}")
    return parsed.astimezone(UTC)


def parse_israel_local_utc(value: str) -> datetime:
    """Yad2's dates (`updatedAt`): ISO text with no zone, Israel local time (spike §3, §S2.4;
    DECISIONS.md #492), to UTC. A time inside the autumn change's repeated hour reads as the
    earlier one (summer time, `fold=0`); a time inside the spring gap reads with winter time."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValueError(f"expected Israel local time with no zone: {value!r}")
    return parsed.replace(tzinfo=ISRAEL_ZONE).astimezone(UTC)


def parse_local_date(value: str) -> date:
    """A calendar date written as ISO text with no zone and no time of day (Yad2's
    `entranceDate`, `"2026-11-01T00:00:00"`): its date as written, never moved by a zone."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None or parsed.time() != datetime.min.time():
        raise ValueError(f"expected a date at midnight with no zone: {value!r}")
    return parsed.date()


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
