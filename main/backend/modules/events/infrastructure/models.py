from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class NewsEventModel(Base):
    __tablename__ = "news_events"
    __table_args__ = (
        Index("ix_news_events_event_type", "event_type"),
        Index("ix_news_events_article_id", "article_id"),
        Index("ix_news_events_event_date", "event_date"),
        Index("ix_news_events_type_event_date", "event_type", "event_date"),
    )

    event_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    article_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    sentiment: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    importance: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    headline: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    symbols: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    sectors: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    keywords: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
    )

    source: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="rule-based",
    )

    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
