"""
External API Mocks

Provides mock classes for external services used by AxiePro:
- SkyMavisMock: Mock SkyMavis GraphQL API (marketplace data)
- RoninRPCMock: Mock Ronin RPC (blockchain data)

Usage:
    import respx
    from tests.mocks import SkyMavisMock

    with respx.mock:
        mock = SkyMavisMock()
        mock.mock_listings([axie1, axie2])

        # Your test code here - API calls will use mocked responses
"""

from .skymavis_mock import SkyMavisMock
from .ronin_rpc_mock import RoninRPCMock

__all__ = [
    "SkyMavisMock",
    "RoninRPCMock",
]
