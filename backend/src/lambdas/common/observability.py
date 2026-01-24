"""
Observability Utilities for Lambda Functions

Provides pre-configured AWS Lambda Powertools instances for:
- Structured logging with correlation IDs
- Distributed tracing with X-Ray
- CloudWatch custom metrics

All Lambda functions should import these instances to ensure
consistent observability across the datafeed system.

Usage:
    from src.lambdas.common import logger, tracer, metrics
    from aws_lambda_powertools.metrics import MetricUnit

    @logger.inject_lambda_context
    @tracer.capture_lambda_handler
    @metrics.log_metrics
    def handler(event, context):
        logger.info("Processing event", extra={"event_type": "price_ingestion"})
        tracer.put_annotation("class", "beast")
        metrics.add_metric(name="SnapshotsStored", unit=MetricUnit.Count, value=18)
"""

from aws_lambda_powertools import Logger, Tracer, Metrics


# Service name used across all observability tools
SERVICE_NAME = "axiepro-datafeed"

# Shared Logger instance
# - Outputs structured JSON logs
# - Automatically adds Lambda context
# - Supports correlation_id for request tracing
logger = Logger(service=SERVICE_NAME)

# Shared Tracer instance
# - Integrates with AWS X-Ray
# - Captures Lambda handler and method traces
# - Supports annotations and metadata
tracer = Tracer(service=SERVICE_NAME)

# Shared Metrics instance
# - Publishes to CloudWatch Metrics
# - Automatic EMF (Embedded Metric Format) output
# - Namespace: axiepro-datafeed
metrics = Metrics(service=SERVICE_NAME, namespace=SERVICE_NAME)


def log_lambda_start(event_type: str, **extra) -> None:
    """
    Log Lambda invocation start with standard fields.

    Args:
        event_type: Type of event being processed
        **extra: Additional fields to log
    """
    logger.info(
        f"Starting {event_type}",
        extra={"event_type": event_type, **extra},
    )


def log_lambda_complete(
    event_type: str,
    success: bool = True,
    **extra,
) -> None:
    """
    Log Lambda invocation completion with standard fields.

    Args:
        event_type: Type of event that was processed
        success: Whether processing was successful
        **extra: Additional fields to log
    """
    if success:
        logger.info(
            f"Completed {event_type}",
            extra={"event_type": event_type, "success": True, **extra},
        )
    else:
        logger.error(
            f"Failed {event_type}",
            extra={"event_type": event_type, "success": False, **extra},
        )


def add_metric(name: str, value: float, unit: str = "Count") -> None:
    """
    Add a metric with simplified API.

    Args:
        name: Metric name
        value: Metric value
        unit: Metric unit (default: Count)
    """
    from aws_lambda_powertools.metrics import MetricUnit

    unit_map = {
        "Count": MetricUnit.Count,
        "Seconds": MetricUnit.Seconds,
        "Milliseconds": MetricUnit.Milliseconds,
        "Bytes": MetricUnit.Bytes,
        "Percent": MetricUnit.Percent,
    }

    metrics.add_metric(
        name=name,
        value=value,
        unit=unit_map.get(unit, MetricUnit.Count),
    )
