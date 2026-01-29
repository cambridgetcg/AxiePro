"""
Retry utilities with exponential backoff.

Provides retry decorators and utilities for resilient API calls.
Uses tenacity for robust retry logic.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, Union

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
    retry_if_exception,
)

logger = logging.getLogger(__name__)


# Default retry configuration
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_MIN_WAIT_SECONDS = 1
DEFAULT_MAX_WAIT_SECONDS = 8
DEFAULT_MULTIPLIER = 2


class RetryableError(Exception):
    """Base class for errors that should trigger a retry."""
    pass


class RateLimitError(RetryableError):
    """Raised when API returns 429 rate limit."""

    def __init__(self, retry_after: int = 30, message: str = "Rate limited"):
        self.retry_after = retry_after
        self.message = message
        super().__init__(f"{message}, retry after {retry_after}s")


class ServerError(RetryableError):
    """Raised when API returns 5xx server error."""

    def __init__(self, status_code: int, message: str = "Server error"):
        self.status_code = status_code
        self.message = message
        super().__init__(f"{message}: HTTP {status_code}")


def is_retryable_exception(exception: BaseException) -> bool:
    """
    Determine if an exception should trigger a retry.

    Retries on:
    - Connection errors (timeouts, DNS failures, etc.)
    - Server errors (5xx)
    - Rate limits (429) - but with longer wait
    - Custom RetryableError subclasses

    Does NOT retry on:
    - Client errors (4xx except 429)
    - Validation errors
    - Authentication errors
    """
    # Custom retryable errors
    if isinstance(exception, RetryableError):
        return True

    # HTTPX connection/timeout errors
    if isinstance(exception, (httpx.TimeoutException, httpx.ConnectError)):
        return True

    # HTTP status errors
    if isinstance(exception, httpx.HTTPStatusError):
        status = exception.response.status_code
        # Retry on server errors (5xx)
        if 500 <= status < 600:
            return True
        # Retry on rate limits (429)
        if status == 429:
            return True
        # Don't retry on other client errors
        return False

    # Connection reset, etc.
    if isinstance(exception, (ConnectionError, OSError)):
        return True

    return False


def is_retryable_http_response(response: httpx.Response) -> bool:
    """Check if an HTTP response indicates a retryable error."""
    status = response.status_code
    return status == 429 or (500 <= status < 600)


def get_retry_after(response: httpx.Response) -> int:
    """Extract Retry-After header from response, default to 30s."""
    try:
        return int(response.headers.get("Retry-After", 30))
    except (ValueError, TypeError):
        return 30


def create_retry_decorator(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT_SECONDS,
    max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
    multiplier: float = DEFAULT_MULTIPLIER,
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
):
    """
    Create a retry decorator with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default 3)
        min_wait: Minimum wait between retries in seconds (default 1)
        max_wait: Maximum wait between retries in seconds (default 8)
        multiplier: Multiplier for exponential backoff (default 2)
        retryable_exceptions: Tuple of exception types to retry on

    Returns:
        A decorator that adds retry logic to async functions

    Example:
        @create_retry_decorator(max_attempts=3)
        async def fetch_data():
            ...
    """
    if retryable_exceptions:
        retry_condition = retry_if_exception_type(retryable_exceptions)
    else:
        retry_condition = retry_if_exception(is_retryable_exception)

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=multiplier, min=min_wait, max=max_wait),
        retry=retry_condition,
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


# Pre-configured decorator for API calls
retry_on_transient_error = create_retry_decorator(
    max_attempts=3,
    min_wait=1,
    max_wait=8,
    multiplier=2,
)


async def with_retry(
    func: Callable,
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT_SECONDS,
    max_wait: float = DEFAULT_MAX_WAIT_SECONDS,
    **kwargs,
) -> Any:
    """
    Execute an async function with retry logic.

    This is useful when you can't use a decorator (e.g., for methods
    or when you need dynamic retry configuration).

    Args:
        func: Async function to execute
        *args: Positional arguments for func
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait between retries
        max_wait: Maximum wait between retries
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Raises:
        RetryError: If all attempts fail
        The last exception if all attempts fail

    Example:
        result = await with_retry(
            fetch_data,
            url,
            headers=headers,
            max_attempts=5,
        )
    """
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=DEFAULT_MULTIPLIER, min=min_wait, max=max_wait),
        retry=retry_if_exception(is_retryable_exception),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    ):
        with attempt:
            return await func(*args, **kwargs)


async def retry_with_rate_limit_handling(
    func: Callable,
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT_SECONDS,
    **kwargs,
) -> Any:
    """
    Execute an async function with retry and special handling for rate limits.

    When a 429 is encountered, respects the Retry-After header instead of
    using exponential backoff.

    Args:
        func: Async function that returns httpx.Response
        *args: Positional arguments for func
        max_attempts: Maximum retry attempts
        min_wait: Minimum wait between non-429 retries
        **kwargs: Keyword arguments for func

    Returns:
        Result of func

    Example:
        response = await retry_with_rate_limit_handling(
            client.post,
            url,
            json=payload,
        )
    """
    last_exception = None

    for attempt in range(max_attempts):
        try:
            result = await func(*args, **kwargs)

            # Check if result is an HTTP response with retryable status
            if isinstance(result, httpx.Response) and is_retryable_http_response(result):
                if result.status_code == 429:
                    retry_after = get_retry_after(result)
                    logger.warning(
                        f"Rate limited (429), waiting {retry_after}s "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                elif 500 <= result.status_code < 600:
                    wait_time = min_wait * (2 ** attempt)
                    logger.warning(
                        f"Server error ({result.status_code}), waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

            return result

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last_exception = e
            wait_time = min_wait * (2 ** attempt)
            logger.warning(
                f"Connection error: {e}, waiting {wait_time}s "
                f"(attempt {attempt + 1}/{max_attempts})"
            )
            await asyncio.sleep(wait_time)

        except httpx.HTTPStatusError as e:
            last_exception = e
            if e.response.status_code == 429:
                retry_after = get_retry_after(e.response)
                logger.warning(
                    f"Rate limited (429), waiting {retry_after}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                await asyncio.sleep(retry_after)
            elif 500 <= e.response.status_code < 600:
                wait_time = min_wait * (2 ** attempt)
                logger.warning(
                    f"Server error ({e.response.status_code}), waiting {wait_time}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                await asyncio.sleep(wait_time)
            else:
                # Non-retryable HTTP error
                raise

    # All attempts exhausted
    if last_exception:
        raise last_exception
    raise RuntimeError(f"All {max_attempts} attempts failed")


def log_retry_stats(
    operation: str,
    attempt: int,
    max_attempts: int,
    exception: Optional[Exception] = None,
    wait_time: Optional[float] = None,
) -> None:
    """
    Log retry statistics for observability.

    Args:
        operation: Name of the operation being retried
        attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts
        exception: The exception that triggered the retry
        wait_time: Time to wait before next attempt
    """
    extra = {
        "operation": operation,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "remaining_attempts": max_attempts - attempt,
    }

    if exception:
        extra["exception_type"] = type(exception).__name__
        extra["exception_message"] = str(exception)

    if wait_time:
        extra["wait_seconds"] = wait_time

    if attempt < max_attempts:
        logger.warning(
            f"Retrying {operation} (attempt {attempt}/{max_attempts})",
            extra=extra,
        )
    else:
        logger.error(
            f"All retries exhausted for {operation}",
            extra=extra,
        )
