"""
Meta Analyzer Lambda

Runs hourly to detect meta shifts by analyzing price velocity,
volume changes, and trait popularity trends.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Optional

import boto3
from aws_lambda_powertools.metrics import MetricUnit

# Import shared utilities from common module
from src.lambdas.common import (
    logger,
    tracer,
    metrics,
    get_db_connection,
    get_redis_client,
    cache_meta_insights,
    PRICE_VELOCITY_THRESHOLD,
    VOLUME_SPIKE_THRESHOLD,
    EMERGING_META_THRESHOLD,
)


@tracer.capture_method
def get_price_velocity(conn, trait_key: str, hours: int = 24) -> Optional[dict]:
    """Calculate price velocity (rate of change) for a trait."""
    with conn.cursor() as cur:
        # Get current vs historical average
        cur.execute(
            """
            WITH current_price AS (
                SELECT AVG(floor_eth) as price
                FROM price_snapshots
                WHERE trait_key = %s
                  AND time >= NOW() - INTERVAL '2 hours'
                  AND floor_eth IS NOT NULL
            ),
            past_price AS (
                SELECT AVG(floor_eth) as price
                FROM price_snapshots
                WHERE trait_key = %s
                  AND time >= NOW() - INTERVAL '%s hours'
                  AND time < NOW() - INTERVAL '%s hours' + INTERVAL '2 hours'
                  AND floor_eth IS NOT NULL
            )
            SELECT
                c.price as current_price,
                p.price as past_price,
                CASE WHEN p.price > 0
                    THEN ((c.price - p.price) / p.price) * 100
                    ELSE NULL
                END as velocity_percent
            FROM current_price c, past_price p
            """,
            (trait_key, trait_key, hours, hours),
        )
        row = cur.fetchone()

        if not row or row[2] is None:
            return None

        return {
            "current_price": float(row[0]) if row[0] else None,
            "past_price": float(row[1]) if row[1] else None,
            "velocity_percent": float(row[2]),
            "period_hours": hours,
        }


@tracer.capture_method
def get_volume_change(conn, trait_key: str, hours: int = 24) -> Optional[dict]:
    """Calculate volume change for a trait."""
    with conn.cursor() as cur:
        cur.execute(
            """
            WITH current_volume AS (
                SELECT SUM(listings_count) as volume
                FROM price_snapshots
                WHERE trait_key = %s
                  AND time >= NOW() - INTERVAL '%s hours'
            ),
            past_volume AS (
                SELECT SUM(listings_count) as volume
                FROM price_snapshots
                WHERE trait_key = %s
                  AND time >= NOW() - INTERVAL '%s hours' * 2
                  AND time < NOW() - INTERVAL '%s hours'
            )
            SELECT
                c.volume as current_volume,
                p.volume as past_volume,
                CASE WHEN p.volume > 0
                    THEN ((c.volume - p.volume)::float / p.volume) * 100
                    ELSE NULL
                END as change_percent
            FROM current_volume c, past_volume p
            """,
            (trait_key, hours, trait_key, hours, hours),
        )
        row = cur.fetchone()

        if not row or row[2] is None:
            return None

        return {
            "current_volume": int(row[0]) if row[0] else 0,
            "past_volume": int(row[1]) if row[1] else 0,
            "change_percent": float(row[2]),
            "period_hours": hours,
        }


@tracer.capture_method
def detect_meta_shifts(conn) -> List[Dict]:
    """Detect meta shifts across all tracked traits."""
    meta_shifts = []

    # Get all unique traits being tracked
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT trait_key, class
            FROM price_snapshots
            WHERE time >= NOW() - INTERVAL '7 days'
            """
        )
        traits = cur.fetchall()

    for trait_key, axie_class in traits:
        # Check 24h price velocity
        velocity_24h = get_price_velocity(conn, trait_key, 24)
        # Check 7d price trend
        velocity_7d = get_price_velocity(conn, trait_key, 168)
        # Check volume changes
        volume_change = get_volume_change(conn, trait_key, 24)

        shift_type = None
        confidence = 0
        signals = []

        # Rapid price increase (potential pump)
        if velocity_24h and velocity_24h["velocity_percent"] > PRICE_VELOCITY_THRESHOLD:
            signals.append(f"24h price +{velocity_24h['velocity_percent']:.1f}%")
            confidence += 30
            shift_type = "rising"

        # Rapid price decrease (potential dump or meta shift away)
        if velocity_24h and velocity_24h["velocity_percent"] < -PRICE_VELOCITY_THRESHOLD:
            signals.append(f"24h price {velocity_24h['velocity_percent']:.1f}%")
            confidence += 30
            shift_type = "falling"

        # Volume spike (high activity)
        if volume_change and volume_change["change_percent"] > VOLUME_SPIKE_THRESHOLD:
            signals.append(f"Volume +{volume_change['change_percent']:.1f}%")
            confidence += 25

        # Emerging meta (sustained 7d increase)
        if velocity_7d and velocity_7d["velocity_percent"] > EMERGING_META_THRESHOLD:
            signals.append(f"7d trend +{velocity_7d['velocity_percent']:.1f}%")
            confidence += 20
            if not shift_type:
                shift_type = "emerging"

        # Fading meta (sustained 7d decrease)
        if velocity_7d and velocity_7d["velocity_percent"] < -EMERGING_META_THRESHOLD:
            signals.append(f"7d trend {velocity_7d['velocity_percent']:.1f}%")
            confidence += 20
            if not shift_type:
                shift_type = "fading"

        if shift_type and confidence >= 25:
            meta_shifts.append({
                "trait_key": trait_key,
                "class": axie_class,
                "shift_type": shift_type,
                "confidence": min(100, confidence),
                "signals": signals,
                "price_velocity_24h": velocity_24h,
                "price_velocity_7d": velocity_7d,
                "volume_change": volume_change,
                "detected_at": datetime.now(timezone.utc).isoformat(),
            })

    # Sort by confidence
    meta_shifts.sort(key=lambda x: x["confidence"], reverse=True)

    return meta_shifts


