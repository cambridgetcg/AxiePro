"""
Tests for protected wallet endpoints requiring authentication.

Tests the cost basis update endpoint which requires:
1. Valid JWT token
2. Token wallet must match target wallet (ownership check)
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
import jwt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Wallet, WalletHolding
from src.config import get_settings

from tests.conftest import (
    TEST_WALLET_ADDRESS,
    TEST_WALLET_PRIVATE_KEY,
    TEST_WALLET_ADDRESS_2,
    TEST_WALLET_PRIVATE_KEY_2,
    sign_message,
)


# =============================================================================
# Test Data Setup
# =============================================================================

@pytest_asyncio.fixture
async def wallet_with_holding(db_session: AsyncSession) -> tuple[str, int]:
    """Create a test wallet with a holding."""
    # Create wallet
    wallet = Wallet(
        address=TEST_WALLET_ADDRESS,
        first_seen=datetime.utcnow(),
        last_active=datetime.utcnow(),
    )
    db_session.add(wallet)
    await db_session.commit()

    # Create holding
    axie_id = 12345
    holding = WalletHolding(
        wallet_address=TEST_WALLET_ADDRESS,
        axie_id=axie_id,
        acquired_at=datetime.utcnow(),
    )
    db_session.add(holding)
    await db_session.commit()

    return TEST_WALLET_ADDRESS, axie_id


# =============================================================================
# Authentication Requirement Tests
# =============================================================================

class TestCostBasisAuthentication:
    """Tests for authentication requirements on cost basis endpoint."""

    @pytest.mark.asyncio
    async def test_update_cost_basis_no_token(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test that request without token fails."""
        address, axie_id = wallet_with_holding

        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.1}
        )

        assert response.status_code == 422  # Missing required header

    @pytest.mark.asyncio
    async def test_update_cost_basis_invalid_token(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test that request with invalid token fails."""
        address, axie_id = wallet_with_holding

        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.1},
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_cost_basis_expired_token(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test that request with expired token fails."""
        address, axie_id = wallet_with_holding
        settings = get_settings()

        # Create an expired token
        payload = {
            "sub": address,
            "iat": datetime.utcnow() - timedelta(hours=48),
            "exp": datetime.utcnow() - timedelta(hours=24),
            "type": "access",
        }
        expired_token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.1},
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_update_cost_basis_malformed_header(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test that malformed Authorization header fails."""
        address, axie_id = wallet_with_holding

        # Missing "Bearer " prefix
        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.1},
            headers={"Authorization": "some-token-without-bearer"}
        )

        assert response.status_code == 401


# =============================================================================
# Ownership Tests
# =============================================================================

class TestCostBasisOwnership:
    """Tests for wallet ownership requirement on cost basis endpoint."""

    @pytest.mark.asyncio
    async def test_update_cost_basis_wrong_wallet(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test that authenticating as wallet A cannot update wallet B."""
        address, axie_id = wallet_with_holding

        # Authenticate as wallet 2
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS_2}
        )
        challenge = challenge_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY_2)
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        token = verify_response.json()["token"]

        # Try to update wallet 1's holdings with wallet 2's token
        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.1},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        assert "only" in response.json()["detail"].lower()
        assert "your own" in response.json()["detail"].lower()


# =============================================================================
# Successful Update Tests
# =============================================================================

class TestCostBasisUpdate:
    """Tests for successful cost basis updates."""

    @pytest.mark.asyncio
    async def test_update_cost_basis_authenticated(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test successful cost basis update with proper authentication."""
        address, axie_id = wallet_with_holding

        # Get auth token for the wallet
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": address}
        )
        challenge = challenge_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        token = verify_response.json()["token"]

        # Update cost basis
        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={"cost_basis_eth": 0.15},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["axie_id"] == axie_id
        assert data["data"]["cost_basis_eth"] == 0.15

    @pytest.mark.asyncio
    async def test_update_cost_basis_with_acquisition_type(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test updating cost basis with acquisition type."""
        address, axie_id = wallet_with_holding

        # Get auth token
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": address}
        )
        challenge = challenge_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        token = verify_response.json()["token"]

        # Update with acquisition type (use 0.01 to avoid edge case with 0.0)
        response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={
                "cost_basis_eth": 0.01,
                "acquisition_type": "gift",
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["cost_basis_eth"] == 0.01
        assert data["data"]["acquisition_type"] == "gift"

    @pytest.mark.asyncio
    async def test_update_cost_basis_holding_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test updating cost basis for non-existent holding."""
        # Create wallet without holding
        wallet = Wallet(
            address=TEST_WALLET_ADDRESS,
            first_seen=datetime.utcnow(),
        )
        db_session.add(wallet)
        await db_session.commit()

        # Get auth token
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = challenge_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        token = verify_response.json()["token"]

        # Try to update non-existent holding
        response = await client.patch(
            f"/api/v1/wallets/{TEST_WALLET_ADDRESS}/holdings/99999/cost-basis",
            params={"cost_basis_eth": 0.1},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# Integration: Full Auth to Protected Endpoint Flow
# =============================================================================

class TestFullProtectedEndpointFlow:
    """End-to-end tests for the complete auth -> protected endpoint flow."""

    @pytest.mark.asyncio
    async def test_complete_flow_challenge_to_update(
        self, client: AsyncClient, wallet_with_holding: tuple[str, int]
    ):
        """Test the complete flow from challenge to protected endpoint."""
        address, axie_id = wallet_with_holding

        # Step 1: Request challenge
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": address}
        )
        assert challenge_response.status_code == 200
        challenge = challenge_response.json()

        # Step 2: Sign challenge
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)

        # Step 3: Verify and get token
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        assert verify_response.status_code == 200
        token = verify_response.json()["token"]

        # Step 4: Use token to update cost basis
        update_response = await client.patch(
            f"/api/v1/wallets/{address}/holdings/{axie_id}/cost-basis",
            params={
                "cost_basis_eth": 0.25,
                "acquisition_type": "purchase",
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert update_response.status_code == 200

        # Step 5: Verify the update persisted
        data = update_response.json()
        assert data["success"] is True
        assert data["data"]["cost_basis_eth"] == 0.25
        assert data["data"]["acquisition_type"] == "purchase"
        assert data["message"] == "Cost basis updated successfully"
