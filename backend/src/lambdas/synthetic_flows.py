"""
Synthetic Flows Lambda

Runs automated validation flows on a schedule to verify feature effectiveness.
Can also be triggered on-demand via API.

Flows:
- Deal Hunter: Validates deal detection accuracy
- Breeding Planner: Validates breeding simulation accuracy
- Meta Scout: Validates meta shift detection timeliness

Schedule: Every 6 hours (configurable)
Trigger: EventBridge Schedule or API Gateway
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional, List

from aws_lambda_powertools.metrics import MetricUnit

# Import shared observability from common module
from src.lambdas.common import (
    logger,
    tracer,
    metrics,
)
from src.lambdas.common.aws import get_db_credentials


async def get_db_session():
    """Create async database session for synthetic flows."""
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    credentials = get_db_credentials()
    host = os.environ.get("DATABASE_HOST")
    port = os.environ.get("DATABASE_PORT", "5432")
    dbname = os.environ.get("DATABASE_NAME", "axiepro")
    username = credentials.get("username")
    password = credentials.get("password")

    # Construct async connection URL
    database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    return async_session()


async def run_flows(
    flow_types: Optional[List[str]] = None,
    parallel: bool = True,
) -> List[dict]:
    """
    Run synthetic flows.

    Args:
        flow_types: List of flow types to run. If None, runs all flows.
        parallel: If True, run flows in parallel.

    Returns:
        List of flow run results
    """
    from src.services.synthetic_flows import FlowRunner
    from src.models.instrumentation import FlowType

    # Get API base URL
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")

    # Create database session
    db = await get_db_session()

    try:
        # Create flow runner
        runner = FlowRunner(api_base_url, db)

        # Determine which flows to run
        if flow_types:
            # Convert string flow types to enums
            flow_type_enums = [FlowType(ft) for ft in flow_types]
            results = await runner.run_flows(flow_type_enums, parallel=parallel)
        else:
            # Run all flows
            results = await runner.run_all_flows(parallel=parallel)

        # Convert results to dicts
        return [r.to_dict() for r in results]

    finally:
        await db.close()


@tracer.capture_method
@logger.inject_lambda_context
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event, context):
    """
    Lambda handler for synthetic flows.

    Event format:
    {
        "flow_types": ["deal_hunter", "breeding_planner"],  # Optional, defaults to all
        "parallel": true  # Optional, defaults to true
    }

    EventBridge Schedule event:
    {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        ...
    }
    """
    logger.info("Synthetic flows lambda triggered", extra={"event": event})

    # Parse event
    flow_types = None
    parallel = True

    if "flow_types" in event:
        flow_types = event["flow_types"]
    if "parallel" in event:
        parallel = event["parallel"]

    # Run flows
    try:
        results = asyncio.run(run_flows(flow_types, parallel))

        # Log metrics
        for result in results:
            flow_type = result.get("flow_type")
            status = result.get("status")
            validation_score = result.get("validation_score", 0)

            # Record metrics
            metrics.add_metric(
                name=f"SyntheticFlow_{flow_type}_Score",
                unit=MetricUnit.Count,
                value=validation_score,
            )

            if status == "passed":
                metrics.add_metric(
                    name=f"SyntheticFlow_{flow_type}_Passed",
                    unit=MetricUnit.Count,
                    value=1,
                )
            elif status == "failed":
                metrics.add_metric(
                    name=f"SyntheticFlow_{flow_type}_Failed",
                    unit=MetricUnit.Count,
                    value=1,
                )
            elif status == "error":
                metrics.add_metric(
                    name=f"SyntheticFlow_{flow_type}_Error",
                    unit=MetricUnit.Count,
                    value=1,
                )

        # Log summary
        passed = sum(1 for r in results if r.get("status") == "passed")
        failed = sum(1 for r in results if r.get("status") == "failed")
        errors = sum(1 for r in results if r.get("status") == "error")

        logger.info(
            "Synthetic flows completed",
            extra={
                "total_flows": len(results),
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "data": {
                    "total_flows": len(results),
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "results": results,
                },
                "timestamp": datetime.utcnow().isoformat(),
            }),
        }

    except Exception as e:
        logger.exception("Error running synthetic flows")

        metrics.add_metric(
            name="SyntheticFlow_ExecutionError",
            unit=MetricUnit.Count,
            value=1,
        )

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }),
        }
