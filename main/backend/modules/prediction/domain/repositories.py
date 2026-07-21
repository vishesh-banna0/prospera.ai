from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modules.prediction.domain.entities import Prediction


class PredictionRepository(ABC):
    """Persistence port for stored forecasts."""

    @abstractmethod
    async def save(self, prediction: Prediction) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, symbol: str) -> Prediction | None:
        raise NotImplementedError

    @abstractmethod
    async def list_latest(self, limit: int = 50) -> list[Prediction]:
        raise NotImplementedError
