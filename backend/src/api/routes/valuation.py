"""
Valuation API endpoints.

Provides routes for:
- Axie fair market value estimation
- Deal detection and alerts
- Trait statistics
- Model training triggers
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import get_db
from src.services.valuation import HedonicValuationService, ValuationResult
from src.services.cache import get_cache_manager, RedisCacheManager
from src.services.scoring import NormalizedDealScorer
from src.services.deals_aggregator import DealsAggregatorService, get_deals_aggregator

router = APIRouter(prefix="/valuation", tags=["valuation"])


# =========================================================================
# Pydantic Models (Response Schemas)
# =========================================================================

class ValuationResponse(BaseModel):
    """Response for single Axie valuation."""
    axie_id: int
    valuation: Optional[dict] = Field(None, description="Value estimates with confidence intervals (null if unavailable)")
    market_context: Optional[dict] = Field(None, description="Floor prices and market averages (null if unavailable)")
    deal_analysis: Optional[dict] = Field(None, description="Discount percent, z-score, deal status (null if unavailable)")
    feature_contributions: dict = Field(
        default_factory=dict,
        description="Contribution of each feature to the valuation"
    )
    metadata: dict = Field(..., description="Model version, computation timestamp, and availability status")

    class Config:
        json_schema_extra = {
            "example": {
                "axie_id": 12345,
                "valuation": {
                    "hedonic_eth": 0.025,
                    "ml_eth": None,
                    "ensemble_eth": 0.025,
                    "confidence_lower_eth": 0.018,
                    "confidence_upper_eth": 0.034,
                    "confidence_score": 0.85
                },
                "market_context": {
                    "current_listing_eth": 0.020,
                    "class_floor_eth": 0.008,
                    "class_avg_eth": 0.022
                },
                "deal_analysis": {
                    "discount_percent": 20.0,
                    "z_score": -1.8,
                    "deal_score": 65,
                    "is_deal": True,
                    "is_snipe": False
                },
                "feature_contributions": {
                    "class:beast": 0.15,
                    "purity:5": 0.22,
                    "breed:0": 0.08
                },
                "metadata": {
                    "method": "hedonic",
                    "model_version": "hedonic_v20250101_120000",
                    "computed_at": "2025-01-01T12:00:00Z"
                }
            }
        }


class BatchValuationRequest(BaseModel):
    """Request for batch valuation."""
    axie_ids: List[int] = Field(..., min_length=1, max_length=100)


class BatchValuationResponse(BaseModel):
    """Response for batch valuation."""
    success: bool
    valuations: List[dict]
    meta: dict


class DealResponse(BaseModel):
    """Response for deal detection."""
    axie_id: int
    class_: str = Field(..., alias="class")
    listing_price_eth: float
    fair_value_eth: float
    discount_percent: float
    z_score: Optional[float]
    deal_score: int
    deal_type: str
    marketplace_url: str
    detected_at: str

    class Config:
        populate_by_name = True


class DealsListResponse(BaseModel):
    """Response for deals list."""
    success: bool
    data: List[dict]
    meta: dict


class TraitStatsResponse(BaseModel):
    """Response for trait statistics."""
    trait_key: str
    trait_type: str
    class_: Optional[str] = Field(None, alias="class")
    avg_price_eth: Optional[float]
    median_price_eth: Optional[float]
    std_dev_eth: Optional[float]
    sample_count: int
    time_window_hours: int
    computed_at: str

    class Config:
        populate_by_name = True


class ModelStatsResponse(BaseModel):
    """Response for model statistics."""
    model_config = {"protected_namespaces": ()}

    model_version: str
    r_squared: float
    adj_r_squared: float
    rmse: float
    sample_size: int
    feature_count: int
    trained_at: str
    is_active: bool


class TrainModelRequest(BaseModel):
    """Request to train a new model."""
    time_window_days: int = Field(30, ge=7, le=90)
    min_samples: int = Field(1000, ge=100, le=100000)


# =========================================================================
# Endpoints
# =========================================================================

@router.get("/{axie_id}", response_model=ValuationResponse)
async def get_valuation(
    axie_id: int,
    use_cache: bool = Query(True, description="Whether to use cached valuation if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get fair market value estimation for a single Axie.

    The valuation uses a hedonic pricing model that decomposes the price
    into attribute contributions (class, parts, breed count, purity).

    Returns:
    - **valuation**: Value estimates with 95% confidence interval
    - **market_context**: Current floor prices and class averages
    - **deal_analysis**: Whether the current listing is a deal/snipe opportunity
    - **feature_contributions**: How each attribute affects the value
    """
    cache = await get_cache_manager()

    # Check cache first
    if use_cache and cache.is_connected:
        cached = await cache.get_valuation(axie_id)
        if cached:
            return cached

    # Compute valuation
    service = HedonicValuationService(db)
    result = await service.valuate(axie_id, include_market_context=True)

    # Return graceful response for unavailable valuations (no 404)
    if result.confidence_score == 0.0 and result.hedonic_value_eth is None:
        return {
            "axie_id": axie_id,
            "valuation": None,
            "market_context": None,
            "deal_analysis": None,
            "feature_contributions": {},
            "metadata": {
                "method": None,
                "model_version": None,
                "computed_at": None,
                "available": False,
                "reason": "Axie not found in database or insufficient data for valuation"
            }
        }

    # Convert to response format
    response_data = result.to_dict()
    # Mark as available
    response_data["metadata"]["available"] = True

    # Cache the result
    if cache.is_connected:
        await cache.set_valuation(axie_id, response_data)

    return response_data


