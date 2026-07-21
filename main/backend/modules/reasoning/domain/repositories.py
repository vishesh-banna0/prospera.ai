from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modules.reasoning.domain.entities import ReasonedOpinion


class ReasonedOpinionRepository(ABC):
    """Persistence port for explainable opinions."""

    @abstractmethod
    async def save(self, opinion: ReasonedOpinion) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, symbol: str) -> ReasonedOpinion | None:
        raise NotImplementedError

    @abstractmethod
    async def list_latest(self, limit: int = 50) -> list[ReasonedOpinion]:
        raise NotImplementedError
