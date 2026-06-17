from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
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
