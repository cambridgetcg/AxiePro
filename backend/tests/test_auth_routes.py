"""
API endpoint tests for auth routes.

Tests:
- POST /auth/challenge - Create authentication challenge
- POST /auth/verify - Verify signed challenge and get JWT
- DELETE /auth/challenge/{id} - Cancel a challenge
"""

from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.auth import AuthChallenge

from tests.conftest import (
    TEST_WALLET_ADDRESS,
    TEST_WALLET_PRIVATE_KEY,
    TEST_WALLET_ADDRESS_2,
    TEST_WALLET_PRIVATE_KEY_2,
    sign_message,
    create_invalid_signature,
)


# =============================================================================
# Challenge Creation Tests
# =============================================================================

class TestCreateChallenge:
    """Tests for POST /auth/challenge endpoint."""

    @pytest.mark.asyncio
    async def test_create_challenge_success(self, client: AsyncClient):
        """Test successful challenge creation."""
        response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "challenge_id" in data
        assert "message" in data
        assert "expires_at" in data

        # Verify challenge_id is a valid hex string
        assert len(data["challenge_id"]) == 64

        # Verify message contains expected content
        assert TEST_WALLET_ADDRESS.lower() in data["message"].lower()
        assert "AxiePro" in data["message"]
        assert "Nonce:" in data["message"]

        # Verify expires_at is in the future
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        assert expires_at > datetime.now(expires_at.tzinfo)

    @pytest.mark.asyncio
    async def test_create_challenge_mixed_case_address(self, client: AsyncClient):
        """Test that mixed-case addresses are normalized to lowercase."""
        # Use mixed case but keep 0x prefix lowercase (as required by pattern)
        mixed_case_address = "0x" + TEST_WALLET_ADDRESS[2:].upper()

        response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": mixed_case_address}
        )

        assert response.status_code == 200
        data = response.json()

        # Message should contain lowercase address
        assert TEST_WALLET_ADDRESS.lower() in data["message"].lower()

    @pytest.mark.asyncio
    async def test_create_challenge_invalid_address_format(self, client: AsyncClient):
        """Test that invalid address format returns 422."""
        invalid_addresses = [
            "not-an-address",
            "0x123",  # Too short
            "0x" + "g" * 40,  # Invalid hex characters
            "123456789012345678901234567890123456789012",  # Missing 0x prefix
        ]

        for addr in invalid_addresses:
            response = await client.post(
                "/api/v1/auth/challenge",
                json={"address": addr}
            )
            assert response.status_code == 422, f"Expected 422 for address: {addr}"

    @pytest.mark.asyncio
    async def test_create_challenge_missing_address(self, client: AsyncClient):
        """Test that missing address returns 422."""
        response = await client.post(
            "/api/v1/auth/challenge",
            json={}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_multiple_challenges(self, client: AsyncClient):
        """Test that multiple challenges can be created for same wallet."""
        # Create first challenge
        response1 = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        assert response1.status_code == 200
        challenge1 = response1.json()

        # Create second challenge
        response2 = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        assert response2.status_code == 200
        challenge2 = response2.json()

        # Challenges should be different
        assert challenge1["challenge_id"] != challenge2["challenge_id"]
        assert challenge1["message"] != challenge2["message"]


# =============================================================================
# Challenge Verification Tests
# =============================================================================

class TestVerifyChallenge:
    """Tests for POST /auth/verify endpoint."""

    @pytest.mark.asyncio
    async def test_verify_challenge_success(self, client: AsyncClient):
        """Test successful challenge verification."""
        # Create challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        # Sign the message
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)

        # Verify
        response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "token" in data
        assert "expires_at" in data
        assert "address" in data

        # Verify address matches
        assert data["address"] == TEST_WALLET_ADDRESS.lower()

        # Verify token is a JWT (has 3 parts)
        assert len(data["token"].split(".")) == 3

    @pytest.mark.asyncio
    async def test_verify_challenge_not_found(self, client: AsyncClient):
        """Test verification with non-existent challenge_id."""
        response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": "nonexistent" * 4,  # 64 char hex
                "signature": sign_message("test", TEST_WALLET_PRIVATE_KEY),
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_challenge_already_used(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that used challenge cannot be reused."""
        # Create and use challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)

        # First verification should succeed
        response1 = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        assert response1.status_code == 200

        # Second verification should fail
        response2 = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        assert response2.status_code == 400
        assert "already used" in response2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_challenge_expired(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that expired challenge cannot be verified."""
        # Create challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        # Manually expire the challenge in the database
        await db_session.execute(
            update(AuthChallenge)
            .where(AuthChallenge.id == challenge["challenge_id"])
            .values(expires_at=datetime.utcnow() - timedelta(minutes=1))
        )
        await db_session.commit()

        # Try to verify
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_challenge_wrong_signature(self, client: AsyncClient):
        """Test verification with signature from different wallet."""
        # Create challenge for wallet 1
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        # Sign with wallet 2
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY_2)

        # Verify - should fail because recovered address doesn't match
        response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )

        assert response.status_code == 401
        assert "does not match" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_challenge_invalid_signature(self, client: AsyncClient):
        """Test verification with invalid signature."""
        # Create challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        # Use invalid signature
        response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": create_invalid_signature(),
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_verify_challenge_missing_fields(self, client: AsyncClient):
        """Test verification with missing required fields."""
        # Missing signature
        response1 = await client.post(
            "/api/v1/auth/verify",
            json={"challenge_id": "abc123"}
        )
        assert response1.status_code == 422

        # Missing challenge_id
        response2 = await client.post(
            "/api/v1/auth/verify",
            json={"signature": "0x123"}
        )
        assert response2.status_code == 422


