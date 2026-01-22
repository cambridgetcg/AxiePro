"""
Meta Shifts API endpoints.

Exposes meta shift detection signals from the meta analyzer Lambda.
This data helps traders identify early movers and market trends.

Now enhanced with MetaAggregatorService for database-backed queries
in addition to Redis cache reads.
"""

import json
from datetime import datetime, timezone
from typing import Optional, List, Literal
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import get_db
from src.services.meta_aggregator import (
    MetaAggregatorService,
    get_meta_aggregator,
)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

import os

router = APIRouter(prefix="/meta", tags=["meta"])


# =========================================================================
# Pydantic Models (Response Schemas)
# =========================================================================

class MetaShift(BaseModel):
    """Individual meta shift signal."""
    id: Optional[int] = None
    trait_key: str = Field(..., description="Trait identifier (e.g., 'class:beast', 'part:horn:lagging')")
    class_: Optional[str] = Field(None, alias="class", description="Axie class")
    shift_type: str = Field(..., description="Type of shift: rising, falling, emerging, fading")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    signals: List[str] = Field(default=[], description="Contributing signals (e.g., '24h price +15%')")
    velocity_24h: Optional[float] = Field(None, description="24-hour price velocity %")
    velocity_7d: Optional[float] = Field(None, description="7-day price velocity %")
    volume_change_24h: Optional[float] = Field(None, description="24-hour volume change %")
    detected_at: str = Field(..., description="ISO timestamp of detection")

    class Config:
        populate_by_name = True


class MetaSummary(BaseModel):
    """Summary of all meta shifts."""
    timestamp: str
    total_shifts: int
    rising: int
    falling: int
    emerging: int
    fading: int
    top_rising: Optional[List[dict]] = None
    top_falling: Optional[List[dict]] = None


class TrendingTrait(BaseModel):
    """Trending trait with velocity data."""
    trait_key: str
    class_: str = Field(alias="class")
    shift_type: str
    velocity_24h: Optional[float]
    velocity_7d: Optional[float]
    confidence: int
    first_detected: str
    occurrences: int

    class Config:
        populate_by_name = True


class ClassMeta(BaseModel):
    """Meta analysis for a specific class."""
    class_: str = Field(alias="class")
    total_shifts: int
    avg_confidence: float
    shift_breakdown: dict
    recent_shifts: List[dict]

    class Config:
        populate_by_name = True


class MetaShiftsResponse(BaseModel):
    """Response for meta shifts list."""
    success: bool
    data: List[dict]
    meta: dict


class MetaSummaryResponse(BaseModel):
    """Response for meta summary."""
    success: bool
    data: dict
    meta: dict


class TrendingResponse(BaseModel):
    """Response for trending traits."""
    success: bool
    data: List[dict]
    meta: dict


class ClassMetaResponse(BaseModel):
    """Response for class meta analysis."""
    success: bool
    data: dict
    meta: dict


# =========================================================================
# Redis Client Helper (for backward compatibility with lambda cache)
# =========================================================================

_redis_client = None


async def get_redis_client():
    """Get async Redis client for reading meta cache."""
    global _redis_client

    if not REDIS_AVAILABLE:
        return None

    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            _redis_client = redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await _redis_client.ping()
        except Exception:
            _redis_client = None

    return _redis_client


async def get_meta_cache(key: str) -> Optional[dict]:
    """Get data from meta cache (lambda-populated)."""
    client = await get_redis_client()
    if not client:
        return None

    try:
        value = await client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception:
        return None


# =========================================================================
# Endpoints - Enhanced with MetaAggregatorService
# =========================================================================

