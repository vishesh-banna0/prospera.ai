from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.company.domain.entities import CompanyRating, CompanyScore
from backend.modules.company.infrastructure.repositories import (
    InMemoryCompanyScoreRepository,
)
from backend.modules.events.infrastructure.repositories import (
    InMemoryNewsEventRepository,
)
from backend.modules.reasoning.application.dto import AnalyzeReasoningRequest
from backend.modules.reasoning.application.reasoners import ReasoningInputs
from backend.modules.reasoning.application.services import ReasoningService
from backend.modules.reasoning.domain.entities import Stance
from backend.modules.reasoning.infrastructure.reasoners import (
    DeterministicReasoner,
    LLMReasoner,
)
from backend.modules.reasoning.infrastructure.repositories import (
    InMemoryReasonedOpinionRepository,
)
from backend.modules.signals.domain.entities import (
    FusedSignal,
    SignalAction,
    SignalComponent,
)
from backend.modules.signals.infrastructure.repositories import (
    InMemoryFusedSignalRepository,
)
from backend.shared.llm import LLMClient


class FakeLLM(LLMClient):
    def __init__(self, response: str | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def complete(self, system, user, temperature=0.0, max_tokens=None) -> str:
        if self._error is not None:
            raise self._error
        return self._response or ""


def _inputs(action: str = "buy") -> ReasoningInputs:
    return ReasoningInputs(
        symbol="AAA",
        company_name="AAA Inc.",
        fused_action=action,
        fused_score=0.5,
        fused_confidence=0.6,
        company_overall=80.0,
        company_rating="strong",
        signal_drivers=("prediction: up (p_up 0.80)",),
        event_summaries=("earnings_beat (positive, high)",),
        research_snippets=("Record revenue growth in the latest quarter.",),
    )


@pytest.mark.asyncio
async def test_deterministic_reasoner_maps_action_to_stance() -> None:
    reasoner = DeterministicReasoner()
    bullish = await reasoner.reason(_inputs("buy"))
    bearish = await reasoner.reason(_inputs("sell"))
    neutral = await reasoner.reason(_inputs("hold"))

    assert bullish.stance == Stance.BULLISH
    assert bearish.stance == Stance.BEARISH
    assert neutral.stance == Stance.NEUTRAL
    assert "AAA" in bullish.headline
    assert bullish.explanation  # a non-empty explanation was produced
    assert bullish.confidence == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_llm_reasoner_parses_and_falls_back() -> None:
    good = FakeLLM(
        response=(
            '{"stance": "bearish", "headline": "Caution on AAA", '
            '"explanation": "Momentum has weakened.", "drivers": ["weak momentum"]}'
        )
    )
    result = await LLMReasoner(good).reason(_inputs("buy"))
    assert result.stance == Stance.BEARISH
    assert result.explanation == "Momentum has weakened."
    # Confidence comes from the fused signal, not the model.
    assert result.confidence == pytest.approx(0.6)

    broken = FakeLLM(error=RuntimeError("connection refused"))
    fallback = await LLMReasoner(broken).reason(_inputs("buy"))
    assert fallback.stance == Stance.BULLISH  # deterministic fallback used


@pytest.mark.asyncio
async def test_reasoning_service_pipeline() -> None:
    signals = InMemoryFusedSignalRepository()
    await signals.save(
        FusedSignal(
            symbol="AAA",
            as_of=datetime(2026, 6, 3, tzinfo=UTC),
            action=SignalAction.BUY,
            score=0.5,
            confidence=0.6,
            components=(SignalComponent("prediction", 0.7, 0.4, present=True, detail="up"),),
        )
    )
    company = InMemoryCompanyScoreRepository()
    await company.save(
        CompanyScore(
            symbol="AAA",
            as_of=datetime(2026, 6, 2, tzinfo=UTC),
            overall_score=80.0,
            growth_score=80.0,
            risk_score=20.0,
            sentiment_score=70.0,
            rating=CompanyRating.STRONG,
            company_name="AAA Inc.",
        )
    )

    service = ReasoningService(
        signal_repository=signals,
        company_repository=company,
        event_repository=InMemoryNewsEventRepository(),
        opinion_repository=InMemoryReasonedOpinionRepository(),
        reasoner=DeterministicReasoner(),
        research_service=None,
    )

    view = await service.analyze(AnalyzeReasoningRequest(symbol="aaa"))
    assert view.symbol == "AAA"
    assert view.stance == Stance.BULLISH.value
    assert "80" in view.explanation  # references the company score
    assert view.source == "deterministic"

    fetched = await service.get_opinion("AAA")
    assert fetched.stance == view.stance

    listing = await service.list_opinions()
    assert listing.count == 1


@pytest.mark.asyncio
async def test_reasoning_service_neutral_without_signals() -> None:
    service = ReasoningService(
        signal_repository=InMemoryFusedSignalRepository(),
        company_repository=InMemoryCompanyScoreRepository(),
        event_repository=InMemoryNewsEventRepository(),
        opinion_repository=InMemoryReasonedOpinionRepository(),
        reasoner=DeterministicReasoner(),
    )
    view = await service.analyze(AnalyzeReasoningRequest(symbol="ZZZ"))
    assert view.stance == Stance.NEUTRAL.value
