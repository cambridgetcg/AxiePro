"""
Constants for Lambda Functions

Centralized configuration constants to ensure consistency
across all datafeed Lambdas.
"""

import os

# =============================================================================
# Sky Mavis API Configuration
# =============================================================================

# Official Sky Mavis API Gateway endpoint for Axie Marketplace
# This endpoint requires API key authentication via X-API-Key header
SKYMAVIS_API_ENDPOINT = "https://api-gateway.skymavis.com/graphql/axie-marketplace"

# Get the effective API endpoint (allows proxy override)
def get_skymavis_endpoint() -> str:
    """
    Get the SkyMavis API endpoint.

    Priority:
    1. AXIE_PROXY_URL environment variable (for Cloudflare Worker proxy)
    2. Default official API gateway endpoint

    Returns:
        API endpoint URL
    """
    return os.environ.get("AXIE_PROXY_URL", SKYMAVIS_API_ENDPOINT)


# =============================================================================
# Deal Detection Thresholds
# =============================================================================
# These values can be overridden via AWS Parameter Store.
# Use get_threshold() functions for runtime values with Parameter Store lookup.

# Default values (used as fallbacks if Parameter Store is unavailable)
_DEFAULT_DEAL_THRESHOLD_PERCENT = 20
_DEFAULT_SNIPE_THRESHOLD_PERCENT = 40
_DEFAULT_MIN_DISCOUNT_ETH = 0.001
_DEFAULT_NOTIFICATION_THRESHOLD_SCORE = 70

# Backwards-compatible constants (use for static references only)
DEAL_THRESHOLD_PERCENT = _DEFAULT_DEAL_THRESHOLD_PERCENT
SNIPE_THRESHOLD_PERCENT = _DEFAULT_SNIPE_THRESHOLD_PERCENT
MIN_DISCOUNT_ETH = _DEFAULT_MIN_DISCOUNT_ETH
NOTIFICATION_THRESHOLD_SCORE = _DEFAULT_NOTIFICATION_THRESHOLD_SCORE


# =============================================================================
# Meta Analysis Thresholds
# =============================================================================
# These values can be overridden via AWS Parameter Store.

# Default values (used as fallbacks if Parameter Store is unavailable)
_DEFAULT_PRICE_VELOCITY_THRESHOLD = 15
_DEFAULT_VOLUME_SPIKE_THRESHOLD = 200
_DEFAULT_EMERGING_META_THRESHOLD = 10

# Backwards-compatible constants (use for static references only)
PRICE_VELOCITY_THRESHOLD = _DEFAULT_PRICE_VELOCITY_THRESHOLD
VOLUME_SPIKE_THRESHOLD = _DEFAULT_VOLUME_SPIKE_THRESHOLD
EMERGING_META_THRESHOLD = _DEFAULT_EMERGING_META_THRESHOLD


# =============================================================================
# Threshold Getter Functions (with Parameter Store lookup)
# =============================================================================

def get_deal_threshold_percent() -> int:
    """Get deal threshold percentage from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/deal_percent", _DEFAULT_DEAL_THRESHOLD_PERCENT)
    except ImportError:
        return _DEFAULT_DEAL_THRESHOLD_PERCENT


def get_snipe_threshold_percent() -> int:
    """Get snipe threshold percentage from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/snipe_percent", _DEFAULT_SNIPE_THRESHOLD_PERCENT)
    except ImportError:
        return _DEFAULT_SNIPE_THRESHOLD_PERCENT


def get_min_discount_eth() -> float:
    """Get minimum discount ETH from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_float_parameter
        return get_float_parameter("thresholds/min_discount_eth", _DEFAULT_MIN_DISCOUNT_ETH)
    except ImportError:
        return _DEFAULT_MIN_DISCOUNT_ETH


def get_notification_threshold_score() -> int:
    """Get notification threshold score from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/notification_score", _DEFAULT_NOTIFICATION_THRESHOLD_SCORE)
    except ImportError:
        return _DEFAULT_NOTIFICATION_THRESHOLD_SCORE


def get_price_velocity_threshold() -> int:
    """Get price velocity threshold from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/price_velocity", _DEFAULT_PRICE_VELOCITY_THRESHOLD)
    except ImportError:
        return _DEFAULT_PRICE_VELOCITY_THRESHOLD


def get_volume_spike_threshold() -> int:
    """Get volume spike threshold from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/volume_spike", _DEFAULT_VOLUME_SPIKE_THRESHOLD)
    except ImportError:
        return _DEFAULT_VOLUME_SPIKE_THRESHOLD


def get_emerging_meta_threshold() -> int:
    """Get emerging meta threshold from Parameter Store or default."""
    try:
        from src.lambdas.common.parameters import get_int_parameter
        return get_int_parameter("thresholds/emerging_meta", _DEFAULT_EMERGING_META_THRESHOLD)
    except ImportError:
        return _DEFAULT_EMERGING_META_THRESHOLD


# =============================================================================
# Axie Classes and Parts
# =============================================================================

# All Axie classes
AXIE_CLASSES = [
    "beast",
    "aquatic",
    "plant",
    "bird",
    "bug",
    "reptile",
    "mech",
    "dawn",
    "dusk",
]

# Primary classes with sample parts for price tracking
# Maps class to list of representative part IDs
TRACKED_PARTS_BY_CLASS = {
    "beast": [
        "eyes-chubby",
        "ears-zen",
        "horn-imp",
        "mouth-nut-cracker",
        "back-ronin",
        "tail-cottontail",
    ],
    "aquatic": [
        "eyes-clear",
        "ears-nimo",
        "horn-anemone",
        "mouth-lam",
        "back-goldfish",
        "tail-nimo",
    ],
    "plant": [
        "eyes-papi",
        "ears-leafy",
        "horn-cactus",
        "mouth-zigzag",
        "back-pumpkin",
        "tail-carrot",
    ],
    "bird": [
        "eyes-mavis",
        "ears-pink-cheek",
        "horn-eggshell",
        "mouth-peace-maker",
        "back-pigeon-post",
        "tail-post-fight",
    ],
    "bug": [
        "eyes-bookworm",
        "ears-ear-breathing",
        "horn-antenna",
        "mouth-pincer",
        "back-snail-shell",
        "tail-fish-snack",
    ],
    "reptile": [
        "eyes-topaz",
        "ears-small-frill",
        "horn-scaly-spear",
        "mouth-razor-bite",
        "back-green-thorns",
        "tail-iguana",
    ],
}

# Number of parts to sample per class for price tracking
PARTS_SAMPLE_SIZE = 2


# =============================================================================
# HTTP Client Configuration
# =============================================================================

# Default timeout for HTTP requests in seconds
HTTP_TIMEOUT_SECONDS = 30.0

# Default headers for SkyMavis API requests
def get_skymavis_headers(api_key: str = None, internal_secret: str = None) -> dict:
    """
    Get headers for SkyMavis API requests.

    Args:
        api_key: SkyMavis API key (optional but recommended)
        internal_secret: Internal secret for proxy auth (optional)

    Returns:
        Headers dict
    """
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://app.axieinfinity.com",
        "User-Agent": "Mozilla/5.0 (compatible; AxiePro/1.0)",
        "Referer": "https://app.axieinfinity.com/",
    }

    if api_key:
        headers["X-API-Key"] = api_key

    # Add auth header for proxy if configured
    if internal_secret and os.environ.get("AXIE_PROXY_URL"):
        headers["Authorization"] = f"Bearer {internal_secret}"

    return headers
