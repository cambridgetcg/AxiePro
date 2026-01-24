"""
Market Aggregator Service

Computes market statistics from price_snapshots and sales data.
Provides efficient aggregated metrics for 24h, 7d, 30d periods.

Cache Strategy:
- market_stats:{period} -> Pre-computed stats (TTL: 5 min)
- floor_prices:latest -> Latest floor prices per class (TTL: 1 min)
- price_history:{trait_key}:{interval} -> Time-series data (TTL: 15 min)
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, TypedDict, Literal
from dataclasses import dataclass, asdict

from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Sale, Listing, Axie, PriceSnapshot, MarketStats
from src.services.cache import get_cache_manager, RedisCacheManager

logger = logging.getLogger(__name__)


# Type definitions
PeriodType = Literal["1h", "24h", "7d", "30d"]


class PeriodStats(TypedDict):
    """Statistics for a single time period."""
    volume_eth: float
    sales_count: int
    avg_price_eth: float
    median_price_eth: float
    floor_price_eth: Optional[float]
    max_price_eth: Optional[float]
    unique_buyers: int
    unique_sellers: int
    active_listings: int


class FloorPrice(TypedDict):
    """Floor price for a class."""
    class_: str
    floor_eth: float
    count: int
    change_24h: Optional[float]


class PricePoint(TypedDict):
    """Single point in price time-series."""
    time: str
    floor_eth: Optional[float]
    avg_eth: Optional[float]
    volume: int
    listings_count: int


@dataclass
class MarketAggregatorConfig:
    """Configuration for market aggregator."""
    cache_ttl_stats: int = 300       # 5 minutes
    cache_ttl_floor: int = 60        # 1 minute
    cache_ttl_history: int = 900     # 15 minutes
    default_history_limit: int = 100


class MarketAggregatorService:
    """
    Service for computing and caching market statistics.

    Aggregates data from:
    - price_snapshots: Time-series floor prices (from ingestion lambda)
    - sales: Historical sales records
    - listings: Active marketplace listings

    Usage:
        aggregator = MarketAggregatorService(db, cache)
        stats = await aggregator.get_market_stats()
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[RedisCacheManager] = None,
        config: Optional[MarketAggregatorConfig] = None,
    ):
        self.db = db
        self.cache = cache
        self.config = config or MarketAggregatorConfig()

    async def get_market_stats(
        self,
        use_cache: bool = True,
    ) -> dict[str, PeriodStats]:
        """
        Get market statistics for all periods (24h, 7d, 30d).

        Returns:
            Dict with keys "24h", "7d", "30d" containing PeriodStats
        """
        cache_key = "market_stats:all"

        # Try cache first
        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug("Returning cached market stats")
                return cached

        # Compute fresh statistics
        stats = {}
        periods = [("24h", 1), ("7d", 7), ("30d", 30)]

        for period_name, days in periods:
            stats[period_name] = await self._compute_period_stats(days)

        # Cache results
        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, stats, self.config.cache_ttl_stats)

        return stats

    async def get_period_stats(
        self,
        period: PeriodType,
        axie_class: Optional[str] = None,
        use_cache: bool = True,
    ) -> PeriodStats:
        """
        Get statistics for a specific period and optional class filter.

        Args:
            period: Time period ("1h", "24h", "7d", "30d")
            axie_class: Optional filter by class
            use_cache: Whether to use cached results
        """
        days = {"1h": 1/24, "24h": 1, "7d": 7, "30d": 30}[period]
        cache_key = f"market_stats:{period}:{axie_class or 'all'}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        stats = await self._compute_period_stats(days, axie_class)

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, stats, self.config.cache_ttl_stats)

        return stats

    async def _compute_period_stats(
        self,
        days: float,
        axie_class: Optional[str] = None,
    ) -> PeriodStats:
        """Compute statistics for a time period from database."""
        # Use utcnow() for comparison with naive datetime columns (sales.sold_at)
        since = datetime.utcnow() - timedelta(days=days)

        # Build base query for sales
        sales_query = select(
            func.count(Sale.id).label("sales_count"),
            func.coalesce(func.sum(Sale.price_eth), 0).label("volume_eth"),
            func.coalesce(func.avg(Sale.price_eth), 0).label("avg_price"),
            func.count(func.distinct(Sale.buyer_address)).label("unique_buyers"),
            func.count(func.distinct(Sale.seller_address)).label("unique_sellers"),
        ).where(Sale.sold_at >= since)

        # Apply class filter if specified
        if axie_class:
            sales_query = sales_query.join(
                Axie, Sale.axie_id == Axie.id
            ).where(Axie.class_ == axie_class.lower())

        result = await self.db.execute(sales_query)
        row = result.one()

        # Get median price (requires separate query)
        median_price = await self._compute_median_price(since, axie_class)

        # Get floor price from latest snapshots or active listings
        floor_price = await self._get_current_floor(axie_class)

        # Get max price
        max_query = select(func.max(Sale.price_eth)).where(Sale.sold_at >= since)
        if axie_class:
            max_query = max_query.join(
                Axie, Sale.axie_id == Axie.id
            ).where(Axie.class_ == axie_class.lower())
        max_result = await self.db.execute(max_query)
        max_price = max_result.scalar()

        # Get active listings count
        listings_query = select(func.count(Listing.id)).where(
            Listing.status == "active"
        )
        if axie_class:
            listings_query = listings_query.join(
                Axie, Listing.axie_id == Axie.id
            ).where(Axie.class_ == axie_class.lower())
        listings_result = await self.db.execute(listings_query)
        active_listings = listings_result.scalar() or 0

        return PeriodStats(
            volume_eth=float(row.volume_eth or 0),
            sales_count=row.sales_count or 0,
            avg_price_eth=float(row.avg_price or 0),
            median_price_eth=float(median_price) if median_price else 0,
            floor_price_eth=float(floor_price) if floor_price else None,
            max_price_eth=float(max_price) if max_price else None,
            unique_buyers=row.unique_buyers or 0,
            unique_sellers=row.unique_sellers or 0,
            active_listings=active_listings,
        )

    async def _compute_median_price(
        self,
        since: datetime,
        axie_class: Optional[str] = None,
    ) -> Optional[Decimal]:
        """Compute median sale price for a period."""
        # Use percentile_cont for accurate median
        # Fallback to simple approach for compatibility
        query = (
            select(Sale.price_eth)
            .where(Sale.sold_at >= since)
            .order_by(Sale.price_eth)
        )

        if axie_class:
            query = query.join(
                Axie, Sale.axie_id == Axie.id
            ).where(Axie.class_ == axie_class.lower())

        result = await self.db.execute(query)
        prices = [row[0] for row in result.all()]

        if not prices:
            return None

        mid = len(prices) // 2
        if len(prices) % 2 == 0:
            return (prices[mid - 1] + prices[mid]) / 2
        return prices[mid]

    async def _get_current_floor(
        self,
        axie_class: Optional[str] = None,
    ) -> Optional[Decimal]:
        """Get current floor price from active listings."""
        query = select(func.min(Listing.price_eth)).where(
            Listing.status == "active"
        )

        if axie_class:
            query = query.join(
                Axie, Listing.axie_id == Axie.id
            ).where(Axie.class_ == axie_class.lower())

        result = await self.db.execute(query)
        return result.scalar()

    async def get_floor_prices_by_class(
        self,
        use_cache: bool = True,
    ) -> list[FloorPrice]:
        """
        Get current floor prices for all classes with 24h change.

        Returns:
            List of FloorPrice objects with class, floor, count, and change
        """
        cache_key = "floor_prices:by_class"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        # Current floor prices from listings (using class_ column directly)
        query = (
            select(
                Listing.class_,
                func.min(Listing.price_eth).label("floor_eth"),
                func.count(Listing.id).label("count"),
            )
            .where(and_(
                Listing.status == "active",
                Listing.class_.isnot(None)
            ))
            .group_by(Listing.class_)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Get 24h-ago floor prices from snapshots for change calculation
        yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
        snapshot_query = (
            select(
                PriceSnapshot.class_,
                PriceSnapshot.floor_eth,
            )
            .where(
                and_(
                    PriceSnapshot.trait_key.like("class:%"),
                    PriceSnapshot.time <= yesterday,
                )
            )
            .order_by(PriceSnapshot.class_, PriceSnapshot.time.desc())
            .distinct(PriceSnapshot.class_)
        )

        try:
            snapshot_result = await self.db.execute(snapshot_query)
            old_floors = {row.class_: row.floor_eth for row in snapshot_result.all()}
        except Exception:
            old_floors = {}

        floors = []
        for row in rows:
            class_name = row.class_.value if hasattr(row.class_, 'value') else str(row.class_)
            current_floor = float(row.floor_eth)
            old_floor = old_floors.get(class_name)

            change_24h = None
            if old_floor and float(old_floor) > 0:
                change_24h = ((current_floor - float(old_floor)) / float(old_floor)) * 100

            floors.append(FloorPrice(
                class_=class_name,
                floor_eth=current_floor,
                count=row.count,
                change_24h=round(change_24h, 2) if change_24h is not None else None,
            ))

        # Cache results
        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, floors, self.config.cache_ttl_floor)

        return floors

    async def get_price_history(
        self,
        trait_key: str,
        interval: str = "1h",
        limit: int = 100,
        use_cache: bool = True,
    ) -> list[PricePoint]:
        """
        Get price history time-series for a trait.

        Args:
            trait_key: Trait identifier (e.g., "class:beast", "part:eyes:kotaro")
            interval: Time bucket interval ("5m", "1h", "1d")
            limit: Maximum number of points to return
        """
        cache_key = f"price_history:{trait_key}:{interval}:{limit}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        # Query price_snapshots
        query = (
            select(
                PriceSnapshot.time,
                PriceSnapshot.floor_eth,
                PriceSnapshot.avg_eth,
                PriceSnapshot.volume,
                PriceSnapshot.listings_count,
            )
            .where(PriceSnapshot.trait_key == trait_key)
            .order_by(PriceSnapshot.time.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        points = [
            PricePoint(
                time=row.time.isoformat(),
                floor_eth=float(row.floor_eth) if row.floor_eth else None,
                avg_eth=float(row.avg_eth) if row.avg_eth else None,
                volume=row.volume or 0,
                listings_count=row.listings_count or 0,
            )
            for row in reversed(rows)  # Chronological order
        ]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, points, self.config.cache_ttl_history)

        return points

    async def get_class_price_history(
        self,
        axie_class: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[PricePoint]:
        """Get price history for a specific class."""
        return await self.get_price_history(
            trait_key=f"class:{axie_class.lower()}",
            interval=interval,
            limit=limit,
        )

    async def get_market_summary(self) -> dict:
        """
        Get complete market summary including stats, floors, and trends.

        Combines multiple queries into a single response for dashboard.
        """
        # Parallel fetch all data
        stats = await self.get_market_stats()
        floors = await self.get_floor_prices_by_class()

        # Calculate trends
        trend_24h = None
        if stats["24h"]["volume_eth"] > 0 and stats["7d"]["volume_eth"] > 0:
            daily_avg_7d = stats["7d"]["volume_eth"] / 7
            if daily_avg_7d > 0:
                trend_24h = ((stats["24h"]["volume_eth"] - daily_avg_7d) / daily_avg_7d) * 100

        return {
            "stats": stats,
            "floor_prices": floors,
            "trends": {
                "volume_trend_24h": round(trend_24h, 2) if trend_24h is not None else None,
            },
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }


# Factory function for dependency injection
async def get_market_aggregator(
    db: AsyncSession,
    cache: Optional[RedisCacheManager] = None,
) -> MarketAggregatorService:
    """Create MarketAggregatorService instance with optional cache."""
    if cache is None:
        try:
            cache = await get_cache_manager()
        except Exception:
            cache = None

    return MarketAggregatorService(db, cache)
