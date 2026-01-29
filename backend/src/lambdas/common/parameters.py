"""
Parameter Store Utilities

Provides utilities for reading configuration from AWS Systems Manager Parameter Store.
Parameters are cached for the lifetime of the Lambda execution context.
"""

import os
from typing import Any, Dict, Optional
from decimal import Decimal
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.lambdas.common.observability import logger


# Global SSM client (connection reuse)
_ssm_client = None

# Parameter Store prefix
PARAMETER_PREFIX = os.environ.get("PARAMETER_PREFIX", "/axiepro")


def get_ssm_client():
    """Get or create SSM client with retry configuration."""
    global _ssm_client
    if _ssm_client is None:
        config = Config(
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
            connect_timeout=5,
            read_timeout=10,
        )
        _ssm_client = boto3.client("ssm", config=config)
        logger.info("Created SSM client")
    return _ssm_client


@lru_cache(maxsize=50)
def get_parameter(name: str, default: Any = None, decrypt: bool = False) -> Optional[str]:
    """
    Get a parameter from Parameter Store with caching.

    Args:
        name: Parameter name (without prefix, e.g., "deal_threshold_percent")
        default: Default value if parameter not found
        decrypt: Whether to decrypt SecureString parameters

    Returns:
        Parameter value as string, or default if not found
    """
    full_name = f"{PARAMETER_PREFIX}/{name}"

    try:
        client = get_ssm_client()
        response = client.get_parameter(
            Name=full_name,
            WithDecryption=decrypt,
        )
        value = response["Parameter"]["Value"]
        logger.debug(f"Retrieved parameter: {full_name}")
        return value

    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            logger.debug(f"Parameter not found: {full_name}, using default: {default}")
            return default
        logger.error(f"Error getting parameter {full_name}: {e}")
        return default

    except Exception as e:
        logger.error(f"Unexpected error getting parameter {full_name}: {e}")
        return default


def get_int_parameter(name: str, default: int = 0) -> int:
    """Get a parameter as integer."""
    value = get_parameter(name, str(default))
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_float_parameter(name: str, default: float = 0.0) -> float:
    """Get a parameter as float."""
    value = get_parameter(name, str(default))
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def get_decimal_parameter(name: str, default: Decimal = Decimal("0")) -> Decimal:
    """Get a parameter as Decimal."""
    value = get_parameter(name, str(default))
    try:
        return Decimal(value)
    except Exception:
        return default


def get_bool_parameter(name: str, default: bool = False) -> bool:
    """Get a parameter as boolean."""
    value = get_parameter(name, str(default).lower())
    return value.lower() in ("true", "1", "yes", "on")


@lru_cache(maxsize=1)
def get_all_thresholds() -> Dict[str, Any]:
    """
    Get all threshold parameters at once with caching.

    Returns a dict with all threshold values, using defaults if not found.
    """
    thresholds = {
        # Deal Detection Thresholds
        "deal_threshold_percent": get_int_parameter("thresholds/deal_percent", 20),
        "snipe_threshold_percent": get_int_parameter("thresholds/snipe_percent", 40),
        "min_discount_eth": get_float_parameter("thresholds/min_discount_eth", 0.001),
        "notification_threshold_score": get_int_parameter("thresholds/notification_score", 70),

        # Meta Analysis Thresholds
        "price_velocity_threshold": get_int_parameter("thresholds/price_velocity", 15),
        "volume_spike_threshold": get_int_parameter("thresholds/volume_spike", 200),
        "emerging_meta_threshold": get_int_parameter("thresholds/emerging_meta", 10),

        # Health Check Thresholds
        "listings_freshness_minutes": get_int_parameter("thresholds/listings_freshness", 15),
        "sales_freshness_minutes": get_int_parameter("thresholds/sales_freshness", 60),
        "price_snapshots_freshness_minutes": get_int_parameter("thresholds/snapshots_freshness", 30),
    }

    logger.info(
        "Loaded threshold parameters",
        extra={"thresholds": thresholds},
    )

    return thresholds


def clear_parameter_cache() -> None:
    """Clear the parameter cache (for testing or forced refresh)."""
    get_parameter.cache_clear()
    get_all_thresholds.cache_clear()
    logger.info("Parameter cache cleared")


def reset_ssm_client() -> None:
    """Reset the global SSM client (for testing)."""
    global _ssm_client
    _ssm_client = None
