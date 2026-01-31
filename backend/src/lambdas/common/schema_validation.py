"""
Schema Validation Layer

Validates Lambda data structures against actual database schemas to prevent
table/column mismatches. Catches schema drift at development time.
"""

from typing import Dict, Set, Optional, Any
from dataclasses import dataclass


@dataclass
class TableSchema:
    """Represents the expected schema for a database table."""

    table_name: str
    required_columns: Set[str]
    optional_columns: Set[str]

    @property
    def all_columns(self) -> Set[str]:
        """Get all valid columns (required + optional)."""
        return self.required_columns | self.optional_columns

    def validate_record(self, record: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate a record against this schema.

        Args:
            record: Dictionary of column -> value mappings

        Returns:
            (is_valid, error_message) tuple
        """
        record_keys = set(record.keys())

        # Check for missing required columns
        missing = self.required_columns - record_keys
        if missing:
            return False, f"Missing required columns: {missing}"

        # Check for unknown columns
        unknown = record_keys - self.all_columns
        if unknown:
            return False, f"Unknown columns: {unknown}"

        return True, None


# Define schemas for all tables used by Lambdas
AXIE_SALES_SCHEMA = TableSchema(
    table_name="axie_sales",
    required_columns={
        "axie_id",
        "tx_hash",
        "block_number",
        "block_timestamp",
        "price_token",
        "token_type",
    },
    optional_columns={
        "price_usd",
        "eth_usd_rate",
        "ron_usd_rate",
        "seller",
        "buyer",
        "class",
        "breed_count",
        "price_raw",
    },
)

AXIES_SCHEMA = TableSchema(
    table_name="axies",
    required_columns={
        "axie_id",
    },
    optional_columns={
        "class",
        "breed_count",
        "hp",
        "speed",
        "skill",
        "morale",
        "stage",
        "title",
        "genes",
        "matron_id",
        "sire_id",
        "birth_date",
        "owner",
        "first_seen_at",
        "last_updated",
    },
)

EXCHANGE_RATES_SCHEMA = TableSchema(
    table_name="exchange_rates",
    required_columns={
        "eth_usd",
        "ron_usd",
        "recorded_at",
    },
    optional_columns=set(),
)


def validate_sales_record(record: Dict[str, Any]) -> None:
    """
    Validate a sales record before insertion.

    Raises:
        ValueError: If record doesn't match schema
    """
    is_valid, error = AXIE_SALES_SCHEMA.validate_record(record)
    if not is_valid:
        raise ValueError(f"Invalid axie_sales record: {error}")


def validate_axie_record(record: Dict[str, Any]) -> None:
    """
    Validate an axie metadata record before insertion.

    Raises:
        ValueError: If record doesn't match schema
    """
    is_valid, error = AXIES_SCHEMA.validate_record(record)
    if not is_valid:
        raise ValueError(f"Invalid axies record: {error}")


def validate_exchange_rate_record(record: Dict[str, Any]) -> None:
    """
    Validate an exchange rate record before insertion.

    Raises:
        ValueError: If record doesn't match schema
    """
    is_valid, error = EXCHANGE_RATES_SCHEMA.validate_record(record)
    if not is_valid:
        raise ValueError(f"Invalid exchange_rates record: {error}")
