"""Gate G: one collection run (SCHEMA.md, Gate G; DECISIONS.md #472; `PHASE_5.md` point 5).

Written by `jobs/run_once.py` when the run starts (`running`) and when it ends (`succeeded` or
`failed`); its Apify cost is filled later by `jobs/settle_costs.py`, from the run's charged events
read 15 minutes or more after it ended (#450, point 6). The source of the digest's run lines, the
failure alert, the site's "last run" and the scheduler's timer (#61).

`rows_fetched` is the rows the Apify dataset returned (what is billed); `rows_skipped` the rows that
failed to map (#71 D); both `None` until known. `charged_events` is the run's `chargedEventCounts`:
the end-of-run (preliminary, `ASSUMPTIONS.md` P19) map when the run ends, the settled one once
`cost_usd` is set. `window_capped` is always false: collection is never capped after a pause
(#473, point 12 B). `source` (version 2, `PHASE_6.md` point 19) tells Facebook's runs from Yad2's;
a Yad2 run leaves the Apify fields `None`.
"""

import json
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from tlv_hunter.parsing.datetimes import require_utc

RUN_RECORD_SCHEMA_VERSION = 2

Trigger = Literal["scheduled", "manual"]
RunStatus = Literal["running", "succeeded", "failed"]
RunSource = Literal["facebook", "yad2"]


class RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: int
    run_id: str
    trigger: Trigger
    started_at: datetime
    finished_at: datetime | None
    status: RunStatus
    failure_kind: str | None
    rows_fetched: int | None
    rows_skipped: int | None
    window_since: datetime | None
    window_capped: bool
    apify_run_id: str | None
    charged_events: dict[str, int] | None
    cost_usd: float | None
    cost_settled_at: datetime | None
    source: RunSource = "facebook"

    @classmethod
    def from_stored_json(cls, doc: str) -> "RunRecord":
        """Read a stored run. A version-1 one (every run before Yad2) reads as version 2 with
        `source` `"facebook"`. Read-time only, as `User.from_stored_json` does."""
        data = json.loads(doc)
        if isinstance(data, dict) and data.get("schema_version") == 1:
            if "source" in data:
                raise ValueError("a version-1 RunRecord cannot carry source")
            doc = json.dumps(
                {**data, "source": "facebook", "schema_version": RUN_RECORD_SCHEMA_VERSION}
            )
        return cls.model_validate_json(doc)

    @field_validator("started_at", "finished_at", "window_since", "cost_settled_at")
    @classmethod
    def _require_utc(cls, value: datetime | None) -> datetime | None:
        return None if value is None else require_utc(value)

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.schema_version != RUN_RECORD_SCHEMA_VERSION:
            raise ValueError(f"unknown RunRecord schema_version {self.schema_version!r}")
        if not self.run_id:
            raise ValueError("run_id is empty")
        if (self.status == "running") != (self.finished_at is None):
            raise ValueError("finished_at is None exactly while the run is running")
        if (self.status == "failed") != (self.failure_kind is not None):
            raise ValueError("failure_kind is set exactly when the run failed")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at is before started_at")
        for name in ("rows_fetched", "rows_skipped"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")
        if any(count < 0 for count in (self.charged_events or {}).values()):
            raise ValueError("a charged event count cannot be negative")
        if (self.cost_usd is None) != (self.cost_settled_at is None):
            raise ValueError("cost_usd and cost_settled_at are set together")
        if self.cost_usd is not None and self.cost_usd < 0:
            raise ValueError("cost_usd cannot be negative")
        if self.cost_usd is not None and self.status == "running":
            raise ValueError("a running run has no settled cost")
        if self.source == "yad2" and (
            self.apify_run_id is not None
            or self.charged_events is not None
            or self.cost_usd is not None
        ):
            raise ValueError("a Yad2 run has no Apify run, charged events or cost")
        return self
