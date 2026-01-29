"""
Health Check Lambda

Monitors data freshness across the ingestion pipeline.
Checks timestamps in key tables and alerts if data is stale.

Runs every 5 minutes to provide early warning of ingestion failures.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Tuple

from aws_lambda_powertools.metrics import MetricUnit

from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_db_connection,
)


# Freshness thresholds (in minutes)
FRESHNESS_THRESHOLDS = {
    "listings": 15,      # Listings should be updated every 5 minutes
    "sales": 60,         # Sales should be updated every 30 minutes
    "price_snapshots": 30,  # Price snapshots every 15 minutes
}

# Minimum expected record counts (sanity check)
MIN_EXPECTED_COUNTS = {
    "listings": 100,     # Should have at least 100 active listings
    "sales": 10,         # Should have at least 10 sales in last 24h
    "price_snapshots": 5,  # Should have at least 5 snapshots in last hour
}


@tracer.capture_method
def check_table_freshness(conn, table: str, timestamp_column: str, threshold_minutes: int) -> Dict[str, Any]:
    """
    Check the freshness of data in a table.

    Returns:
        Dict with freshness status and details
    """
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        # Get the most recent timestamp
        cur.execute(f"SELECT MAX({timestamp_column}) FROM {table}")
        result = cur.fetchone()
        latest_timestamp = result[0] if result else None

        if latest_timestamp is None:
            return {
                "table": table,
                "status": "NO_DATA",
                "latest_timestamp": None,
                "age_minutes": None,
                "threshold_minutes": threshold_minutes,
                "is_fresh": False,
                "message": f"No data found in {table}",
            }

        # Ensure timezone awareness
        if latest_timestamp.tzinfo is None:
            latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)

        age = now - latest_timestamp
        age_minutes = age.total_seconds() / 60
        is_fresh = age_minutes <= threshold_minutes

        return {
            "table": table,
            "status": "FRESH" if is_fresh else "STALE",
            "latest_timestamp": latest_timestamp.isoformat(),
            "age_minutes": round(age_minutes, 2),
            "threshold_minutes": threshold_minutes,
            "is_fresh": is_fresh,
            "message": f"{table} is {'fresh' if is_fresh else 'STALE'} ({age_minutes:.1f} min old)",
        }


@tracer.capture_method
def check_record_counts(conn, table: str, min_expected: int, time_window_hours: int = 24) -> Dict[str, Any]:
    """
    Check if table has expected minimum record count.

    Returns:
        Dict with count status and details
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)

    # Map tables to their timestamp columns for filtering
    timestamp_columns = {
        "listings": "updated_at",
        "sales": "sold_at",
        "price_snapshots": "time",
    }

    timestamp_col = timestamp_columns.get(table, "created_at")

    with conn.cursor() as cur:
        # Count recent records
        cur.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {timestamp_col} >= %s",
            (cutoff,)
        )
        result = cur.fetchone()
        count = result[0] if result else 0

        meets_minimum = count >= min_expected

        return {
            "table": table,
            "status": "SUFFICIENT" if meets_minimum else "LOW",
            "count": count,
            "min_expected": min_expected,
            "time_window_hours": time_window_hours,
            "meets_minimum": meets_minimum,
            "message": f"{table} has {count} records (min: {min_expected})",
        }


@tracer.capture_method
def check_active_listings_by_class(conn) -> Dict[str, Any]:
    """
    Check active listings distribution by class.

    Returns:
        Dict with class distribution status
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT class_, COUNT(*) as count
            FROM listings
            WHERE status = 'active'
            GROUP BY class_
            ORDER BY count DESC
        """)
        results = cur.fetchall()

        class_counts = {row[0]: row[1] for row in results}
        total = sum(class_counts.values())

        # Check if any class has zero listings (potential issue)
        expected_classes = ["Aquatic", "Beast", "Bird", "Bug", "Dawn", "Dusk", "Mech", "Plant", "Reptile"]
        missing_classes = [c for c in expected_classes if c not in class_counts or class_counts.get(c, 0) == 0]

        return {
            "total_active": total,
            "by_class": class_counts,
            "missing_classes": missing_classes,
            "has_all_classes": len(missing_classes) == 0,
            "message": f"{total} active listings across {len(class_counts)} classes",
        }


@tracer.capture_method
def check_ingestion_errors(conn, hours: int = 1) -> Dict[str, Any]:
    """
    Check for recent ingestion errors in logs (if stored in DB).

    For now, this is a placeholder that could be extended to check
    CloudWatch logs or a dedicated error tracking table.
    """
    # This could be extended to query an error_logs table if one exists
    return {
        "status": "OK",
        "message": "Error tracking via CloudWatch Logs",
    }


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for health checks."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting health check at {timestamp}")

    conn = get_db_connection()
    health_results: List[Dict[str, Any]] = []
    overall_healthy = True

    try:
        # Check freshness of each table
        freshness_checks = [
            ("listings", "updated_at"),
            ("sales", "sold_at"),
            ("price_snapshots", "time"),
        ]

        for table, timestamp_col in freshness_checks:
            threshold = FRESHNESS_THRESHOLDS.get(table, 60)
            result = check_table_freshness(conn, table, timestamp_col, threshold)
            health_results.append(result)

            if not result["is_fresh"]:
                overall_healthy = False
                logger.warning(f"Data freshness issue: {result['message']}")

            # Publish metrics
            metrics.add_metric(
                name=f"DataAge_{table}",
                unit=MetricUnit.Count,
                value=result["age_minutes"] if result["age_minutes"] else 999
            )

        # Check record counts
        for table, min_count in MIN_EXPECTED_COUNTS.items():
            time_window = 1 if table == "price_snapshots" else 24
            result = check_record_counts(conn, table, min_count, time_window)
            health_results.append(result)

            if not result["meets_minimum"]:
                overall_healthy = False
                logger.warning(f"Record count issue: {result['message']}")

        # Check listings distribution
        listings_dist = check_active_listings_by_class(conn)
        health_results.append({
            "check": "listings_distribution",
            **listings_dist
        })

        if not listings_dist["has_all_classes"]:
            logger.warning(f"Missing listing classes: {listings_dist['missing_classes']}")

        # Publish overall health metric
        metrics.add_metric(
            name="DataPipelineHealthy",
            unit=MetricUnit.Count,
            value=1 if overall_healthy else 0
        )

    finally:
        conn.close()

    # Build response
    status_code = 200 if overall_healthy else 503
    health_status = "HEALTHY" if overall_healthy else "UNHEALTHY"

    logger.info(
        f"Health check complete: {health_status}",
        extra={
            "overall_healthy": overall_healthy,
            "checks_passed": sum(1 for r in health_results if r.get("is_fresh", r.get("meets_minimum", True))),
            "total_checks": len(health_results),
        }
    )

    return {
        "statusCode": status_code,
        "body": json.dumps({
            "status": health_status,
            "timestamp": timestamp.isoformat(),
            "checks": health_results,
            "summary": {
                "overall_healthy": overall_healthy,
                "checks_run": len(health_results),
            },
        }),
    }
