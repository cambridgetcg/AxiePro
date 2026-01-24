"""
Instrumentation API endpoints.

Provides event collection and feedback endpoints for the Claude-AxiePro
feedback system. Enables systematic measurement of feature effectiveness
and purpose alignment.

Endpoints:
  POST /instrumentation/events       - Record instrumentation events
  POST /instrumentation/events/batch - Record multiple events
  GET  /instrumentation/health       - Get overall product health
  GET  /instrumentation/health/{feature} - Get feature-specific health
  GET  /instrumentation/purpose      - Get purpose alignment analysis
  GET  /instrumentation/gaps         - Get identified gaps
  GET  /instrumentation/insights     - Get actionable insights
  POST /instrumentation/flows/run/{flow_type} - Run synthetic validation flow
  POST /instrumentation/flows/run-all - Run all synthetic validation flows
  GET  /instrumentation/flows/runs   - Get recent flow runs
  GET  /instrumentation/flows/health - Get synthetic flow health
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import get_db
from src.models.instrumentation import EventType, Feature, FlowType
from src.services.instrumentation import get_instrumentation_service
from src.services.synthetic_flows import FlowRunner

router = APIRouter(prefix="/instrumentation", tags=["instrumentation"])


# =========================================================================
# Pydantic Models (Request/Response Schemas)
# =========================================================================

class EventCreate(BaseModel):
    """Request schema for creating an instrumentation event."""
    event_type: str = Field(
        ...,
        description="Event type: usage, performance, error, value"
    )
    feature: str = Field(
        ...,
        description="Feature: explorer, breeding, deals, meta, analytics, portfolio, valuation"
    )
    action: str = Field(
        ...,
        max_length=100,
        description="Specific action (e.g., 'search', 'filter', 'simulate')"
    )
    session_id: Optional[str] = Field(
        None,
        max_length=36,
        description="Anonymous session identifier (UUID)"
    )
    data: Optional[dict] = Field(
        None,
        description="Additional event data (JSON)"
    )


class EventResponse(BaseModel):
    """Response schema for event creation."""
    success: bool
    data: dict
    meta: dict


class BatchEventsCreate(BaseModel):
    """Request schema for batch event creation."""
    events: List[EventCreate] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="List of events to record (max 100)"
    )


class BatchEventsResponse(BaseModel):
    """Response schema for batch event creation."""
    success: bool
    data: dict
    meta: dict


class HealthResponse(BaseModel):
    """Response schema for health status."""
    success: bool
    data: dict
    meta: dict


class PurposeResponse(BaseModel):
    """Response schema for purpose alignment."""
    success: bool
    data: dict
    meta: dict


class GapsResponse(BaseModel):
    """Response schema for gaps detection."""
    success: bool
    data: dict
    meta: dict


class InsightsResponse(BaseModel):
    """Response schema for insights."""
    success: bool
    data: dict
    meta: dict


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/events", response_model=EventResponse)
async def record_event(
    event: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a single instrumentation event.

    Events are used to track feature usage, performance, errors, and value
    delivery. This data enables purpose alignment measurement.

    **Event Types:**
    - `usage`: User interactions (searches, clicks, simulations)
    - `performance`: Timing and latency data
    - `error`: Error occurrences
    - `value`: Value delivery indicators (deal quality, prediction accuracy)

    **Features:**
    - `explorer`: Axie search and filtering
    - `breeding`: Breeding simulation
    - `deals`: Deal detection
    - `meta`: Meta shift analysis
    - `analytics`: Market analytics
    - `portfolio`: Portfolio tracking
    - `valuation`: Price valuation
    """
    try:
        event_type = EventType(event.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event_type. Must be one of: {[e.value for e in EventType]}"
        )

    try:
        feature = Feature(event.feature)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature. Must be one of: {[f.value for f in Feature]}"
        )

    service = await get_instrumentation_service()
    created_event = await service.record_event(
        db=db,
        event_type=event_type,
        feature=feature,
        action=event.action,
        session_id=event.session_id,
        data=event.data,
    )

    return {
        "success": True,
        "data": created_event.to_dict(),
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.post("/events/batch", response_model=BatchEventsResponse)
async def record_batch_events(
    batch: BatchEventsCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Record multiple instrumentation events in a single request.

    More efficient than individual calls for high-volume event collection.
    Maximum 100 events per batch.
    """
    # Validate all events first
    validated_events = []
    for idx, event in enumerate(batch.events):
        try:
            event_type = EventType(event.event_type)
            feature = Feature(event.feature)
            validated_events.append({
                "event_type": event_type.value,
                "feature": feature.value,
                "action": event.action,
                "session_id": event.session_id,
                "data": event.data,
            })
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event at index {idx}: {str(e)}"
            )

    service = await get_instrumentation_service()
    recorded_count = await service.record_batch_events(db, validated_events)

    return {
        "success": True,
        "data": {
            "recorded": recorded_count,
            "submitted": len(batch.events),
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


@router.get("/health", response_model=HealthResponse)
async def get_overall_health(
    db: AsyncSession = Depends(get_db),
):
    """
    Get overall product health status.

    Returns health metrics for all features including:
    - Overall health score (0-100)
    - Per-feature status (healthy, warning, degraded)
    - Error rates and usage counts

    Health is calculated from the last 24 hours of instrumentation data.
    """
    service = await get_instrumentation_service()
    health = await service.get_overall_health(db)

    return {
        "success": True,
        "data": health,
        "meta": {
            "cache_ttl_seconds": service.TTL_HEALTH,
        }
    }


@router.get("/health/{feature}", response_model=HealthResponse)
async def get_feature_health(
    feature: str,
    hours: int = Query(24, ge=1, le=168, description="Time window in hours (max 168 = 1 week)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get health status for a specific feature.

    Returns detailed health metrics including:
    - Status (healthy, warning, degraded)
    - Usage count and unique sessions
    - Error count and error rate

    Status thresholds:
    - healthy: error rate < 5%
    - warning: error rate 5-10%
    - degraded: error rate > 10%
    """
    try:
        feature_enum = Feature(feature)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feature. Must be one of: {[f.value for f in Feature]}"
        )

    service = await get_instrumentation_service()
    health = await service.get_feature_health(db, feature_enum, hours)

    return {
        "success": True,
        "data": health,
        "meta": {
            "cache_ttl_seconds": service.TTL_HEALTH,
        }
    }


@router.get("/purpose", response_model=PurposeResponse)
async def get_purpose_alignment(
    db: AsyncSession = Depends(get_db),
):
    """
    Get purpose alignment analysis.

    Analyzes how well AxiePro fulfills its purpose:
    **"Help serious traders dominate the Axie market"**

    Returns:
    - Overall alignment score (0-100)
    - Per-feature effectiveness scores
    - Feature importance weights
    - Features needing attention
    - Top contributing features

    **Effectiveness Formula:**
    `(correctness * 0.3) + (usability * 0.2) + (value * 0.4) + (reliability * 0.1)`

    Value is weighted highest (40%) because delivering trader value is the purpose.

    **Target Score:** 75+ indicates the product is genuinely helping traders dominate.
    """
    service = await get_instrumentation_service()
    purpose = await service.calculate_purpose_alignment(db)

    return {
        "success": True,
        "data": purpose,
        "meta": {
            "cache_ttl_seconds": service.TTL_PURPOSE,
            "target_score": 75,
        }
    }


@router.get("/gaps", response_model=GapsResponse)
async def get_gaps(
    db: AsyncSession = Depends(get_db),
):
    """
    Get identified gaps in feature effectiveness.

    Returns prioritized list of gaps with:
    - Priority (high, medium)
    - Affected feature
    - Weakest effectiveness component
    - Recommended action

    High priority gaps have effectiveness < 60.
    Medium priority gaps have effectiveness < 70.
    """
    service = await get_instrumentation_service()
    gaps = await service.detect_gaps(db)

    return {
        "success": True,
        "data": gaps,
        "meta": {
            "cache_ttl_seconds": service.TTL_HEALTH,
        }
    }


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    db: AsyncSession = Depends(get_db),
):
    """
    Get actionable insights from instrumentation data.

    Returns categorized insights with:
    - Category (usage, reliability, purpose)
    - Severity (error, warning, info)
    - Specific data supporting the insight
    - Recommended action

    Use these insights to guide development priorities and
    improve purpose alignment.
    """
    service = await get_instrumentation_service()
    insights = await service.generate_insights(db)

    return {
        "success": True,
        "data": insights,
        "meta": {
            "cache_ttl_seconds": service.TTL_HEALTH,
        }
    }


