"""
SQLAlchemy models for wallet tracking.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
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
    __table_args__ = {"schema": "axie"}

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
    token_balances: Mapped[list["WalletTokenBalance"]] = relationship(
        "WalletTokenBalance",
        back_populates="wallet",
        cascade="all, delete-orphan",
    )


class WalletHolding(Base):
    """Current Axie holdings for tracked wallets."""

    __tablename__ = "wallet_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(
        String(42),
        ForeignKey("axie.wallets.address", ondelete="CASCADE"),
        nullable=False,
    )
    axie_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("axie.axies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Acquisition data (cost basis)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acquisition_price_eth: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 8))
    acquisition_type: Mapped[Optional[str]] = mapped_column(
        String(20), default="unknown"
    )  # purchase, breeding, gift, transfer, airdrop

    # Cost basis tracking
    cost_basis_eth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), comment="Adjusted cost basis (may include breeding costs)"
    )
    cost_basis_method: Mapped[str] = mapped_column(
        String(10), default="fifo"
    )  # fifo, avg, lifo

    # P&L tracking
    current_value_eth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), comment="Cached hedonic valuation"
    )
    last_valued_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment="When current_value_eth was last computed"
    )
    unrealized_pnl_eth: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8), comment="current_value - cost_basis"
    )
    unrealized_pnl_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), comment="(current_value - cost_basis) / cost_basis * 100"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="holdings")

    __table_args__ = (
        UniqueConstraint("wallet_address", "axie_id", name="uq_wallet_axie"),
        Index("idx_holdings_wallet", "wallet_address"),
        Index("idx_holdings_axie", "axie_id"),
        {"schema": "axie"},
    )

    @property
    def has_cost_basis(self) -> bool:
        """Check if cost basis is available for P&L calculation."""
        return self.cost_basis_eth is not None and self.cost_basis_eth > 0

    def compute_unrealized_pnl(self) -> None:
        """Compute unrealized P&L from current value and cost basis."""
        if self.current_value_eth and self.cost_basis_eth and self.cost_basis_eth > 0:
            self.unrealized_pnl_eth = self.current_value_eth - self.cost_basis_eth
            self.unrealized_pnl_percent = (
                (self.unrealized_pnl_eth / self.cost_basis_eth) * 100
            )
        else:
            self.unrealized_pnl_eth = None
            self.unrealized_pnl_percent = None


class TokenType(str, PyEnum):
    """Supported token types on Ronin chain."""

    RON = "RON"  # Native Ronin token
    WETH = "WETH"  # Wrapped ETH (Axie marketplace currency)
    WRON = "WRON"  # Wrapped RON
    AXS = "AXS"  # Axie Infinity Shards (governance)
    SLP = "SLP"  # Smooth Love Potion (breeding)


class WalletTokenBalance(Base):
    """
    Current token balances for tracked wallets.

    Caches balances fetched from Ronin RPC to avoid repeated blockchain calls.
    Updated on-demand when wallet endpoints are accessed or via background sync.
    """

    __tablename__ = "wallet_token_balances"
    __table_args__ = {"schema": "axie"}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_address: Mapped[str] = mapped_column(
        String(42),
        ForeignKey("axie.wallets.address", ondelete="CASCADE"),
        nullable=False,
    )
    token_type: Mapped[TokenType] = mapped_column(
        Enum(TokenType),
        nullable=False,
    )

    # Balance data
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        comment="Token balance in native units (e.g., 1.5 WETH)",
    )
    balance_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 2),
        comment="USD value at last update",
    )
    token_price_usd: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(20, 8),
        comment="Token price in USD at last update",
    )

    # Metadata
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When balance was last fetched",
    )
    block_number: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        comment="Block number at last update (for debugging)",
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Relationships
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="token_balances")

    @property
    def is_stale(self, ttl_minutes: int = 5) -> bool:
        """Check if balance data is stale (older than TTL)."""
        if not self.last_updated:
            return True
        age_seconds = (datetime.utcnow() - self.last_updated).total_seconds()
        return age_seconds > (ttl_minutes * 60)

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "token": self.token_type.value,
            "balance": float(self.balance),
            "balance_usd": float(self.balance_usd) if self.balance_usd else None,
            "token_price_usd": (
                float(self.token_price_usd) if self.token_price_usd else None
            ),
            "last_updated": self.last_updated.isoformat(),
        }
