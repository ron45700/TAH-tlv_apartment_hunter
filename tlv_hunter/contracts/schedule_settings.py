"""Gate G: the schedule, as the admin sets it on the site (SCHEMA.md, Gate G; DECISIONS.md #61,
#472, #474; `PHASE_5.md` points 5, 8, 11). One row.

Read by the scheduler at every slot, so a change applies at once (#61). `quiet_from` and
`quiet_until` are Israel local time as `HH:MM` text: converted only by the schedule (invariant 9);
equal values mean no quiet hours. `run_now_requested_at` is the admin's last "run now" (the site
has no Apify key: the scheduler starts the run). `last_digest_at` is when the bot last sent the
daily digest, so a restart neither repeats nor skips one. `updated_by` and `updated_at` are the
admin's last change of the settings; `updated_by` is `None` for the row the scheduler first writes
from its `.env` values.

Version 2 (`PHASE_6.md` point 19): Yad2's own rhythm, `yad2_interval_minutes` and the daytime hours
`yad2_hours_from` to `yad2_hours_until` (Israel local time, `HH:MM`, from before until) in which a
Yad2 run may start; all three `None` (a version-1 row, read as version 2) means no Yad2 runs.
"""

import json
import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.contracts.user import require_opaque_id
from tlv_hunter.parsing.datetimes import require_utc

SCHEDULE_SETTINGS_SCHEMA_VERSION = 2
INTERVAL_MINUTES = range(5, 24 * 60 + 1)
_HH_MM = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
# Version 2 adds Yad2's rhythm, all `None` on a version-1 row.
_ADDED_IN_VERSION_2 = {
    "yad2_interval_minutes": None,
    "yad2_hours_from": None,
    "yad2_hours_until": None,
}


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
    yad2_interval_minutes: int | None = None
    yad2_hours_from: str | None = None
    yad2_hours_until: str | None = None

    @classmethod
    def from_stored_json(cls, doc: str) -> "ScheduleSettings":
        """Read the stored row. A version-1 one reads as version 2 with no Yad2 rhythm. Read-time
        only, as `User.from_stored_json` does: written as version 2 on its next save."""
        data = json.loads(doc)
        if isinstance(data, dict) and data.get("schema_version") == 1:
            if _ADDED_IN_VERSION_2.keys() & data.keys():
                raise ValueError("a version-1 ScheduleSettings cannot carry version-2 fields")
            doc = json.dumps(
                {**data, **_ADDED_IN_VERSION_2, "schema_version": SCHEDULE_SETTINGS_SCHEMA_VERSION}
            )
        return cls.model_validate_json(doc)

    @field_validator("quiet_from", "quiet_until", "yad2_hours_from", "yad2_hours_until")
    @classmethod
    def _hh_mm(cls, value: str | None) -> str | None:
        if value is not None and not _HH_MM.fullmatch(value):
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
        yad2 = (self.yad2_interval_minutes, self.yad2_hours_from, self.yad2_hours_until)
        if any(value is None for value in yad2) and any(value is not None for value in yad2):
            raise ValueError("Yad2's interval and hours are set together or not at all")
        if self.yad2_interval_minutes is not None:
            if self.yad2_interval_minutes not in INTERVAL_MINUTES:
                raise ValueError(
                    f"yad2_interval_minutes must be from {INTERVAL_MINUTES.start} to "
                    f"{INTERVAL_MINUTES[-1]}"
                )
            if not self.yad2_hours_from < self.yad2_hours_until:
                raise ValueError("yad2_hours_from is before yad2_hours_until (daytime only)")
        return self
