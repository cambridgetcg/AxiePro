"""
SQLAlchemy models for wallet tracking.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Wallet(Base):
    """Tracked wallet addresses."""

    __tablename__ = "wallets"

    address: Mapped[str] = mapped_column(String(42), primary_key=True)
    alias: Mapped[Optional[str]] = mapped_column(String(100))

    # Activity tracking
    first_seen: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Aggregated trading stats
    total_buy_volume_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    total_sell_volume_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    axie_count: Mapped[int] = mapped_column(Integer, default=0)

    # Tracking flags
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_whale: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    holdings: Mapped[list["WalletHolding"]] = relationship(
        "WalletHolding",
        back_populates="wallet",
        cascade="all, delete-orphan",
    )


class WalletHolding(Base):
    """Current Axie holdings for tracked wallets."""

    __tablename__ = "wallet_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(
        String(42),
        ForeignKey("wallets.address", ondelete="CASCADE"),
        nullable=False,
    )
    axie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Acquisition data
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acquisition_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("wallet_address", "axie_id", name="uq_wallet_axie"),
        Index("idx_holdings_wallet", "wallet_address"),
        Index("idx_holdings_axie", "axie_id"),
    )
