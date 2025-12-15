"""
Deal Detector Lambda

Triggered by Kinesis stream for real-time deal detection.
Identifies undervalued Axies by comparing listing prices to market averages.
"""
import json
import os
import base64
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Deal thresholds
DEAL_THRESHOLD_PERCENT = 20  # 20% below average = deal
SNIPE_THRESHOLD_PERCENT = 40  # 40% below = snipe opportunity
MIN_DISCOUNT_ETH = Decimal("0.001")  # Minimum discount to qualify


def get_secrets() -> dict:
    """Retrieve secrets from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    response = client.get_secret_value(SecretId=os.environ["SECRET_NAME"])
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection."""
    secrets = get_secrets()
    import psycopg2
    return psycopg2.connect(secrets["DATABASE_URL"])


def get_redis_client():
    """Get Redis client for caching."""
    secrets = get_secrets()
    if "REDIS_URL" not in secrets:
        return None
    import redis
    return redis.from_url(secrets["REDIS_URL"])


@tracer.capture_method
def get_recent_average(conn, trait_key: str, axie_class: str, hours: int = 24) -> Optional[Decimal]:
    """Get recent average price for a trait."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT AVG(avg_eth) as avg_price
            FROM price_snapshots
            WHERE trait_key = %s
              AND class = %s
              AND time >= NOW() - INTERVAL '%s hours'
              AND avg_eth IS NOT NULL
            """,
            (trait_key, axie_class, hours),
        )
        row = cur.fetchone()
        return Decimal(str(row[0])) if row and row[0] else None


@tracer.capture_method
def get_floor_price(conn, trait_key: str, axie_class: str) -> Optional[Decimal]:
    """Get most recent floor price for a trait."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT floor_eth
            FROM price_snapshots
            WHERE trait_key = %s
              AND class = %s
              AND floor_eth IS NOT NULL
            ORDER BY time DESC
            LIMIT 1
            """,
            (trait_key, axie_class),
        )
        row = cur.fetchone()
        return Decimal(str(row[0])) if row and row[0] else None


@tracer.capture_method
def analyze_listing(conn, listing: dict) -> Optional[dict]:
    """Analyze a new listing for deal potential."""
    axie_id = listing.get("axie_id")
    axie_class = listing.get("class", "").lower()
    price_eth = Decimal(str(listing.get("price_eth", 0)))
    parts = listing.get("parts", [])

    if not axie_id or not axie_class or price_eth <= 0:
        return None

    # Check class-level pricing
    class_avg = get_recent_average(conn, f"class:{axie_class}", axie_class)
    class_floor = get_floor_price(conn, f"class:{axie_class}", axie_class)

    if not class_avg:
        return None

    discount_percent = ((class_avg - price_eth) / class_avg) * 100

    # Check if it's a deal
    if discount_percent < DEAL_THRESHOLD_PERCENT:
        return None

    # Check part-level pricing for better accuracy
    part_discounts = []
    for part in parts:
        part_id = part.get("id")
        if not part_id:
            continue

        part_avg = get_recent_average(conn, f"part:{part_id}", axie_class)
        if part_avg and part_avg > 0:
            part_discount = ((part_avg - price_eth) / part_avg) * 100
            part_discounts.append({
                "part_id": part_id,
                "part_name": part.get("name"),
                "avg_price": float(part_avg),
                "discount_percent": float(part_discount),
            })

    # Calculate deal score (0-100)
    deal_score = min(100, int(discount_percent * 1.5))

    # Boost score for rare parts with high discounts
    if part_discounts:
        best_part_discount = max(p["discount_percent"] for p in part_discounts)
        if best_part_discount > 30:
            deal_score = min(100, deal_score + 10)

    is_snipe = discount_percent >= SNIPE_THRESHOLD_PERCENT

    return {
        "axie_id": axie_id,
        "class": axie_class,
        "price_eth": float(price_eth),
        "class_avg_eth": float(class_avg),
        "class_floor_eth": float(class_floor) if class_floor else None,
        "discount_percent": float(discount_percent),
        "deal_score": deal_score,
        "is_snipe": is_snipe,
        "part_analysis": part_discounts,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


@tracer.capture_method
def store_deal(conn, deal: dict):
    """Store detected deal in database."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO detected_deals (
                axie_id, class, price_eth, avg_eth, discount_percent,
                deal_score, is_snipe, part_analysis, detected_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (axie_id, detected_at) DO NOTHING
            """,
            (
                deal["axie_id"],
                deal["class"],
                deal["price_eth"],
                deal["class_avg_eth"],
                deal["discount_percent"],
                deal["deal_score"],
                deal["is_snipe"],
                json.dumps(deal["part_analysis"]),
                deal["detected_at"],
            ),
        )
    conn.commit()


