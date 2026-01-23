"""
E2E tests for deal hunting user flow.

Tests the complete flow of:
1. User browses current deals
2. User checks detailed valuation for a deal
3. User adds to watchlist (via portfolio tracking)
4. User tracks P&L over time
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Axie, AxieClass, Listing, Sale, Deal,
    Wallet, WalletHolding, HedonicCoefficient, TraitStatistics,
)


@pytest.fixture
async def deal_hunting_setup(db: AsyncSession) -> dict:
    """Set up complete data for deal hunting flow."""
    now = datetime.utcnow()

    # Create axies with varying value profiles
    axies = []
    for i in range(10):
        axie = Axie(
            id=10000 + i,
            name=f"Deal Axie {i}",
            class_=AxieClass.BEAST if i < 5 else AxieClass.AQUATIC,
            genes="0x" + hex(i)[2:].zfill(1) * 64,
            breed_count=i % 4,
            purity_score=4 + (i % 3),
            owner_address=f"0x{'a' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create listings with various prices
    listings = []
    for i, axie in enumerate(axies[:6]):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=Decimal(f"0.0{i+1}"),  # 0.01 to 0.06 ETH
            price_usd=Decimal(f"{(i+1) * 20}"),
            status="active",
            listed_at=now - timedelta(hours=i),
        )
        db.add(listing)
        listings.append(listing)

    # Create sales history for price modeling
    sales = []
    for i in range(20):
        sale = Sale(
            axie_id=10000 + (i % 10),
            seller_address=f"0x{'b' * 38}{i:02d}",
            buyer_address=f"0x{'c' * 38}{i:02d}",
            price_eth=Decimal(f"0.0{(i % 5) + 1}"),
            price_usd=Decimal(f"{((i % 5) + 1) * 20}"),
            sold_at=now - timedelta(days=i),
            tx_hash=f"0x{'d' * 60}{i:04d}",
        )
        db.add(sale)
        sales.append(sale)

    # Create deals (some axies are underpriced)
    deals = []
    for i in range(3):
        deal = Deal(
            axie_id=10000 + i,
            listing_price_eth=Decimal(f"0.0{i+1}"),
            fair_value_eth=Decimal(f"0.0{i+3}"),  # Listed below fair value
            discount_percent=Decimal(f"{(i+1) * 20}"),  # 20%, 40%, 60% discount
            deal_score=50 + (i * 15),  # 50, 65, 80
            deal_type="deal" if i < 2 else "snipe",
            is_active=True,
            detected_at=now - timedelta(hours=i),
        )
        db.add(deal)
        deals.append(deal)

    # Create hedonic coefficients for valuation
    coef = HedonicCoefficient(
        model_version="e2e_test_v1",
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
    for class_name in ["beast", "aquatic"]:
        stat = TraitStatistics(
            trait_key=f"class:{class_name}",
            trait_type="class",
            class_name=class_name,
            avg_price_eth=Decimal("0.025"),
            median_price_eth=Decimal("0.020"),
            std_dev_eth=Decimal("0.010"),
            min_price_eth=Decimal("0.010"),
            max_price_eth=Decimal("0.100"),
            sample_count=100,
            time_window_hours=168,
        )
        db.add(stat)

    # Create user wallet
    user_address = "0x" + "u" * 40
    wallet = Wallet(
        address=user_address,
        alias="Deal Hunter",
        first_seen=now - timedelta(days=30),
        last_active=now,
        total_trades=10,
        total_buy_volume_eth=Decimal("0.5"),
        total_sell_volume_eth=Decimal("0.3"),
    )
    db.add(wallet)

    await db.commit()

    return {
        "axies": axies,
        "listings": listings,
        "sales": sales,
        "deals": deals,
        "wallet": wallet,
        "user_address": user_address,
    }


class TestDealHuntingFlow:
    """E2E tests for deal hunting workflow."""

    async def test_complete_deal_hunting_flow(
        self, client: AsyncClient, deal_hunting_setup: dict, db: AsyncSession
    ):
        """
        Complete flow:
        1. Get market overview
        2. Browse current deals
        3. Check valuation of interesting deal
        4. Purchase and track in portfolio
        """
        setup = deal_hunting_setup

        # Step 1: Get market overview
        market_response = await client.get("/market/stats")
        assert market_response.status_code == 200
        market_data = market_response.json()
        assert market_data["success"] is True

        # Step 2: Browse current deals
        deals_response = await client.get("/valuation/deals/live?min_score=50")
        assert deals_response.status_code == 200
        deals_data = deals_response.json()
        assert deals_data["success"] is True
        assert len(deals_data["data"]) > 0

        # Get the best deal
        best_deal = sorted(
            deals_data["data"],
            key=lambda x: x.get("deal_score", 0),
            reverse=True
        )[0]
        deal_axie_id = best_deal["axie_id"]

        # Step 3: Get detailed valuation for the deal
        valuation_response = await client.get(f"/valuation/{deal_axie_id}")
        assert valuation_response.status_code == 200
        valuation_data = valuation_response.json()
        # Verify we got valuation info

        # Step 4: Check the axie details
        axie_response = await client.get(f"/axies/{deal_axie_id}?include_listing=true")
        assert axie_response.status_code == 200
        axie_data = axie_response.json()
        assert axie_data["success"] is True

        # Step 5: Simulate purchasing by adding to wallet holdings
        # (In real app, this would be done after blockchain transaction)
        user_address = setup["user_address"]
        holding = WalletHolding(
            wallet_address=user_address,
            axie_id=deal_axie_id,
            acquired_at=datetime.utcnow(),
            acquisition_type="purchase",
            cost_basis_eth=Decimal(str(best_deal.get("listing_price_eth", 0.01))),
        )
        db.add(holding)
        await db.commit()

        # Step 6: Check portfolio
        portfolio_response = await client.get(f"/wallets/{user_address}/portfolio")
        assert portfolio_response.status_code == 200
        portfolio_data = portfolio_response.json()
        assert portfolio_data["success"] is True
        assert portfolio_data["data"]["holdings_count"] >= 1

    async def test_snipe_opportunity_flow(
        self, client: AsyncClient, deal_hunting_setup: dict
    ):
        """
        Test flow for time-sensitive snipe opportunities.
        1. Get snipe alerts
        2. Quick valuation check
        3. Decision within time window
        """
        # Step 1: Get snipe opportunities
        snipes_response = await client.get("/valuation/deals/snipes")
        assert snipes_response.status_code == 200
        snipes_data = snipes_response.json()
        assert snipes_data["success"] is True

        if len(snipes_data["data"]) > 0:
            snipe = snipes_data["data"][0]
            axie_id = snipe["axie_id"]

            # Step 2: Batch valuation for quick check
            batch_response = await client.post(
                "/valuation/batch",
                json={"axie_ids": [axie_id]}
            )
            assert batch_response.status_code == 200

            # Step 3: Check floor prices for context
            floors_response = await client.get("/valuation/stats/floors")
            assert floors_response.status_code == 200

    async def test_deal_analysis_by_class(
        self, client: AsyncClient, deal_hunting_setup: dict
    ):
        """
        Test flow for analyzing deals within a specific class.
        """
        # Step 1: Get class-specific deals
        class_deals_response = await client.get("/valuation/deals/class/beast")
        assert class_deals_response.status_code == 200
        class_data = class_deals_response.json()
        assert class_data["success"] is True

        # Step 2: Get floor prices for the class
        floors_response = await client.get("/market/floor-prices?class=beast")
        assert floors_response.status_code == 200

        # Step 3: Get recent sales for price context
        sales_response = await client.get("/market/sales?class=beast&sort=date&order=desc")
        assert sales_response.status_code == 200


class TestDealMonitoringFlow:
    """E2E tests for monitoring deals over time."""

    async def test_deals_summary_monitoring(
        self, client: AsyncClient, deal_hunting_setup: dict
    ):
        """Test flow for periodic deal monitoring."""
        # Get overall deals summary
        summary_response = await client.get("/valuation/deals/summary")
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        assert summary_data["success"] is True

        # Get deal statistics
        stats_response = await client.get("/valuation/deals/stats?hours=24")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data["success"] is True

    async def test_historical_deal_tracking(
        self, client: AsyncClient, deal_hunting_setup: dict
    ):
        """Test tracking historical deal performance."""
        setup = deal_hunting_setup
        axie_id = setup["deals"][0].axie_id

        # Get deal history for specific axie
        history_response = await client.get(
            f"/valuation/deals/axie/{axie_id}?include_history=true"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["success"] is True
