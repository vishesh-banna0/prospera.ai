from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean
from sqlalchemy import Date
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class EnvironmentModel(Base):
    __tablename__ = "environments"

    environment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    owner_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
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

    holdings = relationship(
        "HoldingModel",
        back_populates="environment",
        cascade="all, delete-orphan",
    )

    transactions = relationship(
        "TransactionModel",
        back_populates="environment",
        cascade="all, delete-orphan",
    )

    sip_plans = relationship(
        "SipPlanModel",
        back_populates="environment",
        cascade="all, delete-orphan",
    )


class HoldingModel(Base):
    __tablename__ = "holdings"

    holding_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.environment_id"),
        nullable=False,
    )

    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    environment = relationship(
        "EnvironmentModel",
        back_populates="holdings",
    )


class TransactionModel(Base):
    __tablename__ = "transactions"

    transaction_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.environment_id"),
        nullable=False,
    )

    transaction_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    symbol: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
    )

    executed_price: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 2),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    environment = relationship(
        "EnvironmentModel",
        back_populates="transactions",
    )


class SipPlanModel(Base):
    __tablename__ = "sip_plans"

    plan_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.environment_id"),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    symbol_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="INR",
    )

    frequency: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="monthly",
    )

    day_of_month: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    next_run_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
    )

    installments_run: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    installments_skipped: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    environment = relationship(
        "EnvironmentModel",
        back_populates="sip_plans",
    )


class PortfolioSnapshotModel(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    environment_id: Mapped[str] = mapped_column(
        ForeignKey("environments.environment_id"),
        nullable=False,
        index=True,
    )

    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    portfolio_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    total_value: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    unrealized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
    )

# Purpose:
# Placeholder module for simulator persistence models.
#
# Future Responsibilities:
# - Define storage representations for environments, holdings, and transactions.
# - Preserve environment isolation at the schema level.
# - Support future performance snapshots if required.
#
# Dependencies:
# - Database toolkit selected by the project, such as SQLAlchemy.
#
# Future Classes:
# - EnvironmentModel
# - HoldingModel
# - TransactionModel
# - PortfolioSnapshotModel
#
# What Should Not Live Here:
# - Business invariants.
# - Route schemas.
# - Market data provider mappings.
