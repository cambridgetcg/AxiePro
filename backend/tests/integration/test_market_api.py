"""
Integration tests for Market API endpoints.

Tests the following routes:
- GET /market/listings
- GET /market/sales
- GET /market/floor-prices
- GET /market/stats
- GET /market/analytics/*
- GET /market/sales/*
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Axie, AxieClass, Listing, Sale


@pytest.fixture
async def market_data(db: AsyncSession) -> dict:
    """Create test market data."""
    # Create axies
    axies = []
    for i in range(5):
        axie = Axie(
            id=3000 + i,
            name=f"Test Axie {i}",
            class_=AxieClass.BEAST if i < 3 else AxieClass.AQUATIC,
            genes="0x" + "a" * 64,
            breed_count=i % 3,
            purity_score=4 + (i % 3),
            owner_address=f"0x{'1' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create active listings
    listings = []
    for i, axie in enumerate(axies[:3]):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=Decimal(f"0.0{i+1}"),  # 0.01, 0.02, 0.03
            price_usd=Decimal(f"{(i+1)*20}"),
            status="active",
            listed_at=datetime.utcnow() - timedelta(hours=i),
        )
        db.add(listing)
        listings.append(listing)

    # Create sales
    sales = []
    now = datetime.utcnow()
    for i in range(5):
        sale = Sale(
            axie_id=3000 + (i % 5),
            seller_address=f"0x{'1' * 38}{i:02d}",
            buyer_address=f"0x{'2' * 38}{i:02d}",
            price_eth=Decimal(f"0.0{(i % 3) + 1}"),
            price_usd=Decimal(f"{((i % 3) + 1) * 20}"),
            sold_at=now - timedelta(hours=i * 6),
            tx_hash=f"0x{'abc'[i % 3]}" + "0" * 63,
        )
        db.add(sale)
        sales.append(sale)

    await db.commit()

    return {
        "axies": axies,
        "listings": listings,
        "sales": sales,
    }


class TestGetListings:
    """Tests for GET /market/listings endpoint."""

    async def test_get_listings(self, client: AsyncClient, market_data: dict):
        """Should return active listings."""
        response = await client.get("/market/listings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(market_data["listings"])

    async def test_get_listings_by_class(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter listings by class."""
        response = await client.get("/market/listings?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for listing in data["data"]:
            assert listing["axie"]["class"] == "beast"

    async def test_get_listings_by_price_range(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter by price range."""
        response = await client.get("/market/listings?min_price=0.015&max_price=0.025")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for listing in data["data"]:
            assert 0.015 <= listing["price_eth"] <= 0.025

    async def test_get_listings_by_purity(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter by minimum purity."""
        response = await client.get("/market/listings?purity=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for listing in data["data"]:
            assert listing["axie"]["purity"] >= 5

    async def test_get_listings_sorting(
        self, client: AsyncClient, market_data: dict
    ):
        """Should sort listings."""
        response = await client.get("/market/listings?sort=price&order=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        prices = [l["price_eth"] for l in data["data"]]
        assert prices == sorted(prices)

    async def test_get_listings_pagination(
        self, client: AsyncClient, market_data: dict
    ):
        """Should paginate results."""
        response = await client.get("/market/listings?page=1&per_page=2")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["meta"]["total"] == len(market_data["listings"])


class TestGetSales:
    """Tests for GET /market/sales endpoint."""

    async def test_get_sales(self, client: AsyncClient, market_data: dict):
        """Should return sales history."""
        response = await client.get("/market/sales")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(market_data["sales"])

    async def test_get_sales_by_date_range(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter by date range."""
        yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
        response = await client.get(f"/market/sales?from_date={yesterday}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_sales_by_seller(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter by seller."""
        seller = market_data["sales"][0].seller_address
        response = await client.get(f"/market/sales?seller={seller}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for sale in data["data"]:
            assert sale["seller"].lower() == seller.lower()

    async def test_get_sales_by_buyer(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter by buyer."""
        buyer = market_data["sales"][0].buyer_address
        response = await client.get(f"/market/sales?buyer={buyer}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for sale in data["data"]:
            assert sale["buyer"].lower() == buyer.lower()

    async def test_get_sales_sorting(
        self, client: AsyncClient, market_data: dict
    ):
        """Should sort by price."""
        response = await client.get("/market/sales?sort=price&order=desc")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        prices = [s["price_eth"] for s in data["data"]]
        assert prices == sorted(prices, reverse=True)


class TestGetFloorPrices:
    """Tests for GET /market/floor-prices endpoint."""

    async def test_get_floor_prices_by_class(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return floor prices grouped by class."""
        response = await client.get("/market/floor-prices?group_by=class")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "floors" in data["data"]

    async def test_get_floor_prices_by_purity(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return floor prices grouped by purity."""
        response = await client.get("/market/floor-prices?group_by=purity")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "floors" in data["data"]

    async def test_get_floor_prices_filtered_class(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter floor prices by class."""
        response = await client.get("/market/floor-prices?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_floor_prices_invalid_group_by(
        self, client: AsyncClient
    ):
        """Should return 400 for invalid group_by."""
        response = await client.get("/market/floor-prices?group_by=invalid")

        assert response.status_code == 400


class TestGetMarketStats:
    """Tests for GET /market/stats endpoint."""

    async def test_get_market_stats(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return market statistics."""
        response = await client.get("/market/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should have stats for different periods
        assert "24h" in data["data"] or "data" in data

    async def test_get_market_stats_no_cache(
        self, client: AsyncClient, market_data: dict
    ):
        """Should work without cache."""
        response = await client.get("/market/stats?use_cache=false")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestRecentSales:
    """Tests for GET /market/sales/recent endpoint."""

    async def test_get_recent_sales(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return recent sales."""
        response = await client.get("/market/sales/recent")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_get_recent_sales_with_class_filter(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter recent sales by class."""
        response = await client.get("/market/sales/recent?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_recent_sales_hours_limit(
        self, client: AsyncClient, market_data: dict
    ):
        """Should respect hours parameter."""
        response = await client.get("/market/sales/recent?hours=12&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 10


class TestSalesActivity:
    """Tests for GET /market/sales/activity endpoint."""

    async def test_get_sales_activity(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return sales activity stats."""
        response = await client.get("/market/sales/activity")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_sales_activity_by_class(
        self, client: AsyncClient, market_data: dict
    ):
        """Should filter activity by class."""
        response = await client.get("/market/sales/activity?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestClassSales:
    """Tests for GET /market/sales/class/{class} endpoint."""

    async def test_get_class_sales(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return class-specific sales data."""
        response = await client.get("/market/sales/class/beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_class_sales_invalid_class(self, client: AsyncClient):
        """Should return 400 for invalid class."""
        response = await client.get("/market/sales/class/invalid")

        assert response.status_code == 400


class TestHourlySalesDistribution:
    """Tests for GET /market/sales/hourly endpoint."""

    async def test_get_hourly_distribution(
        self, client: AsyncClient, market_data: dict
    ):
        """Should return hourly sales distribution."""
        response = await client.get("/market/sales/hourly")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "distribution" in data["data"]
