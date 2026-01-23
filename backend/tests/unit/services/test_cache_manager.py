"""
Unit tests for Redis Cache Manager.

Tests caching operations for valuations, deals, and trait statistics.
"""

import pytest
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.cache.redis_manager import RedisCacheManager, DecimalEncoder


class TestDecimalEncoder:
    """Test JSON encoder for Decimal types."""

    def test_encode_decimal(self):
        """Should encode Decimal as float."""
        data = {"value": Decimal("0.025")}
        result = json.dumps(data, cls=DecimalEncoder)
        parsed = json.loads(result)

        assert parsed["value"] == 0.025

    def test_encode_datetime(self):
        """Should encode datetime as ISO string."""
        dt = datetime(2025, 1, 15, 12, 30, 45)
        data = {"timestamp": dt}
        result = json.dumps(data, cls=DecimalEncoder)
        parsed = json.loads(result)

        assert parsed["timestamp"] == "2025-01-15T12:30:45"

    def test_encode_mixed(self):
        """Should handle mixed types."""
        data = {
            "axie_id": 12345,
            "price": Decimal("0.025"),
            "updated": datetime(2025, 1, 15),
            "is_deal": True,
            "parts": ["eyes", "mouth"],
        }
        result = json.dumps(data, cls=DecimalEncoder)
        parsed = json.loads(result)

        assert parsed["axie_id"] == 12345
        assert parsed["price"] == 0.025
        assert parsed["is_deal"] is True
        assert len(parsed["parts"]) == 2


