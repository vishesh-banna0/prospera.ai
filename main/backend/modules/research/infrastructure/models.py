from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class ResearchDocumentModel(Base):
    __tablename__ = "research_documents"
    __table_args__ = (
        Index("ix_research_documents_document_type", "document_type"),
        Index("ix_research_documents_published_at", "published_at"),
    )

    document_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    document_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
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

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    chunks = relationship(
        "DocumentChunkModel",
        back_populates="document",
        cascade="all, delete-orphan",
    )


class DocumentChunkModel(Base):
    __tablename__ = "research_chunks"
    __table_args__ = (
        Index("ix_research_chunks_document_id", "document_id"),
        Index("ix_research_chunks_document_type", "document_type"),
    )

    chunk_id: Mapped[str] = mapped_column(
        String(80),
        primary_key=True,
    )

    document_id: Mapped[str] = mapped_column(
        ForeignKey("research_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    document_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    document_title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    document = relationship(
        "ResearchDocumentModel",
        back_populates="chunks",
    )
