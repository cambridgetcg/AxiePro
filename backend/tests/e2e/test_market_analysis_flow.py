"""
E2E tests for market analysis user flow.

Tests the complete flow of:
1. User monitors market statistics
2. User tracks meta shifts and trends
3. User analyzes class-specific performance
4. User tracks price history and floor movements
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Axie, AxieClass, Listing, Sale, MetaShift,
    TraitStatistics, PriceSnapshot,
)


@pytest.fixture
async def market_analysis_setup(db: AsyncSession) -> dict:
    """Set up complete data for market analysis flow."""
    now = datetime.utcnow()

    # Create diverse axie population
    axies = []
    classes = [
        AxieClass.BEAST, AxieClass.AQUATIC, AxieClass.PLANT,
        AxieClass.BIRD, AxieClass.BUG, AxieClass.REPTILE,
    ]

    for i in range(30):
        class_idx = i % len(classes)
        axie = Axie(
            id=40000 + i,
            name=f"Market Axie {i}",
            class_=classes[class_idx],
            genes="0x" + hex(i)[2:].zfill(1) * 64,
            breed_count=i % 5,
            purity_score=3 + (i % 4),
            owner_address=f"0x{'m' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create active listings across classes
    listings = []
    for i, axie in enumerate(axies[:20]):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=Decimal(f"0.0{(i % 9) + 1}"),
            price_usd=Decimal(f"{((i % 9) + 1) * 20}"),
            status="active",
            listed_at=now - timedelta(hours=i),
        )
        db.add(listing)
        listings.append(listing)

    # Create rich sales history for trend analysis
    sales = []
    for i in range(60):
        # Varying prices to create trends
        base_price = 0.01 + (i % 10) * 0.005
        # Add upward trend for beasts
        if i % 6 == 0:  # Beast
            base_price *= 1.1 + (i / 100)

        sale = Sale(
            axie_id=40000 + (i % 30),
            seller_address=f"0x{'s' * 38}{i:02d}",
            buyer_address=f"0x{'b' * 38}{i:02d}",
            price_eth=Decimal(str(round(base_price, 4))),
            price_usd=Decimal(str(round(base_price * 2000, 2))),
            sold_at=now - timedelta(hours=i * 2),
            tx_hash=f"0x{'sale' * 15}{i:04d}",
        )
        db.add(sale)
        sales.append(sale)

    # Create meta shifts
    shifts = []
    for i, (shift_type, axie_class) in enumerate([
        ("rising", "beast"),
        ("rising", "aquatic"),
        ("falling", "plant"),
        ("emerging", "bird"),
        ("fading", "bug"),
    ]):
        shift = MetaShift(
            trait_key=f"class:{axie_class}",
            class_name=axie_class,
            shift_type=shift_type,
            confidence=60 + i * 5,
            velocity_24h=Decimal(f"{(i - 2) * 8}"),
            velocity_7d=Decimal(f"{(i - 2) * 5}"),
            volume_change_24h=Decimal(f"{(i - 2) * 10}"),
            signals=["test_signal"],
            detected_at=now - timedelta(hours=i),
        )
        db.add(shift)
        shifts.append(shift)

    # Create trait statistics
    trait_stats = []
    for class_name in ["beast", "aquatic", "plant", "bird", "bug", "reptile"]:
        stat = TraitStatistics(
            trait_key=f"class:{class_name}",
            trait_type="class",
            class_name=class_name,
            avg_price_eth=Decimal(f"0.0{classes.index(AxieClass(class_name)) + 2}"),
            median_price_eth=Decimal("0.02"),
            std_dev_eth=Decimal("0.01"),
            min_price_eth=Decimal("0.01"),
            max_price_eth=Decimal("0.10"),
            sample_count=50 + classes.index(AxieClass(class_name)) * 10,
            time_window_hours=168,
        )
        db.add(stat)
        trait_stats.append(stat)

    # Create price snapshots for historical analysis
    snapshots = []
    for i in range(24):  # 24 hours of snapshots
        for class_name in ["beast", "aquatic", "plant"]:
            # Simulate price movement
            base_floor = 0.01 + (0.001 * i) if class_name == "beast" else 0.01
            snapshot = PriceSnapshot(
                trait_key=f"class:{class_name}",
                floor_price_eth=Decimal(str(round(base_floor, 4))),
                avg_price_eth=Decimal(str(round(base_floor * 1.5, 4))),
                volume_eth=Decimal(str(round(0.1 + i * 0.01, 4))),
                listing_count=100 - i,
                sales_count=10 + i,
                captured_at=now - timedelta(hours=23 - i),
            )
            db.add(snapshot)
            snapshots.append(snapshot)

    await db.commit()

    return {
        "axies": axies,
        "listings": listings,
        "sales": sales,
        "shifts": shifts,
        "trait_stats": trait_stats,
        "snapshots": snapshots,
    }


class TestMarketOverviewFlow:
    """E2E tests for market overview dashboard."""

    async def test_complete_market_overview(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """
        Complete flow:
        1. Get market-wide statistics
        2. Check floor prices by class
        3. View recent sales activity
        4. Check market summary
        """
        # Step 1: Get market statistics
        stats_response = await client.get("/market/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["success"] is True

        # Step 2: Get floor prices
        floors_response = await client.get("/market/floor-prices?group_by=class")
        assert floors_response.status_code == 200
        floors_data = floors_response.json()
        assert floors_data["success"] is True

        # Step 3: Get recent sales
        sales_response = await client.get("/market/sales/recent?hours=24")
        assert sales_response.status_code == 200
        sales_data = sales_response.json()
        assert sales_data["success"] is True

        # Step 4: Get market summary
        summary_response = await client.get("/market/analytics/summary")
        assert summary_response.status_code == 200

    async def test_market_activity_monitoring(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test monitoring market activity over time."""
        # Get sales activity
        activity_response = await client.get("/market/sales/activity?hours=24")
        assert activity_response.status_code == 200
        activity_data = activity_response.json()
        assert activity_data["success"] is True

        # Get hourly distribution
        hourly_response = await client.get("/market/sales/hourly?hours=24")
        assert hourly_response.status_code == 200
        hourly_data = hourly_response.json()
        assert hourly_data["success"] is True


