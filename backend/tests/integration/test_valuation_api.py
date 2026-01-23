"""
Integration tests for Valuation API endpoints.

Tests the following routes:
- GET /valuation/{axie_id}
- POST /valuation/batch
- GET /valuation/deals/*
- GET /valuation/stats/*
- GET /valuation/model/*
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Axie, AxieClass, Listing, Sale,
    HedonicCoefficient, TraitStatistics, Deal,
)


@pytest.fixture
async def valuation_data(db: AsyncSession) -> dict:
    """Create test data for valuation tests."""
    # Create axies
    axies = []
    for i in range(3):
        axie = Axie(
            id=4000 + i,
            name=f"Valuation Axie {i}",
            class_=AxieClass.BEAST,
            genes="0x" + "a" * 64,
            breed_count=i,
            purity_score=5 + (i % 2),
            owner_address=f"0x{'1' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create listings for the axies
    listings = []
    for i, axie in enumerate(axies):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=Decimal(f"0.0{i+1}"),
            price_usd=Decimal(f"{(i+1)*20}"),
            status="active",
        )
        db.add(listing)
        listings.append(listing)

    # Create sales for price history
    now = datetime.utcnow()
    sales = []
    for i in range(10):
        sale = Sale(
            axie_id=4000 + (i % 3),
            seller_address=f"0x{'3' * 38}{i:02d}",
            buyer_address=f"0x{'4' * 38}{i:02d}",
            price_eth=Decimal(f"0.0{(i % 3) + 1}"),
            price_usd=Decimal(f"{((i % 3) + 1) * 20}"),
            sold_at=now - timedelta(days=i),
            tx_hash=f"0x{'def'[i % 3]}" + "0" * 63,
        )
        db.add(sale)
        sales.append(sale)

    # Create hedonic coefficients for valuation
    coef = HedonicCoefficient(
        model_version="test_v1",
        feature_name="class:beast",
        coefficient=Decimal("0.15"),
        std_error=Decimal("0.01"),
        t_statistic=Decimal("15.0"),
        p_value=Decimal("0.001"),
        is_active=True,
        r_squared=Decimal("0.85"),
        adj_r_squared=Decimal("0.84"),
        rmse=Decimal("0.05"),
        sample_size=1000,
        feature_count=20,
        train_start=now - timedelta(days=30),
        train_end=now,
    )
    db.add(coef)

    # Create trait statistics
    trait_stat = TraitStatistics(
        trait_key="class:beast",
        trait_type="class",
        class_name="beast",
        avg_price_eth=Decimal("0.025"),
        median_price_eth=Decimal("0.020"),
        std_dev_eth=Decimal("0.010"),
        min_price_eth=Decimal("0.010"),
        max_price_eth=Decimal("0.100"),
        sample_count=100,
        time_window_hours=168,
    )
    db.add(trait_stat)

    # Create deals
    deals = []
    for i in range(3):
        deal = Deal(
            axie_id=4000 + i,
            listing_price_eth=Decimal(f"0.0{i+1}"),
            fair_value_eth=Decimal(f"0.0{i+2}"),
            discount_percent=Decimal(f"{(i+1) * 15}"),
            deal_score=50 + (i * 10),
            deal_type="deal" if i < 2 else "snipe",
            is_active=True,
            detected_at=now - timedelta(hours=i),
        )
        db.add(deal)
        deals.append(deal)

    await db.commit()

    return {
        "axies": axies,
        "listings": listings,
        "sales": sales,
        "deals": deals,
    }


class TestGetValuation:
    """Tests for GET /valuation/{axie_id} endpoint."""

    async def test_get_valuation(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return valuation for an axie."""
        axie = valuation_data["axies"][0]
        response = await client.get(f"/valuation/{axie.id}")

        assert response.status_code == 200
        data = response.json()
        assert "valuation" in data or "axie_id" in data

    async def test_get_valuation_no_cache(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should work without cache."""
        axie = valuation_data["axies"][0]
        response = await client.get(f"/valuation/{axie.id}?use_cache=false")

        assert response.status_code == 200

    async def test_get_valuation_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent axie."""
        response = await client.get("/valuation/999999999")

        assert response.status_code == 404


class TestBatchValuation:
    """Tests for POST /valuation/batch endpoint."""

    async def test_batch_valuation(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return valuations for multiple axies."""
        axie_ids = [a.id for a in valuation_data["axies"]]
        response = await client.post(
            "/valuation/batch",
            json={"axie_ids": axie_ids}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["valuations"]) == len(axie_ids)

    async def test_batch_valuation_partial_success(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should handle mix of found and not found axies."""
        axie_ids = [valuation_data["axies"][0].id, 999999999]
        response = await client.post(
            "/valuation/batch",
            json={"axie_ids": axie_ids}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_batch_valuation_empty_list(self, client: AsyncClient):
        """Should reject empty list."""
        response = await client.post(
            "/valuation/batch",
            json={"axie_ids": []}
        )

        assert response.status_code == 422  # Validation error

    async def test_batch_valuation_too_many(self, client: AsyncClient):
        """Should reject more than 100 axies."""
        axie_ids = list(range(1, 102))  # 101 IDs
        response = await client.post(
            "/valuation/batch",
            json={"axie_ids": axie_ids}
        )

        assert response.status_code == 422


class TestLiveDeals:
    """Tests for GET /valuation/deals/live endpoint."""

    async def test_get_live_deals(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return live deals."""
        response = await client.get("/valuation/deals/live")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_get_live_deals_by_class(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should filter deals by class."""
        response = await client.get("/valuation/deals/live?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_live_deals_min_score(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should filter by minimum deal score."""
        response = await client.get("/valuation/deals/live?min_score=60")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # All deals should have score >= 60
        for deal in data["data"]:
            if "deal_score" in deal:
                assert deal["deal_score"] >= 60


class TestSnipeOpportunities:
    """Tests for GET /valuation/deals/snipes endpoint."""

    async def test_get_snipes(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return snipe opportunities."""
        response = await client.get("/valuation/deals/snipes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_snipes_with_limit(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should respect limit parameter."""
        response = await client.get("/valuation/deals/snipes?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 5


class TestDealsSummary:
    """Tests for GET /valuation/deals/summary endpoint."""

    async def test_get_deals_summary(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return deals summary."""
        response = await client.get("/valuation/deals/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDealsStats:
    """Tests for GET /valuation/deals/stats endpoint."""

    async def test_get_deals_stats(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return deal statistics."""
        response = await client.get("/valuation/deals/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestClassDeals:
    """Tests for GET /valuation/deals/class/{class} endpoint."""

    async def test_get_class_deals(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return deals for a class."""
        response = await client.get("/valuation/deals/class/beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestAxieDeal:
    """Tests for GET /valuation/deals/axie/{axie_id} endpoint."""

    async def test_get_axie_deal(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return deal for specific axie."""
        axie = valuation_data["axies"][0]
        response = await client.get(f"/valuation/deals/axie/{axie.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_axie_deal_with_history(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should include deal history when requested."""
        axie = valuation_data["axies"][0]
        response = await client.get(
            f"/valuation/deals/axie/{axie.id}?include_history=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTraitStatistics:
    """Tests for GET /valuation/stats/trait/{key} endpoint."""

    async def test_get_trait_stats(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return trait statistics."""
        response = await client.get("/valuation/stats/trait/class:beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_trait_stats_not_found(self, client: AsyncClient):
        """Should return 404 for unknown trait."""
        response = await client.get("/valuation/stats/trait/invalid:trait")

        assert response.status_code == 404


class TestFloorPrices:
    """Tests for GET /valuation/stats/floors endpoint."""

    async def test_get_floor_prices(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return floor prices by class."""
        response = await client.get("/valuation/stats/floors")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestModelInfo:
    """Tests for GET /valuation/model/info endpoint."""

    async def test_get_model_info(
        self, client: AsyncClient, valuation_data: dict
    ):
        """Should return model information."""
        response = await client.get("/valuation/model/info")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCacheHealth:
    """Tests for GET /valuation/cache/health endpoint."""

    async def test_cache_health(self, client: AsyncClient):
        """Should return cache health status."""
        response = await client.get("/valuation/cache/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
