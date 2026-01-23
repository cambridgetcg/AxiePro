"""
E2E tests for breeding research user flow.

Tests the complete flow of:
1. User researches optimal breeding pairs
2. User simulates breeding outcomes
3. User analyzes expected ROI
4. User tracks breeding history
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Axie, AxieClass, Listing, Sale,
    BreedingPair, Breed,
)


@pytest.fixture
async def breeding_research_setup(db: AsyncSession) -> dict:
    """Set up complete data for breeding research flow."""
    now = datetime.utcnow()

    # Create a diverse pool of breedable axies
    axies = []
    classes = [AxieClass.BEAST, AxieClass.AQUATIC, AxieClass.PLANT]

    # Create pure axies with different classes and breed counts
    for i in range(15):
        class_idx = i % len(classes)
        axie = Axie(
            id=20000 + i,
            name=f"Breeder {i}",
            class_=classes[class_idx],
            genes="0x" + hex(i + 1)[2:].zfill(1) * 64,
            breed_count=i % 5,  # 0-4 breed count
            purity_score=4 + (i % 3),  # 4-6 purity
            owner_address=f"0x{'b' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create listings for some breedable axies
    listings = []
    for i, axie in enumerate(axies[:8]):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=Decimal(f"0.0{(i % 5) + 1}"),
            price_usd=Decimal(f"{((i % 5) + 1) * 20}"),
            status="active",
        )
        db.add(listing)
        listings.append(listing)

    # Create breeding pairs with history
    pairs = []
    breeds = []
    for i in range(3):
        matron_idx = i * 2
        sire_idx = i * 2 + 1

        pair = BreedingPair(
            matron_id=axies[matron_idx].id,
            sire_id=axies[sire_idx].id,
            breed_count=i + 1,
        )
        db.add(pair)
        await db.flush()
        pairs.append(pair)

        # Create offspring records
        for j in range(i + 1):
            breed = Breed(
                pair_id=pair.id,
                offspring_id=30000 + i * 10 + j,  # Hypothetical offspring IDs
                breed_at=now - timedelta(days=(i + 1) * 7 + j),
                breed_cost_slp=2250 * (matron_idx + sire_idx + 2),
                breed_cost_axs=Decimal("0.5"),
                tx_hash=f"0x{'breed' * 12}{i:02d}{j:02d}",
            )
            db.add(breed)
            breeds.append(breed)

    # Create sales data for ROI analysis
    sales = []
    for i in range(10):
        sale = Sale(
            axie_id=20000 + i,
            seller_address=f"0x{'s' * 38}{i:02d}",
            buyer_address=f"0x{'y' * 38}{i:02d}",
            price_eth=Decimal(f"0.0{(i % 3) + 1}"),
            price_usd=Decimal(f"{((i % 3) + 1) * 20}"),
            sold_at=now - timedelta(days=i * 3),
            tx_hash=f"0x{'sale' * 15}{i:04d}",
        )
        db.add(sale)
        sales.append(sale)

    await db.commit()

    return {
        "axies": axies,
        "listings": listings,
        "pairs": pairs,
        "breeds": breeds,
        "sales": sales,
    }


class TestBreedingResearchFlow:
    """E2E tests for breeding research workflow."""

    async def test_complete_breeding_research_flow(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """
        Complete flow:
        1. Browse available breeding stock
        2. Find best pairs for a specific axie
        3. Simulate breeding outcome
        4. Check expected costs and compare to market
        """
        setup = breeding_research_setup
        my_axie = setup["axies"][0]  # First axie is the one we want to breed

        # Step 1: View my axie details
        axie_response = await client.get(f"/axies/{my_axie.id}")
        assert axie_response.status_code == 200
        axie_data = axie_response.json()
        assert axie_data["success"] is True

        # Step 2: Find best breeding partners
        pairs_response = await client.get(f"/breeding/best-pairs?axie_id={my_axie.id}")
        assert pairs_response.status_code == 200
        pairs_data = pairs_response.json()
        assert pairs_data["success"] is True

        if len(pairs_data["data"]) > 0:
            best_partner = pairs_data["data"][0]
            partner_id = best_partner["partner_id"]

            # Step 3: Simulate breeding with best partner
            sim_response = await client.post(
                "/breeding/simulate",
                json={
                    "matron_id": my_axie.id,
                    "sire_id": partner_id,
                }
            )
            assert sim_response.status_code == 200
            sim_data = sim_response.json()
            assert sim_data["success"] is True
            assert "cost" in sim_data["data"]
            assert "class_probabilities" in sim_data["data"]
            assert "part_probabilities" in sim_data["data"]

            # Step 4: Check current floor prices for ROI calculation
            floors_response = await client.get("/market/floor-prices")
            assert floors_response.status_code == 200

    async def test_breeding_with_target_class(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test finding pairs to breed a specific class offspring."""
        setup = breeding_research_setup
        my_axie = setup["axies"][0]

        # Find partners that maximize chance of Beast offspring
        pairs_response = await client.get(
            f"/breeding/best-pairs?axie_id={my_axie.id}&target_class=beast"
        )
        assert pairs_response.status_code == 200
        pairs_data = pairs_response.json()
        assert pairs_data["success"] is True

        # Verify partners are filtered/sorted by target class probability
        for pair in pairs_data["data"]:
            assert "target_class_probability" in pair

    async def test_compare_multiple_breeding_options(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test comparing different breeding combinations."""
        setup = breeding_research_setup
        my_axie = setup["axies"][0]

        # Get top 3 partners
        pairs_response = await client.get(
            f"/breeding/best-pairs?axie_id={my_axie.id}&per_page=3"
        )
        assert pairs_response.status_code == 200
        pairs_data = pairs_response.json()

        # Simulate breeding with each
        simulations = []
        for pair in pairs_data["data"]:
            sim_response = await client.post(
                "/breeding/simulate",
                json={
                    "matron_id": my_axie.id,
                    "sire_id": pair["partner_id"],
                }
            )
            assert sim_response.status_code == 200
            simulations.append(sim_response.json())

        # Compare expected purities
        for sim in simulations:
            assert "expected_purity" in sim["data"]


class TestBreedingHistoryFlow:
    """E2E tests for breeding history tracking."""

    async def test_view_breeding_history(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test viewing past breeding activity."""
        setup = breeding_research_setup
        axie_id = setup["axies"][0].id  # Axie that has bred before

        # Get breeding history
        history_response = await client.get(
            f"/breeding/history?axie_id={axie_id}"
        )
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["success"] is True

    async def test_breeding_history_by_role(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test filtering breeding history by matron/sire role."""
        setup = breeding_research_setup

        # Get matron's history
        matron_id = setup["pairs"][0].matron_id
        matron_history = await client.get(
            f"/breeding/history?axie_id={matron_id}&role=matron"
        )
        assert matron_history.status_code == 200

        # Get sire's history
        sire_id = setup["pairs"][0].sire_id
        sire_history = await client.get(
            f"/breeding/history?axie_id={sire_id}&role=sire"
        )
        assert sire_history.status_code == 200

    async def test_offspring_analysis(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test analyzing offspring of a breeding pair."""
        setup = breeding_research_setup
        pair = setup["pairs"][0]

        # Get children of the matron
        children_response = await client.get(f"/axies/{pair.matron_id}/children")
        assert children_response.status_code == 200
        children_data = children_response.json()
        assert children_data["success"] is True


class TestBreedingCostAnalysis:
    """E2E tests for breeding cost/ROI analysis."""

    async def test_cost_estimation_flow(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test complete cost estimation for breeding."""
        setup = breeding_research_setup
        matron = setup["axies"][0]
        sire = setup["axies"][1]

        # Step 1: Simulate breeding to get costs
        sim_response = await client.post(
            "/breeding/simulate",
            json={
                "matron_id": matron.id,
                "sire_id": sire.id,
            }
        )
        assert sim_response.status_code == 200
        sim_data = sim_response.json()

        # Verify cost breakdown
        assert "cost" in sim_data["data"]
        cost = sim_data["data"]["cost"]
        assert "slp" in cost
        assert "axs" in cost

        # Step 2: Get market data for ROI analysis
        # Check floor prices
        floors_response = await client.get("/market/floor-prices")
        assert floors_response.status_code == 200

        # Check recent sales for realistic pricing
        sales_response = await client.get("/market/sales/recent?hours=24")
        assert sales_response.status_code == 200

    async def test_virgin_breeder_value_analysis(
        self, client: AsyncClient, breeding_research_setup: dict
    ):
        """Test analyzing value of virgin (0 breed) axies."""
        setup = breeding_research_setup

        # Find virgin axies (breed_count = 0)
        virgin_axies = [a for a in setup["axies"] if a.breed_count == 0]

        if len(virgin_axies) >= 2:
            # Simulate breeding with two virgins
            sim_response = await client.post(
                "/breeding/simulate",
                json={
                    "matron_id": virgin_axies[0].id,
                    "sire_id": virgin_axies[1].id,
                }
            )
            assert sim_response.status_code == 200
            sim_data = sim_response.json()

            # Virgin breeders have lowest SLP cost
            cost = sim_data["data"]["cost"]
            # 900 + 900 = 1800 SLP for two virgins
            assert cost["slp"] <= 2000
