from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CompanyScoreModel(Base):
    __tablename__ = "company_scores"
    __table_args__ = (
        Index("ix_company_scores_symbol", "symbol"),
        Index("ix_company_scores_as_of", "as_of"),
        Index("ix_company_scores_symbol_as_of", "symbol", "as_of"),
    )

    # (symbol, as_of) identifies a scorecard; a surrogate id keeps history so
    # a company can be re-scored over time without overwriting past snapshots.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    growth_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)

    rating: Mapped[str] = mapped_column(String(16), nullable=False)

    company_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)
    market_cap: Mapped[str | None] = mapped_column(String(64), nullable=True)

    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rationale: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="heuristic-v1")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
