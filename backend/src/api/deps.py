"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional

from fastapi import Depends, HTTPException, Header
import jwt

from src.config import get_settings
from src.services.auth import verify_jwt_token


async def get_optional_authenticated_wallet(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Optionally extract authenticated wallet from Authorization header.

    Returns None if no token provided, otherwise returns wallet address.
    Raises HTTPException if token is provided but invalid.
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        return verify_jwt_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_authenticated_wallet(
    authorization: str = Header(..., description="Bearer token from /auth/verify"),
) -> str:
    """
    Extract and verify JWT token from Authorization header.

    Returns the authenticated wallet address.
    Raises HTTPException if token is missing, invalid, or expired.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Use 'Bearer <token>'",
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    try:
        return verify_jwt_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_wallet_ownership(
    target_address: str,
    authenticated_wallet: str = Depends(get_authenticated_wallet),
) -> str:
    """
    Verify that the authenticated wallet matches the target address.

    Use this for endpoints that modify wallet-specific data.

    Args:
        target_address: The wallet address being modified
        authenticated_wallet: The authenticated wallet from JWT

    Returns:
        The authenticated wallet address

    Raises:
        HTTPException: If wallets don't match
    """
    if authenticated_wallet.lower() != target_address.lower():
        raise HTTPException(
            status_code=403,
            detail="You can only modify data for your own wallet",
        )
    return authenticated_wallet
