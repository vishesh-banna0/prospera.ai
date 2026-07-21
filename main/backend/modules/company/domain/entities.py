from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class CompanyRating(StrEnum):
    """A coarse, human-readable summary of a company's overall score."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"


@dataclass(frozen=True, slots=True)
class CompanyScore:
    """A comparable, self-contained scorecard for one company.

    Every score is on a 0..100 scale so companies can be ranked against each
    other directly. The scorecard snapshots the inputs it was derived from (as
    of a date) so it can be stored and compared over time without recomputing.

    Scores are deliberately transparent heuristics, not a black box:
    - growth_score    : trailing price performance (momentum as a growth proxy)
    - risk_score      : return volatility + max drawdown (higher = riskier)
    - sentiment_score : importance-weighted balance of recent news events
    - overall_score   : blended headline score
    True fundamental ratios (revenue/profit growth, debt, cash flow, valuation)
    are a documented future enhancement once profiles carry financial
    statements; the fields exist here so the schema is stable when they land.
    """

    symbol: str
    as_of: datetime

    overall_score: float
    growth_score: float
    risk_score: float
    sentiment_score: float

    rating: CompanyRating

    company_name: str | None = None
    sector: str | None = None
    market_cap: str | None = None

    event_count: int = 0
    price_points: int = 0

    rationale: tuple[str, ...] = field(default_factory=tuple)
    source: str = "heuristic-v1"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Company score symbol cannot be blank.")
        if self.as_of.tzinfo is None:
            raise ValueError("Company score as_of must be timezone aware.")
        for name in ("overall_score", "growth_score", "risk_score", "sentiment_score"):
            value = getattr(self, name)
            clamped = min(100.0, max(0.0, float(value)))
            object.__setattr__(self, name, round(clamped, 2))


# Purpose:
# Define the Phase 10 output: one comparable, explainable company scorecard.
#
# What Should Not Live Here:
# - Scoring math (see scoring.py).
# - Persistence / ORM.
# - HTTP shapes.
