"""
Data Validation Utilities

Provides validation functions for API responses, prices, and other data
to ensure data quality in the ingestion pipeline.
"""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

from aws_lambda_powertools import Logger

logger = Logger(child=True)


class GraphQLError(Exception):
    """Raised when GraphQL response contains errors."""

    def __init__(self, errors: List[Dict[str, Any]], message: str = "GraphQL query failed"):
        self.errors = errors
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        error_messages = [e.get("message", str(e)) for e in self.errors]
        return f"{self.message}: {'; '.join(error_messages)}"


class ValidationError(Exception):
    """Raised when data validation fails."""

    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Validation failed for {field}: {reason}")


# Price validation bounds
MIN_PRICE_ETH = Decimal("0.0001")  # 0.0001 ETH minimum (~$0.30)
MAX_PRICE_ETH = Decimal("100000")  # 100,000 ETH maximum (~$300M)
WEI_PER_ETH = Decimal(10**18)


def check_graphql_errors(response_data: Dict[str, Any]) -> None:
    """
    Check GraphQL response for errors and raise if found.

    GraphQL can return a 200 OK with errors in the response body.
    This function checks for and raises on those errors.

    Args:
        response_data: The parsed JSON response from GraphQL API

    Raises:
        GraphQLError: If the response contains errors

    Example:
        response = await client.post(endpoint, json=payload)
        data = response.json()
        check_graphql_errors(data)  # Raises if errors present
        # Now safe to parse data["data"]
    """
    if not isinstance(response_data, dict):
        raise GraphQLError(
            [{"message": f"Invalid response type: {type(response_data).__name__}"}],
            "GraphQL response is not a valid JSON object"
        )

    errors = response_data.get("errors")
    if errors:
        # Log the errors with context
        for error in errors:
            logger.error(
                "GraphQL error in response",
                extra={
                    "error_message": error.get("message"),
                    "error_path": error.get("path"),
                    "error_extensions": error.get("extensions"),
                }
            )
        raise GraphQLError(errors)

    # Also check for null data which might indicate a problem
    if response_data.get("data") is None and not errors:
        logger.warning("GraphQL response has null data without errors")


def validate_price_wei(
    price_wei: Any,
    field_name: str = "price",
    allow_zero: bool = False,
) -> Optional[Decimal]:
    """
    Validate and convert a price from wei to ETH.

    Args:
        price_wei: Price in wei (string, int, or None)
        field_name: Name of the field for error messages
        allow_zero: Whether to allow zero prices

    Returns:
        Price in ETH as Decimal, or None if input is None/empty

    Raises:
        ValidationError: If price is invalid or out of bounds
    """
    if price_wei is None or price_wei == "":
        return None

    try:
        wei_value = Decimal(str(price_wei))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValidationError(field_name, price_wei, f"Cannot convert to decimal: {e}")

    # Check for negative
    if wei_value < 0:
        raise ValidationError(field_name, price_wei, "Price cannot be negative")

    # Convert to ETH
    price_eth = wei_value / WEI_PER_ETH

    # Check zero
    if not allow_zero and price_eth == 0:
        raise ValidationError(field_name, price_wei, "Price cannot be zero")

    # Check bounds
    if price_eth < MIN_PRICE_ETH:
        raise ValidationError(
            field_name,
            price_wei,
            f"Price {price_eth} ETH is below minimum {MIN_PRICE_ETH} ETH"
        )

    if price_eth > MAX_PRICE_ETH:
        raise ValidationError(
            field_name,
            price_wei,
            f"Price {price_eth} ETH exceeds maximum {MAX_PRICE_ETH} ETH"
        )

    return price_eth


def validate_price_eth(
    price_eth: Any,
    field_name: str = "price",
    allow_zero: bool = False,
) -> Optional[Decimal]:
    """
    Validate a price already in ETH.

    Args:
        price_eth: Price in ETH (string, float, Decimal, or None)
        field_name: Name of the field for error messages
        allow_zero: Whether to allow zero prices

    Returns:
        Price in ETH as Decimal, or None if input is None/empty

    Raises:
        ValidationError: If price is invalid or out of bounds
    """
    if price_eth is None or price_eth == "":
        return None

    try:
        price = Decimal(str(price_eth))
    except (InvalidOperation, ValueError, TypeError) as e:
        raise ValidationError(field_name, price_eth, f"Cannot convert to decimal: {e}")

    if price < 0:
        raise ValidationError(field_name, price_eth, "Price cannot be negative")

    if not allow_zero and price == 0:
        raise ValidationError(field_name, price_eth, "Price cannot be zero")

    if price < MIN_PRICE_ETH:
        raise ValidationError(
            field_name,
            price_eth,
            f"Price {price} ETH is below minimum {MIN_PRICE_ETH} ETH"
        )

    if price > MAX_PRICE_ETH:
        raise ValidationError(
            field_name,
            price_eth,
            f"Price {price} ETH exceeds maximum {MAX_PRICE_ETH} ETH"
        )

    return price


