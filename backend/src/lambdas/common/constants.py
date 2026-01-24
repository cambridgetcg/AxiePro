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

# Percentage below average to qualify as a deal
DEAL_THRESHOLD_PERCENT = 20

# Percentage below average to qualify as a snipe opportunity
SNIPE_THRESHOLD_PERCENT = 40

# Minimum discount in ETH to qualify as a deal
MIN_DISCOUNT_ETH = 0.001

# Minimum deal score to send notification
NOTIFICATION_THRESHOLD_SCORE = 70


# =============================================================================
# Meta Analysis Thresholds
# =============================================================================

# Percentage price change in 24h to signal price velocity
PRICE_VELOCITY_THRESHOLD = 15

# Percentage volume increase to signal volume spike
VOLUME_SPIKE_THRESHOLD = 200

# Percentage price increase over 7 days to signal emerging meta
EMERGING_META_THRESHOLD = 10


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
