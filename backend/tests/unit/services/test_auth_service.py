"""
Unit tests for the auth service.

Tests:
- EIP-191 signature verification
- JWT token creation and verification
"""

from datetime import datetime, timedelta
import time

import pytest
import jwt
from eth_account import Account
from eth_account.messages import encode_defunct

from src.services.auth import (
    verify_signature,
    create_jwt_token,
    verify_jwt_token,
    SignatureVerificationError,
)
from src.config import get_settings

from tests.conftest import (
    TEST_WALLET_ADDRESS,
    TEST_WALLET_PRIVATE_KEY,
    TEST_WALLET_ADDRESS_2,
    TEST_WALLET_PRIVATE_KEY_2,
    sign_message,
    create_invalid_signature,
)


# =============================================================================
# Signature Verification Tests
# =============================================================================

class TestVerifySignature:
    """Tests for verify_signature function."""

    def test_verify_signature_valid(self):
        """Test that a valid signature recovers the correct address."""
        message = "Test message for signing"
        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY)

        recovered = verify_signature(message, signature)

        # Address should match (case-insensitive)
        assert recovered.lower() == TEST_WALLET_ADDRESS.lower()

    def test_verify_signature_valid_without_0x_prefix(self):
        """Test signature verification works without 0x prefix."""
        message = "Test message for signing"
        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY)

        # Remove 0x prefix
        signature_no_prefix = signature[2:] if signature.startswith("0x") else signature

        recovered = verify_signature(message, signature_no_prefix)

        assert recovered.lower() == TEST_WALLET_ADDRESS.lower()

    def test_verify_signature_invalid(self):
        """Test that an invalid signature raises SignatureVerificationError."""
        message = "Test message for signing"
        invalid_sig = create_invalid_signature()

        with pytest.raises(SignatureVerificationError) as excinfo:
            verify_signature(message, invalid_sig)

        assert "Invalid signature" in str(excinfo.value)

    def test_verify_signature_wrong_message(self):
        """Test that signing one message and verifying another recovers wrong address."""
        message1 = "Original message"
        message2 = "Different message"

        # Sign message1
        signature = sign_message(message1, TEST_WALLET_PRIVATE_KEY)

        # Verify against message2 - should recover a different address
        recovered = verify_signature(message2, signature)

        # The recovered address should NOT match the signer
        assert recovered.lower() != TEST_WALLET_ADDRESS.lower()

    def test_verify_signature_different_wallet(self):
        """Test that signature from wallet A doesn't match wallet B."""
        message = "Test message"

        # Sign with wallet 2
        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY_2)

        # Verify - should recover wallet 2's address
        recovered = verify_signature(message, signature)

        assert recovered.lower() == TEST_WALLET_ADDRESS_2.lower()
        assert recovered.lower() != TEST_WALLET_ADDRESS.lower()

    def test_verify_signature_empty_message(self):
        """Test signature verification with empty message."""
        message = ""
        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY)

        recovered = verify_signature(message, signature)

        assert recovered.lower() == TEST_WALLET_ADDRESS.lower()

    def test_verify_signature_multiline_message(self):
        """Test signature verification with multiline message (like challenge)."""
        message = """Sign this message to authenticate with AxiePro.

Wallet: 0x1234567890abcdef
Nonce: abc123
Timestamp: 2024-01-01T00:00:00Z

This signature will not trigger any blockchain transaction or cost any gas."""

        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY)
        recovered = verify_signature(message, signature)

        assert recovered.lower() == TEST_WALLET_ADDRESS.lower()


# =============================================================================
# JWT Token Creation Tests
# =============================================================================