@router.get("/summary", response_model=MetaSummaryResponse)
async def get_meta_summary(
    use_cache: bool = Query(True, description="Use cached results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get summary of current meta shifts.

    Returns counts of each shift type (rising, falling, emerging, fading),
    the timestamp of the last analysis, and top movers.

    Data sources:
    - Primary: MetaAggregatorService (database)
    - Fallback: Redis cache (lambda-populated)
    """
    try:
        aggregator = await get_meta_aggregator(db)
        summary = await aggregator.get_meta_summary(use_cache=use_cache)

        return {
            "success": True,
            "data": summary,
            "meta": {
                "source": "database",
                "cached": use_cache,
            }
        }
    except Exception as e:
        # Fallback to Redis cache
        summary = await get_meta_cache("meta:summary")

        if not summary:
            raise HTTPException(
                status_code=503,
                detail="Meta analysis data not available. The meta analyzer runs hourly."
            )

        return {
            "success": True,
            "data": summary,
            "meta": {
                "source": "redis_cache",
                "cache_key": "meta:summary",
                "ttl_seconds": 3600,
            }
        }


@router.get("/shifts", response_model=MetaShiftsResponse)
async def get_meta_shifts(
    shift_type: Optional[str] = Query(
        None,
        description="Filter by shift type: rising, falling, emerging, fading"
    ),
    min_confidence: int = Query(
        25,
        ge=0,
        le=100,
        description="Minimum confidence score (0-100)"
    ),
    hours: int = Query(24, ge=1, le=168, description="Look back period in hours"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    use_cache: bool = Query(True, description="Use cached results"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current meta shift signals.

    Meta shifts indicate significant changes in trait pricing or volume:
    - **rising**: Rapid price increase (>15% in 24h)
    - **falling**: Rapid price decrease (>15% in 24h)
    - **emerging**: Sustained price increase (>10% over 7 days)
    - **fading**: Sustained price decrease (>10% over 7 days)

    Higher confidence indicates more signals aligned (velocity + volume + trend).
    """
    if shift_type and shift_type not in ["rising", "falling", "emerging", "fading"]:
        raise HTTPException(
            status_code=400,
            detail="shift_type must be one of: rising, falling, emerging, fading"
        )

    try:
        aggregator = await get_meta_aggregator(db)

        if shift_type:
            shifts = await aggregator.get_shifts_by_type(
                shift_type=shift_type,
                min_confidence=min_confidence,
                limit=limit,
                hours=hours,
                use_cache=use_cache,
            )
        else:
            result = await aggregator.get_all_shifts(
                min_confidence=min_confidence,
                hours=hours,
                limit=limit,
            )
            shifts = result["shifts"]

        return {
            "success": True,
            "data": shifts,
            "meta": {
                "count": len(shifts),
                "shift_type_filter": shift_type,
                "min_confidence": min_confidence,
                "hours": hours,
                "source": "database",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }
    except Exception:
        # Fallback to Redis cache
        shifts = []

        if shift_type:
            type_shifts = await get_meta_cache(f"meta:{shift_type}")
            if type_shifts:
                shifts = type_shifts
        else:
            for stype in ["rising", "falling", "emerging", "fading"]:
                type_shifts = await get_meta_cache(f"meta:{stype}")
                if type_shifts:
                    shifts.extend(type_shifts)

        shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]
        shifts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        shifts = shifts[:limit]

        return {
            "success": True,
            "data": shifts,
            "meta": {
                "count": len(shifts),
                "shift_type_filter": shift_type,
                "min_confidence": min_confidence,
                "source": "redis_cache",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        }


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_traits(
    shift_types: Optional[str] = Query(
        None,
        description="Comma-separated shift types to filter (e.g., 'rising,emerging')"
    ),
    min_confidence: int = Query(30, ge=0, le=100),
    limit: int = Query(20, ge=1, le=50),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get currently trending traits based on recent meta shifts.

    Returns traits with multiple shift detections or high confidence,
    aggregated over the last 48 hours.
    """
    aggregator = await get_meta_aggregator(db)

    types_list = None
    if shift_types:
        types_list = [t.strip() for t in shift_types.split(",")]

    trending = await aggregator.get_trending_traits(
        shift_types=types_list,
        min_confidence=min_confidence,
        limit=limit,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": trending,
        "meta": {
            "count": len(trending),
            "shift_types_filter": types_list,
            "min_confidence": min_confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/velocity-leaders", response_model=MetaShiftsResponse)
async def get_velocity_leaders(
    direction: Literal["up", "down"] = Query("up", description="Price direction"),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(10, ge=1, le=50),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get traits with highest price velocity (fastest movers).

    - **up**: Biggest gainers (positive velocity)
    - **down**: Biggest losers (negative velocity)
    """
    aggregator = await get_meta_aggregator(db)

    leaders = await aggregator.get_velocity_leaders(
        direction=direction,
        hours=hours,
        limit=limit,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": leaders,
        "meta": {
            "count": len(leaders),
            "direction": direction,
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/class/{axie_class}", response_model=ClassMetaResponse)
async def get_class_meta(
    axie_class: str,
    hours: int = Query(24, ge=1, le=168),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get meta analysis for a specific Axie class.

    Returns aggregated stats and recent shifts for the class.
    """
    aggregator = await get_meta_aggregator(db)

    class_data = await aggregator.get_class_meta(
        axie_class=axie_class,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": class_data,
        "meta": {
            "class": axie_class.lower(),
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/trait/{trait_key:path}", response_model=MetaShiftsResponse)
async def get_trait_meta_history(
    trait_key: str,
    days: int = Query(7, ge=1, le=30, description="Look back period in days"),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get meta shift history for a specific trait.

    Trait keys follow the format:
    - `class:beast` - Class-level meta
    - `part:horn:lagging` - Part-level meta
    """
    aggregator = await get_meta_aggregator(db)

    history = await aggregator.get_trait_history(
        trait_key=trait_key,
        days=days,
        use_cache=use_cache,
    )

    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No meta shift history found for trait: {trait_key}"
        )

    return {
        "success": True,
        "data": history,
        "meta": {
            "trait_key": trait_key,
            "days": days,
            "count": len(history),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


# =========================================================================
# Convenience Endpoints (shift type shortcuts)
# =========================================================================

@router.get("/rising", response_model=MetaShiftsResponse)
async def get_rising_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
    hours: int = Query(24, ge=1, le=168),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get traits with rising prices (>15% in 24h).

    These traits are experiencing rapid price increases and may
    indicate emerging meta or pump activity.
    """
    aggregator = await get_meta_aggregator(db)

    shifts = await aggregator.get_shifts_by_type(
        shift_type="rising",
        min_confidence=min_confidence,
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "rising",
            "min_confidence": min_confidence,
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/falling", response_model=MetaShiftsResponse)
async def get_falling_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
    hours: int = Query(24, ge=1, le=168),
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get traits with falling prices (>15% drop in 24h).

    These traits are experiencing rapid price decreases.
    """
    aggregator = await get_meta_aggregator(db)

    shifts = await aggregator.get_shifts_by_type(
        shift_type="falling",
        min_confidence=min_confidence,
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "falling",
            "min_confidence": min_confidence,
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/emerging", response_model=MetaShiftsResponse)
async def get_emerging_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
    hours: int = Query(168, ge=1, le=336),  # Default 7 days for emerging
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get emerging meta trends (>10% sustained increase over 7 days).

    These traits show sustained growth patterns and may indicate
    new meta forming.
    """
    aggregator = await get_meta_aggregator(db)

    shifts = await aggregator.get_shifts_by_type(
        shift_type="emerging",
        min_confidence=min_confidence,
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "emerging",
            "min_confidence": min_confidence,
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/fading", response_model=MetaShiftsResponse)
async def get_fading_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
    hours: int = Query(168, ge=1, le=336),  # Default 7 days for fading
    use_cache: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """
    Get fading meta trends (>10% sustained decrease over 7 days).

    These traits show sustained decline and may indicate
    meta shifting away.
    """
    aggregator = await get_meta_aggregator(db)

    shifts = await aggregator.get_shifts_by_type(
        shift_type="fading",
        min_confidence=min_confidence,
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "fading",
            "min_confidence": min_confidence,
            "hours": hours,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    }


@router.get("/health")
async def meta_health(
    db: AsyncSession = Depends(get_db),
):
    """
    Check meta service health status.

    Returns connection status for both database and Redis.
    """
    # Check Redis
    redis_client = await get_redis_client()
    redis_available = redis_client is not None

    redis_summary = None
    if redis_available:
        redis_summary = await get_meta_cache("meta:summary")

    # Check database via aggregator
    db_available = False
    db_shift_count = 0
    try:
        aggregator = await get_meta_aggregator(db)
        result = await aggregator.get_all_shifts(limit=1, hours=24)
        db_available = True
        db_shift_count = result.get("total", 0)
    except Exception:
        pass

    return {
        "success": True,
        "data": {
            "redis_available": redis_available,
            "redis_meta_present": redis_summary is not None,
            "redis_last_analysis": redis_summary.get("timestamp") if redis_summary else None,
            "database_available": db_available,
            "database_shifts_24h": db_shift_count,
        }
    }
