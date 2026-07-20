from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from datetime import datetime

from backend.modules.events.domain.entities import EventImportance
from backend.modules.events.domain.entities import EventType
from backend.modules.events.domain.entities import NewsEvent
from backend.modules.events.domain.entities import Sentiment


class NewsEventRepository(ABC):
    """Persistence contract for structured news events.

    Implemented by both an in-memory adapter (tests) and a SQL adapter
    (production) in the infrastructure layer.
    """

    @abstractmethod
    async def upsert_events(
        self,
        events: list[NewsEvent],
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def list_events(
        self,
        event_type: EventType | None = None,
        symbol: str | None = None,
        sector: str | None = None,
        sentiment: Sentiment | None = None,
        importance: EventImportance | None = None,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NewsEvent]:
        raise NotImplementedError

    @abstractmethod
    async def get_event(
        self,
        event_id: str,
    ) -> NewsEvent | None:
        raise NotImplementedError

    @abstractmethod
    async def get_stats(
        self,
    ) -> dict[str, int]:
        raise NotImplementedError
