"""
Integration test fixtures.

Integration tests verify API endpoints with:
- Real database (in-memory SQLite)
- Mocked external APIs (SkyMavis, Ronin RPC)
- Mocked Redis cache
"""

import pytest
import respx
from httpx import Response

# Import from parent conftest (automatically available)
# client, db_session, auth fixtures are already available


# Mark all tests in this directory as integration tests
def pytest_collection_modifyitems(items):
    """Automatically mark all tests in integration/ as integration tests."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


# =============================================================================
# External API Mocking
# =============================================================================

@pytest.fixture
def mock_skymavis():
    """
    Mock SkyMavis GraphQL API.

    Usage:
        def test_something(client, mock_skymavis):
            mock_skymavis.mock_axie_query([axie1, axie2])
            response = await client.get("/api/v1/axies")
    """
    from tests.mocks.skymavis_mock import SkyMavisMock

    with respx.mock:
        yield SkyMavisMock()


@pytest.fixture
def mock_ronin_rpc():
    """
    Mock Ronin RPC.

    Usage:
        def test_something(client, mock_ronin_rpc):
            mock_ronin_rpc.mock_get_balance(address, 1000000000)
            response = await client.get(f"/api/v1/wallets/{address}")
    """
    from tests.mocks.ronin_rpc_mock import RoninRPCMock

    with respx.mock:
        yield RoninRPCMock()


@pytest.fixture
def mock_all_external(mock_skymavis, mock_ronin_rpc):
    """
    Convenience fixture that provides both mocks.

    Usage:
        def test_something(client, mock_all_external):
            skymavis, ronin = mock_all_external
            skymavis.mock_listings([...])
            ronin.mock_get_balance(...)
    """
    return mock_skymavis, mock_ronin_rpc


# =============================================================================
# Test Data Helpers
# =============================================================================

@pytest.fixture
def make_listing():
    """Factory fixture for creating listing test data."""
    from tests.factories import ListingFactory
    return ListingFactory.create


@pytest.fixture
def make_axie():
    """Factory fixture for creating Axie test data."""
    from tests.factories import AxieFactory
    return AxieFactory.create


@pytest.fixture
def make_sale():
    """Factory fixture for creating sale test data."""
    from tests.factories import SaleFactory
    return SaleFactory.create
