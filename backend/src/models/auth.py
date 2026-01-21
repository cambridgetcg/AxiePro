"""
Authentication models for wallet-based authentication.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import String, DateTime, Boolean, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class AuthChallenge(Base):
    """
    Nonce challenges for wallet authentication.

    Flow:
    1. Client requests challenge for a wallet address
    2. Server generates random nonce and stores challenge
    3. Client signs the challenge message with wallet
    4. Server verifies signature and issues JWT
    5. Challenge is marked as used (one-time use)
    """

    __tablename__ = "auth_challenges"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    nonce: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_challenge_wallet_expires", "wallet_address", "expires_at"),
    )

    @classmethod
    def create(cls, wallet_address: str, ttl_minutes: int = 5) -> "AuthChallenge":
        """
        Create a new authentication challenge.

        Args:
            wallet_address: The wallet address requesting authentication
            ttl_minutes: Time-to-live for the challenge in minutes

        Returns:
            A new AuthChallenge instance (not yet committed to DB)
        """
        nonce = secrets.token_hex(32)
        timestamp = datetime.utcnow()

        # EIP-191 compatible message that's clear to users
        message = f"""Sign this message to authenticate with AxiePro.

Wallet: {wallet_address.lower()}
Nonce: {nonce}
Timestamp: {timestamp.isoformat()}Z

This signature will not trigger any blockchain transaction or cost any gas."""

        return cls(
            id=secrets.token_hex(32),
            wallet_address=wallet_address.lower(),
            nonce=nonce,
            message=message,
            created_at=timestamp,
            expires_at=timestamp + timedelta(minutes=ttl_minutes),
        )

    @property
    def is_expired(self) -> bool:
        """Check if the challenge has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the challenge is still valid (not expired and not used)."""
        return not self.used and not self.is_expired

    def mark_used(self) -> None:
        """Mark the challenge as used."""
        self.used = True
        self.used_at = datetime.utcnow()
