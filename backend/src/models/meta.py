"""
SQLAlchemy models for Meta analysis data.

Maps to the meta_shifts table created in migration b7e2f3a4c5d6.
"""

from datetime import datetime
from typing import Optional, List
import enum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ShiftType(str, enum.Enum):
    """Meta shift types."""
    RISING = "rising"
    FALLING = "falling"
    EMERGING = "emerging"
    FADING = "fading"


class MetaShift(Base):
    """
    Meta shift records detected by the meta_analyzer lambda.

    Each record represents a detected meta shift for a trait:
    - rising: Rapid price increase (>15% in 24h)
    - falling: Rapid price decrease (>15% in 24h)
    - emerging: Sustained price increase (>10% over 7 days)
    - fading: Sustained price decrease (>10% over 7 days)
    """

    __tablename__ = "meta_shifts"

    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Trait identification
    trait_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    class_: Mapped[str] = mapped_column("class", String(20), nullable=False, index=True)

    # Shift classification
    shift_type: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[Optional[int]] = mapped_column(Integer)  # 0-100

    # Signal data
    signals: Mapped[Optional[List]] = mapped_column(JSON)  # Array of signal descriptions

    # Velocity metrics
    velocity_24h: Mapped[Optional[float]] = mapped_column(Float)  # Price change % in 24h
    velocity_7d: Mapped[Optional[float]] = mapped_column(Float)   # Price change % in 7d
    volume_change_24h: Mapped[Optional[float]] = mapped_column(Float)  # Volume change % in 24h

    # Timestamp
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Composite index for recent high-confidence shifts
    __table_args__ = (
        Index("idx_meta_shifts_type_confidence", "shift_type", "confidence"),
        Index("idx_meta_shifts_class_type", "class", "shift_type"),
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "trait_key": self.trait_key,
            "class": self.class_,
            "shift_type": self.shift_type,
            "confidence": self.confidence,
            "signals": self.signals or [],
            "velocity_24h": self.velocity_24h,
            "velocity_7d": self.velocity_7d,
            "volume_change_24h": self.volume_change_24h,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
        }
