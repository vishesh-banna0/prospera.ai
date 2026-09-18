from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from backend.modules.prediction.domain.entities import ModelOutput


class PredictionModelContract(ABC):
    """Port for a price-forecasting model.

    A model turns a chronological close-price series into a ``ModelOutput``
    (direction + probability + expected return + confidence). The Phase 12
    default is a dependency-free logistic-regression baseline; a trained
    scikit-learn / XGBoost / LightGBM model, or an LSTM/GRU/TFT deep model, can
    implement the same contract and be swapped in at the composition root
    without touching the service, domain, or API layers.

    ``event_score`` carries news evidence for the symbol into the forecast: a
    value in [-1, 1] summarizing recent event sentiment weighted by
    importance, where 0 means "no recent news, or news that nets out". It is
    on the port (rather than hidden inside one implementation) because a
    forecaster that ignores it and one that uses it must remain
    interchangeable — the price-only models accept and ignore it, while the
    ensemble uses it to tilt the blend.

    Implementations must be deterministic: the same inputs must always produce
    the same forecast, so backtests and tests are reproducible.
    """

    name: str = "model"

    @abstractmethod
    def predict(
        self,
        closes: Sequence[float],
        horizon_days: int = 1,
        event_score: float = 0.0,
    ) -> ModelOutput:
        raise NotImplementedError