@router.post("/batch", response_model=BatchValuationResponse)
async def batch_valuation(
    request: BatchValuationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Get valuations for multiple Axies efficiently.

    Maximum 100 Axies per request. Results are returned in the same
    order as the input list.
    """
    cache = await get_cache_manager()

    # Check cache for all IDs
    cached_results = {}
    if cache.is_connected:
        cached_results = await cache.get_valuations_batch(request.axie_ids)

    # Find IDs that need computation
    missing_ids = [
        aid for aid in request.axie_ids
        if cached_results.get(aid) is None
    ]

    # Compute missing valuations
    computed = {}
    if missing_ids:
        service = HedonicValuationService(db)
        results = await service.batch_valuate(missing_ids)
        for result in results:
            data = result.to_dict()
            computed[result.axie_id] = data
            # Cache the result
            if cache.is_connected:
                await cache.set_valuation(result.axie_id, data)

    # Combine results in original order
    valuations = []
    success_count = 0

    for axie_id in request.axie_ids:
        if axie_id in cached_results and cached_results[axie_id]:
            valuations.append(cached_results[axie_id])
            success_count += 1
        elif axie_id in computed:
            valuations.append(computed[axie_id])
            if computed[axie_id].get("valuation", {}).get("ensemble_eth"):
                success_count += 1
        else:
            valuations.append({"axie_id": axie_id, "error": "Not found"})

    return {
        "success": True,
        "valuations": valuations,
        "meta": {
            "requested": len(request.axie_ids),
            "successful": success_count,
            "cached": len(request.axie_ids) - len(missing_ids),
        }
    }


@router.get("/deals/live", response_model=DealsListResponse)
async def get_live_deals(
    class_: Optional[str] = Query(None, alias="class", description="Filter by Axie class"),
    min_score: int = Query(50, ge=0, le=100, description="Minimum deal score"),
    limit: int = Query(20, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168, description="Look back period in hours"),
    include_normalized: bool = Query(True, description="Include normalized scoring"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current deal opportunities with normalized scoring.

    Deals are listings priced significantly below their estimated fair value.
    Uses database queries with Redis caching for efficient access.

    **Legacy Scoring (deal_score):**
    - Deal (50-79): 20-40% below FMV
    - Snipe (80+): 40%+ below FMV

    **Normalized Scoring (normalized_score):**
    - SNIPE (80-100): Exceptional, act immediately
    - ELITE (60-79): High value, strong buy
    - GOOD (40-59): Above average
    - FAIR (20-39): Marginal
    - PASS (0-19): Below threshold

    Results are sorted by deal score (best deals first).
    """
    aggregator = await get_deals_aggregator(db)

    deals = await aggregator.get_live_deals(
        axie_class=class_,
        min_score=min_score,
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    # Add normalized scoring if requested
    if include_normalized and deals:
        scorer = NormalizedDealScorer()
        for deal in deals:
            score_result = scorer.score_deal(deal)
            deal["normalized_score"] = score_result.normalized_score
            deal["tier"] = score_result.tier.value
            deal["tier_label"] = score_result.tier_label
            deal["tier_color"] = score_result.tier_color
            deal["score_components"] = {
                "discount_percentile": round(score_result.discount_percentile, 3),
                "confidence_percentile": round(score_result.confidence_percentile, 3),
                "liquidity_score": round(score_result.liquidity_score, 3),
                "time_score": round(score_result.time_score, 3),
            }

    return {
        "success": True,
        "data": deals,
        "meta": {
            "count": len(deals),
            "min_score": min_score,
            "class_filter": class_,
            "hours": hours,
            "source": "database",
            "scoring_version": "2.0" if include_normalized else "1.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/deals/snipes", response_model=DealsListResponse)
async def get_snipe_opportunities(
    limit: int = Query(20, ge=1, le=50),
    hours: int = Query(24, ge=1, le=168, description="Look back period in hours"),
    include_normalized: bool = Query(True, description="Include normalized scoring"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get top snipe opportunities (high-value deals) with normalized scoring.

    Snipes are extremely undervalued listings (40%+ below FMV)
    that represent the best buying opportunities.
    Uses database queries with Redis caching for efficient access.

    **Tier System:**
    - SNIPE tier deals have normalized_score 80-100
    - Time-sensitive: score decays based on listing freshness
    """
    aggregator = await get_deals_aggregator(db)

    snipes = await aggregator.get_snipes(
        limit=limit,
        hours=hours,
        use_cache=use_cache,
    )

    # Add normalized scoring if requested
    if include_normalized and snipes:
        scorer = NormalizedDealScorer()
        for snipe in snipes:
            score_result = scorer.score_deal(snipe)
            snipe["normalized_score"] = score_result.normalized_score
            snipe["tier"] = score_result.tier.value
            snipe["tier_label"] = score_result.tier_label
            snipe["tier_color"] = score_result.tier_color
            snipe["score_components"] = {
                "discount_percentile": round(score_result.discount_percentile, 3),
                "confidence_percentile": round(score_result.confidence_percentile, 3),
                "liquidity_score": round(score_result.liquidity_score, 3),
                "time_score": round(score_result.time_score, 3),
            }

    return {
        "success": True,
        "data": snipes,
        "meta": {
            "count": len(snipes),
            "hours": hours,
            "source": "database",
            "scoring_version": "2.0" if include_normalized else "1.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/deals/summary")
async def get_deals_summary(
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive deals summary.

    Returns:
    - Total deal counts (overall and active)
    - Breakdown by Axie class
    - Average discount and score
    - Top deals and snipe opportunities
    """
    aggregator = await get_deals_aggregator(db)
    summary = await aggregator.get_deals_summary(use_cache=use_cache)

    return {
        "success": True,
        "data": summary,
        "meta": {
            "source": "database",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/deals/stats")
async def get_deals_stats(
    hours: int = Query(24, ge=1, le=168, description="Period in hours"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregated deal statistics.

    Returns metrics including:
    - Total deals detected and sold
    - Average time to sell
    - Average discount and score
    - Snipe rate percentage
    """
    aggregator = await get_deals_aggregator(db)
    stats = await aggregator.get_deal_stats(hours=hours, use_cache=use_cache)

    return {
        "success": True,
        "data": stats,
        "meta": {
            "hours": hours,
            "source": "database",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/deals/class/{axie_class}")
async def get_class_deals(
    axie_class: str,
    hours: int = Query(24, ge=1, le=168, description="Look back period in hours"),
    use_cache: bool = Query(True, description="Use cached results if available"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deal analysis for a specific Axie class.

    Returns:
    - Total and active deal counts for the class
    - Average discount and score
    - Recent deals for the class
    """
    aggregator = await get_deals_aggregator(db)
    data = await aggregator.get_class_deals(
        axie_class=axie_class,
        hours=hours,
        use_cache=use_cache,
    )

    return {
        "success": True,
        "data": data,
        "meta": {
            "class": axie_class.lower(),
            "hours": hours,
            "source": "database",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/deals/axie/{axie_id}")
async def get_axie_deal(
    axie_id: int,
    include_history: bool = Query(False, description="Include deal history"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get deal information for a specific Axie.

    Returns the most recent deal detection for the Axie.
    Optionally includes historical deal detections.
    """
    aggregator = await get_deals_aggregator(db)

    if include_history:
        history = await aggregator.get_deal_history(axie_id)
        return {
            "success": True,
            "data": history,
            "meta": {
                "axie_id": axie_id,
                "count": len(history),
                "source": "database",
                "timestamp": datetime.utcnow().isoformat(),
            }
        }

    deal = await aggregator.get_deal_by_axie(axie_id)

    if not deal:
        raise HTTPException(
            status_code=404,
            detail=f"No deal found for Axie {axie_id}"
        )

    return {
        "success": True,
        "data": deal,
        "meta": {
            "axie_id": axie_id,
            "source": "database",
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/stats/trait/{trait_key}")
async def get_trait_statistics(
    trait_key: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get price statistics for a specific trait.

    Trait keys follow the format:
    - `class:beast` - Class-level stats
    - `part:eyes:kotaro` - Part-level stats
    - `breed:0` - Breed count stats

    Returns average, median, std dev, and sample count.
    """
    cache = await get_cache_manager()

    # Check cache
    if cache.is_connected:
        cached = await cache.get_trait_stats(trait_key)
        if cached:
            return {"success": True, "data": cached}

    # Query from valuation service
    service = HedonicValuationService(db)
    stats = await service._get_trait_stats(trait_key)

    if not stats:
        raise HTTPException(
            status_code=404,
            detail=f"No statistics found for trait: {trait_key}"
        )

    data = stats.to_dict()

    # Cache result
    if cache.is_connected:
        await cache.set_trait_stats(trait_key, data)

    return {"success": True, "data": data}


@router.get("/stats/floors")
async def get_floor_prices(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current floor prices by class.

    Returns the lowest listed price for each Axie class.
    Data is sourced from the price_snapshots table populated by
    the price_ingestion lambda every 5 minutes.
    """
    import logging
    logger = logging.getLogger(__name__)

    cache = await get_cache_manager()

    # Try cache first (TTL: 5 minutes)
    if cache.is_connected:
        try:
            floors = await cache.get_all_floor_prices()
            if floors:
                return {
                    "success": True,
                    "data": floors,
                    "meta": {"source": "cache"}
                }
        except Exception as e:
            logger.warning(f"Cache read failed for floor prices: {e}")

    # Query latest floor prices from price_snapshots table
    # This table is populated by the price_ingestion lambda every 5 minutes
    try:
        # Get the most recent floor price for each class
        # Using DISTINCT ON to get the latest snapshot per class
        query = text("""
            SELECT DISTINCT ON (class)
                class,
                floor_eth,
                time as snapshot_time
            FROM price_snapshots
            WHERE trait_key LIKE 'class:%'
              AND floor_eth IS NOT NULL
              AND time >= NOW() - INTERVAL '1 hour'
            ORDER BY class, time DESC
        """)

        result = await db.execute(query)
        rows = result.fetchall()

        floors = {}
        latest_snapshot = None

        for row in rows:
            class_name = row.class_.lower() if hasattr(row, 'class_') else row[0].lower()
            floor_eth = float(row.floor_eth) if hasattr(row, 'floor_eth') else float(row[1])
            snapshot_time = row.snapshot_time if hasattr(row, 'snapshot_time') else row[2]

            if floor_eth and floor_eth > 0:
                floors[class_name] = floor_eth

                # Track the most recent snapshot time
                if latest_snapshot is None or snapshot_time > latest_snapshot:
                    latest_snapshot = snapshot_time

                # Update cache for each class
                if cache.is_connected:
                    try:
                        await cache.set_floor_price(class_name, floor_eth)
                    except Exception as cache_error:
                        logger.warning(f"Failed to cache floor price for {class_name}: {cache_error}")

        if floors:
            return {
                "success": True,
                "data": floors,
                "meta": {
                    "source": "price_snapshots",
                    "snapshot_time": latest_snapshot.isoformat() if latest_snapshot else None,
                    "classes_found": len(floors),
                }
            }

        # Fallback: If no recent snapshots, try computing from sales data
        logger.warning("No recent price snapshots found, falling back to sales data")
        service = HedonicValuationService(db)
        stats = await service.compute_trait_statistics(time_window_hours=24)

        floors = {}
        for key, stat in stats.items():
            if key.startswith("class:"):
                class_name = key.split(":")[1]
                if stat.min_price_eth:
                    floors[class_name] = float(stat.min_price_eth)
                    if cache.is_connected:
                        try:
                            await cache.set_floor_price(class_name, float(stat.min_price_eth))
                        except Exception as cache_error:
                            logger.warning(f"Failed to cache floor price for {class_name}: {cache_error}")

        return {
            "success": True,
            "data": floors,
            "meta": {
                "source": "computed_fallback",
                "message": "Using sales-based computation as fallback"
            }
        }

    except Exception as e:
        logger.error(f"Failed to get floor prices: {e}")
        # Return empty data gracefully instead of 500 error
        return {
            "success": True,
            "data": {},
            "meta": {
                "source": "none",
                "message": "Floor price data not available. Market data collection may be pending."
            }
        }


@router.get("/model/info")
async def get_model_info(
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about the current valuation model.

    Returns model version, training statistics (R², RMSE),
    and training metadata.
    """
    service = HedonicValuationService(db)
    coefficients = await service._load_active_coefficients()

    if not coefficients:
        return {
            "success": True,
            "data": {
                "status": "no_model",
                "message": "No trained model available. Use POST /model/train to train one."
            }
        }

    return {
        "success": True,
        "data": {
            "model_version": coefficients.model_version,
            "r_squared": coefficients.r_squared,
            "adj_r_squared": coefficients.adj_r_squared,
            "rmse": coefficients.rmse,
            "sample_size": coefficients.sample_size,
            "feature_count": coefficients.feature_count,
            "train_start": coefficients.train_start.isoformat(),
            "train_end": coefficients.train_end.isoformat(),
            "trained_at": coefficients.trained_at.isoformat(),
        }
    }


@router.post("/model/train")
async def train_model(
    request: TrainModelRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Train a new hedonic pricing model.

    This trains the model using historical sales data from the specified
    time window. Training happens in the background and typically takes
    a few seconds to complete.

    **Note**: This endpoint should be restricted to admin users in production.
    """
    # In production, add authentication check here

    async def train_task():
        service = HedonicValuationService(db)
        try:
            result = await service.compute_coefficients(
                time_window_days=request.time_window_days,
                min_samples=request.min_samples,
            )
            # Also recompute trait statistics
            await service.compute_trait_statistics()
        except Exception as e:
            # Log error
            import logging
            logging.error(f"Model training failed: {e}")

    background_tasks.add_task(train_task)

    return {
        "success": True,
        "message": "Model training started in background",
        "parameters": {
            "time_window_days": request.time_window_days,
            "min_samples": request.min_samples,
        }
    }


@router.post("/stats/refresh")
async def refresh_statistics(
    background_tasks: BackgroundTasks,
    time_window_hours: int = Query(168, ge=24, le=720),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh trait statistics.

    Recomputes price statistics for all traits using the specified
    time window (default 7 days).

    **Note**: This endpoint should be restricted to admin users in production.
    """
    async def refresh_task():
        service = HedonicValuationService(db)
        try:
            await service.compute_trait_statistics(time_window_hours=time_window_hours)
        except Exception as e:
            import logging
            logging.error(f"Statistics refresh failed: {e}")

    background_tasks.add_task(refresh_task)

    return {
        "success": True,
        "message": "Statistics refresh started in background",
        "parameters": {"time_window_hours": time_window_hours}
    }


@router.get("/cache/health")
async def cache_health():
    """
    Check cache health status.

    Returns Redis connection status and memory usage.
    """
    cache = await get_cache_manager()
    status = await cache.health_check()

    return {
        "success": True,
        "data": status,
    }
