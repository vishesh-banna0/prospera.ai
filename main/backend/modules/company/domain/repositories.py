from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modules.company.domain.entities import CompanyScore


class CompanyScoreRepository(ABC):
    """Persistence port for company scorecards.

    Latest-score-per-symbol is the common read, so ``get_latest`` is a
    first-class method rather than a filtered list call.
    """

    @abstractmethod
    async def save(self, score: CompanyScore) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, symbol: str) -> CompanyScore | None:
        raise NotImplementedError

    @abstractmethod
    async def list_latest(self, limit: int = 50) -> list[CompanyScore]:
        raise NotImplementedError
