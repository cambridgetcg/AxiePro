"""
End-to-end test fixtures.

E2E tests verify complete user flows across multiple endpoints.
External APIs are mocked but internal services are real.
"""

import pytest


# Mark all tests in this directory as e2e tests
def pytest_collection_modifyitems(items):
    """Automatically mark all tests in e2e/ as e2e tests."""
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


@pytest.fixture
def e2e_client(client, mock_skymavis, mock_ronin_rpc):
    """
    Client configured for E2E testing.

    Provides:
    - HTTP client for API calls
    - Mocked external APIs
    - Real database (in-memory SQLite)

    Usage:
        async def test_user_flow(e2e_client):
            client, mocks = e2e_client
            mocks["skymavis"].mock_listings([...])
            response = await client.get("/api/v1/market/listings")
    """
    return client, {
        "skymavis": mock_skymavis,
        "ronin_rpc": mock_ronin_rpc,
    }


@pytest.fixture
def authenticated_e2e_client(authenticated_client, mock_skymavis, mock_ronin_rpc):
    """
    Authenticated client for E2E testing.

    Same as e2e_client but pre-authenticated with test wallet.
    """
    return authenticated_client, {
        "skymavis": mock_skymavis,
        "ronin_rpc": mock_ronin_rpc,
    }
