from __future__ import annotations

import math
from collections.abc import Sequence

# Feature engineering for the price-based baseline model. Pure functions over a
# chronological close-price series — no I/O, no dependencies — so the whole
# feature/label pipeline is deterministic and unit-testable.

# The longest window any feature looks back over; the dataset needs at least
# this much history before the first usable row.
_MAX_WINDOW = 14


def _sma(values: Sequence[float], end: int, window: int) -> float:
    start = end - window + 1
    if start < 0:
        window = end + 1
        start = 0
    window_values = values[start : end + 1]
    return sum(window_values) / len(window_values)


def _rsi(closes: Sequence[float], end: int, period: int = 14) -> float:
    start = end - period
    if start < 0:
        start = 0
    gains = 0.0
    losses = 0.0
    count = 0
    for i in range(start + 1, end + 1):
        change = closes[i] - closes[i - 1]
        if change >= 0:
            gains += change
        else:
            losses -= change
        count += 1
    if count == 0:
        return 50.0
    avg_gain = gains / count
    avg_loss = losses / count
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _return_over(closes: Sequence[float], end: int, window: int) -> float:
    start = end - window
    if start < 0 or closes[start] <= 0:
        return 0.0
    return (closes[end] - closes[start]) / closes[start]


def _volatility(closes: Sequence[float], end: int, window: int = 10) -> float:
    returns: list[float] = []
    start = max(1, end - window + 1)
    for i in range(start, end + 1):
        if closes[i - 1] > 0:
            returns.append((closes[i] - closes[i - 1]) / closes[i - 1])
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance)


FEATURE_NAMES = ("ret_1", "ret_5", "ret_10", "sma_ratio", "volatility", "rsi")


def feature_vector(closes: Sequence[float], end: int) -> list[float]:
    """The feature vector describing the state at index ``end``."""

    sma10 = _sma(closes, end, 10)
    sma_ratio = (closes[end] / sma10 - 1.0) if sma10 > 0 else 0.0
    return [
        _return_over(closes, end, 1),
        _return_over(closes, end, 5),
        _return_over(closes, end, 10),
        sma_ratio,
        _volatility(closes, end, 10),
        _rsi(closes, end, 14) / 100.0,  # scale to ~0..1
    ]


def build_dataset(
    closes: Sequence[float],
    horizon: int = 1,
) -> tuple[list[list[float]], list[int], list[float] | None]:
    """Return (X, y, latest_features) for supervised next-move classification.

    Each row is the feature vector at day t; its label is 1 if the close
    ``horizon`` days later is higher, else 0. ``latest_features`` is the vector
    at the final day (no label yet) used to make the live prediction. Returns
    an empty dataset when there is not enough history.
    """

    n = len(closes)
    if n < _MAX_WINDOW + horizon + 1:
        latest = feature_vector(closes, n - 1) if n > _MAX_WINDOW else None
        return [], [], latest

    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for t in range(_MAX_WINDOW, n - horizon):
        x_rows.append(feature_vector(closes, t))
        y_rows.append(1 if closes[t + horizon] > closes[t] else 0)

    latest = feature_vector(closes, n - 1)
    return x_rows, y_rows, latest
