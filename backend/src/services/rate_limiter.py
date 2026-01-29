"""
Token bucket rate limiter for external API calls.

Provides smooth rate limiting with burst capacity for SkyMavis and other external APIs.
"""

import asyncio
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.

    Allows burst up to max_tokens, then refills at rate_per_second.
    Thread-safe for async usage.

    Example:
        limiter = TokenBucketRateLimiter(requests_per_minute=10, burst_size=5)
        async with limiter:
            # Make API call
            response = await client.get(url)
    """

    def __init__(
        self,
        requests_per_minute: int = 10,
        burst_size: Optional[int] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Sustained request rate
            burst_size: Maximum burst capacity (defaults to requests_per_minute / 6)
        """
        self.requests_per_minute = requests_per_minute
        self.rate_per_second = requests_per_minute / 60.0
        self.max_tokens = burst_size if burst_size is not None else max(1, requests_per_minute // 6)
        self.tokens = float(self.max_tokens)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, timeout: float = 120.0) -> bool:
        """
        Acquire a token, waiting if necessary.

        Args:
            timeout: Maximum time to wait for a token (seconds)

        Returns:
            True if token acquired, False if timeout

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        start = time.monotonic()

        while True:
            async with self._lock:
                self._refill()

                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    logger.debug(
                        f"Rate limiter: token acquired, {self.tokens:.1f} remaining"
                    )
                    return True

            # Calculate wait time
            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                logger.warning(f"Rate limiter: timeout after {elapsed:.1f}s")
                return False

            # Wait for approximately one token
            wait_time = min(1.0 / self.rate_per_second, timeout - elapsed)
            logger.debug(f"Rate limiter: waiting {wait_time:.2f}s for token")
            await asyncio.sleep(wait_time)

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.rate_per_second
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

    async def __aenter__(self) -> "TokenBucketRateLimiter":
        """Async context manager - acquire token on entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        pass

    @property
    def available_tokens(self) -> float:
        """Get current available tokens (approximate)."""
        return self.tokens

    def reset(self) -> None:
        """Reset rate limiter to full capacity."""
        self.tokens = float(self.max_tokens)
        self.last_refill = time.monotonic()


# Global rate limiter instance for SkyMavis API
_skymavis_rate_limiter: Optional[TokenBucketRateLimiter] = None


def get_skymavis_rate_limiter() -> TokenBucketRateLimiter:
    """
    Get or create global SkyMavis rate limiter.

    Uses conservative settings to avoid 429 errors:
    - 10 requests per minute sustained
    - Burst of 3 requests
    """
    global _skymavis_rate_limiter
    if _skymavis_rate_limiter is None:
        _skymavis_rate_limiter = TokenBucketRateLimiter(
            requests_per_minute=10,
            burst_size=3,
        )
        logger.info("Created SkyMavis rate limiter: 10 req/min, burst 3")
    return _skymavis_rate_limiter


def reset_skymavis_rate_limiter() -> None:
    """Reset the global SkyMavis rate limiter."""
    global _skymavis_rate_limiter
    _skymavis_rate_limiter = None
