"""
Meta Aggregator Service

Aggregates meta shift data from the meta_shifts table and Redis cache.
Provides efficient access to meta analysis data for the API layer.

Cache Strategy:
- meta:summary -> Overall summary (TTL: 5 min, from lambda)
- meta:{shift_type} -> Shifts by type (TTL: 1 hour, from lambda)
- meta_history:{trait_key} -> Historical shifts (TTL: 15 min)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict, Literal, List
from dataclasses import dataclass

from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import MetaShift, PriceSnapshot
from src.services.cache import get_cache_manager, RedisCacheManager

logger = logging.getLogger(__name__)


# Type definitions
ShiftTypeFilter = Literal["rising", "falling", "emerging", "fading"]


class MetaShiftData(TypedDict):
    """Single meta shift record."""
    id: int
    trait_key: str
    class_: str
    shift_type: str
    confidence: int
    signals: List[str]
    velocity_24h: Optional[float]
    velocity_7d: Optional[float]
    volume_change_24h: Optional[float]
    detected_at: str


class MetaSummaryData(TypedDict):
    """Meta summary statistics."""
    timestamp: str
    total_shifts: int
    rising: int
    falling: int
    emerging: int
    fading: int
    top_rising: List[MetaShiftData]
    top_falling: List[MetaShiftData]


class ClassMetaData(TypedDict):
    """Meta data for a specific class."""
    class_: str
    total_shifts: int
    avg_confidence: float
    shift_breakdown: dict
    recent_shifts: List[MetaShiftData]


class TrendingTrait(TypedDict):
    """Trending trait with velocity data."""
    trait_key: str
    class_: str
    shift_type: str
    velocity_24h: Optional[float]
    velocity_7d: Optional[float]
    confidence: int
    first_detected: str
    occurrences: int


class TraitHistoryPoint(TypedDict):
    """Historical point for a trait."""
    detected_at: str
    shift_type: str
    confidence: int
    velocity_24h: Optional[float]
    velocity_7d: Optional[float]
    volume_change_24h: Optional[float]


@dataclass
class MetaAggregatorConfig:
    """Configuration for meta aggregator."""
    cache_ttl_summary: int = 300      # 5 minutes
    cache_ttl_shifts: int = 300       # 5 minutes
    cache_ttl_history: int = 900      # 15 minutes
    default_limit: int = 20
    min_confidence: int = 25


class MetaAggregatorService:
    """
    Service for aggregating and caching meta shift data.

    Combines data from:
    - meta_shifts table: Historical shift records
    - Redis cache: Latest shifts from meta_analyzer lambda
    - price_snapshots: Supporting time-series data

    Usage:
        aggregator = MetaAggregatorService(db, cache)
        summary = await aggregator.get_meta_summary()
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: Optional[RedisCacheManager] = None,
        config: Optional[MetaAggregatorConfig] = None,
    ):
        self.db = db
        self.cache = cache
        self.config = config or MetaAggregatorConfig()

    async def get_meta_summary(
        self,
        use_cache: bool = True,
    ) -> MetaSummaryData:
        """
        Get comprehensive meta summary.

        Returns overall shift counts and top movers.
        """
        cache_key = "meta_aggregator:summary"

        # Try cache first
        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                logger.debug("Returning cached meta summary")
                return cached

        # Get counts by shift type from last 24 hours
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        count_query = (
            select(
                MetaShift.shift_type,
                func.count(MetaShift.id).label("count"),
            )
            .where(MetaShift.detected_at >= since)
            .group_by(MetaShift.shift_type)
        )

        result = await self.db.execute(count_query)
        counts = {row.shift_type: row.count for row in result.all()}

        # Get top rising shifts
        top_rising = await self._get_top_shifts("rising", limit=5)

        # Get top falling shifts
        top_falling = await self._get_top_shifts("falling", limit=5)

        summary = MetaSummaryData(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_shifts=sum(counts.values()),
            rising=counts.get("rising", 0),
            falling=counts.get("falling", 0),
            emerging=counts.get("emerging", 0),
            fading=counts.get("fading", 0),
            top_rising=top_rising,
            top_falling=top_falling,
        )

        # Cache results
        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, summary, self.config.cache_ttl_summary)

        return summary

    async def _get_top_shifts(
        self,
        shift_type: str,
        limit: int = 5,
    ) -> List[MetaShiftData]:
        """Get top shifts by confidence for a shift type."""
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.shift_type == shift_type,
                    MetaShift.detected_at >= since,
                    MetaShift.confidence >= self.config.min_confidence,
                )
            )
            .order_by(MetaShift.confidence.desc(), MetaShift.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        shifts = result.scalars().all()

        return [self._shift_to_dict(s) for s in shifts]

    async def get_shifts_by_type(
        self,
        shift_type: ShiftTypeFilter,
        min_confidence: int = 25,
        limit: int = 20,
        hours: int = 24,
        use_cache: bool = True,
    ) -> List[MetaShiftData]:
        """
        Get meta shifts filtered by type.

        Args:
            shift_type: Filter by rising, falling, emerging, or fading
            min_confidence: Minimum confidence score (0-100)
            limit: Maximum results to return
            hours: Look back period in hours
            use_cache: Whether to use cached results
        """
        cache_key = f"meta_aggregator:shifts:{shift_type}:{min_confidence}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached[:limit]

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.shift_type == shift_type,
                    MetaShift.detected_at >= since,
                    MetaShift.confidence >= min_confidence,
                )
            )
            .order_by(MetaShift.confidence.desc(), MetaShift.detected_at.desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        shifts = result.scalars().all()

        data = [self._shift_to_dict(s) for s in shifts]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_shifts)

        return data

    async def get_trait_history(
        self,
        trait_key: str,
        days: int = 7,
        use_cache: bool = True,
    ) -> List[TraitHistoryPoint]:
        """
        Get historical meta shifts for a specific trait.

        Returns all detected shifts for the trait over the specified period.
        """
        cache_key = f"meta_aggregator:history:{trait_key}:{days}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        since = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.trait_key == trait_key,
                    MetaShift.detected_at >= since,
                )
            )
            .order_by(MetaShift.detected_at.desc())
        )

        result = await self.db.execute(query)
        shifts = result.scalars().all()

        history = [
            TraitHistoryPoint(
                detected_at=s.detected_at.isoformat(),
                shift_type=s.shift_type,
                confidence=s.confidence or 0,
                velocity_24h=s.velocity_24h,
                velocity_7d=s.velocity_7d,
                volume_change_24h=s.volume_change_24h,
            )
            for s in shifts
        ]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, history, self.config.cache_ttl_history)

        return history

    async def get_class_meta(
        self,
        axie_class: str,
        hours: int = 24,
        use_cache: bool = True,
    ) -> ClassMetaData:
        """
        Get meta analysis for a specific Axie class.

        Returns aggregated stats and recent shifts for the class.
        """
        cache_key = f"meta_aggregator:class:{axie_class}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Get aggregated stats
        stats_query = (
            select(
                MetaShift.shift_type,
                func.count(MetaShift.id).label("count"),
                func.avg(MetaShift.confidence).label("avg_confidence"),
            )
            .where(
                and_(
                    MetaShift.class_ == axie_class.lower(),
                    MetaShift.detected_at >= since,
                )
            )
            .group_by(MetaShift.shift_type)
        )

        stats_result = await self.db.execute(stats_query)
        stats_rows = stats_result.all()

        shift_breakdown = {row.shift_type: row.count for row in stats_rows}
        total_shifts = sum(shift_breakdown.values())
        avg_confidence = (
            sum(row.avg_confidence * row.count for row in stats_rows) / total_shifts
            if total_shifts > 0 else 0
        )

        # Get recent shifts
        recent_query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.class_ == axie_class.lower(),
                    MetaShift.detected_at >= since,
                )
            )
            .order_by(MetaShift.detected_at.desc())
            .limit(10)
        )

        recent_result = await self.db.execute(recent_query)
        recent_shifts = recent_result.scalars().all()

        data = ClassMetaData(
            class_=axie_class.lower(),
            total_shifts=total_shifts,
            avg_confidence=round(avg_confidence, 1),
            shift_breakdown=shift_breakdown,
            recent_shifts=[self._shift_to_dict(s) for s in recent_shifts],
        )

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_shifts)

        return data

    async def get_trending_traits(
        self,
        shift_types: Optional[List[str]] = None,
        min_confidence: int = 30,
        limit: int = 20,
        use_cache: bool = True,
    ) -> List[TrendingTrait]:
        """
        Get currently trending traits based on recent meta shifts.

        Groups shifts by trait and returns those with multiple occurrences
        or high confidence scores.
        """
        cache_key = f"meta_aggregator:trending:{min_confidence}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached[:limit]

        since = datetime.now(timezone.utc) - timedelta(hours=48)

        # Build filter conditions
        conditions = [
            MetaShift.detected_at >= since,
            MetaShift.confidence >= min_confidence,
        ]

        if shift_types:
            conditions.append(MetaShift.shift_type.in_(shift_types))

        # Aggregate by trait
        query = (
            select(
                MetaShift.trait_key,
                MetaShift.class_,
                func.max(MetaShift.shift_type).label("shift_type"),
                func.max(MetaShift.velocity_24h).label("velocity_24h"),
                func.max(MetaShift.velocity_7d).label("velocity_7d"),
                func.max(MetaShift.confidence).label("max_confidence"),
                func.min(MetaShift.detected_at).label("first_detected"),
                func.count(MetaShift.id).label("occurrences"),
            )
            .where(and_(*conditions))
            .group_by(MetaShift.trait_key, MetaShift.class_)
            .order_by(desc("max_confidence"), desc("occurrences"))
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        trending = [
            TrendingTrait(
                trait_key=row.trait_key,
                class_=row.class_,
                shift_type=row.shift_type,
                velocity_24h=row.velocity_24h,
                velocity_7d=row.velocity_7d,
                confidence=row.max_confidence or 0,
                first_detected=row.first_detected.isoformat() if row.first_detected else "",
                occurrences=row.occurrences,
            )
            for row in rows
        ]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, trending, self.config.cache_ttl_shifts)

        return trending

    async def get_velocity_leaders(
        self,
        direction: Literal["up", "down"] = "up",
        hours: int = 24,
        limit: int = 10,
        use_cache: bool = True,
    ) -> List[MetaShiftData]:
        """
        Get traits with highest price velocity (fastest movers).

        Args:
            direction: "up" for gainers, "down" for losers
            hours: Look back period
            limit: Maximum results
        """
        cache_key = f"meta_aggregator:velocity:{direction}:{hours}"

        if use_cache and self.cache and self.cache.is_connected:
            cached = await self.cache._get(cache_key)
            if cached:
                return cached[:limit]

        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Order by velocity (positive for up, negative for down)
        if direction == "up":
            order_col = MetaShift.velocity_24h.desc()
            velocity_filter = MetaShift.velocity_24h > 0
        else:
            order_col = MetaShift.velocity_24h.asc()
            velocity_filter = MetaShift.velocity_24h < 0

        query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.detected_at >= since,
                    velocity_filter,
                    MetaShift.velocity_24h.isnot(None),
                )
            )
            .order_by(order_col)
            .limit(limit)
        )

        result = await self.db.execute(query)
        shifts = result.scalars().all()

        data = [self._shift_to_dict(s) for s in shifts]

        if self.cache and self.cache.is_connected:
            await self.cache._set(cache_key, data, self.config.cache_ttl_shifts)

        return data

    async def get_all_shifts(
        self,
        min_confidence: int = 25,
        hours: int = 24,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """
        Get all recent meta shifts with pagination.

        Returns shifts sorted by detected_at (most recent first).
        """
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        # Count total
        count_query = (
            select(func.count(MetaShift.id))
            .where(
                and_(
                    MetaShift.detected_at >= since,
                    MetaShift.confidence >= min_confidence,
                )
            )
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get shifts
        query = (
            select(MetaShift)
            .where(
                and_(
                    MetaShift.detected_at >= since,
                    MetaShift.confidence >= min_confidence,
                )
            )
            .order_by(MetaShift.detected_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(query)
        shifts = result.scalars().all()

        return {
            "shifts": [self._shift_to_dict(s) for s in shifts],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _shift_to_dict(self, shift: MetaShift) -> MetaShiftData:
        """Convert MetaShift model to TypedDict."""
        return MetaShiftData(
            id=shift.id,
            trait_key=shift.trait_key,
            class_=shift.class_,
            shift_type=shift.shift_type,
            confidence=shift.confidence or 0,
            signals=shift.signals or [],
            velocity_24h=shift.velocity_24h,
            velocity_7d=shift.velocity_7d,
            volume_change_24h=shift.volume_change_24h,
            detected_at=shift.detected_at.isoformat() if shift.detected_at else "",
        )


# Factory function for dependency injection
async def get_meta_aggregator(
    db: AsyncSession,
    cache: Optional[RedisCacheManager] = None,
) -> MetaAggregatorService:
    """Create MetaAggregatorService instance with optional cache."""
    if cache is None:
        try:
            cache = await get_cache_manager()
        except Exception:
            cache = None

    return MetaAggregatorService(db, cache)
