"""
Redis Client Management for Lambda Functions

Provides sync Redis client management for caching in Lambda context.
Handles graceful degradation when Redis is unavailable.

The Redis URL is expected to be stored in the API secrets under the
REDIS_URL key.
"""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from src.lambdas.common.aws import get_secrets_cached

# Try to import redis, gracefully handle if not available
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False


def get_redis_url() -> Optional[str]:
    """
    Get Redis URL from secrets or environment.

    Priority:
    1. REDIS_URL from API secrets (AWS Secrets Manager)
    2. REDIS_URL environment variable (for local development)

    Returns:
        Redis URL string or None if not configured.
    """
    # Try secrets first
    try:
        secrets = get_secrets_cached()
        redis_url = secrets.get("REDIS_URL")
        if redis_url:
            return redis_url
    except Exception:
        pass

    # Fall back to environment variable
    return os.environ.get("REDIS_URL")


def get_redis_client(
    redis_url: Optional[str] = None,
    decode_responses: bool = True,
) -> Optional["redis.Redis"]:
    """
    Get a Redis client connection.

    Returns None if Redis is not available or not configured,
    allowing callers to gracefully skip caching.

    Args:
        redis_url: Optional explicit Redis URL. If not provided,
                   fetched from secrets/environment.
        decode_responses: If True, decode Redis responses to strings.

    Returns:
        Redis client or None if unavailable.

    Example:
        client = get_redis_client()
        if client:
            client.set("key", "value")
            client.close()
    """
    if not REDIS_AVAILABLE:
        return None

    url = redis_url or get_redis_url()
    if not url:
        return None

    try:
        return redis.from_url(url, decode_responses=decode_responses)
    except Exception:
        return None


@contextmanager
def redis_connection(
    redis_url: Optional[str] = None,
    decode_responses: bool = True,
) -> Generator[Optional["redis.Redis"], None, None]:
    """
    Context manager for Redis connections with automatic cleanup.

    Yields None if Redis is unavailable, allowing graceful degradation.

    Args:
        redis_url: Optional explicit Redis URL.
        decode_responses: If True, decode Redis responses to strings.

    Yields:
        Redis client or None if unavailable.

    Example:
        with redis_connection() as client:
            if client:
                client.set("key", "value")
            else:
                # Caching disabled, continue without cache
                pass
        # Connection automatically closed
    """
    client = get_redis_client(redis_url, decode_responses)
    try:
        yield client
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass


def cache_deal(
    client: Optional["redis.Redis"],
    deal: dict,
    axie_class: str,
    deal_score: int,
    is_snipe: bool = False,
) -> bool:
    """
    Cache a detected deal in Redis.

    Stores deals in sorted sets for efficient retrieval by score.
    Handles None client gracefully for when Redis is unavailable.

    Args:
        client: Redis client (or None)
        deal: Deal data dict (will be JSON serialized)
        axie_class: Axie class for class-specific list
        deal_score: Deal score (0-100) for ranking
        is_snipe: If True, also add to snipes list

    Returns:
        True if cached successfully, False otherwise.
    """
    if not client:
        return False

    import json

    try:
        deal_json = json.dumps(deal)

        # Add to class-specific deals list
        key = f"deals:{axie_class.lower()}"
        client.zadd(key, {deal_json: deal_score})
        client.zremrangebyrank(key, 0, -101)  # Keep top 100
        client.expire(key, 86400)  # 24 hour TTL

        # Add to global snipes if applicable
        if is_snipe:
            snipes_key = "snipes:all"
            client.zadd(snipes_key, {deal_json: deal_score})
            client.zremrangebyrank(snipes_key, 0, -51)  # Keep top 50
            client.expire(snipes_key, 86400)

        return True
    except Exception:
        return False


def cache_meta_insights(
    client: Optional["redis.Redis"],
    shifts: list,
    summary: dict,
    ttl: int = 3600,
) -> bool:
    """
    Cache meta insights in Redis.

    Args:
        client: Redis client (or None)
        shifts: List of meta shift dicts by type
        summary: Summary dict with counts
        ttl: Time-to-live in seconds (default 1 hour)

    Returns:
        True if cached successfully, False otherwise.
    """
    if not client:
        return False

    import json

    try:
        # Store by shift type
        for shift_type in ["rising", "falling", "emerging", "fading"]:
            type_shifts = [s for s in shifts if s.get("shift_type") == shift_type]
            if type_shifts:
                client.set(
                    f"meta:{shift_type}",
                    json.dumps(type_shifts[:20]),
                    ex=ttl,
                )

        # Store summary
        client.set("meta:summary", json.dumps(summary), ex=ttl)

        return True
    except Exception:
        return False
