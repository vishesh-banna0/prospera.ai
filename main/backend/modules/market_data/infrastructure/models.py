from __future__ import annotations

from datetime import date
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger
from sqlalchemy import Boolean
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class MarketInstrumentModel(Base):
    __tablename__ = "market_instruments"

    symbol: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )

    instrument_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    exchange: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    native_currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )

    asset_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="stock",
    )

    isin: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    sector: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    industry: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    provider_symbol: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    price_bars = relationship(
        "HistoricalPriceModel",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )


class HistoricalPriceModel(Base):
    __tablename__ = "historical_price_bars"
    __table_args__ = (
        UniqueConstraint(
            "symbol",
            "price_date",
            name="uq_historical_price_bars_symbol_price_date",
        ),
        Index("ix_historical_price_bars_symbol_price_date", "symbol", "price_date"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    symbol: Mapped[str] = mapped_column(
        ForeignKey("market_instruments.symbol"),
        nullable=False,
        index=True,
    )

    price_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    open_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    high_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    low_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    close_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    adjusted_close_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    volume: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    split_coefficient: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )

    dividend_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    instrument = relationship(
        "MarketInstrumentModel",
        back_populates="price_bars",
    )


class CompanyProfileModel(Base):
    __tablename__ = "company_profiles"

    symbol: Mapped[str] = mapped_column(
        ForeignKey("market_instruments.symbol"),
        primary_key=True,
    )

    instrument_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    native_currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
    )

    exchange: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    asset_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    sector: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    industry: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        index=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    market_cap: Mapped[Decimal | None] = mapped_column(
        Numeric(24, 2),
        nullable=True,
    )

    employees: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
