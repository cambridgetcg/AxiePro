"""
Authentication service for wallet signature verification.

Uses EIP-191 personal sign for message verification.
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
from eth_account.messages import encode_defunct
from eth_account import Account

from src.config import get_settings


class SignatureVerificationError(Exception):
    """Raised when signature verification fails."""

    pass


def verify_signature(message: str, signature: str) -> str:
    """
    Verify an EIP-191 personal sign signature and recover the signer address.

    Args:
        message: The original message that was signed
        signature: The signature (hex string, with or without 0x prefix)

    Returns:
        The recovered wallet address (checksummed)

    Raises:
        SignatureVerificationError: If signature is invalid or cannot be verified
    """
    try:
        # Ensure signature has 0x prefix
        if not signature.startswith("0x"):
            signature = "0x" + signature

        # Encode the message for EIP-191 personal sign
        message_encoded = encode_defunct(text=message)

        # Recover the address from the signature
        recovered_address = Account.recover_message(
            message_encoded,
            signature=signature,
        )

        return recovered_address

    except Exception as e:
        raise SignatureVerificationError(f"Invalid signature: {e}")


def create_jwt_token(
    wallet_address: str,
    expiry_hours: Optional[int] = None,
) -> tuple[str, datetime]:
    """
    Create a JWT token for an authenticated wallet.

    Args:
        wallet_address: The authenticated wallet address
        expiry_hours: Token expiry in hours (defaults to settings.jwt_expiry_hours)

    Returns:
        Tuple of (token, expiry_datetime)
    """
    settings = get_settings()

    if expiry_hours is None:
        expiry_hours = settings.jwt_expiry_hours

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=expiry_hours)

    payload = {
        "sub": wallet_address.lower(),
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256",
    )

    return token, expires_at


def verify_jwt_token(token: str) -> str:
    """
    Verify a JWT token and extract the wallet address.

    Args:
        token: The JWT token to verify

    Returns:
        The wallet address from the token

    Raises:
        jwt.ExpiredSignatureError: If token is expired
        jwt.InvalidTokenError: If token is invalid
    """
    settings = get_settings()

    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
    )

    return payload["sub"]