def validate_timestamp(
    timestamp: Any,
    field_name: str = "timestamp",
    max_age_days: int = 365,
    allow_future: bool = False,
    future_tolerance_minutes: int = 5,
) -> Optional[datetime]:
    """
    Validate and convert a Unix timestamp.

    Args:
        timestamp: Unix timestamp (int, string, or None)
        field_name: Name of the field for error messages
        max_age_days: Maximum age of timestamp in days
        allow_future: Whether to allow future timestamps
        future_tolerance_minutes: How many minutes into future to tolerate

    Returns:
        datetime object in UTC, or None if input is None

    Raises:
        ValidationError: If timestamp is invalid or out of bounds
    """
    if timestamp is None or timestamp == "":
        return None

    try:
        ts_value = int(timestamp)
    except (ValueError, TypeError) as e:
        raise ValidationError(field_name, timestamp, f"Cannot convert to timestamp: {e}")

    # Handle millisecond timestamps
    if ts_value > 10**12:
        ts_value = ts_value // 1000

    try:
        dt = datetime.fromtimestamp(ts_value, tz=timezone.utc)
    except (ValueError, OSError) as e:
        raise ValidationError(field_name, timestamp, f"Invalid timestamp value: {e}")

    now = datetime.now(timezone.utc)

    # Check for future
    if not allow_future:
        max_future = now + timedelta(minutes=future_tolerance_minutes)
        if dt > max_future:
            raise ValidationError(
                field_name,
                timestamp,
                f"Timestamp {dt.isoformat()} is in the future"
            )

    # Check for too old
    min_allowed = now - timedelta(days=max_age_days)
    if dt < min_allowed:
        raise ValidationError(
            field_name,
            timestamp,
            f"Timestamp {dt.isoformat()} is older than {max_age_days} days"
        )

    return dt


def validate_address(
    address: Any,
    field_name: str = "address",
    require_prefix: bool = True,
) -> Optional[str]:
    """
    Validate an Ethereum/Ronin address.

    Args:
        address: Address string or None
        field_name: Name of the field for error messages
        require_prefix: Whether to require 0x prefix

    Returns:
        Lowercased address string, or None if input is None

    Raises:
        ValidationError: If address format is invalid
    """
    if address is None or address == "":
        return None

    if not isinstance(address, str):
        raise ValidationError(field_name, address, "Address must be a string")

    addr = address.strip().lower()

    # Check prefix
    if require_prefix and not addr.startswith("0x"):
        raise ValidationError(field_name, address, "Address must start with 0x")

    # Remove prefix for length check
    addr_hex = addr[2:] if addr.startswith("0x") else addr

    # Check length (40 hex characters = 20 bytes)
    if len(addr_hex) != 40:
        raise ValidationError(
            field_name,
            address,
            f"Address must be 40 hex characters, got {len(addr_hex)}"
        )

    # Check valid hex
    try:
        int(addr_hex, 16)
    except ValueError:
        raise ValidationError(field_name, address, "Address contains invalid hex characters")

    return addr


def validate_axie_id(axie_id: Any, field_name: str = "axie_id") -> Optional[int]:
    """
    Validate an Axie ID.

    Args:
        axie_id: Axie ID (int, string, or None)
        field_name: Name of the field for error messages

    Returns:
        Axie ID as integer, or None if input is None

    Raises:
        ValidationError: If ID is invalid
    """
    if axie_id is None or axie_id == "":
        return None

    try:
        id_value = int(axie_id)
    except (ValueError, TypeError) as e:
        raise ValidationError(field_name, axie_id, f"Cannot convert to integer: {e}")

    if id_value <= 0:
        raise ValidationError(field_name, axie_id, "Axie ID must be positive")

    # Axie IDs are uint256 but practically much smaller
    # Current max is around 12 million
    if id_value > 100_000_000:
        raise ValidationError(
            field_name,
            axie_id,
            f"Axie ID {id_value} seems unreasonably large"
        )

    return id_value


def safe_validate_price_wei(
    price_wei: Any,
    field_name: str = "price",
    default: Optional[Decimal] = None,
) -> Tuple[Optional[Decimal], Optional[str]]:
    """
    Validate price without raising, return error message instead.

    Useful for batch processing where you want to log invalid records
    but continue processing.

    Returns:
        Tuple of (validated_price, error_message)
        - If valid: (Decimal, None)
        - If invalid: (default, error_message)
    """
    try:
        return validate_price_wei(price_wei, field_name), None
    except ValidationError as e:
        return default, str(e)


def safe_validate_timestamp(
    timestamp: Any,
    field_name: str = "timestamp",
    default: Optional[datetime] = None,
) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Validate timestamp without raising, return error message instead.

    Returns:
        Tuple of (validated_timestamp, error_message)
    """
    try:
        return validate_timestamp(timestamp, field_name), None
    except ValidationError as e:
        return default, str(e)
