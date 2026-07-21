from __future__ import annotations

from collections.abc import Sequence

from backend.modules.signals.domain.entities import SignalAction, SignalComponent

# A blended score at or beyond this magnitude tips Hold into Buy/Sell.
_ACTION_THRESHOLD = 0.2


def blend(components: Sequence[SignalComponent]) -> tuple[float, float]:
    """Blend present components into (score, confidence).

    ``score`` is the weight-normalized average of present components' scores,
    in [-1, 1]. ``confidence`` combines the strength of the blended score with
    how much of the total possible weight was actually available (more signals
    present -> more trustworthy), so a lone weak signal never reads as certain.
    """

    present = [c for c in components if c.present and c.weight > 0]
    if not present:
        return 0.0, 0.0

    total_weight = sum(c.weight for c in present)
    score = sum(c.score * c.weight for c in present) / total_weight

    all_weight = sum(c.weight for c in components if c.weight > 0) or total_weight
    coverage = total_weight / all_weight  # fraction of possible signal present
    confidence = min(1.0, abs(score) * coverage * 1.5)
    return score, confidence


def action_for(score: float) -> SignalAction:
    if score >= _ACTION_THRESHOLD:
        return SignalAction.BUY
    if score <= -_ACTION_THRESHOLD:
        return SignalAction.SELL
    return SignalAction.HOLD


def fuse(components: Sequence[SignalComponent]) -> tuple[SignalAction, float, float]:
    """Return (action, score, confidence) from a set of signal components."""

    score, confidence = blend(components)
    return action_for(score), score, confidence


# Purpose:
# Pure, deterministic blending of normalized signals into a single decision.
#
# What Should Not Live Here:
# - Fetching signals (the application service builds the components).
# - Persistence / HTTP.