# =============================================================================
# Challenge Cancellation Tests
# =============================================================================

class TestCancelChallenge:
    """Tests for DELETE /auth/challenge/{challenge_id} endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_challenge_success(self, client: AsyncClient):
        """Test successful challenge cancellation."""
        # Create challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        # Cancel it
        response = await client.delete(
            f"/api/v1/auth/challenge/{challenge['challenge_id']}"
        )

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it can't be used
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        assert verify_response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_challenge_not_found(self, client: AsyncClient):
        """Test cancellation of non-existent challenge."""
        response = await client.delete(
            "/api/v1/auth/challenge/" + "a" * 64
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_challenge_already_used(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Test that used challenge cannot be cancelled."""
        # Create and use challenge
        create_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        challenge = create_response.json()

        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)
        await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )

        # Try to cancel
        response = await client.delete(
            f"/api/v1/auth/challenge/{challenge['challenge_id']}"
        )

        assert response.status_code == 400
        assert "already used" in response.json()["detail"].lower()


# =============================================================================
# Full Auth Flow Integration Tests
# =============================================================================

class TestAuthFlowIntegration:
    """Integration tests for complete authentication flow."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self, client: AsyncClient):
        """Test the complete authentication flow end-to-end."""
        # Step 1: Request challenge
        challenge_response = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        assert challenge_response.status_code == 200
        challenge = challenge_response.json()

        # Step 2: Sign the message (simulating wallet signing)
        signature = sign_message(challenge["message"], TEST_WALLET_PRIVATE_KEY)

        # Step 3: Verify signature and get token
        verify_response = await client.post(
            "/api/v1/auth/verify",
            json={
                "challenge_id": challenge["challenge_id"],
                "signature": signature,
            }
        )
        assert verify_response.status_code == 200
        auth_data = verify_response.json()

        # Verify we got a valid token
        assert "token" in auth_data
        assert auth_data["address"] == TEST_WALLET_ADDRESS.lower()

        # Step 4: Use token for authenticated request (health check with auth header)
        # Just verify the token format is correct
        token_parts = auth_data["token"].split(".")
        assert len(token_parts) == 3, "JWT should have 3 parts"

    @pytest.mark.asyncio
    async def test_concurrent_challenges_different_wallets(self, client: AsyncClient):
        """Test that different wallets can have concurrent challenges."""
        # Create challenge for wallet 1
        response1 = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS}
        )
        assert response1.status_code == 200
        challenge1 = response1.json()

        # Create challenge for wallet 2
        response2 = await client.post(
            "/api/v1/auth/challenge",
            json={"address": TEST_WALLET_ADDRESS_2}
        )
        assert response2.status_code == 200
        challenge2 = response2.json()

        # Both should be verifiable
        sig1 = sign_message(challenge1["message"], TEST_WALLET_PRIVATE_KEY)
        sig2 = sign_message(challenge2["message"], TEST_WALLET_PRIVATE_KEY_2)

        verify1 = await client.post(
            "/api/v1/auth/verify",
            json={"challenge_id": challenge1["challenge_id"], "signature": sig1}
        )
        verify2 = await client.post(
            "/api/v1/auth/verify",
            json={"challenge_id": challenge2["challenge_id"], "signature": sig2}
        )

        assert verify1.status_code == 200
        assert verify2.status_code == 200
        assert verify1.json()["address"] == TEST_WALLET_ADDRESS.lower()
        assert verify2.json()["address"] == TEST_WALLET_ADDRESS_2.lower()
