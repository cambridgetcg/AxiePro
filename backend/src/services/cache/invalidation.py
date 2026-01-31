"""
Cache Invalidation Service

Provides event-based cache invalidation for Redis cache layer.
Complements TTL-based expiration with immediate invalidation on data changes.

Usage:
    from src.services.cache.invalidation import CacheInvalidator

    invalidator = CacheInvalidator()

    # Invalidate specific keys
    await invalidator.invalidate_sales_cache(axie_class="Beast")

    # Invalidate by pattern
    await invalidator.invalidate_pattern("market:floor:*")
"""

import asyncio
import logging
from typing import List, Optional, Set
from datetime import datetime

from src.services.cache.redis_manager import RedisCacheManager


logger = logging.getLogger(__name__)


class CacheInvalidator:
    """
    Event-based cache invalidation for Redis.

    Provides pattern-based and targeted cache invalidation to complement
    TTL-based expiration. Ensures cache consistency on data changes.
    """

    def __init__(self, redis_manager: Optional[RedisCacheManager] = None):
        """
        Initialize cache invalidator.

        Args:
            redis_manager: Redis cache manager instance (creates new if None)
        """
        self.redis = redis_manager or RedisCacheManager()

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.

        Uses SCAN to avoid blocking Redis on large key sets.

        Args:
            pattern: Redis key pattern (e.g., "market:floor:*")

        Returns:
            Number of keys invalidated
        """
        keys_deleted = 0

        try:
            # Use SCAN to iterate through keys (non-blocking)
            cursor = 0
            batch_size = 100

            while True:
                # SCAN returns (cursor, [keys])
                cursor, keys = await self.redis.client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=batch_size
                )

                if keys:
                    # Delete keys in batch
                    deleted = await self.redis.client.delete(*keys)
                    keys_deleted += deleted
                    logger.debug(f"Invalidated {deleted} keys matching '{pattern}'")

                # SCAN returns 0 when complete
                if cursor == 0:
                    break

            logger.info(f"Invalidated {keys_deleted} cache keys for pattern: {pattern}")
            return keys_deleted

        except Exception as e:
            logger.error(f"Error invalidating pattern '{pattern}': {e}")
            return 0

    async def invalidate_keys(self, keys: List[str]) -> int:
        """
        Invalidate specific cache keys.

        Args:
            keys: List of exact cache keys to invalidate

        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0

        try:
            deleted = await self.redis.client.delete(*keys)
            logger.info(f"Invalidated {deleted}/{len(keys)} cache keys")
            return deleted

        except Exception as e:
            logger.error(f"Error invalidating keys: {e}")
            return 0

    # Domain-specific invalidation methods

    async def invalidate_sales_cache(
        self,
        axie_id: Optional[int] = None,
        axie_class: Optional[str] = None,
    ) -> int:
        """
        Invalidate sales-related cache on new sale ingestion.

        Args:
            axie_id: Specific axie ID (invalidates axie-specific cache)
            axie_class: Axie class (invalidates class-wide cache)

        Returns:
            Number of keys invalidated
        """
        patterns_to_invalidate = []

        # Invalidate general sales cache
        patterns_to_invalidate.append("market:sales:*")
        patterns_to_invalidate.append("market:activity:*")

        # Invalidate class-specific cache
        if axie_class:
            patterns_to_invalidate.append(f"market:floor:{axie_class.lower()}:*")
            patterns_to_invalidate.append(f"market:class:{axie_class.lower()}:*")

        # Invalidate axie-specific cache
        if axie_id:
            patterns_to_invalidate.append(f"axie:{axie_id}:*")
            patterns_to_invalidate.append(f"valuation:{axie_id}:*")

        total_deleted = 0
        for pattern in patterns_to_invalidate:
            total_deleted += await self.invalidate_pattern(pattern)

        logger.info(
            f"Invalidated sales cache: axie_id={axie_id}, "
            f"class={axie_class}, deleted={total_deleted}"
        )
        return total_deleted

    async def invalidate_listings_cache(
        self,
        axie_id: Optional[int] = None,
        axie_class: Optional[str] = None,
    ) -> int:
        """
        Invalidate listings-related cache on new listing ingestion.

        Args:
            axie_id: Specific axie ID
            axie_class: Axie class

        Returns:
            Number of keys invalidated
        """
        patterns_to_invalidate = [
            "market:listings:*",
            "deals:*",  # Listings change affects deal detection
        ]

        if axie_class:
            patterns_to_invalidate.append(f"market:floor:{axie_class.lower()}:*")

        if axie_id:
            patterns_to_invalidate.append(f"axie:{axie_id}:*")

        total_deleted = 0
        for pattern in patterns_to_invalidate:
            total_deleted += await self.invalidate_pattern(pattern)

        logger.info(
            f"Invalidated listings cache: axie_id={axie_id}, "
            f"class={axie_class}, deleted={total_deleted}"
        )
        return total_deleted

    async def invalidate_metadata_cache(self, axie_id: int) -> int:
        """
        Invalidate metadata cache on axie metadata update.

        Args:
            axie_id: Axie ID with updated metadata

        Returns:
            Number of keys invalidated
        """
        patterns_to_invalidate = [
            f"axie:{axie_id}:*",
            f"valuation:{axie_id}:*",
        ]

        total_deleted = 0
        for pattern in patterns_to_invalidate:
            total_deleted += await self.invalidate_pattern(pattern)

        logger.info(f"Invalidated metadata cache for axie {axie_id}: deleted={total_deleted}")
        return total_deleted

    async def invalidate_floor_prices(self, axie_class: Optional[str] = None) -> int:
        """
        Invalidate floor price cache on price update.

        Args:
            axie_class: Specific class to invalidate (None = all classes)

        Returns:
            Number of keys invalidated
        """
        if axie_class:
            pattern = f"market:floor:{axie_class.lower()}:*"
        else:
            pattern = "market:floor:*"

        deleted = await self.invalidate_pattern(pattern)
        logger.info(f"Invalidated floor prices: class={axie_class}, deleted={deleted}")
        return deleted

    async def invalidate_deals_cache(self) -> int:
        """
        Invalidate deal detection cache.

        Should be called when:
        - New listings ingested
        - Floor prices updated
        - Deal detection thresholds changed

        Returns:
            Number of keys invalidated
        """
        deleted = await self.invalidate_pattern("deals:*")
        logger.info(f"Invalidated deals cache: deleted={deleted}")
        return deleted

    async def invalidate_all(self) -> int:
        """
        Invalidate entire cache (nuclear option).

        Use sparingly - prefer targeted invalidation.

        Returns:
            Number of keys deleted
        """
        logger.warning("Invalidating ALL cache keys - this may impact performance")

        # Flush entire cache
        try:
            await self.redis.client.flushdb()
            logger.info("Flushed entire Redis cache")
            return -1  # Unknown count

        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return 0


