from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FuseSignalRequest:
    symbol: str
    event_limit: int = 50


@dataclass(frozen=True, slots=True)
class SignalComponentView:
    name: str
    score: float
    weight: float
    present: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class FusedSignalView:
    symbol: str
    as_of: datetime
    action: str
    score: float
    confidence: float
    components: tuple[SignalComponentView, ...] = field(default_factory=tuple)
    rationale: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class FusedSignalsView:
    signals: tuple[FusedSignalView, ...]
    count: int


# Purpose:
# Application-layer request/response contracts for Phase 13 signal fusion.