class TestMetaTrackingFlow:
    """E2E tests for meta shift tracking."""

    async def test_complete_meta_tracking_flow(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """
        Complete flow:
        1. Get meta summary
        2. Check rising/falling trends
        3. Analyze class-specific meta
        4. Track trait history
        """
        # Step 1: Get meta summary
        summary_response = await client.get("/meta/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        assert summary_data["success"] is True

        # Step 2: Check rising trends
        rising_response = await client.get("/meta/rising?min_confidence=50")
        assert rising_response.status_code == 200
        rising_data = rising_response.json()
        assert rising_data["success"] is True

        # Step 3: Check falling trends
        falling_response = await client.get("/meta/falling?min_confidence=50")
        assert falling_response.status_code == 200

        # Step 4: Get trending traits
        trending_response = await client.get("/meta/trending")
        assert trending_response.status_code == 200

    async def test_velocity_leaders_analysis(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test analyzing fastest moving assets."""
        # Get gainers
        gainers_response = await client.get("/meta/velocity-leaders?direction=up")
        assert gainers_response.status_code == 200
        gainers_data = gainers_response.json()
        assert gainers_data["success"] is True

        # Get losers
        losers_response = await client.get("/meta/velocity-leaders?direction=down")
        assert losers_response.status_code == 200

    async def test_meta_shift_alerts_flow(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test flow for setting up meta shift monitoring."""
        # Get all shifts with high confidence
        shifts_response = await client.get("/meta/shifts?min_confidence=70")
        assert shifts_response.status_code == 200
        shifts_data = shifts_response.json()
        assert shifts_data["success"] is True

        # Get emerging trends (potential early signals)
        emerging_response = await client.get("/meta/emerging?min_confidence=50")
        assert emerging_response.status_code == 200


class TestClassAnalysisFlow:
    """E2E tests for class-specific market analysis."""

    async def test_single_class_deep_dive(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """
        Test deep analysis of a single class:
        1. Get floor price
        2. Get recent sales
        3. Get meta shifts
        4. Get price history
        """
        target_class = "beast"

        # Step 1: Get floor prices for class
        floors_response = await client.get(f"/market/floor-prices?class={target_class}")
        assert floors_response.status_code == 200

        # Step 2: Get class-specific sales
        sales_response = await client.get(f"/market/sales/class/{target_class}")
        assert sales_response.status_code == 200
        sales_data = sales_response.json()
        assert sales_data["success"] is True

        # Step 3: Get meta shifts for class
        meta_response = await client.get(f"/meta/class/{target_class}")
        assert meta_response.status_code == 200
        meta_data = meta_response.json()
        assert meta_data["success"] is True

        # Step 4: Get trait statistics
        stats_response = await client.get(f"/valuation/stats/trait/class:{target_class}")
        assert stats_response.status_code == 200

    async def test_class_comparison_flow(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test comparing multiple classes."""
        classes = ["beast", "aquatic", "plant"]
        class_data = {}

        for class_name in classes:
            # Get floors
            floors = await client.get(f"/market/floor-prices?class={class_name}")
            assert floors.status_code == 200

            # Get sales activity
            activity = await client.get(f"/market/sales/class/{class_name}")
            assert activity.status_code == 200

            class_data[class_name] = {
                "floors": floors.json(),
                "activity": activity.json(),
            }

        # All classes should have data
        assert len(class_data) == 3


class TestPriceHistoryFlow:
    """E2E tests for price history analysis."""

    async def test_trait_price_history(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test viewing price history for a trait."""
        # Get price history for beast class
        history_response = await client.get(
            "/market/analytics/price-history?trait_key=class:beast&interval=1h&limit=24"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["success"] is True

    async def test_class_price_history(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test class-specific price history endpoint."""
        history_response = await client.get(
            "/market/analytics/class-history/beast?interval=1h&limit=24"
        )
        assert history_response.status_code == 200

    async def test_analytics_floor_prices_with_change(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test analytics floor prices with 24h change."""
        floors_response = await client.get("/market/analytics/floor-prices")
        assert floors_response.status_code == 200
        floors_data = floors_response.json()
        assert floors_data["success"] is True


class TestMarketListingsFlow:
    """E2E tests for browsing market listings."""

    async def test_browse_listings_with_filters(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test browsing listings with various filters."""
        # Browse beast listings under 0.05 ETH
        response = await client.get(
            "/market/listings?class=beast&max_price=0.05&sort=price&order=asc"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # All returned listings should be beasts under 0.05 ETH
        for listing in data["data"]:
            assert listing["axie"]["class"] == "beast"
            assert listing["price_eth"] <= 0.05

    async def test_browse_high_purity_listings(
        self, client: AsyncClient, market_analysis_setup: dict
    ):
        """Test finding high purity axies."""
        response = await client.get("/market/listings?purity=5&sort=price&order=asc")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        for listing in data["data"]:
            assert listing["axie"]["purity"] >= 5
