from __future__ import annotations

import math
from collections.abc import Sequence

from backend.modules.prediction.application.models import PredictionModelContract
from backend.modules.prediction.domain.entities import ModelOutput, PredictionDirection
from backend.modules.prediction.domain.features import (
    FEATURE_NAMES,
    build_dataset,
    feature_vector,
)


def _sigmoid(x: float) -> float:
    if x < -35:
        return 0.0
    if x > 35:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


class LogisticBaselineModel(PredictionModelContract):
    """A dependency-free logistic-regression next-move classifier.

    It trains on the symbol's own price history (walk-forward technical
    features -> "did price rise over the horizon?") using plain gradient descent
    in pure Python, then predicts the probability that the next move is up.

    Deterministic by construction: weights start at zero and the learning rate,
    iteration count, and standardization are fixed, so the same series always
    yields the same forecast (important for reproducible tests and backtests).
    It is a genuine *baseline* — the point is a clean, honest floor to beat, and
    a stable seam to drop a trained sklearn/XGBoost/deep model behind the same
    contract. With too little history it returns a neutral, low-confidence call.
    """

    name = "logistic-baseline-v1"

    def __init__(self, iterations: int = 400, learning_rate: float = 0.3) -> None:
        self._iterations = iterations
        self._learning_rate = learning_rate

    def predict(self, closes: Sequence[float], horizon_days: int = 1) -> ModelOutput:
        closes = [float(c) for c in closes]
        x_rows, y_rows, latest = build_dataset(closes, horizon=horizon_days)

        if latest is None or len(x_rows) < 20 or len(set(y_rows)) < 2:
            # Not enough signal to train a stable classifier -> neutral call.
            features = dict(zip(FEATURE_NAMES, latest)) if latest else {}
            return ModelOutput(
                direction=PredictionDirection.NEUTRAL,
                probability_up=0.5,
                expected_return_pct=0.0,
                confidence=0.0,
                features=features,
            )

        means, stds = self._standardization(x_rows)
        x_std = [self._standardize(row, means, stds) for row in x_rows]
        weights, bias = self._train(x_std, y_rows)

        latest_std = self._standardize(latest, means, stds)
        logit = bias + sum(w * xi for w, xi in zip(weights, latest_std))
        probability_up = _sigmoid(logit)

        # Confidence is how far the probability is from a coin flip; the
        # expected move scales that edge by the series' recent volatility.
        confidence = abs(probability_up - 0.5) * 2.0
        recent_vol_pct = self._recent_volatility_pct(closes)
        expected_return_pct = (probability_up - 0.5) * 2.0 * recent_vol_pct * horizon_days

        direction = PredictionDirection.NEUTRAL
        if probability_up > 0.55:
            direction = PredictionDirection.UP
        elif probability_up < 0.45:
            direction = PredictionDirection.DOWN

        return ModelOutput(
            direction=direction,
            probability_up=probability_up,
            expected_return_pct=expected_return_pct,
            confidence=confidence,
            features={name: round(v, 6) for name, v in zip(FEATURE_NAMES, latest)},
        )

    def _standardization(
        self, rows: list[list[float]]
    ) -> tuple[list[float], list[float]]:
        cols = len(rows[0])
        means = [0.0] * cols
        for row in rows:
            for j in range(cols):
                means[j] += row[j]
        means = [m / len(rows) for m in means]

        stds = [0.0] * cols
        for row in rows:
            for j in range(cols):
                stds[j] += (row[j] - means[j]) ** 2
        stds = [math.sqrt(s / len(rows)) or 1.0 for s in stds]
        return means, stds

    def _standardize(
        self, row: Sequence[float], means: list[float], stds: list[float]
    ) -> list[float]:
        return [(row[j] - means[j]) / stds[j] for j in range(len(row))]

    def _train(
        self, x_std: list[list[float]], y: list[int]
    ) -> tuple[list[float], float]:
        n = len(x_std)
        cols = len(x_std[0])
        weights = [0.0] * cols
        bias = 0.0

        for _ in range(self._iterations):
            grad_w = [0.0] * cols
            grad_b = 0.0
            for row, label in zip(x_std, y):
                logit = bias + sum(w * xi for w, xi in zip(weights, row))
                error = _sigmoid(logit) - label
                for j in range(cols):
                    grad_w[j] += error * row[j]
                grad_b += error
            for j in range(cols):
                weights[j] -= self._learning_rate * grad_w[j] / n
            bias -= self._learning_rate * grad_b / n

        return weights, bias

    def _recent_volatility_pct(self, closes: Sequence[float], window: int = 10) -> float:
        start = max(1, len(closes) - window)
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(start, len(closes))
            if closes[i - 1] > 0
        ]
        if not returns:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance) * 100.0


# Feature_vector is re-exported for callers that want the live features without
# a full prediction (e.g. diagnostics).
__all__ = ["LogisticBaselineModel", "feature_vector"]
