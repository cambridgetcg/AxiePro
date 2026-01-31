"""
Integration test: Sales Ingestion Schema Compliance

Validates that sales_ingestion.py produces records that match the actual
axie_sales table schema. Catches table/column mismatches before deployment.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any

# Import the actual schema validator
from src.lambdas.common.schema_validation import (
    AXIE_SALES_SCHEMA,
    validate_sales_record,
)

# Import the actual conversion function from sales_ingestion
from src.lambdas.sales_ingestion import convert_sale_to_record
from src.services.ronin_rpc_client import Sale


class TestSalesSchemaCompliance:
    """Test that sales_ingestion.py complies with axie_sales schema."""

    def test_convert_sale_to_record_produces_valid_schema(self):
        """Test that convert_sale_to_record() output matches axie_sales schema."""
        # Create a sample Sale object (from RoninRPCClient)
        sample_sale = Sale(
            axie_id=11111111,
            tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            block_number=12345678,
            block_timestamp=datetime.now(timezone.utc),
            price_token=Decimal("0.05"),
            token_type="WETH",
            price_usd=Decimal("150.00"),
            seller="0xabcdef1234567890abcdef1234567890abcdef12",
            buyer="0x1234567890abcdef1234567890abcdef12345678",
        )

        # Convert using actual production function
        record = convert_sale_to_record(
            sample_sale,
            eth_usd_rate=Decimal("3000.00"),
            ron_usd_rate=Decimal("0.15"),
        )

        # Validate against schema - should not raise
        validate_sales_record(record)

        # Verify required columns are present
        assert "axie_id" in record
        assert "tx_hash" in record
        assert "block_number" in record
        assert "block_timestamp" in record
        assert "price_token" in record
        assert "token_type" in record

    def test_schema_defines_all_required_columns(self):
        """Verify AXIE_SALES_SCHEMA includes all non-nullable columns."""
        required = AXIE_SALES_SCHEMA.required_columns

        # These are NOT NULL in schema
        assert "axie_id" in required
        assert "tx_hash" in required
        assert "block_number" in required
        assert "block_timestamp" in required
        assert "price_token" in required
        assert "token_type" in required

    def test_schema_defines_all_optional_columns(self):
        """Verify AXIE_SALES_SCHEMA includes all nullable columns."""
        optional = AXIE_SALES_SCHEMA.optional_columns

        # These are nullable in schema
        assert "price_usd" in optional
        assert "eth_usd_rate" in optional
        assert "ron_usd_rate" in optional
        assert "seller" in optional
        assert "buyer" in optional
        assert "class" in optional
        assert "breed_count" in optional
        assert "price_raw" in optional

    def test_no_unknown_columns_in_record(self):
        """Ensure convert_sale_to_record doesn't produce unknown columns."""
        sample_sale = Sale(
            axie_id=11111111,
            tx_hash="0x" + "a" * 64,
            block_number=12345678,
            block_timestamp=datetime.now(timezone.utc),
            price_token=Decimal("0.05"),
            token_type="WETH",
            price_usd=None,
            seller=None,
            buyer=None,
        )

        record = convert_sale_to_record(sample_sale)

        # All keys should be valid columns
        record_keys = set(record.keys())
        valid_columns = AXIE_SALES_SCHEMA.all_columns

        unknown = record_keys - valid_columns
        assert not unknown, f"Record contains unknown columns: {unknown}"

    def test_old_column_names_not_present(self):
        """Ensure old column names (seller_address, buyer_address, etc.) are gone."""
        sample_sale = Sale(
            axie_id=11111111,
            tx_hash="0x" + "a" * 64,
            block_number=12345678,
            block_timestamp=datetime.now(timezone.utc),
            price_token=Decimal("0.05"),
            token_type="WETH",
            price_usd=Decimal("150.00"),
            seller="0x" + "a" * 40,
            buyer="0x" + "b" * 40,
        )

        record = convert_sale_to_record(sample_sale)

        # Old column names should NOT appear
        assert "seller_address" not in record, "Old column 'seller_address' still present"
        assert "buyer_address" not in record, "Old column 'buyer_address' still present"
        assert "price_eth" not in record, "Old column 'price_eth' still present"
        assert "sold_at" not in record, "Old column 'sold_at' still present"
        assert "marketplace" not in record, "Old column 'marketplace' still present"

        # New column names SHOULD appear
        assert "seller" in record
        assert "buyer" in record
        assert "price_token" in record
        assert "block_timestamp" in record

    def test_table_name_is_axie_sales(self):
        """Verify schema references correct table name."""
        assert AXIE_SALES_SCHEMA.table_name == "axie_sales", \
            "Schema should reference 'axie_sales' not 'sales'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