@tracer.capture_method
def notify_deal(deal: dict):
    """Send notification for high-value deals."""
    if deal["deal_score"] < 70:
        return

    # Publish to SNS for notifications
    sns = boto3.client("sns", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    topic_arn = os.environ.get("DEAL_ALERT_TOPIC_ARN")

    if not topic_arn:
        logger.warning("No SNS topic configured for deal alerts")
        return

    message = {
        "type": "SNIPE_ALERT" if deal["is_snipe"] else "DEAL_ALERT",
        "axie_id": deal["axie_id"],
        "class": deal["class"],
        "price_eth": deal["price_eth"],
        "discount_percent": deal["discount_percent"],
        "deal_score": deal["deal_score"],
        "marketplace_url": f"https://app.axieinfinity.com/marketplace/axies/{deal['axie_id']}",
    }

    sns.publish(
        TopicArn=topic_arn,
        Message=json.dumps(message),
        Subject=f"{'🔥 SNIPE' if deal['is_snipe'] else '💰 Deal'}: Axie #{deal['axie_id']} - {deal['discount_percent']:.1f}% off",
    )

    metrics.add_metric(name="DealNotificationsSent", unit=MetricUnit.Count, value=1)


@tracer.capture_method
def cache_deal(redis_client, deal: dict):
    """Cache deal in Redis for quick frontend access."""
    if not redis_client:
        return

    # Add to sorted set of recent deals (scored by deal_score)
    key = f"deals:{deal['class']}"
    redis_client.zadd(key, {json.dumps(deal): deal["deal_score"]})

    # Trim to keep only top 100 deals per class
    redis_client.zremrangebyrank(key, 0, -101)

    # Also add to global snipes if applicable
    if deal["is_snipe"]:
        redis_client.zadd("snipes:all", {json.dumps(deal): deal["deal_score"]})
        redis_client.zremrangebyrank("snipes:all", 0, -51)

    # Set TTL on deal keys (24 hours)
    redis_client.expire(key, 86400)
    redis_client.expire("snipes:all", 86400)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for deal detection from Kinesis stream."""
    logger.info(f"Processing {len(event.get('Records', []))} Kinesis records")

    conn = get_db_connection()
    redis_client = get_redis_client()

    deals_found = 0
    snipes_found = 0
    errors = 0

    try:
        for record in event.get("Records", []):
            try:
                # Decode Kinesis record
                payload = base64.b64decode(record["kinesis"]["data"])
                listing = json.loads(payload)

                # Analyze listing
                deal = analyze_listing(conn, listing)

                if deal:
                    deals_found += 1
                    if deal["is_snipe"]:
                        snipes_found += 1

                    # Store, cache, and notify
                    store_deal(conn, deal)
                    cache_deal(redis_client, deal)
                    notify_deal(deal)

                    logger.info(f"Deal detected: Axie #{deal['axie_id']} - {deal['discount_percent']:.1f}% off")

            except Exception as e:
                logger.error(f"Error processing record: {e}")
                errors += 1

    finally:
        conn.close()
        if redis_client:
            redis_client.close()

    metrics.add_metric(name="DealsFound", unit=MetricUnit.Count, value=deals_found)
    metrics.add_metric(name="SnipesFound", unit=MetricUnit.Count, value=snipes_found)
    metrics.add_metric(name="ProcessingErrors", unit=MetricUnit.Count, value=errors)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "records_processed": len(event.get("Records", [])),
            "deals_found": deals_found,
            "snipes_found": snipes_found,
            "errors": errors,
        }),
    }
