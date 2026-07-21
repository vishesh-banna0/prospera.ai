from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Stance(StrEnum):
    """The reasoning engine's explainable directional opinion."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class ReasonedOpinion:
    """A stored, explainable opinion about one symbol.

    This is the "explainable" half of the platform: not just a stance, but the
    written explanation and the enumerated drivers behind it, plus any research
    citations, so a human can see *why*.
    """

    symbol: str
    as_of: datetime

    stance: Stance
    headline: str
    explanation: str
    confidence: float

    drivers: tuple[str, ...] = field(default_factory=tuple)
    citations: tuple[str, ...] = field(default_factory=tuple)
    source: str = "deterministic"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Reasoned opinion symbol cannot be blank.")
        if not self.headline.strip():
            raise ValueError("Reasoned opinion headline cannot be blank.")
        if self.as_of.tzinfo is None:
            raise ValueError("Reasoned opinion as_of must be timezone aware.")
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence))))


# Purpose:
# Define the Phase 11 output: an explainable bullish/bearish/neutral opinion.
#
# What Should Not Live Here:
# - How the opinion is generated (reasoner adapters).
# - Persistence / HTTP.
