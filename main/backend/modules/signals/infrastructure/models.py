from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FusedSignalModel(Base):
    __tablename__ = "fused_signals"
    __table_args__ = (
        Index("ix_fused_signals_symbol", "symbol"),
        Index("ix_fused_signals_as_of", "as_of"),
        Index("ix_fused_signals_symbol_as_of", "symbol", "as_of"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    action: Mapped[str] = mapped_column(String(8), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Component breakdown + rationale stored as JSON for full explainability.
    components: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    rationale: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
