from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from backend.modules.prediction.application.models import PredictionModelContract
from backend.modules.prediction.domain.entities import ModelOutput, PredictionDirection

_UP_THRESHOLD = 0.55
_DOWN_THRESHOLD = 0.45

# A probability of exactly 0 or 1 has infinite log-odds, which would let one
# over-confident member veto every other. Clamping bounds any single model's
# influence.
_PROBABILITY_FLOOR = 1e-6

# How hard the news signal may push the blended forecast, in log-odds. An
# event score of +/-1 (uniformly strong, high-importance news) shifts the
# probability by roughly 10 percentage points around the midpoint. Event
# sentiment is a real but weak predictor of returns, so the tilt is
# deliberately small: it should break ties, not overrule the price models.
_MAX_EVENT_TILT = 0.4


@dataclass(frozen=True, slots=True)
class WeightedModel:
    model: PredictionModelContract
    weight: float


def _logit(probability: float) -> float:
    p = min(max(probability, _PROBABILITY_FLOOR), 1.0 - _PROBABILITY_FLOOR)
    return math.log(p / (1.0 - p))


def _sigmoid(x: float) -> float:
    if x < -35:
        return 0.0
    if x > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


class EnsemblePredictor(PredictionModelContract):
    """Blends several forecasters and tilts the result by news-event evidence.

    This is the hybrid layer. Three different views of the same series are
    combined:

      * a **machine-learning** classifier (logistic regression on technical
        features) — learns a decision boundary from labelled history;
      * an **EWMA drift/volatility** model — estimates the conditional mean and
        variance of the return process;
      * an **AR(1)** model — captures short-horizon momentum or reversal.

    They fail in different ways, which is the entire reason to combine them:
    the classifier needs enough labelled history, the time-series models need a
    stable variance, and neither knows anything about the news.

    Probabilities are pooled in **log-odds** space rather than averaged
    directly. Averaging probabilities is the wrong operation — it drags a
    confident, correct model toward the middle — whereas averaging log-odds is
    the standard way to pool independent evidence.

    Finally the **event score** (news sentiment weighted by importance, in
    [-1, 1]) is applied as an additive log-odds tilt. That is what makes this
    event-driven rather than purely technical: the price models say what the
    series has been doing, and the news term says what just happened to the
    company. The tilt is capped so news can shade a forecast but never
    manufacture one.

    Members that lack data return zero confidence and are excluded rather than
    counted as a neutral vote, so a thin history reduces the ensemble's
    confidence instead of silently diluting its signal.
    """

    name = "hybrid-ensemble-v1"

    def __init__(self, members: Sequence[WeightedModel]) -> None:
        if not members:
            raise ValueError("An ensemble needs at least one member model.")
        self._members = tuple(members)

    def predict(
        self,
        closes: Sequence[float],
        horizon_days: int = 1,
        event_score: float = 0.0,
    ) -> ModelOutput:
        horizon = max(1, int(horizon_days))
        event_score = min(max(float(event_score), -1.0), 1.0)

        features: dict[str, float] = {}
        weighted_logit = 0.0
        weighted_return = 0.0
        used_weight = 0.0
        total_weight = sum(m.weight for m in self._members if m.weight > 0)

        for member in self._members:
            if member.weight <= 0:
                continue
            try:
                output = member.model.predict(closes, horizon_days=horizon)
            except Exception:
                # One broken member must not take down the forecast.
                continue

            # Zero confidence means the member declined to make a call.
            if output.confidence <= 0.0:
                features[f"{member.model.name}_available"] = 0.0
                continue

            features[f"{member.model.name}_available"] = 1.0
            features[f"{member.model.name}_p_up"] = round(output.probability_up, 6)
            features[f"{member.model.name}_expected_return_pct"] = round(
                output.expected_return_pct, 6
            )

            weighted_logit += member.weight * _logit(output.probability_up)
            weighted_return += member.weight * output.expected_return_pct
            used_weight += member.weight

        if used_weight <= 0.0:
            # Nothing had enough data to speak.
            return ModelOutput(
                direction=PredictionDirection.NEUTRAL,
                probability_up=0.5,
                expected_return_pct=0.0,
                confidence=0.0,
                features={**features, "event_score": round(event_score, 6)},
            )

        blended_logit = weighted_logit / used_weight
        expected_return_pct = weighted_return / used_weight

        event_tilt = _MAX_EVENT_TILT * event_score
        probability_up = _sigmoid(blended_logit + event_tilt)

        # Coverage: how much of the ensemble actually contributed. A forecast
        # from one of three models should not read as confidently as one all
        # three agree on.
        coverage = used_weight / total_weight if total_weight > 0 else 0.0
        confidence = abs(probability_up - 0.5) * 2.0 * coverage

        direction = PredictionDirection.NEUTRAL
        if probability_up > _UP_THRESHOLD:
            direction = PredictionDirection.UP
        elif probability_up < _DOWN_THRESHOLD:
            direction = PredictionDirection.DOWN

        features.update(
            {
                "event_score": round(event_score, 6),
                "event_tilt_logodds": round(event_tilt, 6),
                "model_coverage": round(coverage, 4),
                "blended_logodds": round(blended_logit, 6),
                "horizon_days": float(horizon),
            }
        )

        return ModelOutput(
            direction=direction,
            probability_up=probability_up,
            expected_return_pct=expected_return_pct,
            confidence=confidence,
            features=features,
        )


def build_default_ensemble() -> EnsemblePredictor:
    """The standard three-model blend.

    Weights favour the time-series models slightly over the classifier: the
    classifier needs a long labelled history to be stable, while the EWMA and
    AR(1) fits degrade more gracefully on short series. They are fixed rather
    than fitted because fitting ensemble weights on the same history the
    members were fitted on is how backtests end up lying.
    """

    # Imported here to keep the module importable without a circular import
    # back through the predictors module.
    from backend.modules.prediction.infrastructure.predictors import (
        LogisticBaselineModel,
    )
    from backend.modules.prediction.infrastructure.timeseries import (
        Ar1Model,
        EwmaDriftModel,
    )

    return EnsemblePredictor(
        [
            WeightedModel(LogisticBaselineModel(), weight=0.30),
            WeightedModel(EwmaDriftModel(), weight=0.40),
            WeightedModel(Ar1Model(), weight=0.30),
        ]
    )


# Purpose:
# The hybrid forecaster: pool several models' probabilities in log-odds space
# and tilt the result by news-event evidence, producing one horizon-aware
# forecast that combines event intelligence, machine learning and time series.
#
# What Should Not Live Here:
# - The member models themselves (predictors.py, timeseries.py).
# - Fetching the event score (the application service supplies it).

__all__ = ["EnsemblePredictor", "WeightedModel", "build_default_ensemble"]
