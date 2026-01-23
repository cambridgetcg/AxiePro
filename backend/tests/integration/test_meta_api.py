"""
Integration tests for Meta Shifts API endpoints.

Tests the following routes:
- GET /meta/summary
- GET /meta/shifts
- GET /meta/trending
- GET /meta/velocity-leaders
- GET /meta/class/{class}
- GET /meta/trait/{trait_key}
- GET /meta/rising, /meta/falling, /meta/emerging, /meta/fading
- GET /meta/health
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import MetaShift


@pytest.fixture
async def meta_data(db: AsyncSession) -> dict:
    """Create test data for meta shift tests."""
    shifts = []
    now = datetime.utcnow()

    # Create various shift types
    shift_types = ["rising", "falling", "emerging", "fading"]
    classes = ["beast", "aquatic", "plant", "bird"]

    for i, (shift_type, axie_class) in enumerate(
        [(st, c) for st in shift_types for c in classes[:2]]
    ):
        shift = MetaShift(
            trait_key=f"class:{axie_class}",
            class_name=axie_class,
            shift_type=shift_type,
            confidence=50 + (i * 5) % 50,  # 50-95 range
            velocity_24h=Decimal(f"{(i % 5) * 5 - 10}"),  # -10 to 10
            velocity_7d=Decimal(f"{(i % 7) * 3 - 9}"),  # -9 to 9
            volume_change_24h=Decimal(f"{(i % 3) * 10 - 10}"),  # -10 to 10
            signals=["test_signal_1", "test_signal_2"],
            detected_at=now - timedelta(hours=i % 24),
        )
        db.add(shift)
        shifts.append(shift)

    # Create some trait-level shifts
    parts = ["horn", "back", "tail"]
    for i, part in enumerate(parts):
        shift = MetaShift(
            trait_key=f"part:{part}:test",
            class_name="beast",
            shift_type="rising" if i % 2 == 0 else "emerging",
            confidence=60 + i * 10,
            velocity_24h=Decimal(f"{i * 5}"),
            velocity_7d=Decimal(f"{i * 3}"),
            volume_change_24h=Decimal(f"{i * 8}"),
            signals=["part_signal"],
            detected_at=now - timedelta(hours=i),
        )
        db.add(shift)
        shifts.append(shift)

    await db.commit()

    return {"shifts": shifts}


class TestMetaSummary:
    """Tests for GET /meta/summary endpoint."""

    async def test_get_meta_summary(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return meta summary."""
        response = await client.get("/meta/summary")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_meta_summary_no_cache(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should work without cache."""
        response = await client.get("/meta/summary?use_cache=false")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMetaShifts:
    """Tests for GET /meta/shifts endpoint."""

    async def test_get_meta_shifts(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return all shifts."""
        response = await client.get("/meta/shifts")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    async def test_get_meta_shifts_by_type(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter shifts by type."""
        response = await client.get("/meta/shifts?shift_type=rising")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # All shifts should be rising type
        for shift in data["data"]:
            assert shift.get("shift_type") == "rising"

    async def test_get_meta_shifts_min_confidence(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter by minimum confidence."""
        response = await client.get("/meta/shifts?min_confidence=70")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        for shift in data["data"]:
            assert shift.get("confidence", 0) >= 70

    async def test_get_meta_shifts_limit(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should respect limit parameter."""
        response = await client.get("/meta/shifts?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 5

    async def test_get_meta_shifts_invalid_type(self, client: AsyncClient):
        """Should reject invalid shift type."""
        response = await client.get("/meta/shifts?shift_type=invalid")

        assert response.status_code == 400


class TestTrendingTraits:
    """Tests for GET /meta/trending endpoint."""

    async def test_get_trending_traits(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return trending traits."""
        response = await client.get("/meta/trending")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_trending_traits_filter_types(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter by shift types."""
        response = await client.get("/meta/trending?shift_types=rising,emerging")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_trending_traits_min_confidence(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter by minimum confidence."""
        response = await client.get("/meta/trending?min_confidence=50")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestVelocityLeaders:
    """Tests for GET /meta/velocity-leaders endpoint."""

    async def test_get_velocity_leaders_up(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return fastest gainers."""
        response = await client.get("/meta/velocity-leaders?direction=up")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_velocity_leaders_down(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return fastest losers."""
        response = await client.get("/meta/velocity-leaders?direction=down")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_velocity_leaders_limit(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should respect limit."""
        response = await client.get("/meta/velocity-leaders?limit=3")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 3


class TestClassMeta:
    """Tests for GET /meta/class/{class} endpoint."""

    async def test_get_class_meta(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return meta for a class."""
        response = await client.get("/meta/class/beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_class_meta_hours_filter(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter by hours."""
        response = await client.get("/meta/class/beast?hours=12")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestTraitMetaHistory:
    """Tests for GET /meta/trait/{trait_key} endpoint."""

    async def test_get_trait_history(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return trait meta history."""
        response = await client.get("/meta/trait/class:beast")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_trait_history_days_filter(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should filter by days."""
        response = await client.get("/meta/trait/class:beast?days=3")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    async def test_get_trait_history_not_found(self, client: AsyncClient):
        """Should return 404 for unknown trait."""
        response = await client.get("/meta/trait/unknown:trait")

        assert response.status_code == 404


class TestConvenienceEndpoints:
    """Tests for shift type shortcut endpoints."""

    async def test_get_rising(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return rising shifts."""
        response = await client.get("/meta/rising")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meta"]["shift_type"] == "rising"

    async def test_get_falling(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return falling shifts."""
        response = await client.get("/meta/falling")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meta"]["shift_type"] == "falling"

    async def test_get_emerging(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return emerging shifts."""
        response = await client.get("/meta/emerging")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meta"]["shift_type"] == "emerging"

    async def test_get_fading(
        self, client: AsyncClient, meta_data: dict
    ):
        """Should return fading shifts."""
        response = await client.get("/meta/fading")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["meta"]["shift_type"] == "fading"


class TestMetaHealth:
    """Tests for GET /meta/health endpoint."""

    async def test_meta_health(self, client: AsyncClient, meta_data: dict):
        """Should return health status."""
        response = await client.get("/meta/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "database_available" in data["data"]
