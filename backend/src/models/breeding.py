"""
SQLAlchemy models for breeding data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
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


class BreedingPair(Base):
    """Tracks breeding pairs and their history."""

    __tablename__ = "breeding_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    matron_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="CASCADE"),
        nullable=False,
    )
    sire_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Breeding stats
    breed_count: Mapped[int] = mapped_column(Integer, default=0)
    last_breed: Mapped[Optional[datetime]] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    breeds: Mapped[list["Breed"]] = relationship(
        "Breed",
        back_populates="pair",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("matron_id", "sire_id", name="uq_breeding_pair"),
        Index("idx_breeding_pairs_matron", "matron_id"),
        Index("idx_breeding_pairs_sire", "sire_id"),
    )


class Breed(Base):
    """Individual breeding events."""

    __tablename__ = "breeds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pair_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("breeding_pairs.id", ondelete="CASCADE"),
        nullable=False,
    )
    offspring_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axies.id", ondelete="SET NULL"),
    )

    # Transaction data
    tx_hash: Mapped[str] = mapped_column(String(66), unique=True, nullable=False)
    breed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Breeding costs
    breed_cost_slp: Mapped[Optional[int]] = mapped_column(Integer)
    breed_cost_axs: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    pair: Mapped["BreedingPair"] = relationship("BreedingPair", back_populates="breeds")

    __table_args__ = (
        Index("idx_breeds_pair", "pair_id"),
        Index("idx_breeds_offspring", "offspring_id"),
        Index("idx_breeds_date", "breed_at"),
    )
