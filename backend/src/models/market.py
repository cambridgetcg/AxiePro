"""
SQLAlchemy models for market data (listings, sales, prices).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .axie import AxieClass

if TYPE_CHECKING:
    from .axie import Axie


class Listing(Base):
    """Active marketplace listings."""

    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    axie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)

    # Pricing
    price_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Timestamps
    listed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Status: active, sold, cancelled
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    axie: Mapped["Axie"] = relationship("Axie", back_populates="listings")

    __table_args__ = (
        Index("idx_listings_axie", "axie_id"),
        Index("idx_listings_price", "price_eth"),
        Index("idx_listings_status_price", "status", "price_eth"),
    )


class Sale(Base):
    """Historical sales records."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    axie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="SET NULL"),
    )
    seller_address: Mapped[str] = mapped_column(String(42), nullable=False)
    buyer_address: Mapped[str] = mapped_column(String(42), nullable=False)

    # Pricing
    price_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Transaction data
    tx_hash: Mapped[str] = mapped_column(String(66), unique=True, nullable=False)
    sold_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    marketplace: Mapped[str] = mapped_column(String(50), default="official")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    axie: Mapped[Optional["Axie"]] = relationship("Axie", back_populates="sales")

    __table_args__ = (
        Index("idx_sales_axie", "axie_id"),
        Index("idx_sales_sold_at", "sold_at"),
        Index("idx_sales_seller", "seller_address"),
        Index("idx_sales_buyer", "buyer_address"),
        Index("idx_sales_price", "price_eth"),
    )


class PriceHistory(Base):
    """
    Time-series price history for traits.

    Note: In production with TimescaleDB, this would be a hypertable.
    The table structure is designed for TimescaleDB but works with regular PostgreSQL.
    """

    __tablename__ = "price_history"

    # Composite primary key for time-series
    time: Mapped[datetime] = mapped_column(DateTime, primary_key=True)
    class_: Mapped[Optional[str]] = mapped_column("class", String(20), primary_key=True)
    trait_key: Mapped[str] = mapped_column(String(100), primary_key=True)

    # Price metrics
    floor_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    avg_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    median_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    max_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    # Volume metrics
    volume: Mapped[int] = mapped_column(Integer, default=0)
    volume_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)

    __table_args__ = (
        Index("idx_price_history_time", "time"),
        Index("idx_price_history_class", "class"),
        Index("idx_price_history_trait", "trait_key"),
    )
