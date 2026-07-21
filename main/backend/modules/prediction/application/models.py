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
    """

    name: str = "model"

    @abstractmethod
    def predict(self, closes: Sequence[float], horizon_days: int = 1) -> ModelOutput:
        raise NotImplementedError
