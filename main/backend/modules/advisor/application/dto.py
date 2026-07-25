from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AdvisorRequest:
    """Options for one advisory run (all optional; sensible defaults)."""

    max_events: int = 40


@dataclass(frozen=True, slots=True)
class SectorImpactView:
    sector: str
    impact: str  # "positive" | "negative" | "mixed" | "neutral"
    magnitude: str  # "high" | "medium" | "low"
    drivers: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class RecommendationView:
    target: str  # symbol or sector
    action: str  # "buy" | "sell" | "hold" | "avoid"
    horizon: str  # "short_term" | "long_term"
    rationale: str
    trigger: str | None = None  # exit/entry condition (esp. short-term)
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class AdvisorReportView:
    """The full advisory readout: what happened, who's affected, what to do."""

    market_summary: str
    sectors: tuple[SectorImpactView, ...]
    short_term: tuple[RecommendationView, ...]
    long_term: tuple[RecommendationView, ...]
    narrative: str
    event_count: int
    generated_at: datetime
    # role -> the model that produced it, or "deterministic" when it fell back.
    models: dict[str, str] = field(default_factory=dict)
    source: str = "deterministic"  # "llm" | "deterministic" | "mixed" | "none"


# Purpose:
# Request/response contracts for the multi-agent AI Advisor.