class TestRedisCacheManager:
    """Test RedisCacheManager methods."""

    @pytest.fixture
    def cache_manager(self) -> RedisCacheManager:
        """Create cache manager without connecting."""
        return RedisCacheManager(
            redis_url="redis://localhost:6379/0",
            key_prefix="test:",
        )

    @pytest.fixture
    def connected_cache(self) -> RedisCacheManager:
        """Create cache manager with mocked Redis client."""
        cache = RedisCacheManager(
            redis_url="redis://localhost:6379/0",
            key_prefix="test:",
        )

        # Mock the Redis client
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.setex.return_value = True
        mock_client.delete.return_value = 1
        mock_client.mget.return_value = [None, None]
        mock_client.zadd.return_value = 1
        mock_client.zrevrangebyscore.return_value = []
        mock_client.zrevrange.return_value = []
        mock_client.zremrangebyrank.return_value = 0
        mock_client.expire.return_value = True
        mock_client.info.return_value = {"used_memory": 1024 * 1024}
        mock_client.scan.return_value = (0, [])

        # Create a proper mock pipeline that supports chaining
        # Note: pipeline() is synchronous, but execute() is async
        mock_pipe = MagicMock()
        mock_pipe.setex.return_value = mock_pipe
        mock_pipe.zadd.return_value = mock_pipe
        mock_pipe.zremrangebyrank.return_value = mock_pipe
        mock_pipe.expire.return_value = mock_pipe
        mock_pipe.execute = AsyncMock(return_value=[True] * 10)

        # Make pipeline() return synchronously
        def sync_pipeline():
            return mock_pipe
        mock_client.pipeline = sync_pipeline

        cache._client = mock_client
        cache._connected = True

        return cache

    def test_key_building(self, cache_manager: RedisCacheManager):
        """Should build keys with prefix."""
        key = cache_manager._key("valuation", "12345")
        assert key == "test:valuation:12345"

        key = cache_manager._key("deals", "beast")
        assert key == "test:deals:beast"

    def test_is_connected_false_initially(self, cache_manager: RedisCacheManager):
        """Should not be connected initially."""
        assert cache_manager.is_connected is False

    def test_is_connected_true_after_connect(self, connected_cache: RedisCacheManager):
        """Should be connected after successful connect."""
        assert connected_cache.is_connected is True

    # =========================================================================
    # Valuation Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_set_valuation(self, connected_cache: RedisCacheManager):
        """Should set valuation in cache."""
        valuation = {
            "axie_id": 12345,
            "hedonic_eth": 0.025,
        }

        result = await connected_cache.set_valuation(12345, valuation)

        assert result is True
        connected_cache._client.setex.assert_called_once()
        call_args = connected_cache._client.setex.call_args
        assert "test:valuation:12345" in call_args[0]
        assert call_args[0][1] == 900  # Default TTL

    @pytest.mark.asyncio
    async def test_set_valuation_custom_ttl(self, connected_cache: RedisCacheManager):
        """Should respect custom TTL."""
        valuation = {"axie_id": 12345}

        await connected_cache.set_valuation(12345, valuation, ttl=60)

        call_args = connected_cache._client.setex.call_args
        assert call_args[0][1] == 60

    @pytest.mark.asyncio
    async def test_get_valuation_miss(self, connected_cache: RedisCacheManager):
        """Should return None on cache miss."""
        connected_cache._client.get.return_value = None

        result = await connected_cache.get_valuation(12345)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_valuation_hit(self, connected_cache: RedisCacheManager):
        """Should return cached valuation on hit."""
        cached_data = json.dumps({"axie_id": 12345, "hedonic_eth": 0.025})
        connected_cache._client.get.return_value = cached_data

        result = await connected_cache.get_valuation(12345)

        assert result is not None
        assert result["axie_id"] == 12345
        assert result["hedonic_eth"] == 0.025

    @pytest.mark.asyncio
    async def test_get_valuations_batch(self, connected_cache: RedisCacheManager):
        """Should get multiple valuations efficiently."""
        # Mock mget to return some hits and some misses
        connected_cache._client.mget.return_value = [
            json.dumps({"axie_id": 1, "hedonic_eth": 0.01}),
            None,
            json.dumps({"axie_id": 3, "hedonic_eth": 0.03}),
        ]

        result = await connected_cache.get_valuations_batch([1, 2, 3])

        assert len(result) == 3
        assert result[1] is not None
        assert result[2] is None
        assert result[3] is not None

    @pytest.mark.asyncio
    async def test_invalidate_valuation(self, connected_cache: RedisCacheManager):
        """Should delete valuation from cache."""
        result = await connected_cache.invalidate_valuation(12345)

        assert result is True
        connected_cache._client.delete.assert_called_once_with("test:valuation:12345")

    # =========================================================================
    # Trait Statistics Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_set_trait_stats(self, connected_cache: RedisCacheManager):
        """Should cache trait statistics."""
        stats = {
            "trait_key": "class:beast",
            "avg_price_eth": 0.025,
        }

        result = await connected_cache.set_trait_stats("class:beast", stats)

        assert result is True
        call_args = connected_cache._client.setex.call_args
        assert "test:trait_stats:class:beast" in call_args[0]
        assert call_args[0][1] == 3600  # Default TTL

    @pytest.mark.asyncio
    async def test_get_trait_stats(self, connected_cache: RedisCacheManager):
        """Should retrieve cached trait stats."""
        cached_data = json.dumps({
            "trait_key": "class:beast",
            "avg_price_eth": 0.025,
        })
        connected_cache._client.get.return_value = cached_data

        result = await connected_cache.get_trait_stats("class:beast")

        assert result is not None
        assert result["avg_price_eth"] == 0.025

    @pytest.mark.asyncio
    async def test_set_trait_stats_batch(self, connected_cache: RedisCacheManager):
        """Should set multiple trait stats efficiently."""
        stats_dict = {
            "class:beast": {"avg_price_eth": 0.025},
            "class:plant": {"avg_price_eth": 0.018},
        }

        # Mock pipeline
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [True, True, True, True]
        connected_cache._client.pipeline.return_value = mock_pipe

        result = await connected_cache.set_trait_stats_batch(stats_dict)

        assert result is True

    # =========================================================================
    # Deal Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_add_deal(self, connected_cache: RedisCacheManager):
        """Should add deal to sorted set."""
        deal = {
            "axie_id": 12345,
            "class": "beast",
            "discount_percent": 25.0,
        }

        # Mock pipeline
        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [1, 0, True]
        connected_cache._client.pipeline.return_value = mock_pipe

        result = await connected_cache.add_deal(deal, deal_score=70, axie_class="beast")

        assert result is True

    @pytest.mark.asyncio
    async def test_add_snipe_to_snipes_list(self, connected_cache: RedisCacheManager):
        """Should add high-score deals to snipes list."""
        deal = {
            "axie_id": 12345,
            "class": "beast",
            "discount_percent": 50.0,
        }

        mock_pipe = AsyncMock()
        mock_pipe.execute.return_value = [1, 0, True] * 3
        connected_cache._client.pipeline.return_value = mock_pipe

        result = await connected_cache.add_deal(deal, deal_score=85)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_top_deals(self, connected_cache: RedisCacheManager):
        """Should retrieve top deals by score."""
        connected_cache._client.zrevrangebyscore.return_value = [
            json.dumps({"axie_id": 1, "deal_score": 90}),
            json.dumps({"axie_id": 2, "deal_score": 80}),
        ]

        result = await connected_cache.get_top_deals(limit=10)

        assert len(result) == 2
        assert result[0]["axie_id"] == 1

    @pytest.mark.asyncio
    async def test_get_top_deals_with_class_filter(self, connected_cache: RedisCacheManager):
        """Should filter deals by class."""
        connected_cache._client.zrevrangebyscore.return_value = [
            json.dumps({"axie_id": 1, "class": "beast"}),
        ]

        result = await connected_cache.get_top_deals(limit=10, axie_class="beast")

        # Check that class-specific key was used
        call_args = connected_cache._client.zrevrangebyscore.call_args
        assert "test:deals:beast" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_top_deals_with_min_score(self, connected_cache: RedisCacheManager):
        """Should respect minimum score filter."""
        connected_cache._client.zrevrangebyscore.return_value = []

        await connected_cache.get_top_deals(limit=10, min_score=70)

        call_args = connected_cache._client.zrevrangebyscore.call_args
        assert call_args[1]["min"] == 70

    @pytest.mark.asyncio
    async def test_get_snipes(self, connected_cache: RedisCacheManager):
        """Should retrieve snipe opportunities."""
        connected_cache._client.zrevrange.return_value = [
            json.dumps({"axie_id": 1, "deal_score": 95}),
        ]

        result = await connected_cache.get_snipes(limit=5)

        assert len(result) == 1
        call_args = connected_cache._client.zrevrange.call_args
        assert "test:snipes:all" in call_args[0]

    # =========================================================================
    # Floor Price Cache Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_set_floor_price(self, connected_cache: RedisCacheManager):
        """Should cache floor price."""
        result = await connected_cache.set_floor_price("beast", 0.008)

        assert result is True
        call_args = connected_cache._client.setex.call_args
        assert "test:floor:beast" in call_args[0]
        assert call_args[0][1] == 300  # 5 min TTL

    @pytest.mark.asyncio
    async def test_get_floor_price(self, connected_cache: RedisCacheManager):
        """Should retrieve cached floor price."""
        connected_cache._client.get.return_value = json.dumps({
            "floor_eth": 0.008,
            "updated_at": "2025-01-15T12:00:00",
        })

        result = await connected_cache.get_floor_price("beast")

        assert result == 0.008

    @pytest.mark.asyncio
    async def test_get_floor_price_miss(self, connected_cache: RedisCacheManager):
        """Should return None on cache miss."""
        connected_cache._client.get.return_value = None

        result = await connected_cache.get_floor_price("beast")

        assert result is None

    # =========================================================================
    # Utility Method Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_health_check(self, connected_cache: RedisCacheManager):
        """Should return health status."""
        result = await connected_cache.health_check()

        # Note: available depends on whether redis lib is installed
        assert result["connected"] is True
        assert "memory_used_mb" in result

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self, cache_manager: RedisCacheManager):
        """Should report disconnected status."""
        result = await cache_manager.health_check()

        assert result["connected"] is False

    @pytest.mark.asyncio
    async def test_clear_all(self, connected_cache: RedisCacheManager):
        """Should clear all cached keys."""
        connected_cache._client.scan.return_value = (0, ["test:key1", "test:key2"])
        connected_cache._client.delete.return_value = 2

        result = await connected_cache.clear_all()

        assert result is True


class TestCacheManagerDisconnected:
    """Test cache manager behavior when disconnected."""

    @pytest.fixture
    def disconnected_cache(self) -> RedisCacheManager:
        """Create disconnected cache manager."""
        cache = RedisCacheManager(redis_url="redis://localhost:6379/0")
        cache._connected = False
        return cache

    @pytest.mark.asyncio
    async def test_set_valuation_when_disconnected(
        self,
        disconnected_cache: RedisCacheManager,
    ):
        """Should return False when not connected."""
        result = await disconnected_cache.set_valuation(12345, {})
        assert result is False

    @pytest.mark.asyncio
    async def test_get_valuation_when_disconnected(
        self,
        disconnected_cache: RedisCacheManager,
    ):
        """Should return None when not connected."""
        result = await disconnected_cache.get_valuation(12345)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_top_deals_when_disconnected(
        self,
        disconnected_cache: RedisCacheManager,
    ):
        """Should return empty list when not connected."""
        result = await disconnected_cache.get_top_deals()
        assert result == []


# Run with: pytest tests/test_cache_manager.py -v
