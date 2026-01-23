"""
Integration tests for Axies API endpoints.

Tests the following routes:
- GET /axies (search and filter)
- GET /axies/{id} (single axie)
- GET /axies/{id}/genes
- GET /axies/{id}/siblings
- GET /axies/{id}/children
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Axie, AxieClass, Listing
from tests.factories import AxieFactory, ListingFactory


@pytest.fixture
async def seeded_axies(db: AsyncSession) -> list[Axie]:
    """Create test Axies in the database."""
    axies_data = [
        AxieFactory.create(axie_id=1001, class_name="Beast", purity=6, breed_count=0),
        AxieFactory.create(axie_id=1002, class_name="Beast", purity=4, breed_count=2),
        AxieFactory.create(axie_id=1003, class_name="Aquatic", purity=6, breed_count=0),
        AxieFactory.create(axie_id=1004, class_name="Plant", purity=5, breed_count=1),
        AxieFactory.create(axie_id=1005, class_name="Bird", purity=3, breed_count=4),
    ]

    axies = []
    for data in axies_data:
        axie = Axie(
            id=int(data["id"]),
            name=data["name"],
            class_=AxieClass(data["class"]),
            genes=data["genes"],
            breed_count=data["breedCount"],
            purity_score=data["purity"],
            owner_address=data["owner"],
        )
        db.add(axie)
        axies.append(axie)

    await db.commit()
    return axies


@pytest.fixture
async def listed_axies(db: AsyncSession, seeded_axies: list[Axie]) -> list[Listing]:
    """Create listings for some axies."""
    listings = []
    for i, axie in enumerate(seeded_axies[:3]):
        listing = Listing(
            axie_id=axie.id,
            seller_address=axie.owner_address,
            price_eth=0.01 * (i + 1),  # 0.01, 0.02, 0.03
            price_usd=20.0 * (i + 1),
            status="active",
        )
        db.add(listing)
        listings.append(listing)

    await db.commit()
    return listings


class TestSearchAxies:
    """Tests for GET /axies endpoint."""

    async def test_search_axies_no_filters(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should return all axies when no filters applied."""
        response = await client.get("/axies")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(seeded_axies)
        assert "meta" in data
        assert data["meta"]["total"] == len(seeded_axies)

    async def test_search_axies_by_class(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should filter by class."""
        response = await client.get("/axies?class=beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2  # Two beasts
        for axie in data["data"]:
            assert axie["class"] == "beast"

    async def test_search_axies_by_multiple_classes(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should filter by multiple classes."""
        response = await client.get("/axies?classes=beast,aquatic")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3  # 2 beasts + 1 aquatic

    async def test_search_axies_by_purity(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should filter by minimum purity."""
        response = await client.get("/axies?purity=6")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2  # Two with purity=6
        for axie in data["data"]:
            assert axie["purity_score"] >= 6

    async def test_search_axies_by_breed_count(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should filter by max breed count."""
        response = await client.get("/axies?breed_count=1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for axie in data["data"]:
            assert axie["breed_count"] <= 1

    async def test_search_axies_listed_only(
        self, client: AsyncClient, listed_axies: list[Listing]
    ):
        """Should filter to only listed axies."""
        response = await client.get("/axies?listed_only=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == len(listed_axies)

    async def test_search_axies_by_price_range(
        self, client: AsyncClient, listed_axies: list[Listing]
    ):
        """Should filter by price range."""
        response = await client.get("/axies?min_price=0.015&max_price=0.025")

        assert response.status_code == 200
        data = response.json()
        # Only the 0.02 ETH listing should match
        assert data["success"] is True

    async def test_search_axies_pagination(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should paginate results."""
        response = await client.get("/axies?page=1&per_page=2")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        assert data["meta"]["page"] == 1
        assert data["meta"]["per_page"] == 2
        assert data["meta"]["total_pages"] == 3  # 5 axies / 2 per page = 3

    async def test_search_axies_sorting(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should sort results by specified field."""
        response = await client.get("/axies?sort=purity&order=desc")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Check that results are sorted by purity descending
        purities = [a["purity_score"] for a in data["data"]]
        assert purities == sorted(purities, reverse=True)

    async def test_search_axies_invalid_class(self, client: AsyncClient):
        """Should return 400 for invalid class."""
        response = await client.get("/axies?class=invalid_class")

        assert response.status_code == 400


class TestGetAxie:
    """Tests for GET /axies/{id} endpoint."""

    async def test_get_axie_from_db(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should return axie from database."""
        axie = seeded_axies[0]
        response = await client.get(f"/axies/{axie.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(axie.id)
        assert data["data"]["class"] == axie.class_.value

    async def test_get_axie_with_listing(
        self, client: AsyncClient, listed_axies: list[Listing]
    ):
        """Should include listing data when requested."""
        listing = listed_axies[0]
        response = await client.get(f"/axies/{listing.axie_id}?include_listing=true")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "listing" in data["data"]
        assert data["data"]["listing"]["price_eth"] == float(listing.price_eth)

    async def test_get_axie_not_found(self, client: AsyncClient, mock_skymavis):
        """Should return 404 for non-existent axie."""
        mock_skymavis.mock_axie_not_found()
        response = await client.get("/axies/999999999")

        assert response.status_code == 404


class TestGetAxieGenes:
    """Tests for GET /axies/{id}/genes endpoint."""

    async def test_get_axie_genes(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should return parsed gene data."""
        axie = seeded_axies[0]
        response = await client.get(f"/axies/{axie.id}/genes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        # Gene data should contain parsed parts
        assert "class" in data["data"] or "cls" in data["data"]

    async def test_get_axie_genes_not_found(
        self, client: AsyncClient, mock_skymavis
    ):
        """Should return 404 for non-existent axie."""
        mock_skymavis.mock_axie_not_found()
        response = await client.get("/axies/999999999/genes")

        assert response.status_code == 404


class TestGetAxieSiblings:
    """Tests for GET /axies/{id}/siblings endpoint."""

    @pytest.fixture
    async def family_axies(self, db: AsyncSession) -> dict:
        """Create axie family for sibling tests."""
        # Create parents
        matron = Axie(
            id=2001,
            name="Matron",
            class_=AxieClass.BEAST,
            genes="0x" + "a" * 64,
            breed_count=2,
            purity_score=5,
            owner_address="0x" + "1" * 40,
        )
        sire = Axie(
            id=2002,
            name="Sire",
            class_=AxieClass.BEAST,
            genes="0x" + "b" * 64,
            breed_count=2,
            purity_score=5,
            owner_address="0x" + "1" * 40,
        )
        db.add(matron)
        db.add(sire)

        # Create siblings
        child1 = Axie(
            id=2003,
            name="Child 1",
            class_=AxieClass.BEAST,
            genes="0x" + "c" * 64,
            breed_count=0,
            purity_score=5,
            matron_id=2001,
            sire_id=2002,
            owner_address="0x" + "1" * 40,
        )
        child2 = Axie(
            id=2004,
            name="Child 2",
            class_=AxieClass.BEAST,
            genes="0x" + "d" * 64,
            breed_count=0,
            purity_score=6,
            matron_id=2001,
            sire_id=2002,
            owner_address="0x" + "1" * 40,
        )
        db.add(child1)
        db.add(child2)

        await db.commit()

        return {
            "matron": matron,
            "sire": sire,
            "child1": child1,
            "child2": child2,
        }

    async def test_get_siblings(self, client: AsyncClient, family_axies: dict):
        """Should return siblings."""
        child1 = family_axies["child1"]
        response = await client.get(f"/axies/{child1.id}/siblings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should find child2 as sibling
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == str(family_axies["child2"].id)

    async def test_get_siblings_no_siblings(
        self, client: AsyncClient, seeded_axies: list[Axie]
    ):
        """Should return empty for axie without siblings."""
        axie = seeded_axies[0]  # Has no matron/sire
        response = await client.get(f"/axies/{axie.id}/siblings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0

    async def test_get_siblings_not_found(self, client: AsyncClient):
        """Should return 404 for non-existent axie."""
        response = await client.get("/axies/999999999/siblings")

        assert response.status_code == 404


class TestGetAxieChildren:
    """Tests for GET /axies/{id}/children endpoint."""

    async def test_get_children(self, client: AsyncClient, family_axies: dict):
        """Should return children."""
        matron = family_axies["matron"]
        response = await client.get(f"/axies/{matron.id}/children")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2  # Both children

    async def test_get_children_pagination(
        self, client: AsyncClient, family_axies: dict
    ):
        """Should paginate children results."""
        matron = family_axies["matron"]
        response = await client.get(f"/axies/{matron.id}/children?per_page=1")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["meta"]["total"] == 2
