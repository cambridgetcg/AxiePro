"""
Shared pytest fixtures for auth testing.

Provides:
- Async database session (in-memory SQLite)
- FastAPI test client
- Test wallet with known private key for signing
- Helper functions for signature generation
"""

import asyncio
from datetime import datetime, timedelta
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from eth_account import Account
from eth_account.messages import encode_defunct
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.main import app
from src.models.database import Base
from src.models import get_db


# =============================================================================
# Test Wallet Configuration
# =============================================================================

# Known test wallet for predictable signatures
# NEVER use this key for real funds!
TEST_WALLET_PRIVATE_KEY = "0x" + "a" * 64  # Simple test key: 64 'a's
TEST_WALLET_ACCOUNT = Account.from_key(TEST_WALLET_PRIVATE_KEY)
TEST_WALLET_ADDRESS = TEST_WALLET_ACCOUNT.address.lower()

# Second test wallet for "wrong wallet" tests
TEST_WALLET_PRIVATE_KEY_2 = "0x" + "b" * 64
TEST_WALLET_ACCOUNT_2 = Account.from_key(TEST_WALLET_PRIVATE_KEY_2)
TEST_WALLET_ADDRESS_2 = TEST_WALLET_ACCOUNT_2.address.lower()


# =============================================================================
# Database Fixtures
# =============================================================================

# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh database engine for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


# =============================================================================
# FastAPI Test Client
# =============================================================================

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing API endpoints."""

    # Override the database dependency
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up
    app.dependency_overrides.clear()


# =============================================================================
# Signature Helpers
# =============================================================================

def sign_message(message: str, private_key: str = TEST_WALLET_PRIVATE_KEY) -> str:
    """
    Sign a message using EIP-191 personal sign.

    Args:
        message: The message to sign
        private_key: The private key to sign with (defaults to TEST_WALLET_PRIVATE_KEY)

    Returns:
        The signature as a hex string with 0x prefix
    """
    account = Account.from_key(private_key)
    message_encoded = encode_defunct(text=message)
    signed = account.sign_message(message_encoded)
    return signed.signature.hex()


def create_invalid_signature() -> str:
    """Create an invalid signature for testing."""
    return "0x" + "00" * 65


# =============================================================================
# Auth Helper Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def auth_challenge(client: AsyncClient) -> dict:
    """Create an auth challenge and return the response data."""
    response = await client.post(
        "/api/v1/auth/challenge",
        json={"address": TEST_WALLET_ADDRESS}
    )
    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, auth_challenge: dict) -> str:
    """
    Complete the auth flow and return a valid JWT token.

    This fixture:
    1. Gets a challenge
    2. Signs it with the test wallet
    3. Verifies the signature
    4. Returns the JWT token
    """
    # Sign the challenge message
    signature = sign_message(auth_challenge["message"])

    # Verify the challenge
    response = await client.post(
        "/api/v1/auth/verify",
        json={
            "challenge_id": auth_challenge["challenge_id"],
            "signature": signature,
        }
    )
    assert response.status_code == 200
    return response.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    """Return headers with Bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def test_wallet_address() -> str:
    """Return the test wallet address."""
    return TEST_WALLET_ADDRESS


@pytest.fixture
def test_wallet_private_key() -> str:
    """Return the test wallet private key."""
    return TEST_WALLET_PRIVATE_KEY


@pytest.fixture
def other_wallet_address() -> str:
    """Return a different wallet address for ownership tests."""
    return TEST_WALLET_ADDRESS_2


@pytest.fixture
def other_wallet_private_key() -> str:
    """Return a different wallet private key."""
    return TEST_WALLET_PRIVATE_KEY_2
