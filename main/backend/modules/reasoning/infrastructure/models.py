from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ReasonedOpinionModel(Base):
    __tablename__ = "reasoned_opinions"
    __table_args__ = (
        Index("ix_reasoned_opinions_symbol", "symbol"),
        Index("ix_reasoned_opinions_as_of", "as_of"),
        Index("ix_reasoned_opinions_symbol_as_of", "symbol", "as_of"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    stance: Mapped[str] = mapped_column(String(16), nullable=False)
    headline: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    drivers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    citations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="deterministic")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
