from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.signals.domain.entities import (
    FusedSignal,
    SignalAction,
    SignalComponent,
)
from backend.modules.signals.domain.repositories import FusedSignalRepository
from backend.modules.signals.infrastructure.models import FusedSignalModel


class InMemoryFusedSignalRepository(FusedSignalRepository):
    """List-backed store for tests and offline development."""

    def __init__(self) -> None:
        self._signals: list[FusedSignal] = []

    async def save(self, signal: FusedSignal) -> None:
        self._signals.append(signal)

    async def get_latest(self, symbol: str) -> FusedSignal | None:
        matches = [s for s in self._signals if s.symbol == symbol]
        return max(matches, key=lambda s: s.as_of) if matches else None

    async def list_latest(self, limit: int = 50) -> list[FusedSignal]:
        latest_by_symbol: dict[str, FusedSignal] = {}
        for signal in self._signals:
            current = latest_by_symbol.get(signal.symbol)
            if current is None or signal.as_of > current.as_of:
                latest_by_symbol[signal.symbol] = signal
        ordered = sorted(latest_by_symbol.values(), key=lambda s: s.as_of, reverse=True)
        return ordered[:limit]


class SqlFusedSignalRepository(FusedSignalRepository):
    """SQLAlchemy-backed fused-signal repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, signal: FusedSignal) -> None:
        self._session.add(
            FusedSignalModel(
                symbol=signal.symbol,
                as_of=signal.as_of,
                action=signal.action.value,
                score=signal.score,
                confidence=signal.confidence,
                components=[self._component_to_dict(c) for c in signal.components],
                rationale=list(signal.rationale),
                created_at=signal.created_at,
            )
        )
        await self._session.flush()

    async def get_latest(self, symbol: str) -> FusedSignal | None:
        stmt = (
            select(FusedSignalModel)
            .where(FusedSignalModel.symbol == symbol)
            .order_by(desc(FusedSignalModel.as_of))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_latest(self, limit: int = 50) -> list[FusedSignal]:
        stmt = (
            select(FusedSignalModel)
            .order_by(desc(FusedSignalModel.as_of))
            .limit(limit * 20)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        latest_by_symbol: dict[str, FusedSignalModel] = {}
        for model in models:
            if model.symbol not in latest_by_symbol:
                latest_by_symbol[model.symbol] = model

        entities = [self._to_entity(m) for m in latest_by_symbol.values()]
        entities.sort(key=lambda s: s.as_of, reverse=True)
        return entities[:limit]

    def _component_to_dict(self, component: SignalComponent) -> dict:
        return {
            "name": component.name,
            "score": component.score,
            "weight": component.weight,
            "present": component.present,
            "detail": component.detail,
        }

    def _to_entity(self, model: FusedSignalModel) -> FusedSignal:
        components = tuple(
            SignalComponent(
                name=item.get("name", ""),
                score=float(item.get("score", 0.0)),
                weight=float(item.get("weight", 0.0)),
                present=bool(item.get("present", False)),
                detail=item.get("detail", ""),
            )
            for item in (model.components or [])
        )
        return FusedSignal(
            symbol=model.symbol,
            as_of=self._ensure_aware(model.as_of),
            action=SignalAction(model.action),
            score=model.score,
            confidence=model.confidence,
            components=components,
            rationale=tuple(model.rationale or ()),
            created_at=self._ensure_aware(model.created_at),
        )

    def _ensure_aware(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
