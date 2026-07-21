from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from backend.modules.company.domain.repositories import CompanyScoreRepository
from backend.modules.events.domain.repositories import NewsEventRepository
from backend.modules.prediction.domain.repositories import PredictionRepository
from backend.modules.signals.application.dto import (
    FusedSignalsView,
    FusedSignalView,
    FuseSignalRequest,
    SignalComponentView,
)
from backend.modules.signals.domain.entities import FusedSignal, SignalComponent
from backend.modules.signals.domain.fusion import fuse
from backend.modules.signals.domain.repositories import FusedSignalRepository

logger = logging.getLogger(__name__)

_SENTIMENT_SIGN = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
_IMPORTANCE_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}

# Relative importance of each source. They need not sum to 1 — the blender
# normalizes by the weight of whichever signals are actually present.
_NEWS_WEIGHT = 0.25
_COMPANY_WEIGHT = 0.35
_PREDICTION_WEIGHT = 0.40


class SignalFusionService:
    """Phase 13 application boundary.

    Reads the *stored outputs* of the upstream layers — recent news events
    (Phase 8), the latest company scorecard (Phase 10), and the latest price
    forecast (Phase 12) — normalizes each into a [-1, 1] signal, and blends
    them into one Buy/Hold/Sell decision with an explanation.

    Run ``/company/analyze`` and ``/predictions/predict`` first for a fully
    informed signal; missing inputs are simply excluded from the blend rather
    than treated as neutral, so the decision reflects only real evidence.
    """

    def __init__(
        self,
        event_repository: NewsEventRepository,
        company_repository: CompanyScoreRepository,
        prediction_repository: PredictionRepository,
        signal_repository: FusedSignalRepository,
        commit: Callable[[], Awaitable[None]] | None = None,
    ) -> None:
        self._events = event_repository
        self._company = company_repository
        self._prediction = prediction_repository
        self._signals = signal_repository
        self._commit = commit

    async def fuse_signal(self, request: FuseSignalRequest) -> FusedSignalView:
        symbol = request.symbol.strip().upper()

        news = await self._news_component(symbol, request.event_limit)
        company = await self._company_component(symbol)
        prediction = await self._prediction_component(symbol)
        components = (news, company, prediction)

        action, score, confidence = fuse(components)

        signal = FusedSignal(
            symbol=symbol,
            as_of=datetime.now(UTC),
            action=action,
            score=score,
            confidence=confidence,
            components=components,
            rationale=self._rationale(components, action),
        )
        await self._signals.save(signal)
        if self._commit is not None:
            await self._commit()

        return self._to_view(signal)

    async def get_signal(self, symbol: str) -> FusedSignalView:
        signal = await self._signals.get_latest(symbol.strip().upper())
        if signal is None:
            raise ValueError(f"No fused signal found for '{symbol}'. Run fuse first.")
        return self._to_view(signal)

    async def list_signals(self, limit: int = 50) -> FusedSignalsView:
        limit = min(max(1, int(limit)), 200)
        signals = await self._signals.list_latest(limit=limit)
        return FusedSignalsView(
            signals=tuple(self._to_view(s) for s in signals), count=len(signals)
        )

    async def _news_component(self, symbol: str, event_limit: int) -> SignalComponent:
        try:
            events = await self._events.list_events(
                symbol=symbol, limit=min(max(1, event_limit), 200)
            )
        except Exception as exc:
            logger.warning("News signal unavailable for %s: %s", symbol, exc)
            events = []

        if not events:
            return SignalComponent("news", 0.0, _NEWS_WEIGHT, present=False, detail="no recent events")

        weights = [
            _SENTIMENT_SIGN.get(e.sentiment.value, 0.0)
            * _IMPORTANCE_WEIGHT.get(e.importance.value, 0.5)
            for e in events
        ]
        score = max(-1.0, min(1.0, sum(weights) / len(weights)))
        return SignalComponent(
            "news", score, _NEWS_WEIGHT, present=True,
            detail=f"{len(events)} recent events",
        )

    async def _company_component(self, symbol: str) -> SignalComponent:
        try:
            score_card = await self._company.get_latest(symbol)
        except Exception as exc:
            logger.warning("Company signal unavailable for %s: %s", symbol, exc)
            score_card = None

        if score_card is None:
            return SignalComponent("company", 0.0, _COMPANY_WEIGHT, present=False, detail="not scored yet")

        score = max(-1.0, min(1.0, (score_card.overall_score - 50.0) / 50.0))
        return SignalComponent(
            "company", score, _COMPANY_WEIGHT, present=True,
            detail=f"overall {score_card.overall_score:.0f} ({score_card.rating.value})",
        )

    async def _prediction_component(self, symbol: str) -> SignalComponent:
        try:
            prediction = await self._prediction.get_latest(symbol)
        except Exception as exc:
            logger.warning("Prediction signal unavailable for %s: %s", symbol, exc)
            prediction = None

        if prediction is None:
            return SignalComponent("prediction", 0.0, _PREDICTION_WEIGHT, present=False, detail="no forecast yet")

        score = max(-1.0, min(1.0, (prediction.probability_up - 0.5) * 2.0))
        return SignalComponent(
            "prediction", score, _PREDICTION_WEIGHT, present=True,
            detail=f"{prediction.direction.value} (p_up {prediction.probability_up:.2f})",
        )

    def _rationale(self, components, action) -> tuple[str, ...]:
        lines = [f"Decision: {action.value.upper()}."]
        for component in components:
            if component.present:
                lines.append(f"{component.name}: {component.score:+.2f} — {component.detail}.")
            else:
                lines.append(f"{component.name}: not available ({component.detail}).")
        return tuple(lines)

    def _to_view(self, signal: FusedSignal) -> FusedSignalView:
        return FusedSignalView(
            symbol=signal.symbol,
            as_of=signal.as_of,
            action=signal.action.value,
            score=round(signal.score, 4),
            confidence=round(signal.confidence, 4),
            components=tuple(
                SignalComponentView(
                    name=c.name,
                    score=round(c.score, 4),
                    weight=c.weight,
                    present=c.present,
                    detail=c.detail,
                )
                for c in signal.components
            ),
            rationale=signal.rationale,
        )
