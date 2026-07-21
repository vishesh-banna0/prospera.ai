from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AnalyzeReasoningRequest:
    symbol: str
    event_limit: int = 10
    research_top_k: int = 3


@dataclass(frozen=True, slots=True)
class ReasonedOpinionView:
    symbol: str
    as_of: datetime
    stance: str
    headline: str
    explanation: str
    confidence: float
    drivers: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    source: str = "deterministic"


@dataclass(frozen=True, slots=True)
class ReasonedOpinionsView:
    opinions: tuple[ReasonedOpinionView, ...]
    count: int


# Purpose:
# Application-layer request/response contracts for Phase 11 reasoning.
