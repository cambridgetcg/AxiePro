"""
Cache Invalidator Lambda

Event-driven cache invalidation triggered by SNS notifications from
data ingestion Lambdas. Provides immediate cache updates on data changes.

Triggered by:
- sales_ingestion Lambda (new sales)
- listings_ingestion Lambda (new listings)
- price_ingestion Lambda (floor price updates)
- metadata_ingestion Lambda (axie metadata updates)

SNS Message Format:
{
    "event_type": "sales_ingested" | "listings_ingested" | "prices_updated" | "metadata_updated",
    "axie_ids": [1, 2, 3],  # Optional
    "axie_classes": ["Beast", "Plant"],  # Optional
    "timestamp": "2026-01-31T12:00:00Z"
}
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Set
from datetime import datetime

from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

# Import shared utilities
from src.lambdas.common import logger, tracer, metrics

# Import cache invalidation service
from src.services.cache.invalidation import (
    invalidate_on_sales_ingestion,
    invalidate_on_listings_ingestion,
    invalidate_on_price_update,
    CacheInvalidator,
)


@tracer.capture_method
async def handle_sales_ingested(message: Dict[str, Any]) -> int:
    """
    Handle sales ingestion event.

    Args:
        message: SNS message with sales data

    Returns:
        Number of cache keys invalidated
    """
    axie_ids = message.get("axie_ids", [])
    axie_classes = set(message.get("axie_classes", []))

    logger.info(
        f"Handling sales ingestion: {len(axie_ids)} axies, "
        f"{len(axie_classes)} classes"
    )

    await invalidate_on_sales_ingestion(axie_ids, axie_classes)

    # Record metrics
    metrics.add_metric(
        name="CacheInvalidatedSales",
        unit=MetricUnit.Count,
        value=len(axie_classes)
    )

    return len(axie_classes)


@tracer.capture_method
async def handle_listings_ingested(message: Dict[str, Any]) -> int:
    """
    Handle listings ingestion event.

    Args:
        message: SNS message with listings data

    Returns:
        Number of cache keys invalidated
    """
    axie_classes = set(message.get("axie_classes", []))

    logger.info(f"Handling listings ingestion: {len(axie_classes)} classes")

    await invalidate_on_listings_ingestion(axie_classes)

    # Record metrics
    metrics.add_metric(
        name="CacheInvalidatedListings",
        unit=MetricUnit.Count,
        value=len(axie_classes)
    )

    return len(axie_classes)


@tracer.capture_method
async def handle_prices_updated(message: Dict[str, Any]) -> int:
    """
    Handle price update event.

    Args:
        message: SNS message with price data

    Returns:
        Number of cache keys invalidated
    """
    axie_classes = set(message.get("axie_classes", []))

    logger.info(f"Handling price update: {len(axie_classes)} classes")

    await invalidate_on_price_update(axie_classes)

    # Record metrics
    metrics.add_metric(
        name="CacheInvalidatedPrices",
        unit=MetricUnit.Count,
        value=len(axie_classes)
    )

    return len(axie_classes)


@tracer.capture_method
async def handle_metadata_updated(message: Dict[str, Any]) -> int:
    """
    Handle metadata update event.

    Args:
        message: SNS message with metadata update

    Returns:
        Number of cache keys invalidated
    """
    axie_ids = message.get("axie_ids", [])

    logger.info(f"Handling metadata update: {len(axie_ids)} axies")

    invalidator = CacheInvalidator()

    total_deleted = 0
    for axie_id in axie_ids:
        deleted = await invalidator.invalidate_metadata_cache(axie_id)
        total_deleted += deleted

    # Record metrics
    metrics.add_metric(
        name="CacheInvalidatedMetadata",
        unit=MetricUnit.Count,
        value=len(axie_ids)
    )

    return total_deleted


@tracer.capture_method
async def process_sns_message(message: str) -> int:
    """
    Process SNS message and route to appropriate handler.

    Args:
        message: JSON string from SNS

    Returns:
        Number of cache keys invalidated
    """
    try:
        data = json.loads(message)
        event_type = data.get("event_type")

        logger.info(f"Processing cache invalidation event: {event_type}")

        if event_type == "sales_ingested":
            return await handle_sales_ingested(data)

        elif event_type == "listings_ingested":
            return await handle_listings_ingested(data)

        elif event_type == "prices_updated":
            return await handle_prices_updated(data)

        elif event_type == "metadata_updated":
            return await handle_metadata_updated(data)

        else:
            logger.warning(f"Unknown event type: {event_type}")
            return 0

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in SNS message: {e}")
        metrics.add_metric(name="InvalidationErrors", unit=MetricUnit.Count, value=1)
        return 0

    except Exception as e:
        logger.error(f"Error processing SNS message: {e}")
        metrics.add_metric(name="InvalidationErrors", unit=MetricUnit.Count, value=1)
        raise


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for cache invalidation events.

    Processes SNS messages from data ingestion Lambdas and invalidates
    relevant cache keys in Redis.

    Args:
        event: SNS event with Records
        context: Lambda context

    Returns:
        Dict with processing results
    """
    logger.info("Cache invalidator Lambda invoked")

    async def process_event():
        total_invalidated = 0
        processed_records = 0
        failed_records = 0

        try:
            # Process all SNS records
            records = event.get("Records", [])

            for record in records:
                try:
                    # Extract SNS message
                    sns_message = record.get("Sns", {}).get("Message", "")

                    # Process message
                    invalidated = await process_sns_message(sns_message)
                    total_invalidated += invalidated
                    processed_records += 1

                except Exception as e:
                    logger.error(f"Error processing record: {e}")
                    failed_records += 1

            logger.info(
                f"Cache invalidation complete: "
                f"processed={processed_records}, "
                f"failed={failed_records}, "
                f"invalidated={total_invalidated} keys"
            )

            return {
                "processed_records": processed_records,
                "failed_records": failed_records,
                "total_invalidated": total_invalidated,
            }

        except Exception as e:
            logger.error(f"Error in cache invalidation: {e}")
            metrics.add_metric(name="InvalidationErrors", unit=MetricUnit.Count, value=1)
            raise

    # Run async event processing
    result = asyncio.run(process_event())

    # Record metrics
    metrics.add_metric(
        name="RecordsProcessed",
        unit=MetricUnit.Count,
        value=result["processed_records"]
    )

    if result["failed_records"] > 0:
        metrics.add_metric(
            name="RecordsFailed",
            unit=MetricUnit.Count,
            value=result["failed_records"]
        )

    return {
        "statusCode": 200 if result["failed_records"] == 0 else 207,
        "body": json.dumps({
            "message": "Cache invalidation complete",
            "processed": result["processed_records"],
            "failed": result["failed_records"],
            "invalidated_keys": result["total_invalidated"],
        }),
    }
