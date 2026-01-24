"""
Deals Aggregator Service

Aggregates deal data from the detected_deals table and Redis cache.
Provides efficient access to deal discovery data for the API layer.

Cache Strategy:
- deals:{class} -> Deals by class (TTL: 1 min, from deal_detector lambda)
- snipes:all -> Top snipe opportunities (TTL: 1 min, from lambda)
- deals_aggregator:summary -> Aggregated summary (TTL: 5 min)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict, Literal, List, Any
from dataclasses import dataclass

from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import DetectedDeal
from src.services.cache import get_cache_manager, RedisCacheManager

logger = logging.getLogger(__name__)


# Type definitions
DealStatusFilter = Literal["active", "sold", "expired"]


class DetectedDealData(TypedDict):
    """Single detected deal record."""
    id: int
    axie_id: int
    class_: str
    price_eth: float
    avg_eth: Optional[float]
    discount_percent: Optional[float]
    deal_score: int
    is_snipe: bool
    part_analysis: List[Any]
    detected_at: str
    status: str
    sold_at: Optional[str]
    marketplace_url: str


class DealsSummaryData(TypedDict):
    """Deals summary statistics."""
    timestamp: str
    total_deals: int
    active_deals: int
    snipe_opportunities: int
    by_class: dict
    avg_discount: float
    avg_score: float
    top_deals: List[DetectedDealData]
    top_snipes: List[DetectedDealData]


class ClassDealsData(TypedDict):
    """Deals data for a specific class."""
    class_: str
    total_deals: int
    active_deals: int
    snipes: int
    avg_discount: float
    avg_score: float
    recent_deals: List[DetectedDealData]


class DealStatsData(TypedDict):
    """Aggregated deal statistics."""
    period_hours: int
    total_detected: int
    total_sold: int
    avg_time_to_sell_minutes: Optional[float]
    avg_discount: float
    avg_score: float
    snipe_rate: float  # Percentage of deals that were snipes


@dataclass
class DealsAggregatorConfig:
    """Configuration for deals aggregator."""
    cache_ttl_summary: int = 300      # 5 minutes
    cache_ttl_deals: int = 60         # 1 minute (deals are time-sensitive)
    cache_ttl_stats: int = 600        # 10 minutes
    default_limit: int = 20
    min_score: int = 50


class DealsAggregatorService:
    """
    Service for aggregating and caching deal discovery data.

    Combines data from:
    - detected_deals table: Historical and active deal records
    - Redis cache: Real-time deals from deal_detector lambda

    Usage:
        aggregator = DealsAggregatorService(db, cache)
        deals = await aggregator.get_live_deals()
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[RedisCacheManager] = None,
        config: Optional[DealsAggregatorConfig] = None,
    ):
        self.db = db
        self.cache = cache
        self.config = config or DealsAggregatorConfig()

    async def get_deals_summary(
        self,
        use_cache: bool = True,
    ) -> DealsSummaryData:
        """
        Get comprehensive deals summary.

        Returns overall deal counts, by-class breakdown, and top opportunities.
        """
        cache_key = "deals_aggregator:summary"

        # Try cache first
        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug("Returning cached deals summary")
                return cached

        # Get counts from last 24 hours
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        # Class breakdown
        class_query = (
            select(
                DetectedDeal.class_,
                func.count(DetectedDeal.id).label("total"),
                func.count(DetectedDeal.id).filter(DetectedDeal.status == "active").label("active"),
                func.count(DetectedDeal.id).filter(DetectedDeal.is_snipe == True).label("snipes"),
            )
            .where(DetectedDeal.detected_at >= since)
            .group_by(DetectedDeal.class_)
        )

        class_result = await self.db.execute(class_query)
        class_rows = class_result.all()

        by_class = {
            row.class_: {
                "total": row.total,
                "active": row.active,
                "snipes": row.snipes,
            }
            for row in class_rows
        }

        # Overall stats
        stats_query = (
            select(
                func.count(DetectedDeal.id).label("total"),
                func.count(DetectedDeal.id).filter(DetectedDeal.status == "active").label("active"),
                func.count(DetectedDeal.id).filter(DetectedDeal.is_snipe == True).label("snipes"),
                func.avg(DetectedDeal.discount_percent).label("avg_discount"),
                func.avg(DetectedDeal.deal_score).label("avg_score"),
            )
            .where(DetectedDeal.detected_at >= since)
        )

        stats_result = await self.db.execute(stats_query)
        stats = stats_result.one()

        # Get top deals and snipes
        top_deals = await self._get_top_deals(limit=5)
        top_snipes = await self._get_snipes(limit=5)

        summary = DealsSummaryData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_deals=stats.total or 0,
            active_deals=stats.active or 0,
            snipe_opportunities=stats.snipes or 0,
            by_class=by_class,
            avg_discount=round(float(stats.avg_discount or 0), 2),
            avg_score=round(float(stats.avg_score or 0), 1),
            top_deals=top_deals,
            top_snipes=top_snipes,
        )

        # Cache results
        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, summary, self.config.cache_ttl_summary)

        return summary

    async def _get_top_deals(
        self,
        limit: int = 5,
    ) -> List[DetectedDealData]:
        """Get top active deals by score."""
        query = (
            select(DetectedDeal)
            .where(
                and_(
                    DetectedDeal.status == "active",
                    DetectedDeal.deal_score >= self.config.min_score,
                )
            )
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        return [self._deal_to_dict(d) for d in deals]

    async def get_live_deals(
        self,
        axie_class: Optional[str] = None,
        min_score: int = 50,
        limit: int = 20,
        hours: int = 24,
        use_cache: bool = True,
    ) -> List[DetectedDealData]:
        """
        Get active deal opportunities.

        Args:
            axie_class: Filter by Axie class (optional)
            min_score: Minimum deal score (0-100)
            limit: Maximum results to return
            hours: Look back period in hours
            use_cache: Whether to use cached results
        """
        cache_key = f"deals_aggregator:live:{axie_class or 'all'}:{min_score}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached[:limit]

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        conditions = [
            DetectedDeal.detected_at >= since,
            DetectedDeal.status == "active",
            DetectedDeal.deal_score >= min_score,
        ]

        if axie_class:
            conditions.append(DetectedDeal.class_ == axie_class.lower())

        query = (
            select(DetectedDeal)
            .where(and_(*conditions))
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        data = [self._deal_to_dict(d) for d in deals]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_deals)

        return data

    async def _get_snipes(
        self,
        limit: int = 5,
    ) -> List[DetectedDealData]:
        """Get top snipe opportunities."""
        query = (
            select(DetectedDeal)
            .where(
                and_(
                    DetectedDeal.status == "active",
                    DetectedDeal.is_snipe == True,
                )
            )
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        return [self._deal_to_dict(d) for d in deals]

    async def get_snipes(
        self,
        limit: int = 20,
        hours: int = 24,
        use_cache: bool = True,
    ) -> List[DetectedDealData]:
        """
        Get top snipe opportunities (high-value deals).

        Snipes are deals with 40%+ discount (deal_score 80+).
        """
        cache_key = f"deals_aggregator:snipes:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached[:limit]

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(DetectedDeal)
            .where(
                and_(
                    DetectedDeal.detected_at >= since,
                    DetectedDeal.status == "active",
                    DetectedDeal.is_snipe == True,
                )
            )
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        data = [self._deal_to_dict(d) for d in deals]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_deals)

        return data

    async def get_deal_by_axie(
        self,
        axie_id: int,
        include_history: bool = False,
    ) -> Optional[DetectedDealData]:
        """
        Get the most recent deal for a specific Axie.

        Args:
            axie_id: The Axie ID to look up
            include_history: If True, return all deals; otherwise just the latest
        """
        query = (
            select(DetectedDeal)
            .where(DetectedDeal.axie_id == axie_id)
            .order_by(DetectedDeal.detected_at.desc())
            .limit(1)
        )

        result = await self.db.execute(query)
        deal = result.scalar_one_or_none()

        if deal:
            return self._deal_to_dict(deal)
        return None

    async def get_deal_history(
        self,
        axie_id: int,
        days: int = 7,
    ) -> List[DetectedDealData]:
        """
        Get deal detection history for a specific Axie.

        Returns all detected deals for the Axie over the specified period.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(DetectedDeal)
            .where(
                and_(
                    DetectedDeal.axie_id == axie_id,
                    DetectedDeal.detected_at >= since,
                )
            )
            .order_by(DetectedDeal.detected_at.desc())
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        return [self._deal_to_dict(d) for d in deals]

    async def get_class_deals(
        self,
        axie_class: str,
        hours: int = 24,
        use_cache: bool = True,
    ) -> ClassDealsData:
        """
        Get deal analysis for a specific Axie class.

        Returns aggregated stats and recent deals for the class.
        """
        cache_key = f"deals_aggregator:class:{axie_class}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get aggregated stats
        stats_query = (
            select(
                func.count(DetectedDeal.id).label("total"),
                func.count(DetectedDeal.id).filter(DetectedDeal.status == "active").label("active"),
                func.count(DetectedDeal.id).filter(DetectedDeal.is_snipe == True).label("snipes"),
                func.avg(DetectedDeal.discount_percent).label("avg_discount"),
                func.avg(DetectedDeal.deal_score).label("avg_score"),
            )
            .where(
                and_(
                    DetectedDeal.class_ == axie_class.lower(),
                    DetectedDeal.detected_at >= since,
                )
            )
        )

        stats_result = await self.db.execute(stats_query)
        stats = stats_result.one()

        # Get recent deals
        recent_query = (
            select(DetectedDeal)
            .where(
                and_(
                    DetectedDeal.class_ == axie_class.lower(),
                    DetectedDeal.detected_at >= since,
                )
            )
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .limit(10)
        )

        recent_result = await self.db.execute(recent_query)
        recent_deals = recent_result.scalars().all()

        data = ClassDealsData(
            class_=axie_class.lower(),
            total_deals=stats.total or 0,
            active_deals=stats.active or 0,
            snipes=stats.snipes or 0,
            avg_discount=round(float(stats.avg_discount or 0), 2),
            avg_score=round(float(stats.avg_score or 0), 1),
            recent_deals=[self._deal_to_dict(d) for d in recent_deals],
        )

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_deals)

        return data

    async def get_deal_stats(
        self,
        hours: int = 24,
        use_cache: bool = True,
    ) -> DealStatsData:
        """
        Get aggregated deal statistics.

        Returns metrics like total detected, sold rate, average time to sell, etc.
        """
        cache_key = f"deals_aggregator:stats:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Basic counts
        stats_query = (
            select(
                func.count(DetectedDeal.id).label("total"),
                func.count(DetectedDeal.id).filter(DetectedDeal.status == "sold").label("sold"),
                func.count(DetectedDeal.id).filter(DetectedDeal.is_snipe == True).label("snipes"),
                func.avg(DetectedDeal.discount_percent).label("avg_discount"),
                func.avg(DetectedDeal.deal_score).label("avg_score"),
            )
            .where(DetectedDeal.detected_at >= since)
        )

        stats_result = await self.db.execute(stats_query)
        stats = stats_result.one()

        # Average time to sell (for sold deals)
        time_query = (
            select(
                func.avg(
                    func.extract("epoch", DetectedDeal.sold_at - DetectedDeal.detected_at) / 60
                ).label("avg_minutes")
            )
            .where(
                and_(
                    DetectedDeal.detected_at >= since,
                    DetectedDeal.status == "sold",
                    DetectedDeal.sold_at.isnot(None),
                )
            )
        )

        time_result = await self.db.execute(time_query)
        avg_time = time_result.scalar()

        total = stats.total or 0
        snipes = stats.snipes or 0

        data = DealStatsData(
            period_hours=hours,
            total_detected=total,
            total_sold=stats.sold or 0,
            avg_time_to_sell_minutes=round(float(avg_time), 2) if avg_time else None,
            avg_discount=round(float(stats.avg_discount or 0), 2),
            avg_score=round(float(stats.avg_score or 0), 1),
            snipe_rate=round((snipes / total * 100) if total > 0 else 0, 2),
        )

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_stats)

        return data

    async def get_all_deals(
        self,
        status: Optional[DealStatusFilter] = None,
        min_score: int = 50,
        hours: int = 24,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Get all deals with pagination.

        Returns deals sorted by deal_score (best deals first).
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        conditions = [
            DetectedDeal.detected_at >= since,
            DetectedDeal.deal_score >= min_score,
        ]

        if status:
            conditions.append(DetectedDeal.status == status)

        # Count total
        count_query = (
            select(func.count(DetectedDeal.id))
            .where(and_(*conditions))
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get deals
        query = (
            select(DetectedDeal)
            .where(and_(*conditions))
            .order_by(DetectedDeal.deal_score.desc(), DetectedDeal.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        deals = result.scalars().all()

        return {
            "deals": [self._deal_to_dict(d) for d in deals],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _deal_to_dict(self, deal: DetectedDeal) -> DetectedDealData:
        """Convert DetectedDeal model to TypedDict."""
        return DetectedDealData(
            id=deal.id,
            axie_id=deal.axie_id,
            class_=deal.class_,
            price_eth=float(deal.price_eth) if deal.price_eth else 0,
            avg_eth=float(deal.avg_eth) if deal.avg_eth else None,
            discount_percent=deal.discount_percent,
            deal_score=deal.deal_score or 0,
            is_snipe=deal.is_snipe or False,
            part_analysis=deal.part_analysis or [],
            detected_at=deal.detected_at.isoformat() if deal.detected_at else "",
            status=deal.status or "active",
            sold_at=deal.sold_at.isoformat() if deal.sold_at else None,
            marketplace_url=f"https://app.axieinfinity.com/marketplace/axies/{deal.axie_id}",
        )


# Factory function for dependency injection
async def get_deals_aggregator(
    db: AsyncSession,
    cache: Optional[RedisCacheManager] = None,
) -> DealsAggregatorService:
    """Create DealsAggregatorService instance with optional cache."""
    if cache is None:
        try:
            cache = await get_cache_manager()
        except Exception:
            cache = None

    return DealsAggregatorService(db, cache)
