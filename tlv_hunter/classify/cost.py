"""What a call costs, and the run's cap, checked before every call (DECISIONS.md #153, #182).

Prices are `gpt-6-luna`'s list prices (`ASSUMPTIONS.md` O2, ASSUMED until a bill confirms them).
Cache writes are counted inside `input_tokens`, as the spike's responses report them (O7).
"""

import json
from dataclasses import dataclass, field
from typing import Any

# USD per 1M tokens.
PRICE_INPUT = 0.10
PRICE_CACHED = 0.01
PRICE_CACHE_WRITE = 0.125
PRICE_OUTPUT = 0.50


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    cached_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int

    @classmethod
    def from_response(cls, response: dict[str, Any]) -> "Usage":
        usage = response.get("usage") or {}
        inputs = usage.get("input_tokens_details") or {}
        outputs = usage.get("output_tokens_details") or {}
        return cls(
            input_tokens=usage.get("input_tokens") or 0,
            cached_tokens=inputs.get("cached_tokens") or 0,
            cache_write_tokens=inputs.get("cache_write_tokens") or 0,
            output_tokens=usage.get("output_tokens") or 0,
            reasoning_tokens=outputs.get("reasoning_tokens") or 0,
        )

    def cost(self) -> float:
        uncached = self.input_tokens - self.cached_tokens - self.cache_write_tokens
        return (
            uncached * PRICE_INPUT
            + self.cached_tokens * PRICE_CACHED
            + self.cache_write_tokens * PRICE_CACHE_WRITE
            + self.output_tokens * PRICE_OUTPUT
        ) / 1e6


def worst_case(request: dict[str, Any]) -> float:
    """An upper bound before the call: every character of the request a token, all written to the
    cache, and the full output limit. The measured rate is about 0.25-0.45 tokens a character."""
    characters = len(json.dumps(request, ensure_ascii=False))
    return (
        characters * max(PRICE_INPUT, PRICE_CACHE_WRITE)
        + request["max_output_tokens"] * PRICE_OUTPUT
    ) / 1e6


@dataclass(frozen=True)
class CallRecord:
    """One call that returned a response, successful or not: it was billed."""

    listing_id: str
    status: str | None
    outcome: str
    usage: Usage
    cost: float
    reported_model: str | None
    seconds: float
    dropped_streets: tuple[str, ...] = ()
    dropped_area_names: tuple[str, ...] = ()
    dropped_other_city: str | None = None


class CapReached(Exception):
    def __init__(self, spent: float, worst: float, cap: float) -> None:
        super().__init__(
            f"the next call could reach ${spent + worst:.4f}, above the ${cap:.2f} cap"
        )
        self.spent = spent
        self.worst = worst
        self.cap = cap


@dataclass
class CostMeter:
    cap: float
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def spent(self) -> float:
        return sum(call.cost for call in self.calls)

    def check(self, worst: float) -> None:
        spent = self.spent
        if spent + worst > self.cap:
            raise CapReached(spent, worst, self.cap)

    def record(self, call: CallRecord) -> None:
        self.calls.append(call)
