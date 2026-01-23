"""
Sales Aggregator Service

Provides recent sales activity data with Redis caching.
Follows the established [X]AggregatorService pattern.

Cache Strategy:
- sales:recent:{hours}:{class} -> Recent sales list (TTL: 2 min)
- sales:activity:{hours}:{class} -> Sales activity stats (TTL: 5 min)
- sales:class:{class}:{hours} -> Class-specific sales (TTL: 5 min)
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, TypedDict, List, Any

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Sale, Axie
from src.services.cache import get_cache_manager, RedisCacheManager

logger = logging.getLogger(__name__)


# Type definitions for response data
class RecentSaleData(TypedDict):
    """Individual sale record for recent sales."""
    id: int
    axie_id: int
    class_: str
    price_eth: float
    price_usd: Optional[float]
    seller_address: str
    buyer_address: str
    tx_hash: str
    sold_at: str
    marketplace: str


class SalesActivityData(TypedDict):
    """Aggregated sales activity statistics."""
    period_hours: int
    total_sales: int
    total_volume_eth: float
    avg_price_eth: float
    median_price_eth: float
    min_price_eth: Optional[float]
    max_price_eth: Optional[float]
    unique_buyers: int
    unique_sellers: int
    sales_per_hour: float
    by_class: dict[str, dict[str, Any]]


class ClassSalesData(TypedDict):
    """Sales data for a specific class."""
    class_: str
    period_hours: int
    total_sales: int
    total_volume_eth: float
    avg_price_eth: float
    recent_sales: List[RecentSaleData]


class SalesAggregatorConfig:
    """Configuration for sales aggregator."""
    cache_ttl_recent: int = 120      # 2 minutes
    cache_ttl_activity: int = 300    # 5 minutes
    cache_ttl_class: int = 300       # 5 minutes
    default_hours: int = 24
    default_limit: int = 50


class SalesAggregatorService:
    """
    Service for aggregating and caching recent sales activity.

    Provides efficient queries for:
    - Recent sales with optional class filter
    - Sales activity statistics
    - Class-specific sales analysis

    Usage:
        aggregator = SalesAggregatorService(db, cache)
        recent = await aggregator.get_recent_sales(hours=24)
        activity = await aggregator.get_sales_activity(hours=24)
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[RedisCacheManager] = None,
        config: Optional[SalesAggregatorConfig] = None,
    ):
        self.db = db
        self.cache = cache
        self.config = config or SalesAggregatorConfig()

    async def get_recent_sales(
        self,
        hours: int = 24,
        axie_class: Optional[str] = None,
        limit: int = 50,
        use_cache: bool = True,
    ) -> List[RecentSaleData]:
        """
        Get recent sales with optional class filter.

        Args:
            hours: Number of hours to look back
            axie_class: Optional filter by Axie class
            limit: Maximum number of sales to return
            use_cache: Whether to use cached results

        Returns:
            List of recent sale records
        """
        cache_key = f"sales:recent:{hours}:{axie_class or 'all'}:{limit}"

        # Try cache first
        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug(f"Returning cached recent sales for {cache_key}")
                return cached

        # Query database
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(Sale, Axie)
            .outerjoin(Axie, Sale.axie_id == Axie.id)
            .where(Sale.sold_at >= since)
            .order_by(desc(Sale.sold_at))
            .limit(limit)
        )

        if axie_class:
            query = query.where(Axie.class_ == axie_class.lower())

        result = await self.db.execute(query)
        rows = result.all()

        sales = []
        for sale, axie in rows:
            sales.append(RecentSaleData(
                id=sale.id,
                axie_id=sale.axie_id or 0,
                class_=axie.class_.value if axie and hasattr(axie.class_, 'value') else (str(axie.class_) if axie else 'unknown'),
                price_eth=float(sale.price_eth),
                price_usd=float(sale.price_usd) if sale.price_usd else None,
                seller_address=sale.seller_address,
                buyer_address=sale.buyer_address,
                tx_hash=sale.tx_hash,
                sold_at=sale.sold_at.isoformat() if sale.sold_at else '',
                marketplace=sale.marketplace or 'official',
            ))

        # Cache results
        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, sales, self.config.cache_ttl_recent)

        return sales

    async def get_sales_activity(
        self,
        hours: int = 24,
        axie_class: Optional[str] = None,
        use_cache: bool = True,
    ) -> SalesActivityData:
        """
        Get aggregated sales activity statistics.

        Args:
            hours: Number of hours to analyze
            axie_class: Optional filter by Axie class
            use_cache: Whether to use cached results

        Returns:
            Aggregated sales activity statistics
        """
        cache_key = f"sales:activity:{hours}:{axie_class or 'all'}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug(f"Returning cached sales activity for {cache_key}")
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Main aggregation query
        query = select(
            func.count(Sale.id).label("total_sales"),
            func.coalesce(func.sum(Sale.price_eth), 0).label("total_volume"),
            func.coalesce(func.avg(Sale.price_eth), 0).label("avg_price"),
            func.min(Sale.price_eth).label("min_price"),
            func.max(Sale.price_eth).label("max_price"),
            func.count(func.distinct(Sale.buyer_address)).label("unique_buyers"),
            func.count(func.distinct(Sale.seller_address)).label("unique_sellers"),
        ).where(Sale.sold_at >= since)

        if axie_class:
            query = query.join(Axie, Sale.axie_id == Axie.id).where(
                Axie.class_ == axie_class.lower()
            )

        result = await self.db.execute(query)
        row = result.one()

        # Calculate median price
        median_price = await self._compute_median_price(since, axie_class)

        # Get breakdown by class
        by_class = await self._get_sales_by_class(since)

        activity = SalesActivityData(
            period_hours=hours,
            total_sales=row.total_sales or 0,
            total_volume_eth=float(row.total_volume or 0),
            avg_price_eth=float(row.avg_price or 0),
            median_price_eth=float(median_price) if median_price else 0,
            min_price_eth=float(row.min_price) if row.min_price else None,
            max_price_eth=float(row.max_price) if row.max_price else None,
            unique_buyers=row.unique_buyers or 0,
            unique_sellers=row.unique_sellers or 0,
            sales_per_hour=round((row.total_sales or 0) / max(hours, 1), 2),
            by_class=by_class,
        )

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, activity, self.config.cache_ttl_activity)

        return activity

    async def _compute_median_price(
        self,
        since: datetime,
        axie_class: Optional[str] = None,
    ) -> Optional[Decimal]:
        """Compute median sale price for the period."""
        query = (
            select(Sale.price_eth)
            .where(Sale.sold_at >= since)
            .order_by(Sale.price_eth)
        )

        if axie_class:
            query = query.join(Axie, Sale.axie_id == Axie.id).where(
                Axie.class_ == axie_class.lower()
            )

        result = await self.db.execute(query)
        prices = [row[0] for row in result.all()]

        if not prices:
            return None

        mid = len(prices) // 2
        if len(prices) % 2 == 0:
            return (prices[mid - 1] + prices[mid]) / 2
        return prices[mid]

    async def _get_sales_by_class(
        self,
        since: datetime,
    ) -> dict[str, dict[str, Any]]:
        """Get sales breakdown by class."""
        query = (
            select(
                Axie.class_,
                func.count(Sale.id).label("sales_count"),
                func.coalesce(func.sum(Sale.price_eth), 0).label("volume"),
                func.coalesce(func.avg(Sale.price_eth), 0).label("avg_price"),
            )
            .join(Axie, Sale.axie_id == Axie.id)
            .where(Sale.sold_at >= since)
            .group_by(Axie.class_)
        )

        result = await self.db.execute(query)
        rows = result.all()

        by_class = {}
        for row in rows:
            class_name = row.class_.value if hasattr(row.class_, 'value') else str(row.class_)
            by_class[class_name] = {
                "sales_count": row.sales_count or 0,
                "volume_eth": float(row.volume or 0),
                "avg_price_eth": float(row.avg_price or 0),
            }

        return by_class

    async def get_class_sales(
        self,
        axie_class: str,
        hours: int = 24,
        limit: int = 20,
        use_cache: bool = True,
    ) -> ClassSalesData:
        """
        Get detailed sales data for a specific class.

        Args:
            axie_class: The Axie class to analyze
            hours: Number of hours to look back
            limit: Maximum number of recent sales to include
            use_cache: Whether to use cached results

        Returns:
            Class-specific sales data with recent transactions
        """
        cache_key = f"sales:class:{axie_class.lower()}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug(f"Returning cached class sales for {cache_key}")
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get aggregated stats for this class
        stats_query = (
            select(
                func.count(Sale.id).label("total_sales"),
                func.coalesce(func.sum(Sale.price_eth), 0).label("total_volume"),
                func.coalesce(func.avg(Sale.price_eth), 0).label("avg_price"),
            )
            .join(Axie, Sale.axie_id == Axie.id)
            .where(and_(
                Sale.sold_at >= since,
                Axie.class_ == axie_class.lower(),
            ))
        )

        stats_result = await self.db.execute(stats_query)
        stats_row = stats_result.one()

        # Get recent sales for this class
        recent_sales = await self.get_recent_sales(
            hours=hours,
            axie_class=axie_class,
            limit=limit,
            use_cache=False,  # Already caching the full response
        )

        class_data = ClassSalesData(
            class_=axie_class.lower(),
            period_hours=hours,
            total_sales=stats_row.total_sales or 0,
            total_volume_eth=float(stats_row.total_volume or 0),
            avg_price_eth=float(stats_row.avg_price or 0),
            recent_sales=recent_sales,
        )

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, class_data, self.config.cache_ttl_class)

        return class_data

    async def get_hourly_sales_distribution(
        self,
        hours: int = 24,
        use_cache: bool = True,
    ) -> List[dict[str, Any]]:
        """
        Get hourly distribution of sales for time-series visualization.

        Args:
            hours: Number of hours to look back
            use_cache: Whether to use cached results

        Returns:
            List of hourly data points with sales count and volume
        """
        cache_key = f"sales:hourly:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # PostgreSQL-specific: use date_trunc for hourly grouping
        query = (
            select(
                func.date_trunc('hour', Sale.sold_at).label("hour"),
                func.count(Sale.id).label("sales_count"),
                func.coalesce(func.sum(Sale.price_eth), 0).label("volume"),
                func.coalesce(func.avg(Sale.price_eth), 0).label("avg_price"),
            )
            .where(Sale.sold_at >= since)
            .group_by(func.date_trunc('hour', Sale.sold_at))
            .order_by(func.date_trunc('hour', Sale.sold_at))
        )

        result = await self.db.execute(query)
        rows = result.all()

        distribution = [
            {
                "hour": row.hour.isoformat() if row.hour else '',
                "sales_count": row.sales_count or 0,
                "volume_eth": float(row.volume or 0),
                "avg_price_eth": float(row.avg_price or 0),
            }
            for row in rows
        ]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, distribution, self.config.cache_ttl_activity)

        return distribution


# Factory function for dependency injection
async def get_sales_aggregator(
    db: AsyncSession,
    cache: Optional[RedisCacheManager] = None,
) -> SalesAggregatorService:
    """Create SalesAggregatorService instance with optional cache."""
    if cache is None:
        try:
            cache = await get_cache_manager()
        except Exception:
            cache = None

    return SalesAggregatorService(db, cache)
