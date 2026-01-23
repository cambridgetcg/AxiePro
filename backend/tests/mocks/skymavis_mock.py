"""
SkyMavis GraphQL API Mock

Mocks the SkyMavis GraphQL API used for fetching:
- Marketplace listings
- Axie details
- Sales history
- Floor prices
"""

from typing import Any, Dict, List, Optional
import respx
from httpx import Response


class SkyMavisMock:
    """Mock for SkyMavis GraphQL API."""

    BASE_URL = "https://graphql-gateway.axieinfinity.com/graphql"

    def __init__(self):
        """Initialize the mock."""
        self._routes: List[respx.Route] = []

    def mock_listings(
        self,
        axies: List[Dict[str, Any]],
        total: Optional[int] = None,
    ) -> respx.Route:
        """
        Mock the marketplace listings query.

        Args:
            axies: List of Axie data dictionaries
            total: Total count (defaults to len(axies))

        Returns:
            respx Route for further customization
        """
        if total is None:
            total = len(axies)

        response_data = {
            "data": {
                "axies": {
                    "results": axies,
                    "total": total,
                }
            }
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_axie_detail(self, axie: Dict[str, Any]) -> respx.Route:
        """
        Mock fetching single Axie details.

        Args:
            axie: Axie data dictionary

        Returns:
            respx Route for further customization
        """
        response_data = {
            "data": {
                "axie": axie
            }
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_axie_not_found(self) -> respx.Route:
        """
        Mock Axie not found response.

        Returns:
            respx Route
        """
        response_data = {
            "data": {
                "axie": None
            }
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_sales_history(
        self,
        sales: List[Dict[str, Any]],
        total: Optional[int] = None,
    ) -> respx.Route:
        """
        Mock sales history query.

        Args:
            sales: List of sale data dictionaries
            total: Total count

        Returns:
            respx Route
        """
        if total is None:
            total = len(sales)

        response_data = {
            "data": {
                "settledAuctions": {
                    "results": sales,
                    "total": total,
                }
            }
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_floor_prices(
        self,
        prices: Dict[str, float],
    ) -> respx.Route:
        """
        Mock floor prices by class.

        Args:
            prices: Dictionary mapping class to floor price

        Returns:
            respx Route
        """
        response_data = {
            "data": {
                "marketStats": {
                    "floorPrices": [
                        {"class": cls.lower(), "price": str(price)}
                        for cls, price in prices.items()
                    ]
                }
            }
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_search_query(
        self,
        axies: List[Dict[str, Any]],
        total: Optional[int] = None,
    ) -> respx.Route:
        """
        Mock axie search query.

        Args:
            axies: List of Axie data dictionaries matching search
            total: Total matching count

        Returns:
            respx Route
        """
        # Search uses same response format as listings
        return self.mock_listings(axies, total)

    def mock_error(
        self,
        status_code: int = 500,
        message: str = "Internal server error",
    ) -> respx.Route:
        """
        Mock API error response.

        Args:
            status_code: HTTP status code
            message: Error message

        Returns:
            respx Route
        """
        response_data = {
            "errors": [
                {"message": message}
            ]
        }

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(status_code, json=response_data)
        )
        self._routes.append(route)
        return route

    def mock_rate_limit(self) -> respx.Route:
        """
        Mock rate limit response.

        Returns:
            respx Route
        """
        return self.mock_error(
            status_code=429,
            message="Rate limit exceeded. Please slow down."
        )

    def mock_timeout(self) -> respx.Route:
        """
        Mock request timeout.

        Returns:
            respx Route
        """
        import httpx

        route = respx.post(self.BASE_URL).mock(
            side_effect=httpx.TimeoutException("Connection timed out")
        )
        self._routes.append(route)
        return route

    def mock_graphql_response(
        self,
        data: Dict[str, Any],
        errors: Optional[List[Dict[str, Any]]] = None,
    ) -> respx.Route:
        """
        Mock arbitrary GraphQL response.

        Args:
            data: Response data
            errors: Optional GraphQL errors

        Returns:
            respx Route
        """
        response_data = {"data": data}
        if errors:
            response_data["errors"] = errors

        route = respx.post(self.BASE_URL).mock(
            return_value=Response(200, json=response_data)
        )
        self._routes.append(route)
        return route

    def clear(self) -> None:
        """Clear all mocked routes."""
        self._routes.clear()