# Convenience functions for Lambda usage

async def invalidate_on_sales_ingestion(
    axie_ids: List[int],
    axie_classes: Set[str],
) -> None:
    """
    Invalidate cache after sales ingestion Lambda run.

    Args:
        axie_ids: List of axie IDs with new sales
        axie_classes: Set of classes with new sales
    """
    invalidator = CacheInvalidator()

    # Invalidate general sales cache
    await invalidator.invalidate_pattern("market:sales:*")

    # Invalidate class-specific caches
    for axie_class in axie_classes:
        await invalidator.invalidate_sales_cache(axie_class=axie_class)

    logger.info(
        f"Cache invalidated after sales ingestion: "
        f"{len(axie_ids)} axies, {len(axie_classes)} classes"
    )


async def invalidate_on_listings_ingestion(
    axie_classes: Set[str],
) -> None:
    """
    Invalidate cache after listings ingestion Lambda run.

    Args:
        axie_classes: Set of classes with new/updated listings
    """
    invalidator = CacheInvalidator()

    # Invalidate listings and deals
    await invalidator.invalidate_pattern("market:listings:*")
    await invalidator.invalidate_deals_cache()

    # Invalidate class-specific floor prices
    for axie_class in axie_classes:
        await invalidator.invalidate_floor_prices(axie_class)

    logger.info(
        f"Cache invalidated after listings ingestion: {len(axie_classes)} classes"
    )


async def invalidate_on_price_update(axie_classes: Set[str]) -> None:
    """
    Invalidate cache after price ingestion Lambda run.

    Args:
        axie_classes: Set of classes with updated prices
    """
    invalidator = CacheInvalidator()

    # Invalidate floor prices
    for axie_class in axie_classes:
        await invalidator.invalidate_floor_prices(axie_class)

    # Invalidate market stats
    await invalidator.invalidate_pattern("market:stats:*")
    await invalidator.invalidate_pattern("market:analytics:*")

    logger.info(
        f"Cache invalidated after price update: {len(axie_classes)} classes"
    )
