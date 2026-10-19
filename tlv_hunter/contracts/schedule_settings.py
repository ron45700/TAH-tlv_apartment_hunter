"""Gate G: the schedule, as the admin sets it on the site (SCHEMA.md, Gate G; DECISIONS.md #61,
#472, #474; `PHASE_5.md` points 5, 8, 11). One row.

Read by the scheduler at every slot, so a change applies at once (#61). `quiet_from` and
`quiet_until` are Israel local time as `HH:MM` text: converted only by the schedule (invariant 9);
equal values mean no quiet hours. `run_now_requested_at` is the admin's last "run now" (the site
has no Apify key: the scheduler starts the run). `last_digest_at` is when the bot last sent the
daily digest, so a restart neither repeats nor skips one. `updated_by` and `updated_at` are the
admin's last change of the settings; `updated_by` is `None` for the row the scheduler first writes
from its `.env` values.
"""

import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

SCHEDULE_SETTINGS_SCHEMA_VERSION = 1
INTERVAL_MINUTES = range(5, 24 * 60 + 1)
_HH_MM = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")


class ScheduleSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    interval_minutes: int
    quiet_from: str
    quiet_until: str
    run_now_requested_at: datetime | None
    last_digest_at: datetime | None
    updated_by: str | None
    updated_at: datetime

    @field_validator("quiet_from", "quiet_until")
    @classmethod
    def _hh_mm(cls, value: str) -> str:
        if not _HH_MM.fullmatch(value):
            raise ValueError("must be HH:MM, 00:00 to 23:59")
        return value

    @field_validator("updated_by")
    @classmethod
    def _opaque(cls, value: str | None) -> str | None:
        return require_opaque_id(value)

    @field_validator("run_now_requested_at", "last_digest_at", "updated_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.schema_version != SCHEDULE_SETTINGS_SCHEMA_VERSION:
            raise ValueError(f"unknown ScheduleSettings schema_version {self.schema_version!r}")
        if self.interval_minutes not in INTERVAL_MINUTES:
            raise ValueError(
                f"interval_minutes must be from {INTERVAL_MINUTES.start} to {INTERVAL_MINUTES[-1]}"
            )
        return self
