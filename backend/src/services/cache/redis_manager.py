"""
Redis Cache Manager

Provides caching layer for valuations, trait statistics, and deals.
Implements TTL-based expiration and efficient batch operations.

Cache key structure:
- valuation:{axie_id} -> ValuationResult (TTL: 15 min)
- trait_stats:{trait_key} -> TraitStatistics (TTL: 1 hour)
- deals:{class} -> SortedSet of deals by score (TTL: 24 hours)
- deals:all -> SortedSet of all deals (TTL: 24 hours)
- snipes:all -> SortedSet of snipe opportunities (TTL: 24 hours)
- floor:{class} -> Floor price (TTL: 5 min)
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any, TypeVar, Generic
from dataclasses import asdict

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class RedisCacheManager:
    """
    Redis-based cache manager for valuation data.

    Provides async caching with automatic TTL management
    and batch operations for efficiency.

    Usage:
        cache = RedisCacheManager(redis_url)
        await cache.connect()

        # Cache a valuation
        await cache.set_valuation(axie_id, result)

        # Get cached valuation
        result = await cache.get_valuation(axie_id)

        # Close connection
        await cache.close()
    """

    # Default TTLs in seconds
    TTL_VALUATION = 900      # 15 minutes
    TTL_TRAIT_STATS = 3600   # 1 hour
    TTL_DEALS = 86400        # 24 hours
    TTL_FLOOR = 300          # 5 minutes

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "axie:",
    ):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            key_prefix: Prefix for all cache keys
        """
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.key_prefix = key_prefix
        self._client: Optional["redis.Redis"] = None
        self._connected = False

    async def connect(self) -> bool:
        """
        Connect to Redis.

        Returns:
            True if connected successfully, False otherwise
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, caching disabled")
            return False

        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._connected = False
            return False

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        return self._connected and self._client is not None

    def _key(self, *parts: str) -> str:
        """Build cache key with prefix."""
        return f"{self.key_prefix}{':'.join(parts)}"

    async def _set(
        self,
        key: str,
        value: Any,
        ttl: int,
    ) -> bool:
        """Set a value with TTL."""
        if not self.is_connected:
            return False

        try:
            serialized = json.dumps(value, cls=DecimalEncoder)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def _get(self, key: str) -> Optional[dict]:
        """Get a value from cache."""
        if not self.is_connected:
            return None

        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {e}")
            return None

    async def _delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if not self.is_connected:
            return False

        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {e}")
            return False

    # =========================================================================
    # Valuation Cache Operations
    # =========================================================================

    async def set_valuation(
        self,
        axie_id: int,
        valuation: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache a valuation result.

        Args:
            axie_id: Axie ID
            valuation: Valuation result dict
            ttl: Optional custom TTL in seconds
        """
        key = self._key("valuation", str(axie_id))
        return await self._set(key, valuation, ttl or self.TTL_VALUATION)

    async def get_valuation(self, axie_id: int) -> Optional[dict]:
        """
        Get cached valuation.

        Args:
            axie_id: Axie ID

        Returns:
            Cached valuation dict or None if not found/expired
        """
        key = self._key("valuation", str(axie_id))
        return await self._get(key)

    async def get_valuations_batch(
        self,
        axie_ids: list[int],
    ) -> dict[int, Optional[dict]]:
        """
        Get multiple cached valuations efficiently.

        Args:
            axie_ids: List of Axie IDs

        Returns:
            Dict mapping axie_id to valuation (or None if not cached)
        """
        if not self.is_connected or not axie_ids:
            return {aid: None for aid in axie_ids}

        try:
            keys = [self._key("valuation", str(aid)) for aid in axie_ids]
            values = await self._client.mget(keys)

            result = {}
            for aid, val in zip(axie_ids, values):
                if val:
                    result[aid] = json.loads(val)
                else:
                    result[aid] = None

            return result
        except Exception as e:
            logger.warning(f"Batch cache get failed: {e}")
            return {aid: None for aid in axie_ids}

    async def invalidate_valuation(self, axie_id: int) -> bool:
        """Invalidate cached valuation."""
        key = self._key("valuation", str(axie_id))
        return await self._delete(key)

    # =========================================================================
    # Trait Statistics Cache Operations
    # =========================================================================

    async def set_trait_stats(
        self,
        trait_key: str,
        stats: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache trait statistics.

        Args:
            trait_key: Trait key (e.g., "class:beast", "part:eyes:kotaro")
            stats: Statistics dict
            ttl: Optional custom TTL
        """
        key = self._key("trait_stats", trait_key)
        return await self._set(key, stats, ttl or self.TTL_TRAIT_STATS)

    async def get_trait_stats(self, trait_key: str) -> Optional[dict]:
        """Get cached trait statistics."""
        key = self._key("trait_stats", trait_key)
        return await self._get(key)

    async def set_trait_stats_batch(
        self,
        stats_dict: dict[str, dict],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache multiple trait statistics efficiently.

        Args:
            stats_dict: Dict mapping trait_key to stats
            ttl: Optional custom TTL
        """
        if not self.is_connected or not stats_dict:
            return False

        try:
            pipe = self._client.pipeline()
            ttl_val = ttl or self.TTL_TRAIT_STATS

            for trait_key, stats in stats_dict.items():
                key = self._key("trait_stats", trait_key)
                serialized = json.dumps(stats, cls=DecimalEncoder)
                pipe.setex(key, ttl_val, serialized)

            await pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"Batch trait stats set failed: {e}")
            return False

    # =========================================================================
    # Deal Cache Operations (Sorted Sets)
    # =========================================================================

    async def add_deal(
        self,
        deal: dict,
        deal_score: int,
        axie_class: Optional[str] = None,
    ) -> bool:
        """
        Add a deal to the cache.

        Deals are stored in sorted sets by score for quick retrieval
        of top deals.

        Args:
            deal: Deal data dict
            deal_score: Deal score (0-100) for ranking
            axie_class: Optional class for class-specific list
        """
        if not self.is_connected:
            return False

        try:
            serialized = json.dumps(deal, cls=DecimalEncoder)
            pipe = self._client.pipeline()

            # Add to global deals list
            key_all = self._key("deals", "all")
            pipe.zadd(key_all, {serialized: deal_score})
            pipe.zremrangebyrank(key_all, 0, -101)  # Keep top 100
            pipe.expire(key_all, self.TTL_DEALS)

            # Add to class-specific list if class provided
            if axie_class:
                key_class = self._key("deals", axie_class.lower())
                pipe.zadd(key_class, {serialized: deal_score})
                pipe.zremrangebyrank(key_class, 0, -51)  # Keep top 50 per class
                pipe.expire(key_class, self.TTL_DEALS)

            # Add to snipes list if high score
            if deal_score >= 80:
                key_snipes = self._key("snipes", "all")
                pipe.zadd(key_snipes, {serialized: deal_score})
                pipe.zremrangebyrank(key_snipes, 0, -51)  # Keep top 50 snipes
                pipe.expire(key_snipes, self.TTL_DEALS)

            await pipe.execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to add deal to cache: {e}")
            return False

    async def get_top_deals(
        self,
        limit: int = 20,
        axie_class: Optional[str] = None,
        min_score: int = 0,
    ) -> list[dict]:
        """
        Get top deals by score.

        Args:
            limit: Maximum number of deals to return
            axie_class: Optional class filter
            min_score: Minimum deal score

        Returns:
            List of deal dicts sorted by score descending
        """
        if not self.is_connected:
            return []

        try:
            if axie_class:
                key = self._key("deals", axie_class.lower())
            else:
                key = self._key("deals", "all")

            # Get top deals by score (descending)
            results = await self._client.zrevrangebyscore(
                key,
                max=100,
                min=min_score,
                start=0,
                num=limit,
            )

            deals = []
            for item in results:
                try:
                    deal = json.loads(item)
                    deals.append(deal)
                except json.JSONDecodeError:
                    continue

            return deals
        except Exception as e:
            logger.warning(f"Failed to get deals from cache: {e}")
            return []

    async def get_snipes(self, limit: int = 20) -> list[dict]:
        """Get top snipe opportunities."""
        if not self.is_connected:
            return []

        try:
            key = self._key("snipes", "all")
            results = await self._client.zrevrange(key, 0, limit - 1)

            snipes = []
            for item in results:
                try:
                    snipe = json.loads(item)
                    snipes.append(snipe)
                except json.JSONDecodeError:
                    continue

            return snipes
        except Exception as e:
            logger.warning(f"Failed to get snipes from cache: {e}")
            return []

    async def remove_deal(self, axie_id: int) -> bool:
        """
        Remove a deal from cache (e.g., when sold or delisted).

        Note: This requires scanning - for production, store
        axie_id -> deal_key mapping.
        """
        # For simplicity, we'll let deals expire naturally
        # A production system would maintain an index
        return True

    # =========================================================================
    # Floor Price Cache Operations
    # =========================================================================

    async def set_floor_price(
        self,
        axie_class: str,
        floor_eth: float,
        ttl: Optional[int] = None,
    ) -> bool:
        """Cache floor price for a class."""
        key = self._key("floor", axie_class.lower())
        data = {
            "floor_eth": floor_eth,
            "updated_at": datetime.utcnow().isoformat(),
        }
        return await self._set(key, data, ttl or self.TTL_FLOOR)

    async def get_floor_price(self, axie_class: str) -> Optional[float]:
        """Get cached floor price."""
        key = self._key("floor", axie_class.lower())
        data = await self._get(key)
        if data:
            return data.get("floor_eth")
        return None

    async def get_all_floor_prices(self) -> dict[str, float]:
        """Get all cached floor prices."""
        if not self.is_connected:
            return {}

        classes = ["beast", "bug", "bird", "plant", "aquatic", "reptile", "mech", "dawn", "dusk"]
        result = {}

        for axie_class in classes:
            floor = await self.get_floor_price(axie_class)
            if floor is not None:
                result[axie_class] = floor

        return result

    # =========================================================================
    # Utility Methods
    # =========================================================================

    async def health_check(self) -> dict:
        """Check cache health status."""
        status = {
            "available": REDIS_AVAILABLE,
            "connected": self.is_connected,
            "url": self.redis_url if self.is_connected else None,
        }

        if self.is_connected:
            try:
                info = await self._client.info("memory")
                status["memory_used_mb"] = info.get("used_memory", 0) / (1024 * 1024)
                status["ping_ok"] = await self._client.ping()
            except Exception as e:
                status["error"] = str(e)

        return status

    async def clear_all(self) -> bool:
        """Clear all cached data (use with caution)."""
        if not self.is_connected:
            return False

        try:
            # Only clear keys with our prefix
            pattern = f"{self.key_prefix}*"
            cursor = 0
            deleted = 0

            while True:
                cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self._client.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted} cached keys")
            return True
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False


# Global cache instance
_cache_manager: Optional[RedisCacheManager] = None


async def get_cache_manager(
    redis_url: Optional[str] = None,
) -> RedisCacheManager:
    """
    Get or create the global cache manager instance.

    Args:
        redis_url: Optional Redis URL (uses settings/env if not provided)

    Returns:
        Connected RedisCacheManager instance
    """
    global _cache_manager

    if _cache_manager is None:
        # If no URL provided, read from environment or use default
        if redis_url is None:
            import os
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _cache_manager = RedisCacheManager(redis_url)
        await _cache_manager.connect()

    return _cache_manager
