from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.modules.company.domain.entities import CompanyRating, CompanyScore
from backend.modules.company.infrastructure.repositories import (
    InMemoryCompanyScoreRepository,
)
from backend.modules.events.domain.entities import (
    EventImportance,
    EventType,
    NewsEvent,
    Sentiment,
)
from backend.modules.events.infrastructure.repositories import (
    InMemoryNewsEventRepository,
)
from backend.modules.prediction.domain.entities import Prediction, PredictionDirection
from backend.modules.prediction.infrastructure.repositories import (
    InMemoryPredictionRepository,
)
from backend.modules.signals.application.dto import FuseSignalRequest
from backend.modules.signals.application.services import SignalFusionService
from backend.modules.signals.domain.entities import SignalAction, SignalComponent
from backend.modules.signals.domain.fusion import action_for, blend, fuse
from backend.modules.signals.infrastructure.repositories import (
    InMemoryFusedSignalRepository,
)


# ---- pure fusion math ------------------------------------------------------


def test_action_thresholds() -> None:
    assert action_for(0.5) == SignalAction.BUY
    assert action_for(-0.5) == SignalAction.SELL
    assert action_for(0.05) == SignalAction.HOLD


def test_blend_excludes_absent_components() -> None:
    present = SignalComponent("a", 0.8, 0.5, present=True)
    absent = SignalComponent("b", 0.0, 0.5, present=False)
    score, confidence = blend([present, absent])
    # Only the present component counts, but coverage < 1 tempers confidence.
    assert score == pytest.approx(0.8)
    assert 0.0 < confidence < 0.8


def test_fuse_all_bullish() -> None:
    comps = [
        SignalComponent("news", 0.6, 0.25, present=True),
        SignalComponent("company", 0.5, 0.35, present=True),
        SignalComponent("prediction", 0.7, 0.40, present=True),
    ]
    action, score, confidence = fuse(comps)
    assert action == SignalAction.BUY
    assert score > 0.2
    assert confidence > 0.0


# ---- service pipeline (real in-memory upstream repos) ----------------------


async def _seed_upstream():
    events = InMemoryNewsEventRepository()
    await events.upsert_events(
        [
            NewsEvent(
                event_id="e1",
                article_id="a1",
                event_type=EventType.EARNINGS_BEAT,
                sentiment=Sentiment.POSITIVE,
                importance=EventImportance.HIGH,
                headline="AAA beats",
                event_date=datetime(2026, 6, 1, tzinfo=UTC),
                symbols=("AAA",),
            )
        ]
    )
    company = InMemoryCompanyScoreRepository()
    await company.save(
        CompanyScore(
            symbol="AAA",
            as_of=datetime(2026, 6, 2, tzinfo=UTC),
            overall_score=80.0,
            growth_score=80.0,
            risk_score=20.0,
            sentiment_score=75.0,
            rating=CompanyRating.STRONG,
        )
    )
    predictions = InMemoryPredictionRepository()
    await predictions.save(
        Prediction(
            prediction_id="p1",
            symbol="AAA",
            as_of=datetime(2026, 6, 3, tzinfo=UTC),
            horizon_days=1,
            direction=PredictionDirection.UP,
            probability_up=0.8,
            expected_return_pct=1.2,
            confidence=0.6,
            model_name="logistic-baseline-v1",
        )
    )
    return events, company, predictions


@pytest.mark.asyncio
async def test_fusion_service_produces_buy_from_bullish_inputs() -> None:
    events, company, predictions = await _seed_upstream()
    service = SignalFusionService(
        event_repository=events,
        company_repository=company,
        prediction_repository=predictions,
        signal_repository=InMemoryFusedSignalRepository(),
    )

    view = await service.fuse_signal(FuseSignalRequest(symbol="aaa"))
    assert view.symbol == "AAA"
    assert view.action == SignalAction.BUY.value
    assert view.score > 0.2
    assert all(c.present for c in view.components)  # all three sources present

    fetched = await service.get_signal("AAA")
    assert fetched.action == view.action

    listing = await service.list_signals()
    assert listing.count == 1


@pytest.mark.asyncio
async def test_fusion_service_holds_when_no_signals_present() -> None:
    service = SignalFusionService(
        event_repository=InMemoryNewsEventRepository(),
        company_repository=InMemoryCompanyScoreRepository(),
        prediction_repository=InMemoryPredictionRepository(),
        signal_repository=InMemoryFusedSignalRepository(),
    )
    view = await service.fuse_signal(FuseSignalRequest(symbol="ZZZ"))
    assert view.action == SignalAction.HOLD.value
    assert view.confidence == pytest.approx(0.0)
    assert all(not c.present for c in view.components)
