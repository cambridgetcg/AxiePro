"""
Lambda Common Utilities

Shared utilities for all Lambda functions in the AxiePro datafeed system.
These are sync-focused utilities designed for Lambda execution context,
separate from the async FastAPI utilities in src/services/.

Usage:
    from src.lambdas.common import (
        get_secrets,
        get_db_credentials,
        get_db_connection,
        get_redis_client,
        logger,
        tracer,
        metrics,
        get_skymavis_endpoint,
        DEAL_THRESHOLD_PERCENT,
    )
"""

from src.lambdas.common.aws import (
    get_secrets,
    get_db_credentials,
    get_secrets_cached,
)
from src.lambdas.common.database import (
    get_db_connection,
    db_connection,
)
from src.lambdas.common.redis_client import (
    get_redis_client,
    redis_connection,
    cache_deal,
    cache_meta_insights,
)
from src.lambdas.common.observability import (
    logger,
    tracer,
    metrics,
)
from src.lambdas.common.constants import (
    SKYMAVIS_API_ENDPOINT,
    get_skymavis_endpoint,
    get_skymavis_headers,
    DEAL_THRESHOLD_PERCENT,
    SNIPE_THRESHOLD_PERCENT,
    MIN_DISCOUNT_ETH,
    NOTIFICATION_THRESHOLD_SCORE,
    PRICE_VELOCITY_THRESHOLD,
    VOLUME_SPIKE_THRESHOLD,
    EMERGING_META_THRESHOLD,
    AXIE_CLASSES,
    TRACKED_PARTS_BY_CLASS,
    PARTS_SAMPLE_SIZE,
    HTTP_TIMEOUT_SECONDS,
)

__all__ = [
    # AWS Secrets
    "get_secrets",
    "get_db_credentials",
    "get_secrets_cached",
    # Database
    "get_db_connection",
    "db_connection",
    # Redis
    "get_redis_client",
    "redis_connection",
    "cache_deal",
    "cache_meta_insights",
    # Observability
    "logger",
    "tracer",
    "metrics",
    # Constants - SkyMavis
    "SKYMAVIS_API_ENDPOINT",
    "get_skymavis_endpoint",
    "get_skymavis_headers",
    "HTTP_TIMEOUT_SECONDS",
    # Constants - Deal Detection
    "DEAL_THRESHOLD_PERCENT",
    "SNIPE_THRESHOLD_PERCENT",
    "MIN_DISCOUNT_ETH",
    "NOTIFICATION_THRESHOLD_SCORE",
    # Constants - Meta Analysis
    "PRICE_VELOCITY_THRESHOLD",
    "VOLUME_SPIKE_THRESHOLD",
    "EMERGING_META_THRESHOLD",
    # Constants - Axies
    "AXIE_CLASSES",
    "TRACKED_PARTS_BY_CLASS",
    "PARTS_SAMPLE_SIZE",
]
