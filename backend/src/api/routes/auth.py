"""
Authentication routes for wallet-based authentication.

Flow:
1. POST /auth/challenge - Request a challenge for a wallet address
2. POST /auth/verify - Submit signed challenge to get JWT token
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import get_db
from src.models.auth import AuthChallenge
from src.config import get_settings
from src.services.auth import (
    verify_signature,
    create_jwt_token,
    SignatureVerificationError,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response Models
class ChallengeRequest(BaseModel):
    """Request body for creating an auth challenge."""

    address: str = Field(
        ...,
        description="Wallet address requesting authentication",
        pattern="^0x[a-fA-F0-9]{40}$",
    )


class ChallengeResponse(BaseModel):
    """Response containing the challenge to sign."""

    challenge_id: str = Field(..., description="Unique challenge ID")
    message: str = Field(..., description="Message to sign with wallet")
    expires_at: str = Field(..., description="ISO timestamp when challenge expires")


class VerifyRequest(BaseModel):
    """Request body for verifying a signed challenge."""

    challenge_id: str = Field(..., description="Challenge ID from /challenge")
    signature: str = Field(
        ...,
        description="Wallet signature of the challenge message",
    )


class VerifyResponse(BaseModel):
    """Response containing the JWT token."""

    token: str = Field(..., description="JWT token for authenticated requests")
    expires_at: str = Field(..., description="ISO timestamp when token expires")
    address: str = Field(..., description="Authenticated wallet address")


class AuthStatusResponse(BaseModel):
    """Response for auth status check."""

    authenticated: bool
    address: Optional[str] = None
    expires_at: Optional[str] = None


@router.post("/challenge", response_model=ChallengeResponse)
async def create_challenge(
    request: ChallengeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a nonce challenge for wallet authentication.

    The returned message must be signed by the wallet using EIP-191 personal sign.
    The challenge expires in 5 minutes.

    **Flow:**
    1. Request a challenge with your wallet address
    2. Sign the returned message with your wallet
    3. Submit the signature to /auth/verify
    """
    settings = get_settings()
    address = request.address.lower()

    logger.debug(f"Challenge requested for {address[:10]}...")

    # Clean up old expired challenges for this wallet
    await db.execute(
        delete(AuthChallenge).where(
            AuthChallenge.wallet_address == address,
            AuthChallenge.expires_at < datetime.utcnow(),
        )
    )

    # Create new challenge
    challenge = AuthChallenge.create(
        wallet_address=address,
        ttl_minutes=settings.auth_challenge_ttl_minutes,
    )

    db.add(challenge)
    await db.commit()

    logger.info(f"Challenge created: {challenge.id[:8]}... for {address[:10]}...")

    return ChallengeResponse(
        challenge_id=challenge.id,
        message=challenge.message,
        expires_at=challenge.expires_at.isoformat() + "Z",
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_challenge(
    request: VerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify a signed challenge and issue a JWT token.

    The signature must be created by signing the challenge message
    with the wallet's private key using EIP-191 personal sign.

    **Returns:**
    A JWT token valid for 24 hours that can be used in the
    Authorization header as `Bearer <token>`.
    """
    logger.debug(f"Verification attempt for challenge {request.challenge_id[:8]}...")

    # Get challenge
    result = await db.execute(
        select(AuthChallenge).where(AuthChallenge.id == request.challenge_id)
    )
    challenge = result.scalar_one_or_none()

    if not challenge:
        logger.warning(f"Challenge not found: {request.challenge_id[:8]}...")
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.used:
        logger.warning(f"Challenge already used: {request.challenge_id[:8]}...")
        raise HTTPException(status_code=400, detail="Challenge already used")

    if challenge.is_expired:
        logger.warning(f"Challenge expired: {request.challenge_id[:8]}...")
        raise HTTPException(status_code=400, detail="Challenge expired")

    # Verify signature
    try:
        logger.debug("Verifying signature")
        recovered_address = verify_signature(
            message=challenge.message,
            signature=request.signature,
        )
        logger.debug(f"Signature verified, recovered: {recovered_address[:10]}...")
    except SignatureVerificationError as e:
        logger.warning(f"Signature verification failed: {e}")
        raise HTTPException(status_code=401, detail=str(e))

    # Check that recovered address matches challenge address
    if recovered_address.lower() != challenge.wallet_address:
        logger.warning(
            f"Address mismatch: recovered={recovered_address[:10]}..., "
            f"expected={challenge.wallet_address[:10]}..."
        )
        raise HTTPException(
            status_code=401,
            detail="Signature does not match the challenge wallet address",
        )

    # Mark challenge as used
    challenge.mark_used()
    await db.commit()

    # Generate JWT token
    token, expires_at = create_jwt_token(challenge.wallet_address)

    logger.info(f"Authentication successful for {challenge.wallet_address[:10]}...")

    return VerifyResponse(
        token=token,
        expires_at=expires_at.isoformat() + "Z",
        address=challenge.wallet_address,
    )


@router.delete("/challenge/{challenge_id}")
async def cancel_challenge(
    challenge_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel an unused challenge.

    This is optional - challenges expire automatically after 5 minutes.
    """
    result = await db.execute(
        select(AuthChallenge).where(AuthChallenge.id == challenge_id)
    )
    challenge = result.scalar_one_or_none()

    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if challenge.used:
        raise HTTPException(status_code=400, detail="Challenge already used")

    await db.delete(challenge)
    await db.commit()

    return {"success": True, "message": "Challenge cancelled"}
