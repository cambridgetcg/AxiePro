"""
SQLAlchemy models for Deals data.

Maps to the detected_deals table created in migration b7e2f3a4c5d6.
"""

from datetime import datetime
from typing import Optional, List, Any
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    Numeric,
    String,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class DealStatus(str, enum.Enum):
    """Deal status types."""
    ACTIVE = "active"
    SOLD = "sold"
    EXPIRED = "expired"


class DetectedDeal(Base):
    """
    Detected deal records from the deal_detector lambda.

    Each record represents an undervalued Axie listing:
    - Deal: 20-40% below market average (deal_score 50-79)
    - Snipe: 40%+ below market average (deal_score 80+)
    """

    __tablename__ = "detected_deals"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Axie identification
    axie_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    class_: Mapped[str] = mapped_column("class", String(20), nullable=False, index=True)

    # Pricing data
    price_eth: Mapped[float] = mapped_column(Numeric(20, 8), nullable=False)
    avg_eth: Mapped[Optional[float]] = mapped_column(Numeric(20, 8))
    discount_percent: Mapped[Optional[float]] = mapped_column(Float)

    # Deal scoring
    deal_score: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100
    is_snipe: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    # Part analysis (JSON array of part-level discounts)
    part_analysis: Mapped[Optional[List[Any]]] = mapped_column(JSON)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, sold, expired
    sold_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Composite indices (match migration indices)
    __table_args__ = (
        Index("idx_detected_deals_class_score", "class", "deal_score"),
        Index("idx_detected_deals_status_time", "status", "detected_at"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "axie_id": self.axie_id,
            "class": self.class_,
            "price_eth": float(self.price_eth) if self.price_eth else None,
            "avg_eth": float(self.avg_eth) if self.avg_eth else None,
            "discount_percent": self.discount_percent,
            "deal_score": self.deal_score,
            "is_snipe": self.is_snipe,
            "part_analysis": self.part_analysis or [],
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "status": self.status,
            "sold_at": self.sold_at.isoformat() if self.sold_at else None,
            "marketplace_url": f"https://app.axieinfinity.com/marketplace/axies/{self.axie_id}",
        }
