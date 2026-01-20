"""
Meta Shifts API endpoints.

Exposes meta shift detection signals from the meta analyzer Lambda.
This data helps traders identify early movers and market trends.
"""

import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

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
    trait_key: str = Field(..., description="Trait identifier (e.g., 'class:beast', 'part:horn:lagging')")
    class_: Optional[str] = Field(None, alias="class", description="Axie class")
    shift_type: str = Field(..., description="Type of shift: rising, falling, emerging, fading")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    signals: List[str] = Field(..., description="Contributing signals (e.g., '24h price +15%')")
    price_velocity_24h: Optional[dict] = Field(None, description="24-hour price change data")
    price_velocity_7d: Optional[dict] = Field(None, description="7-day price change data")
    volume_change: Optional[dict] = Field(None, description="Volume change data")
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


class MetaShiftsResponse(BaseModel):
    """Response for meta shifts list."""
    success: bool
    data: List[dict]
    meta: dict


class MetaSummaryResponse(BaseModel):
    """Response for meta summary."""
    success: bool
    data: MetaSummary
    meta: dict


# =========================================================================
# Redis Client Helper
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
    """Get data from meta cache."""
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
# Endpoints
# =========================================================================

@router.get("/summary", response_model=MetaSummaryResponse)
async def get_meta_summary():
    """
    Get summary of current meta shifts.

    Returns counts of each shift type (rising, falling, emerging, fading)
    and the timestamp of the last analysis.
    """
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
    limit: int = Query(20, ge=1, le=50, description="Maximum results"),
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
    shifts = []

    if shift_type:
        # Get specific type
        if shift_type not in ["rising", "falling", "emerging", "fading"]:
            raise HTTPException(
                status_code=400,
                detail="shift_type must be one of: rising, falling, emerging, fading"
            )

        type_shifts = await get_meta_cache(f"meta:{shift_type}")
        if type_shifts:
            shifts = type_shifts
    else:
        # Get all types
        for stype in ["rising", "falling", "emerging", "fading"]:
            type_shifts = await get_meta_cache(f"meta:{stype}")
            if type_shifts:
                shifts.extend(type_shifts)

    # Filter by confidence
    shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]

    # Sort by confidence descending
    shifts.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    # Apply limit
    shifts = shifts[:limit]

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type_filter": shift_type,
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/shifts/{trait_key}", response_model=MetaShiftsResponse)
async def get_trait_meta_shift(
    trait_key: str,
):
    """
    Get meta shift data for a specific trait.

    Trait keys follow the format:
    - `class:beast` - Class-level meta
    - `part:horn:lagging` - Part-level meta
    """
    # Search all shift types for this trait
    matching_shifts = []

    for shift_type in ["rising", "falling", "emerging", "fading"]:
        type_shifts = await get_meta_cache(f"meta:{shift_type}")
        if type_shifts:
            for shift in type_shifts:
                if shift.get("trait_key") == trait_key:
                    matching_shifts.append(shift)

    if not matching_shifts:
        raise HTTPException(
            status_code=404,
            detail=f"No meta shift data found for trait: {trait_key}"
        )

    return {
        "success": True,
        "data": matching_shifts,
        "meta": {
            "trait_key": trait_key,
            "count": len(matching_shifts),
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/rising", response_model=MetaShiftsResponse)
async def get_rising_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
):
    """
    Get traits with rising prices (>15% in 24h).

    These traits are experiencing rapid price increases and may
    indicate emerging meta or pump activity. Use confidence score
    to filter for more reliable signals.
    """
    shifts = await get_meta_cache("meta:rising")

    if not shifts:
        return {
            "success": True,
            "data": [],
            "meta": {
                "count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    # Filter and limit
    shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]
    shifts = shifts[:limit]

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "rising",
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/falling", response_model=MetaShiftsResponse)
async def get_falling_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
):
    """
    Get traits with falling prices (>15% drop in 24h).

    These traits are experiencing rapid price decreases. May indicate
    meta shift away from these traits or market correction.
    """
    shifts = await get_meta_cache("meta:falling")

    if not shifts:
        return {
            "success": True,
            "data": [],
            "meta": {
                "count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]
    shifts = shifts[:limit]

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "falling",
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/emerging", response_model=MetaShiftsResponse)
async def get_emerging_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
):
    """
    Get emerging meta trends (>10% sustained increase over 7 days).

    These traits show sustained growth patterns and may indicate
    new meta forming. More reliable than short-term signals.
    """
    shifts = await get_meta_cache("meta:emerging")

    if not shifts:
        return {
            "success": True,
            "data": [],
            "meta": {
                "count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]
    shifts = shifts[:limit]

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "emerging",
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/fading", response_model=MetaShiftsResponse)
async def get_fading_meta(
    limit: int = Query(20, ge=1, le=50),
    min_confidence: int = Query(25, ge=0, le=100),
):
    """
    Get fading meta trends (>10% sustained decrease over 7 days).

    These traits show sustained decline and may indicate
    meta shifting away. Consider selling or avoiding these traits.
    """
    shifts = await get_meta_cache("meta:fading")

    if not shifts:
        return {
            "success": True,
            "data": [],
            "meta": {
                "count": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    shifts = [s for s in shifts if s.get("confidence", 0) >= min_confidence]
    shifts = shifts[:limit]

    return {
        "success": True,
        "data": shifts,
        "meta": {
            "count": len(shifts),
            "shift_type": "fading",
            "min_confidence": min_confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/health")
async def meta_cache_health():
    """
    Check meta cache health status.

    Returns connection status and availability of meta data.
    """
    client = await get_redis_client()

    if not client:
        return {
            "success": True,
            "data": {
                "redis_available": False,
                "message": "Redis not available or not configured",
            }
        }

    # Check for meta data presence
    summary = await get_meta_cache("meta:summary")

    return {
        "success": True,
        "data": {
            "redis_available": True,
            "meta_data_present": summary is not None,
            "last_analysis": summary.get("timestamp") if summary else None,
            "total_shifts": summary.get("total_shifts") if summary else 0,
        }
    }
