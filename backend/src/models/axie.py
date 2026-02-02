"""
SQLAlchemy models for Axie data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
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

# Note: Removed TYPE_CHECKING imports for Listing and Sale
# The listings relationship was removed since axie.axies table doesn't exist in production


class AxieClass(str, enum.Enum):
    """Axie class types."""
    BEAST = "beast"
    BUG = "bug"
    BIRD = "bird"
    PLANT = "plant"
    AQUATIC = "aquatic"
    REPTILE = "reptile"
    MECH = "mech"
    DAWN = "dawn"
    DUSK = "dusk"


class PartType(str, enum.Enum):
    """Body part types."""
    EYES = "eyes"
    EARS = "ears"
    MOUTH = "mouth"
    HORN = "horn"
    BACK = "back"
    TAIL = "tail"


class GeneType(str, enum.Enum):
    """Gene inheritance types."""
    D = "d"       # Dominant
    R1 = "r1"     # Recessive 1
    R2 = "r2"     # Recessive 2


class Axie(Base):
    """Main Axies table."""

    __tablename__ = "axies"

    # Primary key - uses the Axie NFT ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # Basic info
    name: Mapped[Optional[str]] = mapped_column(String(255))
    class_: Mapped[AxieClass] = mapped_column(
        "class",
        SQLEnum(AxieClass, name="axie_class"),
        nullable=False,
    )
    breed_count: Mapped[int] = mapped_column(SmallInteger, default=0)
    genes: Mapped[str] = mapped_column(String(128), nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(Text)
    owner_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)

    # Timestamps
    birth_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Parent references (self-referential)
    matron_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("axie.axies.id", ondelete="SET NULL"),
    )
    sire_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("axie.axies.id", ondelete="SET NULL"),
    )

    # Precomputed purity scores
    purity_score: Mapped[Optional[int]] = mapped_column(SmallInteger)  # 0-6
    gene_purity_score: Mapped[Optional[int]] = mapped_column(SmallInteger)  # 0-18

    # Stats
    hp: Mapped[Optional[int]] = mapped_column(SmallInteger)
    speed: Mapped[Optional[int]] = mapped_column(SmallInteger)
    skill: Mapped[Optional[int]] = mapped_column(SmallInteger)
    morale: Mapped[Optional[int]] = mapped_column(SmallInteger)

    # Relationships
    # Note: Part/AxiePart tables not created - parts stored in denormalized parts_json column
    matron: Mapped[Optional["Axie"]] = relationship(
        "Axie",
        foreign_keys=[matron_id],
        remote_side=[id],
    )
    sire: Mapped[Optional["Axie"]] = relationship(
        "Axie",
        foreign_keys=[sire_id],
        remote_side=[id],
    )
    # Note: Listings relationship removed - axie.listings table doesn't exist in production
    # Note: Sales relationship removed - Sale model uses denormalized axie.axie_sales table

    # Indexes and schema
    __table_args__ = (
        Index("idx_axies_class", "class"),
        Index("idx_axies_purity", purity_score),
        Index("idx_axies_breed_count", breed_count),
        Index("idx_axies_class_purity", "class", purity_score),
        {"schema": "axie"},
    )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "class": self.class_.value if self.class_ else None,
            "breed_count": self.breed_count,
            "genes": self.genes,
            "image_url": self.image_url,
            "owner": self.owner_address,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "matron_id": self.matron_id,
            "sire_id": self.sire_id,
            "purity_score": self.purity_score,
            "gene_purity_score": self.gene_purity_score,
            "stats": {
                "hp": self.hp,
                "speed": self.speed,
                "skill": self.skill,
                "morale": self.morale,
            },
        }


class Part(Base):
    """Reference table for all body parts."""

    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_: Mapped[AxieClass] = mapped_column(
        "class",
        SQLEnum(AxieClass, name="axie_class"),
        nullable=False,
    )
    type: Mapped[PartType] = mapped_column(
        SQLEnum(PartType, name="part_type"),
        nullable=False,
    )
    # Note: abilities table does not exist in production - FK disabled
    ability_id: Mapped[Optional[int]] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Note: Relationships disabled - tables don't exist in production
    # ability: Mapped[Optional["Ability"]] = relationship("Ability", back_populates="parts")
    # axie_parts: Mapped[list["AxiePart"]] = relationship("AxiePart", back_populates="part")

    __table_args__ = (
        Index("idx_parts_class", "class"),
        Index("idx_parts_type", "type"),
    )


class AxiePart(Base):
    """Junction table linking Axies to their parts (6 parts × 3 genes each)."""

    __tablename__ = "axie_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Note: These tables do not exist in production (parts denormalized in axies.parts_json)
    # FK references disabled to prevent import errors
    axie_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    part_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[PartType] = mapped_column(
        SQLEnum(PartType, name="part_type"),
        nullable=False,
    )
    gene_type: Mapped[GeneType] = mapped_column(
        SQLEnum(GeneType, name="gene_type"),
        nullable=False,
    )

    # Note: Relationships disabled - tables don't exist in production
    # axie: Mapped["Axie"] = relationship("Axie", back_populates="parts")
    # part: Mapped["Part"] = relationship("Part", back_populates="axie_parts")

    __table_args__ = (
        UniqueConstraint("axie_id", "position", "gene_type", name="uq_axie_position_gene"),
        Index("idx_axie_parts_axie", "axie_id"),
        Index("idx_axie_parts_part", "part_id"),
        Index("idx_axie_parts_gene_type", "gene_type"),
    )


class Ability(Base):
    """Abilities/cards for body parts."""

    __tablename__ = "abilities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ability_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_: Mapped[Optional[AxieClass]] = mapped_column(
        "class",
        SQLEnum(AxieClass, name="axie_class"),
    )
    type: Mapped[Optional[PartType]] = mapped_column(
        SQLEnum(PartType, name="part_type"),
    )
    energy_cost: Mapped[int] = mapped_column(SmallInteger, default=1)
    damage: Mapped[int] = mapped_column(SmallInteger, default=0)
    shield: Mapped[int] = mapped_column(SmallInteger, default=0)
    heal: Mapped[int] = mapped_column(SmallInteger, default=0)
    description: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Note: Relationship disabled - tables don't exist in production
    # parts: Mapped[list["Part"]] = relationship("Part", back_populates="ability")
