"""
Instrumentation Service

Handles event collection, metric calculation, and purpose alignment analysis.
Provides the core business logic for the feedback system.

Event flow:
  Frontend → POST /instrumentation/events → InstrumentationService → PostgreSQL + Redis
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from src.models.instrumentation import (
    InstrumentationEvent,
    ValueMetric,
    PurposeAlignmentSnapshot,
    EventType,
    Feature,
)

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class InstrumentationService:
    """
    Service for collecting and analyzing instrumentation data.

    Provides:
    - Event collection and storage
    - Metric aggregation
    - Purpose alignment calculation
    - Health status reporting

    Usage:
        service = InstrumentationService(redis_url)
        await service.connect()

        # Record an event
        await service.record_event(db, event_data)

        # Get feature health
        health = await service.get_feature_health(db, Feature.EXPLORER)
    """

    # Cache TTLs in seconds
    TTL_HEALTH = 300        # 5 minutes
    TTL_PURPOSE = 300       # 5 minutes
    TTL_METRICS = 60        # 1 minute

    # Feature importance weights (toward "helping traders dominate")
    FEATURE_IMPORTANCE = {
        Feature.DEALS: 10,       # Directly finds undervalued assets
        Feature.META: 9,         # Early trend detection = edge
        Feature.EXPLORER: 8,     # Efficient finding
        Feature.BREEDING: 7,     # ROI optimization
        Feature.ANALYTICS: 7,    # Informed decisions
        Feature.PORTFOLIO: 6,    # Performance tracking
        Feature.VALUATION: 8,    # Fair price estimation
    }

    def __init__(
        self,
        redis_url: Optional[str] = None,
        key_prefix: str = "feedback:",
    ):
        """
        Initialize instrumentation service.

        Args:
            redis_url: Redis connection URL
            key_prefix: Prefix for all cache keys
        """
        self.redis_url = redis_url or "redis://localhost:6379/0"
        self.key_prefix = key_prefix
        self._client: Optional["redis.Redis"] = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis cache."""
        if not REDIS_AVAILABLE:
            logger.warning("Redis library not available, caching disabled")
            return False

        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._client.ping()
            self._connected = True
            logger.info(f"InstrumentationService connected to Redis")
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

    async def _cache_set(self, key: str, value: dict, ttl: int) -> bool:
        """Set a value in cache with TTL."""
        if not self.is_connected:
            return False

        try:
            serialized = json.dumps(value, cls=DecimalEncoder)
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {e}")
            return False

    async def _cache_get(self, key: str) -> Optional[dict]:
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

    # =========================================================================
    # Event Collection
    # =========================================================================

    async def record_event(
        self,
        db: AsyncSession,
        event_type: EventType,
        feature: Feature,
        action: str,
        session_id: Optional[str] = None,
        data: Optional[dict] = None,
    ) -> InstrumentationEvent:
        """
        Record an instrumentation event.

        Args:
            db: Database session
            event_type: Type of event (usage, performance, error, value)
            feature: Feature being instrumented
            action: Specific action (e.g., 'search', 'filter', 'simulate')
            session_id: Anonymous session identifier
            data: Additional event data

        Returns:
            Created InstrumentationEvent
        """
        event = InstrumentationEvent(
            event_type=event_type,
            feature=feature,
            action=action,
            session_id=session_id,
            data=data,
            created_at=datetime.utcnow(),
        )

        db.add(event)
        await db.commit()
        await db.refresh(event)

        logger.debug(f"Recorded event: {feature.value}/{action} ({event_type.value})")
        return event

    async def record_batch_events(
        self,
        db: AsyncSession,
        events: List[dict],
    ) -> int:
        """
        Record multiple events in a single transaction.

        Args:
            db: Database session
            events: List of event dicts with keys:
                    event_type, feature, action, session_id, data

        Returns:
            Number of events recorded
        """
        recorded = 0

        for event_data in events:
            try:
                event = InstrumentationEvent(
                    event_type=EventType(event_data["event_type"]),
                    feature=Feature(event_data["feature"]),
                    action=event_data["action"],
                    session_id=event_data.get("session_id"),
                    data=event_data.get("data"),
                    created_at=datetime.utcnow(),
                )
                db.add(event)
                recorded += 1
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid event data: {e}")
                continue

        if recorded > 0:
            await db.commit()

        logger.debug(f"Recorded {recorded} events in batch")
        return recorded

    # =========================================================================
    # Value Metrics
    # =========================================================================

    async def record_value_metric(
        self,
        db: AsyncSession,
        feature: Feature,
        metric_type: str,
        value: float,
        context: Optional[dict] = None,
    ) -> ValueMetric:
        """
        Record a value metric for a feature.

        Args:
            db: Database session
            feature: Feature the metric belongs to
            metric_type: Type of metric (e.g., 'deal_quality', 'prediction_accuracy')
            value: Numeric metric value
            context: Additional context

        Returns:
            Created ValueMetric
        """
        metric = ValueMetric(
            feature=feature,
            metric_type=metric_type,
            value=value,
            context=context,
            created_at=datetime.utcnow(),
        )

        db.add(metric)
        await db.commit()
        await db.refresh(metric)

        logger.debug(f"Recorded value metric: {feature.value}/{metric_type} = {value}")
        return metric

    # =========================================================================
    # Feature Health Analysis
    # =========================================================================

    async def get_feature_health(
        self,
        db: AsyncSession,
        feature: Feature,
        hours: int = 24,
    ) -> dict:
        """
        Calculate health metrics for a feature.

        Args:
            db: Database session
            feature: Feature to analyze
            hours: Time window in hours

        Returns:
            Health metrics dict with usage, errors, performance
        """
        cache_key = self._key("health", feature.value)
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        since = datetime.utcnow() - timedelta(hours=hours)

        # Get usage count
        usage_query = select(func.count(InstrumentationEvent.id)).where(
            and_(
                InstrumentationEvent.feature == feature,
                InstrumentationEvent.event_type == EventType.USAGE,
                InstrumentationEvent.created_at >= since,
            )
        )
        usage_result = await db.execute(usage_query)
        usage_count = usage_result.scalar() or 0

        # Get error count
        error_query = select(func.count(InstrumentationEvent.id)).where(
            and_(
                InstrumentationEvent.feature == feature,
                InstrumentationEvent.event_type == EventType.ERROR,
                InstrumentationEvent.created_at >= since,
            )
        )
        error_result = await db.execute(error_query)
        error_count = error_result.scalar() or 0

        # Calculate error rate
        total = usage_count + error_count
        error_rate = (error_count / total * 100) if total > 0 else 0

        # Get unique sessions
        session_query = select(func.count(func.distinct(InstrumentationEvent.session_id))).where(
            and_(
                InstrumentationEvent.feature == feature,
                InstrumentationEvent.created_at >= since,
            )
        )
        session_result = await db.execute(session_query)
        unique_sessions = session_result.scalar() or 0

        # Determine status
        if error_rate > 10:
            status = "degraded"
        elif error_rate > 5:
            status = "warning"
        else:
            status = "healthy"

        health = {
            "feature": feature.value,
            "status": status,
            "usage_count": usage_count,
            "error_count": error_count,
            "error_rate": round(error_rate, 2),
            "unique_sessions": unique_sessions,
            "time_window_hours": hours,
            "calculated_at": datetime.utcnow().isoformat(),
        }

        await self._cache_set(cache_key, health, self.TTL_HEALTH)
        return health

    async def get_overall_health(self, db: AsyncSession) -> dict:
        """Get health status for all features."""
        cache_key = self._key("health", "overall")
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        features_health = {}
        total_errors = 0
        total_usage = 0

        for feature in Feature:
            health = await self.get_feature_health(db, feature)
            features_health[feature.value] = {
                "status": health["status"],
                "error_rate": health["error_rate"],
                "usage_count": health["usage_count"],
            }
            total_errors += health["error_count"]
            total_usage += health["usage_count"]

        # Overall health score (0-100)
        if total_usage + total_errors > 0:
            overall_error_rate = total_errors / (total_usage + total_errors) * 100
            overall_health = max(0, min(100, 100 - overall_error_rate * 10))
        else:
            overall_health = 100  # No data = assume healthy

        result = {
            "overall_health": round(overall_health),
            "features": features_health,
            "total_usage": total_usage,
            "total_errors": total_errors,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._cache_set(cache_key, result, self.TTL_HEALTH)
        return result

    # =========================================================================
    # Purpose Alignment Analysis
    # =========================================================================

    async def calculate_feature_effectiveness(
        self,
        db: AsyncSession,
        feature: Feature,
        hours: int = 168,  # 1 week
    ) -> dict:
        """
        Calculate effectiveness score for a feature.

        Effectiveness = (correctness * 0.3) + (usability * 0.2) + (value * 0.4) + (reliability * 0.1)

        Args:
            db: Database session
            feature: Feature to analyze
            hours: Time window

        Returns:
            Effectiveness metrics dict
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        # Get health metrics (reliability)
        health = await self.get_feature_health(db, feature, hours=24)
        reliability = max(0, 100 - health["error_rate"] * 10)

        # Get value metrics
        value_query = select(func.avg(ValueMetric.value)).where(
            and_(
                ValueMetric.feature == feature,
                ValueMetric.created_at >= since,
            )
        )
        value_result = await db.execute(value_query)
        avg_value = value_result.scalar() or 50  # Default to 50 if no data

        # Get usage success rate (usability proxy)
        total_events = health["usage_count"] + health["error_count"]
        usability = (health["usage_count"] / total_events * 100) if total_events > 0 else 50

        # Correctness - requires synthetic flow validation (default to 70 for now)
        # This will be populated by synthetic flows in Phase 2
        correctness = 70

        # Calculate weighted effectiveness
        effectiveness = (
            correctness * 0.3 +
            usability * 0.2 +
            float(avg_value) * 0.4 +
            reliability * 0.1
        )

        return {
            "feature": feature.value,
            "effectiveness": round(effectiveness, 1),
            "components": {
                "correctness": round(correctness, 1),
                "usability": round(usability, 1),
                "value": round(float(avg_value), 1),
                "reliability": round(reliability, 1),
            },
            "time_window_hours": hours,
        }

    async def calculate_purpose_alignment(self, db: AsyncSession) -> dict:
        """
        Calculate overall purpose alignment score.

        Purpose: "Help serious traders dominate the Axie market"

        Returns weighted sum of feature effectiveness scores.
        """
        cache_key = self._key("purpose", "current")
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        features = {}
        weighted_sum = 0
        total_weight = 0

        for feature in Feature:
            effectiveness_data = await self.calculate_feature_effectiveness(db, feature)
            importance = self.FEATURE_IMPORTANCE.get(feature, 5)
            contribution = effectiveness_data["effectiveness"] * importance / 100

            features[feature.value] = {
                "effectiveness": effectiveness_data["effectiveness"],
                "importance": importance,
                "contribution": round(contribution, 2),
                "components": effectiveness_data["components"],
            }

            weighted_sum += effectiveness_data["effectiveness"] * importance
            total_weight += importance

        overall_score = weighted_sum / total_weight if total_weight > 0 else 0

        # Identify needs attention (effectiveness < 70)
        needs_attention = [
            f for f, data in features.items()
            if data["effectiveness"] < 70
        ]

        # Identify top contributors
        top_contributors = sorted(
            features.items(),
            key=lambda x: x[1]["contribution"],
            reverse=True,
        )[:3]

        result = {
            "overall_score": round(overall_score, 1),
            "purpose_statement": "Help serious traders dominate the Axie market",
            "features": features,
            "top_contributors": [name for name, _ in top_contributors],
            "needs_attention": needs_attention,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store snapshot
        snapshot = PurposeAlignmentSnapshot(
            overall_score=round(overall_score),
            feature_scores={f: d["effectiveness"] for f, d in features.items()},
            gaps={"needs_attention": needs_attention} if needs_attention else None,
            insights=None,
            created_at=datetime.utcnow(),
        )
        db.add(snapshot)
        await db.commit()

        await self._cache_set(cache_key, result, self.TTL_PURPOSE)
        return result

    # =========================================================================
    # Gap Detection
    # =========================================================================

    async def detect_gaps(self, db: AsyncSession) -> dict:
        """
        Identify gaps in feature effectiveness.

        Returns prioritized list of gaps with recommendations.
        """
        cache_key = self._key("gaps", "current")
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        purpose_data = await self.calculate_purpose_alignment(db)
        gaps = []

        for feature_name, data in purpose_data["features"].items():
            effectiveness = data["effectiveness"]

            if effectiveness < 60:
                priority = "high"
                description = f"{feature_name} effectiveness is critically low"
            elif effectiveness < 70:
                priority = "medium"
                description = f"{feature_name} effectiveness below target"
            else:
                continue

            # Identify which component is weakest
            components = data["components"]
            weakest = min(components.items(), key=lambda x: x[1])

            gaps.append({
                "type": "low_effectiveness",
                "priority": priority,
                "feature": feature_name,
                "title": f"{feature_name.title()} needs improvement",
                "description": description,
                "effectiveness": effectiveness,
                "weakest_component": weakest[0],
                "weakest_score": weakest[1],
                "recommendation": self._get_recommendation(feature_name, weakest[0]),
            })

        # Sort by priority (high first) then by effectiveness (lowest first)
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda x: (priority_order[x["priority"]], x["effectiveness"]))

        result = {
            "gaps": gaps,
            "total_gaps": len(gaps),
            "high_priority": sum(1 for g in gaps if g["priority"] == "high"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._cache_set(cache_key, result, self.TTL_HEALTH)
        return result

    def _get_recommendation(self, feature: str, weak_component: str) -> str:
        """Generate recommendation based on weak component."""
        recommendations = {
            "correctness": f"Review {feature} data accuracy and validation logic",
            "usability": f"Investigate UX issues in {feature} - check error patterns",
            "value": f"Analyze if {feature} is delivering expected trader value",
            "reliability": f"Address stability issues in {feature} - reduce error rate",
        }
        return recommendations.get(weak_component, f"Investigate {feature} performance")

    # =========================================================================
    # Insights Generation
    # =========================================================================

    async def generate_insights(self, db: AsyncSession) -> dict:
        """
        Generate actionable insights from instrumentation data.

        Returns categorized insights with severity and actions.
        """
        cache_key = self._key("insights", "current")
        cached = await self._cache_get(cache_key)
        if cached:
            return cached

        insights = []

        # Get overall health
        health = await self.get_overall_health(db)

        # Check for low usage features
        for feature_name, data in health["features"].items():
            if data["usage_count"] < 10:
                insights.append({
                    "category": "usage",
                    "severity": "warning",
                    "title": f"{feature_name.title()} has low adoption",
                    "data": {"usage_count": data["usage_count"]},
                    "action": f"Investigate why {feature_name} isn't being used",
                })

            if data["error_rate"] > 5:
                insights.append({
                    "category": "reliability",
                    "severity": "error" if data["error_rate"] > 10 else "warning",
                    "title": f"{feature_name.title()} has elevated error rate",
                    "data": {"error_rate": data["error_rate"]},
                    "action": f"Review error logs for {feature_name}",
                })

        # Check purpose alignment
        purpose = await self.calculate_purpose_alignment(db)

        if purpose["overall_score"] < 70:
            insights.append({
                "category": "purpose",
                "severity": "warning",
                "title": "Purpose alignment below target",
                "data": {"score": purpose["overall_score"], "target": 75},
                "action": "Focus on improving features in 'needs_attention' list",
            })

        if purpose["overall_score"] >= 75:
            insights.append({
                "category": "purpose",
                "severity": "info",
                "title": "Purpose alignment is on track",
                "data": {"score": purpose["overall_score"]},
                "action": "Continue monitoring and maintain quality",
            })

        result = {
            "insights": insights,
            "total_insights": len(insights),
            "by_severity": {
                "error": sum(1 for i in insights if i["severity"] == "error"),
                "warning": sum(1 for i in insights if i["severity"] == "warning"),
                "info": sum(1 for i in insights if i["severity"] == "info"),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self._cache_set(cache_key, result, self.TTL_HEALTH)
        return result


# Global service instance
_instrumentation_service: Optional[InstrumentationService] = None


async def get_instrumentation_service(
    redis_url: Optional[str] = None,
) -> InstrumentationService:
    """
    Get or create the global instrumentation service instance.

    Args:
        redis_url: Optional Redis URL (uses env if not provided)

    Returns:
        Connected InstrumentationService instance
    """
    global _instrumentation_service

    if _instrumentation_service is None:
        import os
        if redis_url is None:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _instrumentation_service = InstrumentationService(redis_url)
        await _instrumentation_service.connect()

    return _instrumentation_service
