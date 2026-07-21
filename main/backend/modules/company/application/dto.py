from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AnalyzeCompanyRequest:
    symbol: str
    lookback_days: int = 180
    event_limit: int = 50


@dataclass(frozen=True, slots=True)
class CompanyScoreView:
    symbol: str
    as_of: datetime
    overall_score: float
    growth_score: float
    risk_score: float
    sentiment_score: float
    rating: str
    company_name: str | None = None
    sector: str | None = None
    market_cap: str | None = None
    event_count: int = 0
    price_points: int = 0
    rationale: tuple[str, ...] = field(default_factory=tuple)
    source: str = "heuristic-v1"


@dataclass(frozen=True, slots=True)
class CompanyScoresView:
    companies: tuple[CompanyScoreView, ...]
    count: int


# Purpose:
# Application-layer request/response contracts for Phase 10 company intelligence.
#
# What Should Not Live Here:
# - Scoring math or persistence.
# - HTTP status handling.
