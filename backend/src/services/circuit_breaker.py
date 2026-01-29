"""
Circuit breaker pattern for external API resilience.

Prevents cascading failures by stopping requests to failing services
and allowing them time to recover.
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation - requests allowed
    OPEN = "open"            # Failing - requests rejected
    HALF_OPEN = "half_open"  # Testing recovery - limited requests


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting requests."""

    def __init__(self, message: str = "Circuit breaker is open", recovery_time: float = 0):
        self.message = message
        self.recovery_time = recovery_time
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker for external API calls.

    State transitions:
    - CLOSED → OPEN: After failure_threshold consecutive failures
    - OPEN → HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN → CLOSED: On successful call
    - HALF_OPEN → OPEN: On failed call

    Example:
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        if await breaker.can_execute():
            try:
                result = await api_call()
                await breaker.record_success()
            except Exception:
                await breaker.record_failure()
                raise
        else:
            raise CircuitOpenError()
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for logging
            failure_threshold: Consecutive failures before opening
            recovery_timeout: Seconds to wait before testing recovery
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self._failure_count

    async def can_execute(self) -> bool:
        """
        Check if request should be allowed.

        Returns:
            True if request can proceed, False if circuit is open
        """
        async with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(
                        f"Circuit breaker [{self.name}]: OPEN → HALF_OPEN "
                        f"(testing recovery after {elapsed:.1f}s)"
                    )
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False

            return False

    async def record_success(self) -> None:
        """Record successful call."""
        async with self._lock:
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(
                    f"Circuit breaker [{self.name}]: HALF_OPEN → CLOSED (recovered)"
                )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success
                self._failure_count = 0

    async def record_failure(self, error: Optional[Exception] = None) -> None:
        """Record failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            error_msg = str(error) if error else "unknown error"

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker [{self.name}]: HALF_OPEN → OPEN "
                    f"(recovery failed: {error_msg})"
                )
            elif self._failure_count >= self.failure_threshold:
                if self._state != CircuitState.OPEN:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        f"Circuit breaker [{self.name}]: CLOSED → OPEN "
                        f"(threshold {self.failure_threshold} reached: {error_msg})"
                    )

    def time_until_recovery(self) -> float:
        """Get seconds until circuit might close (0 if not open)."""
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    async def force_open(self) -> None:
        """Force circuit to open state (for testing or manual intervention)."""
        async with self._lock:
            self._state = CircuitState.OPEN
            self._last_failure_time = time.monotonic()
            logger.warning(f"Circuit breaker [{self.name}]: Forced OPEN")

    async def force_close(self) -> None:
        """Force circuit to closed state (for testing or manual intervention)."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            logger.info(f"Circuit breaker [{self.name}]: Forced CLOSED")

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "time_until_recovery": self.time_until_recovery(),
        }


# Global circuit breaker instance for SkyMavis API
_skymavis_circuit_breaker: Optional[CircuitBreaker] = None


def get_skymavis_circuit_breaker() -> CircuitBreaker:
    """
    Get or create global SkyMavis circuit breaker.

    Uses settings appropriate for external API:
    - 5 consecutive failures to open
    - 60 second recovery timeout
    """
    global _skymavis_circuit_breaker
    if _skymavis_circuit_breaker is None:
        _skymavis_circuit_breaker = CircuitBreaker(
            name="skymavis",
            failure_threshold=5,
            recovery_timeout=60.0,
            half_open_max_calls=1,
        )
        logger.info("Created SkyMavis circuit breaker: threshold=5, recovery=60s")
    return _skymavis_circuit_breaker


def reset_skymavis_circuit_breaker() -> None:
    """Reset the global SkyMavis circuit breaker."""
    global _skymavis_circuit_breaker
    _skymavis_circuit_breaker = None
