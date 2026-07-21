from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PredictionModel(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_symbol", "symbol"),
        Index("ix_predictions_as_of", "as_of"),
        Index("ix_predictions_symbol_as_of", "symbol", "as_of"),
    )

    prediction_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)

    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    probability_up: Mapped[float] = mapped_column(Float, nullable=False)
    expected_return_pct: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
