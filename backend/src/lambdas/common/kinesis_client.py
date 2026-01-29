"""
Kinesis Client Utilities

Provides utilities for publishing records to Kinesis Data Streams.
Used by data ingestion Lambdas to feed downstream processing (deal detection).
"""

import json
import os
from typing import Any, Dict, List, Optional
from decimal import Decimal

import boto3
from botocore.config import Config

from src.lambdas.common.observability import logger


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


# Global Kinesis client (connection reuse)
_kinesis_client = None


def get_kinesis_client():
    """Get or create Kinesis client with retry configuration."""
    global _kinesis_client
    if _kinesis_client is None:
        config = Config(
            retries={
                "max_attempts": 3,
                "mode": "adaptive",
            },
            connect_timeout=5,
            read_timeout=10,
        )
        _kinesis_client = boto3.client("kinesis", config=config)
        logger.info("Created Kinesis client")
    return _kinesis_client


def get_kinesis_stream_name() -> Optional[str]:
    """Get Kinesis stream name from environment."""
    return os.environ.get("KINESIS_STREAM_NAME")


def publish_listing_to_kinesis(
    listing: Dict[str, Any],
    stream_name: Optional[str] = None,
) -> bool:
    """
    Publish a single listing to Kinesis stream.

    Args:
        listing: Listing data to publish
        stream_name: Kinesis stream name (defaults to env var)

    Returns:
        True if successful, False otherwise
    """
    stream = stream_name or get_kinesis_stream_name()
    if not stream:
        logger.warning("KINESIS_STREAM_NAME not set, skipping publish")
        return False

    try:
        client = get_kinesis_client()

        # Use axie_id as partition key for consistent routing
        partition_key = str(listing.get("axie_id", "unknown"))

        # Add metadata for downstream processing
        record = {
            "event_type": "listing",
            "data": listing,
        }

        response = client.put_record(
            StreamName=stream,
            Data=json.dumps(record, cls=DecimalEncoder),
            PartitionKey=partition_key,
        )

        logger.debug(
            f"Published listing to Kinesis",
            extra={
                "axie_id": listing.get("axie_id"),
                "shard_id": response.get("ShardId"),
                "sequence_number": response.get("SequenceNumber"),
            },
        )
        return True

    except Exception as e:
        logger.error(
            f"Failed to publish listing to Kinesis: {e}",
            extra={"axie_id": listing.get("axie_id")},
        )
        return False


def publish_listings_batch_to_kinesis(
    listings: List[Dict[str, Any]],
    stream_name: Optional[str] = None,
) -> Dict[str, int]:
    """
    Publish multiple listings to Kinesis in a single batch.

    Uses PutRecords for efficient batch publishing. Kinesis supports up to
    500 records per batch and 1MB total payload.

    Args:
        listings: List of listing data to publish
        stream_name: Kinesis stream name (defaults to env var)

    Returns:
        Dict with counts: {"succeeded": n, "failed": m}
    """
    stream = stream_name or get_kinesis_stream_name()
    if not stream:
        logger.warning("KINESIS_STREAM_NAME not set, skipping batch publish")
        return {"succeeded": 0, "failed": len(listings)}

    if not listings:
        return {"succeeded": 0, "failed": 0}

    try:
        client = get_kinesis_client()

        # Build records for batch
        records = []
        for listing in listings:
            partition_key = str(listing.get("axie_id", "unknown"))
            record_data = {
                "event_type": "listing",
                "data": listing,
            }
            records.append({
                "Data": json.dumps(record_data, cls=DecimalEncoder),
                "PartitionKey": partition_key,
            })

        # Kinesis PutRecords limit is 500 records per call
        succeeded = 0
        failed = 0

        for i in range(0, len(records), 500):
            batch = records[i:i + 500]
            response = client.put_records(
                StreamName=stream,
                Records=batch,
            )

            batch_failed = response.get("FailedRecordCount", 0)
            batch_succeeded = len(batch) - batch_failed
            succeeded += batch_succeeded
            failed += batch_failed

            if batch_failed > 0:
                logger.warning(
                    f"Kinesis batch had {batch_failed} failed records",
                    extra={"batch_size": len(batch)},
                )

        logger.info(
            f"Published {succeeded} listings to Kinesis, {failed} failed",
            extra={"stream": stream},
        )

        return {"succeeded": succeeded, "failed": failed}

    except Exception as e:
        logger.error(f"Failed to publish listings batch to Kinesis: {e}")
        return {"succeeded": 0, "failed": len(listings)}


def reset_kinesis_client() -> None:
    """Reset the global Kinesis client (for testing)."""
    global _kinesis_client
    _kinesis_client = None
