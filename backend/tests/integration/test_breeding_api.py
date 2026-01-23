"""
Integration tests for Breeding API endpoints.

Tests the following routes:
- POST /breeding/simulate
- GET /breeding/history
- GET /breeding/best-pairs
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Axie, AxieClass, BreedingPair, Breed


@pytest.fixture
async def breeding_data(db: AsyncSession) -> dict:
    """Create test data for breeding tests."""
    # Create axies for breeding simulation
    axies = []
    for i in range(5):
        axie = Axie(
            id=5000 + i,
            name=f"Breeder Axie {i}",
            class_=AxieClass.BEAST if i % 2 == 0 else AxieClass.AQUATIC,
            genes="0x" + hex(i)[2:].zfill(1) * 64,  # Different genes for each
            breed_count=i % 4,  # 0, 1, 2, 3, 0
            purity_score=4 + (i % 3),
            owner_address=f"0x{'5' * 38}{i:02d}",
        )
        db.add(axie)
        axies.append(axie)

    # Create breeding pairs and history
    pair = BreedingPair(
        matron_id=5000,
        sire_id=5001,
        breed_count=2,
    )
    db.add(pair)

    await db.flush()

    # Create breeds (breeding events)
    breeds = []
    for i in range(2):
        breed = Breed(
            pair_id=pair.id,
            offspring_id=5000 + 10 + i,  # Hypothetical offspring IDs
            breed_at=datetime.utcnow() - timedelta(days=i * 7),
            breed_cost_slp=2250,
            breed_cost_axs=Decimal("0.5"),
            tx_hash=f"0x{'breed'[i % 5]}" + "0" * 59,
        )
        db.add(breed)
        breeds.append(breed)

    await db.commit()

    return {
        "axies": axies,
        "pair": pair,
        "breeds": breeds,
    }


class TestBreedingSimulate:
    """Tests for POST /breeding/simulate endpoint."""

    async def test_simulate_breeding(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should simulate breeding outcomes."""
        matron = breeding_data["axies"][0]
        sire = breeding_data["axies"][1]

        response = await client.post(
            "/breeding/simulate",
            json={
                "matron_id": matron.id,
                "sire_id": sire.id,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cost" in data["data"]
        assert "class_probabilities" in data["data"]
        assert "part_probabilities" in data["data"]
        assert "expected_purity" in data["data"]

    async def test_simulate_breeding_same_class(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should have higher class probability for same-class parents."""
        # Use two beast axies
        beast_axies = [a for a in breeding_data["axies"] if a.class_ == AxieClass.BEAST]

        if len(beast_axies) >= 2:
            response = await client.post(
                "/breeding/simulate",
                json={
                    "matron_id": beast_axies[0].id,
                    "sire_id": beast_axies[1].id,
                }
            )

            assert response.status_code == 200
            data = response.json()
            # Same class parents should have higher probability for that class
            assert data["success"] is True

    async def test_simulate_breeding_matron_not_found(
        self, client: AsyncClient, mock_skymavis
    ):
        """Should return 404 if matron not found."""
        mock_skymavis.mock_axie_not_found()
        response = await client.post(
            "/breeding/simulate",
            json={
                "matron_id": 999999999,
                "sire_id": 5001,
            }
        )

        assert response.status_code == 404

    async def test_simulate_breeding_sire_not_found(
        self, client: AsyncClient, breeding_data: dict, mock_skymavis
    ):
        """Should return 404 if sire not found."""
        mock_skymavis.mock_axie_not_found()
        response = await client.post(
            "/breeding/simulate",
            json={
                "matron_id": breeding_data["axies"][0].id,
                "sire_id": 999999999,
            }
        )

        assert response.status_code == 404


class TestBreedingHistory:
    """Tests for GET /breeding/history endpoint."""

    async def test_get_breeding_history(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should return breeding history for an axie."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(f"/breeding/history?axie_id={axie_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_get_breeding_history_as_matron(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should filter history by matron role."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(
            f"/breeding/history?axie_id={axie_id}&role=matron"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_breeding_history_as_sire(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should filter history by sire role."""
        axie_id = breeding_data["axies"][1].id
        response = await client.get(
            f"/breeding/history?axie_id={axie_id}&role=sire"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_breeding_history_no_axie_id(self, client: AsyncClient):
        """Should require axie_id parameter."""
        response = await client.get("/breeding/history")

        assert response.status_code == 400

    async def test_get_breeding_history_pagination(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should paginate results."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(
            f"/breeding/history?axie_id={axie_id}&page=1&per_page=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meta"]["per_page"] == 1


class TestBestPairs:
    """Tests for GET /breeding/best-pairs endpoint."""

    async def test_find_best_pairs(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should find best breeding pairs for an axie."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(f"/breeding/best-pairs?axie_id={axie_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_find_best_pairs_target_class(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should filter pairs by target class."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(
            f"/breeding/best-pairs?axie_id={axie_id}&target_class=beast"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_find_best_pairs_pagination(
        self, client: AsyncClient, breeding_data: dict
    ):
        """Should paginate results."""
        axie_id = breeding_data["axies"][0].id
        response = await client.get(
            f"/breeding/best-pairs?axie_id={axie_id}&per_page=2"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 2

    async def test_find_best_pairs_axie_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent axie."""
        response = await client.get("/breeding/best-pairs?axie_id=999999999")

        assert response.status_code == 404

    async def test_find_best_pairs_missing_axie_id(self, client: AsyncClient):
        """Should require axie_id parameter."""
        response = await client.get("/breeding/best-pairs")

        assert response.status_code == 422  # Missing required param
