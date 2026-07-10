from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Index
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class NewsArticleModel(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("url", name="uq_news_articles_url"),
        Index("ix_news_articles_category_published_at", "category", "published_at"),
        Index("ix_news_articles_content_hash", "content_hash"),
    )

    article_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    external_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    body: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    category: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
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

    countries: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    keywords: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