class TestCreateJwtToken:
    """Tests for create_jwt_token function."""

    def test_create_jwt_token_default_expiry(self):
        """Test JWT token creation with default expiry."""
        token, expires_at = create_jwt_token(TEST_WALLET_ADDRESS)

        assert isinstance(token, str)
        assert len(token) > 0
        assert isinstance(expires_at, datetime)

        # Token should expire in the future
        assert expires_at > datetime.utcnow()

    def test_create_jwt_token_custom_expiry(self):
        """Test JWT token creation with custom expiry."""
        token, expires_at = create_jwt_token(TEST_WALLET_ADDRESS, expiry_hours=1)

        # Should expire in approximately 1 hour
        expected_expiry = datetime.utcnow() + timedelta(hours=1)
        assert abs((expires_at - expected_expiry).total_seconds()) < 5

    def test_create_jwt_token_contains_correct_claims(self):
        """Test that JWT token contains correct claims."""
        settings = get_settings()
        token, _ = create_jwt_token(TEST_WALLET_ADDRESS)

        # Decode without verification to inspect claims
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        assert payload["sub"] == TEST_WALLET_ADDRESS.lower()
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload

    def test_create_jwt_token_lowercase_address(self):
        """Test that address is lowercased in token."""
        mixed_case = "0xAbCdEf1234567890AbCdEf1234567890AbCdEf12"
        token, _ = create_jwt_token(mixed_case)

        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

        assert payload["sub"] == mixed_case.lower()


# =============================================================================
# JWT Token Verification Tests
# =============================================================================

class TestVerifyJwtToken:
    """Tests for verify_jwt_token function."""

    def test_verify_jwt_token_valid(self):
        """Test verification of a valid token."""
        token, _ = create_jwt_token(TEST_WALLET_ADDRESS)

        address = verify_jwt_token(token)

        assert address == TEST_WALLET_ADDRESS.lower()

    def test_verify_jwt_token_expired(self):
        """Test that expired token raises ExpiredSignatureError."""
        # Create token that expires immediately
        settings = get_settings()
        payload = {
            "sub": TEST_WALLET_ADDRESS.lower(),
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),  # Already expired
            "type": "access",
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        with pytest.raises(jwt.ExpiredSignatureError):
            verify_jwt_token(token)

    def test_verify_jwt_token_invalid(self):
        """Test that invalid token raises InvalidTokenError."""
        invalid_token = "this.is.not.a.valid.jwt"

        with pytest.raises(jwt.InvalidTokenError):
            verify_jwt_token(invalid_token)

    def test_verify_jwt_token_wrong_secret(self):
        """Test that token signed with wrong secret fails verification."""
        # Create token with different secret
        payload = {
            "sub": TEST_WALLET_ADDRESS.lower(),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
            "type": "access",
        }
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")

        with pytest.raises(jwt.InvalidTokenError):
            verify_jwt_token(token)

    def test_verify_jwt_token_malformed(self):
        """Test that malformed token fails."""
        with pytest.raises(jwt.InvalidTokenError):
            verify_jwt_token("not-a-jwt")

    def test_verify_jwt_token_empty(self):
        """Test that empty token fails."""
        with pytest.raises(jwt.InvalidTokenError):
            verify_jwt_token("")


# =============================================================================
# Integration Tests
# =============================================================================

class TestAuthServiceIntegration:
    """Integration tests for the full auth flow."""

    def test_roundtrip_token_creation_and_verification(self):
        """Test creating a token and then verifying it."""
        # Create token
        token, expires_at = create_jwt_token(TEST_WALLET_ADDRESS)

        # Verify it
        address = verify_jwt_token(token)

        assert address == TEST_WALLET_ADDRESS.lower()
        assert expires_at > datetime.utcnow()

    def test_signature_to_token_flow(self):
        """Test the complete flow: sign message -> verify signature -> create token."""
        message = "Authentication challenge message"

        # Step 1: Sign the message
        signature = sign_message(message, TEST_WALLET_PRIVATE_KEY)

        # Step 2: Verify signature and recover address
        recovered_address = verify_signature(message, signature)
        assert recovered_address.lower() == TEST_WALLET_ADDRESS.lower()

        # Step 3: Create JWT for the recovered address
        token, _ = create_jwt_token(recovered_address)

        # Step 4: Verify the JWT returns the correct address
        token_address = verify_jwt_token(token)
        assert token_address == TEST_WALLET_ADDRESS.lower()
