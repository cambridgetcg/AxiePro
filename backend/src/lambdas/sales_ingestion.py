"""
Sales Ingestion Lambda

Runs every 15 minutes to capture settled marketplace sales.
Fetches from Sky Mavis GraphQL API and stores in Aurora PostgreSQL.
"""
import json
import os
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

import boto3
import httpx
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit

logger = Logger()
tracer = Tracer()
metrics = Metrics()

# Sky Mavis GraphQL endpoint (or proxy URL if configured)
SKYMAVIS_API = os.environ.get(
    "AXIE_PROXY_URL",
    "https://api-gateway.skymavis.com/graphql/marketplace"
)


def get_secrets() -> dict:
    """Retrieve API keys from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    secret_name = os.environ.get("AWS_SECRET_NAME") or os.environ.get("SECRET_NAME")
    if not secret_name:
        raise RuntimeError("AWS_SECRET_NAME or SECRET_NAME environment variable not set")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_db_credentials() -> dict:
    """Retrieve database credentials from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    secret_name = os.environ.get("DATABASE_SECRET_NAME")
    if not secret_name:
        raise RuntimeError("DATABASE_SECRET_NAME environment variable not set")
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_db_connection():
    """Get database connection from secrets and environment variables."""
    credentials = get_db_credentials()
    import psycopg2

    host = os.environ.get("DATABASE_HOST")
    port = os.environ.get("DATABASE_PORT", "5432")
    dbname = os.environ.get("DATABASE_NAME", "axiepro")
    username = credentials.get("username")
    password = credentials.get("password")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=username,
        password=password,
        sslmode="require"
    )


# GraphQL query for recently sold axies with transfer history
SETTLED_AUCTIONS_QUERY = """
query GetSettledAuctions($from: Int!, $size: Int!) {
  settledAuctions {
    axies(from: $from, size: $size, sort: Latest) {
      total
      results {
        id
        class
        transferHistory {
          timestamp
          txHash
          withPrice
          withPriceUsd
          from
          to
        }
      }
    }
  }
}
"""

# Alternative query using recentlyAxiesSold
RECENTLY_SOLD_QUERY = """
query GetRecentlySold($from: Int!, $size: Int!) {
  recentlyAxiesSold(from: $from, size: $size) {
    total
    results {
      id
      class
      order {
        currentPrice
        currentPriceUsd
      }
      transferHistory {
        timestamp
        txHash
        withPrice
        withPriceUsd
        from
        to
      }
    }
  }
}
"""


