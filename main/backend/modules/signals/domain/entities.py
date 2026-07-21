from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class SignalAction(StrEnum):
    """The unified recommendation produced by fusing all signals."""

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"


@dataclass(frozen=True, slots=True)
class SignalComponent:
    """One contributing signal, normalized so components are comparable.

    ``score`` is in [-1, 1] (negative = bearish, positive = bullish),
    ``weight`` is its relative importance, and ``present`` records whether the
    underlying signal actually existed (a missing signal is excluded from the
    blend rather than counted as neutral, which would dilute real signals).
    """

    name: str
    score: float
    weight: float
    present: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class FusedSignal:
    """The stored output of the signal fusion layer for one symbol."""

    symbol: str
    as_of: datetime

    action: SignalAction
    score: float          # blended, in [-1, 1]
    confidence: float     # 0..1

    components: tuple[SignalComponent, ...] = field(default_factory=tuple)
    rationale: tuple[str, ...] = field(default_factory=tuple)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("Fused signal symbol cannot be blank.")
        if self.as_of.tzinfo is None:
            raise ValueError("Fused signal as_of must be timezone aware.")
        object.__setattr__(self, "score", max(-1.0, min(1.0, float(self.score))))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence))))


# Purpose:
# Define the Phase 13 output: a unified, explainable Buy/Hold/Sell decision and
# the normalized components it was blended from.
#
# What Should Not Live Here:
# - Blending math (see fusion.py).
# - Persistence / HTTP.