@router.get("/features")
async def list_features():
    """
    List all available features and event types.

    Use this to understand valid values for event recording.
    """
    return {
        "success": True,
        "data": {
            "features": [f.value for f in Feature],
            "event_types": [e.value for e in EventType],
        },
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
        }
    }


# =========================================================================
# Synthetic Flow Endpoints (Phase 2)
# =========================================================================

class FlowRunResponse(BaseModel):
    """Response schema for flow execution."""
    success: bool
    data: dict
    meta: dict


class FlowRunsResponse(BaseModel):
    """Response schema for flow runs listing."""
    success: bool
    data: List[dict]
    meta: dict


class FlowHealthResponse(BaseModel):
    """Response schema for flow health."""
    success: bool
    data: dict
    meta: dict


@router.post("/flows/run/{flow_type}", response_model=FlowRunResponse)
async def run_synthetic_flow(
    flow_type: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a synthetic validation flow.

    Synthetic flows validate feature effectiveness by simulating real trader
    scenarios and checking results against expectations.

    **Flow Types:**
    - `deal_hunter`: Validates deal detection accuracy
    - `breeding_planner`: Validates breeding simulation accuracy
    - `meta_scout`: Validates meta shift detection timeliness

    **How It Works:**
    1. Flow calls relevant AxiePro API endpoints
    2. Validates responses against expected behavior
    3. Calculates validation score (0-100)
    4. Stores results in database

    **Use Cases:**
    - On-demand feature validation
    - Debugging feature issues
    - Continuous monitoring
    """
    try:
        flow_type_enum = FlowType(flow_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid flow_type. Must be one of: {[f.value for f in FlowType]}"
        )

    # Get API base URL from environment or use default
    import os
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    # Create runner and execute flow
    runner = FlowRunner(api_base_url, db)
    try:
        result = await runner.run_flow(flow_type_enum)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Flow execution failed: {str(e)}"
        )

    return {
        "success": True,
        "data": result.to_dict(),
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "flow_type": flow_type,
        }
    }


@router.post("/flows/run-all", response_model=FlowRunsResponse)
async def run_all_synthetic_flows(
    parallel: bool = Query(True, description="Run flows in parallel"),
    db: AsyncSession = Depends(get_db),
):
    """
    Run all synthetic validation flows.

    Executes all available flows (Deal Hunter, Breeding Planner, Meta Scout)
    and returns results.

    **Parameters:**
    - `parallel`: If true (default), runs all flows concurrently for faster execution

    **Use Cases:**
    - Comprehensive health check
    - Pre-deployment validation
    - Regular monitoring
    """
    import os
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    runner = FlowRunner(api_base_url, db)
    try:
        results = await runner.run_all_flows(parallel=parallel)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Flow execution failed: {str(e)}"
        )

    return {
        "success": True,
        "data": [r.to_dict() for r in results],
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(results),
            "parallel": parallel,
        }
    }


@router.get("/flows/runs", response_model=FlowRunsResponse)
async def get_flow_runs(
    flow_type: Optional[str] = Query(None, description="Filter by flow type"),
    limit: int = Query(10, ge=1, le=100, description="Max number of runs to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent synthetic flow runs.

    Returns historical flow execution results for monitoring and analysis.

    **Parameters:**
    - `flow_type`: Optional filter by specific flow type
    - `limit`: Maximum number of runs to return (1-100)

    **Response includes:**
    - Execution status (passed, failed, error)
    - Validation score (0-100)
    - Number of checks passed/total
    - Detailed validation results
    - Timestamps
    """
    flow_type_enum = None
    if flow_type:
        try:
            flow_type_enum = FlowType(flow_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid flow_type. Must be one of: {[f.value for f in FlowType]}"
            )

    import os
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    runner = FlowRunner(api_base_url, db)
    runs = await runner.get_recent_runs(flow_type_enum, limit)

    return {
        "success": True,
        "data": [r.to_dict() for r in runs],
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "count": len(runs),
            "flow_type": flow_type,
        }
    }