@tracer.capture_method
def store_meta_shifts(conn, shifts: List[Dict]):
    """Store detected meta shifts."""
    with conn.cursor() as cur:
        for shift in shifts:
            cur.execute(
                """
                INSERT INTO meta_shifts (
                    trait_key, class, shift_type, confidence, signals,
                    velocity_24h, velocity_7d, volume_change_24h, detected_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    shift["trait_key"],
                    shift["class"],
                    shift["shift_type"],
                    shift["confidence"],
                    json.dumps(shift["signals"]),
                    shift["price_velocity_24h"]["velocity_percent"] if shift["price_velocity_24h"] else None,
                    shift["price_velocity_7d"]["velocity_percent"] if shift["price_velocity_7d"] else None,
                    shift["volume_change"]["change_percent"] if shift["volume_change"] else None,
                    shift["detected_at"],
                ),
            )
    conn.commit()


@tracer.capture_method
def publish_insights(shifts: List[Dict]):
    """Publish meta insights to SNS for downstream consumers."""
    if not shifts:
        return

    sns = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    topic_arn = os.environ.get("META_INSIGHTS_TOPIC_ARN")

    if not topic_arn:
        logger.warning("No SNS topic configured for meta insights")
        return

    # Publish top shifts
    top_shifts = shifts[:10]

    message = {
        "type": "META_ANALYSIS",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "shifts_detected": len(shifts),
        "top_shifts": top_shifts,
    }

    sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
        Subject=f"Meta Analysis: {len(shifts)} shifts detected",
    )


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for meta analysis."""
    logger.info("Starting meta analysis")

    conn = get_db_connection()
    redis_client = get_redis_client()

    try:
        # Detect meta shifts
        shifts = detect_meta_shifts(conn)

        logger.info(f"Detected {len(shifts)} meta shifts")

        # Store results
        if shifts:
            store_meta_shifts(conn, shifts)
            publish_insights(shifts)

            # Cache in Redis
            summary = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_shifts": len(shifts),
                "rising": len([s for s in shifts if s["shift_type"] == "rising"]),
                "falling": len([s for s in shifts if s["shift_type"] == "falling"]),
                "emerging": len([s for s in shifts if s["shift_type"] == "emerging"]),
                "fading": len([s for s in shifts if s["shift_type"] == "fading"]),
            }
            cache_meta_insights(redis_client, shifts, summary)

        # Log metrics
        metrics.add_metric(name="MetaShiftsDetected", unit=MetricUnit.Count, value=len(shifts))

        for shift_type in ["rising", "falling", "emerging", "fading"]:
            count = len([s for s in shifts if s["shift_type"] == shift_type])
            metrics.add_metric(name=f"MetaShifts_{shift_type}", unit=MetricUnit.Count, value=count)

    finally:
        conn.close()
        if redis_client:
            redis_client.close()

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Meta analysis complete",
            "shifts_detected": len(shifts),
            "top_shifts": shifts[:5] if shifts else [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
    }