@tracer.capture_method
async def fetch_settled_sales(
    client: httpx.AsyncClient,
    page_from: int = 0,
    page_size: int = 50,
    api_key: Optional[str] = None,
    internal_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch settled auction sales from Sky Mavis API."""
    variables = {
        "from": page_from,
        "size": page_size,
    }

    headers = {
        "Content-Type": "application/json",
        "Origin": "https://app.axieinfinity.com",
        "User-Agent": "Mozilla/5.0 (compatible; AxiePro/1.0)",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    if internal_secret and os.environ.get("AXIE_PROXY_URL"):
        headers["Authorization"] = f"Bearer {internal_secret}"

    response = await client.post(
        SKYMAVIS_API,
        json={"query": SETTLED_AUCTIONS_QUERY, "variables": variables},
        headers=headers,
    )
    response.raise_for_status()
    return response.json()


@tracer.capture_method
def parse_sales_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parse sales data from GraphQL response.

    Extracts the most recent sale from each axie's transfer history.
    """
    sales = []

    axies_data = (
        response_data.get("data", {})
        .get("settledAuctions", {})
        .get("axies", {})
        .get("results", [])
    )

    for axie in axies_data:
        axie_id = axie.get("id")
        axie_class = axie.get("class", "Unknown")
        transfers = axie.get("transferHistory", [])

        if not axie_id or not transfers:
            continue

        # Find transfers with price (these are sales, not gifts)
        for transfer in transfers:
            price_wei = transfer.get("withPrice")
            if not price_wei:
                continue

            tx_hash = transfer.get("txHash")
            timestamp = transfer.get("timestamp")
            seller = transfer.get("from")
            buyer = transfer.get("to")
            price_usd = transfer.get("withPriceUsd")

            if not all([tx_hash, timestamp, seller, buyer]):
                continue

            # Convert wei to ETH
            try:
                price_eth = Decimal(price_wei) / Decimal(10**18)
            except (ValueError, TypeError):
                logger.warning(f"Invalid price for axie {axie_id}: {price_wei}")
                continue

            # Parse timestamp (Unix timestamp in seconds)
            try:
                sold_at = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
            except (ValueError, TypeError):
                logger.warning(f"Invalid timestamp for axie {axie_id}: {timestamp}")
                continue

            sales.append({
                "axie_id": int(axie_id),
                "class_": axie_class,
                "seller_address": seller.lower() if seller else None,
                "buyer_address": buyer.lower() if buyer else None,
                "price_eth": price_eth,
                "price_usd": Decimal(str(price_usd)) if price_usd else None,
                "tx_hash": tx_hash,
                "sold_at": sold_at,
                "marketplace": "official",
            })

    return sales


@tracer.capture_method
def store_sales(conn, sales: List[Dict[str, Any]]) -> int:
    """
    Store sales in database with deduplication.

    Uses ON CONFLICT DO NOTHING on tx_hash to avoid duplicates.
    Returns the number of new sales inserted.
    """
    if not sales:
        return 0

    inserted = 0

    with conn.cursor() as cur:
        for sale in sales:
            try:
                cur.execute(
                    """
                    INSERT INTO sales (
                        axie_id, seller_address, buyer_address,
                        price_eth, price_usd, tx_hash, sold_at, marketplace
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tx_hash) DO NOTHING
                    """,
                    (
                        sale["axie_id"],
                        sale["seller_address"],
                        sale["buyer_address"],
                        sale["price_eth"],
                        sale["price_usd"],
                        sale["tx_hash"],
                        sale["sold_at"],
                        sale["marketplace"],
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                logger.error(f"Error inserting sale {sale.get('tx_hash')}: {e}")
                continue

        conn.commit()

    return inserted


@tracer.capture_method
def get_cutoff_timestamp(conn, hours: int = 48) -> Optional[datetime]:
    """
    Get the most recent sale timestamp to avoid fetching old data.

    Returns the timestamp of the most recent sale, or a default cutoff.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    with conn.cursor() as cur:
        cur.execute("SELECT MAX(sold_at) FROM sales")
        result = cur.fetchone()
        if result and result[0]:
            # If we have recent data, only go back a bit
            most_recent = result[0]
            if most_recent.tzinfo is None:
                most_recent = most_recent.replace(tzinfo=timezone.utc)
            # Go back 2 hours from most recent to catch any stragglers
            return max(cutoff, most_recent - timedelta(hours=2))

    return cutoff


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics
def handler(event, context):
    """Lambda handler for sales ingestion."""
    timestamp = datetime.now(timezone.utc)
    logger.info(f"Starting sales ingestion at {timestamp}")

    async def ingest():
        conn = get_db_connection()
        secrets = get_secrets()
        api_key = secrets.get("SKYMAVIS_API_KEY")
        internal_secret = secrets.get("INTERNAL_SECRET")
        using_proxy = bool(os.environ.get("AXIE_PROXY_URL"))

        logger.info(f"Using API key: {api_key[:8]}..." if api_key else "No API key found!")
        logger.info(f"Using proxy: {using_proxy}, endpoint: {SKYMAVIS_API}")

        total_inserted = 0
        total_fetched = 0
        pages_fetched = 0
        max_pages = 10  # Limit to prevent runaway fetching
        page_size = 100

        try:
            cutoff = get_cutoff_timestamp(conn)
            logger.info(f"Fetching sales since {cutoff}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                page_from = 0

                while pages_fetched < max_pages:
                    try:
                        result = await fetch_settled_sales(
                            client,
                            page_from=page_from,
                            page_size=page_size,
                            api_key=api_key,
                            internal_secret=internal_secret,
                        )

                        sales = parse_sales_from_response(result)
                        total_fetched += len(sales)

                        if not sales:
                            logger.info(f"No more sales found at page {pages_fetched}")
                            break

                        # Filter to only recent sales
                        recent_sales = [s for s in sales if s["sold_at"] >= cutoff]

                        if not recent_sales:
                            logger.info(f"No sales after cutoff at page {pages_fetched}")
                            break

                        inserted = store_sales(conn, recent_sales)
                        total_inserted += inserted
                        pages_fetched += 1

                        logger.info(
                            f"Page {pages_fetched}: fetched {len(sales)}, "
                            f"recent {len(recent_sales)}, inserted {inserted}"
                        )

                        # If we inserted fewer than expected, we might be hitting duplicates
                        if inserted == 0 and pages_fetched > 1:
                            logger.info("No new sales inserted, stopping pagination")
                            break

                        page_from += page_size

                    except httpx.HTTPStatusError as e:
                        logger.error(f"HTTP error fetching page {pages_fetched}: {e}")
                        metrics.add_metric(name="IngestionHTTPErrors", unit=MetricUnit.Count, value=1)
                        break
                    except Exception as e:
                        logger.error(f"Error fetching page {pages_fetched}: {e}")
                        metrics.add_metric(name="IngestionErrors", unit=MetricUnit.Count, value=1)
                        break

        finally:
            conn.close()

        return {
            "total_fetched": total_fetched,
            "total_inserted": total_inserted,
            "pages_fetched": pages_fetched,
        }

    result = asyncio.get_event_loop().run_until_complete(ingest())

    metrics.add_metric(name="SalesFetched", unit=MetricUnit.Count, value=result["total_fetched"])
    metrics.add_metric(name="SalesInserted", unit=MetricUnit.Count, value=result["total_inserted"])
    metrics.add_metric(name="PagesFetched", unit=MetricUnit.Count, value=result["pages_fetched"])

    logger.info(
        f"Sales ingestion complete: fetched {result['total_fetched']}, "
        f"inserted {result['total_inserted']} from {result['pages_fetched']} pages"
    )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Sales ingestion complete",
            "sales_fetched": result["total_fetched"],
            "sales_inserted": result["total_inserted"],
            "pages_fetched": result["pages_fetched"],
            "timestamp": timestamp.isoformat(),
        }),
    }
