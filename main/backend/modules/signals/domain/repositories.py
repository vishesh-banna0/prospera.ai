from __future__ import annotations

from abc import ABC, abstractmethod

from backend.modules.signals.domain.entities import FusedSignal


class FusedSignalRepository(ABC):
    """Persistence port for fused Buy/Hold/Sell signals."""

    @abstractmethod
    async def save(self, signal: FusedSignal) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, symbol: str) -> FusedSignal | None:
        raise NotImplementedError

    @abstractmethod
    async def list_latest(self, limit: int = 50) -> list[FusedSignal]:
        raise NotImplementedError