@router.get("/flows/health", response_model=FlowHealthResponse)
async def get_flows_health(
    flow_type: Optional[str] = Query(None, description="Get health for specific flow"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get synthetic flow health status.

    Returns health metrics based on recent flow executions.

    **If flow_type specified:**
    Returns health for that specific flow including:
    - Status (healthy, degraded, no_data)
    - Recent run count
    - Pass/fail/error counts
    - Success rate percentage
    - Average validation score

    **If no flow_type (overall health):**
    Returns aggregated health across all flows including:
    - Overall status (healthy, warning, degraded)
    - Per-flow health metrics
    - Count of healthy vs degraded flows

    **Status Definitions:**
    - healthy: Success rate >= 80%
    - degraded: Success rate < 80%
    - warning: 1+ flows degraded
    - no_data: No recent runs
    """
    import os
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    runner = FlowRunner(api_base_url, db)

    if flow_type:
        try:
            flow_type_enum = FlowType(flow_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid flow_type. Must be one of: {[f.value for f in FlowType]}"
            )

        health = await runner.get_flow_health(flow_type_enum)
    else:
        health = await runner.get_overall_health()

    return {
        "success": True,
        "data": health,
        "meta": {
            "timestamp": datetime.utcnow().isoformat(),
            "flow_type": flow_type,
        }
    }
