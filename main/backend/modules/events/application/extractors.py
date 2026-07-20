from __future__ import annotations

from abc import ABC
from abc import abstractmethod

from backend.modules.events.domain.entities import NewsEvent
from backend.modules.news.domain.entities import NewsArticle


class EventExtractorContract(ABC):
    """Port for turning one article into zero or more structured events.

    This is the seam that keeps the extraction *strategy* swappable. The
    Phase 8 default is a deterministic rule-based adapter (no API key, runs
    in tests offline). A future LLM-backed adapter can implement the same
    contract with a prompt + structured-output call, and nothing in the
    service, domain, or API layers has to change.

    An article legitimately maps to zero events (not every article reports a
    financial event), so returning an empty list is expected, not an error.
    """

    @abstractmethod
    async def extract_events(
        self,
        article: NewsArticle,
    ) -> list[NewsEvent]:
        raise NotImplementedError
