from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AdvisorRequest:
    """Options for one advisory run (all optional; sensible defaults)."""

    max_events: int = 40
    # When set, the Advisor reads that environment's positions and adds a
    # portfolio pass: market-wide calls are mapped onto what is actually held,
    # so the advice is about this portfolio rather than about the market in
    # the abstract. Omit it for the original market-wide report.
    environment_id: str | None = None


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
class HoldingActionView:
    """What the market view implies for one position actually held."""

    symbol: str
    action: str  # "add" | "trim" | "exit" | "hold"
    weight_pct: float
    rationale: str
    # The event/sector call this was derived from, for traceability.
    driver: str | None = None
    confidence: float = 0.5


@dataclass(frozen=True, slots=True)
class PortfolioAdviceView:
    """The Advisor's portfolio pass — present only when holdings were supplied."""

    environment_id: str
    holdings_count: int
    actions: tuple[HoldingActionView, ...] = field(default_factory=tuple)
    # Positions large enough that a single-name shock moves the whole book.
    concentration_warnings: tuple[str, ...] = field(default_factory=tuple)
    # Market calls that the portfolio has no exposure to — the opportunities.
    unheld_opportunities: tuple[str, ...] = field(default_factory=tuple)
    summary: str = ""


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
    # Populated when the request named an environment holding positions.
    portfolio: PortfolioAdviceView | None = None


# Purpose:
# Request/response contracts for the multi-agent AI Advisor.
