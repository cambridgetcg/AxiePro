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
    SmallInteger,
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
        ForeignKey("axie.axies.id", ondelete="CASCADE"),
        nullable=False,
    )
    seller_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)

    # Pricing
    price_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))

    # Axie info (stored directly to avoid joins)
    class_: Mapped[Optional[str]] = mapped_column("class_", String(20), index=True)
    breed_count: Mapped[Optional[int]] = mapped_column(SmallInteger, default=0)

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
        Index("idx_listings_class_status_price", "class_", "status", "price_eth"),
        {"schema": "axie"},
    )


class Sale(Base):
    """
    Historical sales records from Lambda ingestion.

    Maps to axie.axie_sales table populated by sales_ingestion Lambda.
    """

    __tablename__ = "axie_sales"
    __table_args__ = (
        Index("idx_axie_sales_axie", "axie_id"),
        Index("idx_axie_sales_timestamp", "block_timestamp"),
        Index("idx_axie_sales_seller", "seller"),
        Index("idx_axie_sales_buyer", "buyer"),
        {"schema": "axie"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    axie_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    block_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Pricing
    price_token: Mapped[Decimal] = mapped_column(Numeric(36, 18), nullable=False)
    token_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'ETH' or 'RON'
    price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    eth_usd_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 2))
    ron_usd_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    # Participants
    seller: Mapped[str] = mapped_column(String(42), nullable=False)
    buyer: Mapped[str] = mapped_column(String(42), nullable=False)

    # Axie metadata (denormalized for performance)
    class_: Mapped[Optional[str]] = mapped_column("class", String(20))
    breed_count: Mapped[Optional[int]] = mapped_column(SmallInteger)
    price_raw: Mapped[Optional[str]] = mapped_column(String(78))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Compatibility properties for existing code
    @property
    def price_eth(self) -> Decimal:
        """Return price in ETH equivalent."""
        if self.token_type == 'ETH':
            return self.price_token
        elif self.token_type == 'RON' and self.ron_usd_rate and self.eth_usd_rate:
            # Convert RON to ETH: RON * RON_USD / ETH_USD
            return self.price_token * self.ron_usd_rate / self.eth_usd_rate
        return self.price_token  # Fallback

    @property
    def sold_at(self) -> datetime:
        """Alias for block_timestamp for compatibility."""
        return self.block_timestamp

    @property
    def seller_address(self) -> str:
        """Alias for seller for compatibility."""
        return self.seller

    @property
    def buyer_address(self) -> str:
        """Alias for buyer for compatibility."""
        return self.buyer

    @property
    def marketplace(self) -> str:
        """Default marketplace."""
        return "official"


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


class PriceSnapshot(Base):
    """
    Time-series price snapshots captured by the price_ingestion lambda.

    This maps to the partitioned price_snapshots table which stores
    floor prices and statistics every 5 minutes.

    Table is partitioned by month for efficient time-range queries.
    """

    __tablename__ = "price_snapshots"
    __table_args__ = {"schema": "axie"}

    # Composite primary key for time-series
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    trait_key: Mapped[str] = mapped_column(Text, primary_key=True)
    class_: Mapped[str] = mapped_column("class", Text, primary_key=True)

    # Price metrics
    floor_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    avg_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    # Volume and count metrics
    volume: Mapped[int] = mapped_column(Integer, default=0)
    listings_count: Mapped[int] = mapped_column(Integer, default=0)


class MarketStats(Base):
    """
    Pre-aggregated market statistics for different time periods.

    Computed periodically by the market_aggregator service and cached
    for fast API responses.
    """

    __tablename__ = "market_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Time period: 1h, 24h, 7d, 30d
    period: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Optional class filter (null = all classes)
    class_: Mapped[Optional[str]] = mapped_column("class", String(20), index=True)

    # Volume metrics
    volume_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)

    # Price metrics
    avg_price_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    median_price_eth: Mapped[Decimal] = mapped_column(Numeric(20, 8), default=0)
    floor_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    max_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    # Participant metrics
    unique_buyers: Mapped[int] = mapped_column(Integer, default=0)
    unique_sellers: Mapped[int] = mapped_column(Integer, default=0)

    # Listing metrics
    active_listings: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        index=True
    )

    __table_args__ = (
        UniqueConstraint("period", "class", name="uq_market_stats_period_class"),
        Index("idx_market_stats_period_computed", "period", "computed_at"),
    )
