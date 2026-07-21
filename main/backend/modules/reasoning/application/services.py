from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from backend.modules.company.domain.repositories import CompanyScoreRepository
from backend.modules.events.domain.repositories import NewsEventRepository
from backend.modules.reasoning.application.dto import (
    AnalyzeReasoningRequest,
    ReasonedOpinionsView,
    ReasonedOpinionView,
)
from backend.modules.reasoning.application.reasoners import (
    ReasonerContract,
    ReasoningInputs,
)
from backend.modules.reasoning.domain.entities import ReasonedOpinion, Stance
from backend.modules.reasoning.domain.repositories import ReasonedOpinionRepository
from backend.modules.research.application.dto import ResearchQueryRequest
from backend.modules.signals.domain.repositories import FusedSignalRepository

logger = logging.getLogger(__name__)


class ReasoningService:
    """Phase 11 application boundary.

    Gathers the fused signal (Phase 13), company scorecard (Phase 10), recent
    events (Phase 8), and research context (Phase 9), hands them to a pluggable
    reasoner, and stores the resulting explainable opinion. The reasoner does no
    I/O, so the whole engine is testable offline; an LLM reasoner is a drop-in.
    """

    def __init__(
        self,
        signal_repository: FusedSignalRepository,
        company_repository: CompanyScoreRepository,
        event_repository: NewsEventRepository,
        opinion_repository: ReasonedOpinionRepository,
        reasoner: ReasonerContract,
        research_service=None,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._signals = signal_repository
        self._company = company_repository
        self._events = event_repository
        self._opinions = opinion_repository
        self._reasoner = reasoner
        self._research = research_service
        self._commit = commit

    async def analyze(self, request: AnalyzeReasoningRequest) -> ReasonedOpinionView:
        symbol = request.symbol.strip().upper()
        inputs = await self._gather_inputs(symbol, request)

        result = await self._reasoner.reason(inputs)

        opinion = ReasonedOpinion(
            symbol=symbol,
            as_of=datetime.now(UTC),
            stance=result.stance,
            headline=result.headline,
            explanation=result.explanation,
            confidence=result.confidence,
            drivers=result.drivers,
            citations=inputs.research_snippets,
            source=self._reasoner.name,
        )
        await self._opinions.save(opinion)
        if self._commit is not None:
            await self._commit()

        return self._to_view(opinion)

    async def get_opinion(self, symbol: str) -> ReasonedOpinionView:
        opinion = await self._opinions.get_latest(symbol.strip().upper())
        if opinion is None:
            raise ValueError(f"No reasoning found for '{symbol}'. Run analyze first.")
        return self._to_view(opinion)

    async def list_opinions(self, limit: int = 50) -> ReasonedOpinionsView:
        limit = min(max(1, int(limit)), 200)
        opinions = await self._opinions.list_latest(limit=limit)
        return ReasonedOpinionsView(
            opinions=tuple(self._to_view(o) for o in opinions), count=len(opinions)
        )

    async def _gather_inputs(
        self, symbol: str, request: AnalyzeReasoningRequest
    ) -> ReasoningInputs:
        fused = await self._safe(self._signals.get_latest(symbol), "fused signal", symbol)
        company = await self._safe(self._company.get_latest(symbol), "company score", symbol)
        events = await self._safe(
            self._events.list_events(symbol=symbol, limit=request.event_limit),
            "events",
            symbol,
            default=[],
        )

        event_summaries = tuple(
            f"{e.event_type.value} ({e.sentiment.value}, {e.importance.value})"
            for e in (events or [])
        )
        signal_drivers = (
            tuple(f"{c.name}: {c.detail}" for c in fused.components if c.present)
            if fused
            else ()
        )
        research_snippets = await self._research_snippets(
            symbol,
            company.company_name if company else None,
            request.research_top_k,
        )

        return ReasoningInputs(
            symbol=symbol,
            company_name=company.company_name if company else None,
            fused_action=fused.action.value if fused else None,
            fused_score=fused.score if fused else None,
            fused_confidence=fused.confidence if fused else None,
            company_overall=company.overall_score if company else None,
            company_rating=company.rating.value if company else None,
            signal_drivers=signal_drivers,
            event_summaries=event_summaries,
            research_snippets=research_snippets,
        )

    async def _research_snippets(
        self, symbol: str, company_name: str | None, top_k: int
    ) -> tuple[str, ...]:
        if self._research is None:
            return ()
        query = company_name or symbol
        try:
            context = await self._research.search(
                ResearchQueryRequest(query=query, top_k=top_k, symbol=symbol)
            )
        except Exception as exc:
            logger.warning("Research context unavailable for %s: %s", symbol, exc)
            return ()
        return tuple(chunk.text[:280] for chunk in context.results)

    async def _safe(self, awaitable, label: str, symbol: str, default=None):
        try:
            return await awaitable
        except Exception as exc:
            logger.warning("%s unavailable for %s: %s", label, symbol, exc)
            return default

    def _to_view(self, opinion: ReasonedOpinion) -> ReasonedOpinionView:
        return ReasonedOpinionView(
            symbol=opinion.symbol,
            as_of=opinion.as_of,
            stance=opinion.stance.value,
            headline=opinion.headline,
            explanation=opinion.explanation,
            confidence=round(opinion.confidence, 4),
            drivers=opinion.drivers,
            citations=opinion.citations,
            source=opinion.source,
        )

    @staticmethod
    def stance_from_action(action: str | None) -> Stance:
        return {
            "buy": Stance.BULLISH,
            "sell": Stance.BEARISH,
            "hold": Stance.NEUTRAL,
        }.get(action or "", Stance.NEUTRAL)
