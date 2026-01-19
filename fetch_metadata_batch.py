#!/usr/bin/env python3
"""
High-throughput Axie metadata fetcher using batch GraphQL queries.

Features:
- Batch queries (up to 20 axies per request)
- Async HTTP with httpx
- Queue-based workflow integration
- Progress tracking and checkpointing
- Robust error handling with retry logic

Usage:
    python3 fetch_metadata_batch.py                  # Process queue
    python3 fetch_metadata_batch.py --test           # Test with 10 axies
    python3 fetch_metadata_batch.py --populate       # Populate queue first
    python3 fetch_metadata_batch.py --status         # Show queue status
"""

import asyncio
import argparse
import json
import subprocess
import sys
import signal
import time
from datetime import datetime
from typing import Optional

try:
    import httpx
except ImportError:
    print("Error: httpx required. Install with: pip3 install httpx")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 required. Install with: pip3 install psycopg2-binary")
    sys.exit(1)

# Configuration
BATCH_SIZE = 20  # Axies per GraphQL request
REQUEST_DELAY = 0.2  # Seconds between requests
GRAPHQL_URL = 'https://api-gateway.skymavis.com/graphql/marketplace'
PROGRESS_INTERVAL = 30  # Seconds between progress reports
CHECKPOINT_INTERVAL = 100  # Axies between checkpoints

# Graceful shutdown
shutdown_requested = False

def handle_signal(sig, frame):
    global shutdown_requested
    print("\n[SHUTDOWN] Graceful shutdown requested...")
    shutdown_requested = True

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)


def get_secrets():
    """Get API key and DB config from AWS Secrets Manager."""
    result = subprocess.run([
        'aws', 'secretsmanager', 'get-secret-value',
        '--secret-id', 'axie-explorer/api-keys',
        '--query', 'SecretString', '--output', 'text',
        '--region', 'us-east-1'
    ], capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Failed to get secrets: {result.stderr}")

    return json.loads(result.stdout)


def get_db_connection(secrets):
    """Create database connection."""
    conn = psycopg2.connect(
        host=secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        port=5432,
        dbname=secrets.get('RDS_DATABASE', 'postgres'),
        user=secrets.get('RDS_USER', 'postgres'),
        password=secrets.get('RDS_PASSWORD', '12345Cardforum')
    )
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")
    conn.commit()
    return conn


def build_batch_query(axie_ids: list[int]) -> str:
    """Build GraphQL query for multiple axies."""
    query_parts = []
    for i, axie_id in enumerate(axie_ids):
        query_parts.append(f'''
            axie{i}: axie(axieId: "{axie_id}") {{
                id
                name
                class
                breedCount
                genes
                image
                owner
                birthDate
                stats {{ hp speed skill morale }}
                parts {{
                    id
                    name
                    class
                    type
                    specialGenes
                }}
            }}
        ''')

    return "{ " + " ".join(query_parts) + " }"


def count_pure_parts(axie_class: str, parts: list) -> int:
    """Count parts matching the Axie's class."""
    if not parts or not axie_class:
        return 0
    return sum(1 for p in parts if p.get('class') == axie_class)


def get_part_by_type(parts: list, part_type: str) -> Optional[str]:
    """Get part ID by type."""
    if not parts:
        return None
    for p in parts:
        if p.get('type') == part_type:
            return p.get('id')
    return None


def insert_metadata(cur, axie_id: int, axie: dict) -> tuple:
    """Insert or update Axie metadata."""
    parts = axie.get('parts', [])
    stats = axie.get('stats', {})
    axie_class = axie.get('class')
    pure_count = count_pure_parts(axie_class, parts)

    cur.execute("""
        INSERT INTO axie_metadata (
            axie_id, name, class, breed_count, genes,
            hp, speed, skill, morale,
            parts_json,
            part_eyes, part_ears, part_mouth, part_horn, part_back, part_tail,
            pure_part_count, birth_date, image_url, owner
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s,
            %s, %s, %s, %s, %s, %s,
            %s, to_timestamp(%s), %s, %s
        )
        ON CONFLICT (axie_id) DO UPDATE SET
            name = EXCLUDED.name,
            breed_count = EXCLUDED.breed_count,
            owner = EXCLUDED.owner,
            updated_at = NOW()
    """, (
        axie_id,
        axie.get('name'),
        axie_class,
        axie.get('breedCount'),
        axie.get('genes'),
        stats.get('hp'),
        stats.get('speed'),
        stats.get('skill'),
        stats.get('morale'),
        json.dumps(parts),
        get_part_by_type(parts, 'Eyes'),
        get_part_by_type(parts, 'Ears'),
        get_part_by_type(parts, 'Mouth'),
        get_part_by_type(parts, 'Horn'),
        get_part_by_type(parts, 'Back'),
        get_part_by_type(parts, 'Tail'),
        pure_count,
        axie.get('birthDate'),
        axie.get('image'),
        axie.get('owner')
    ))

    return axie_class, pure_count


async def fetch_batch(client: httpx.AsyncClient, api_key: str, axie_ids: list[int]) -> dict:
    """Fetch multiple axies in one GraphQL request."""
    query = build_batch_query(axie_ids)

    try:
        response = await client.post(
            GRAPHQL_URL,
            json={"query": query},
            headers={'X-API-Key': api_key, 'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"[RATE LIMITED] Waiting {retry_after}s...")
            await asyncio.sleep(retry_after)
            return await fetch_batch(client, api_key, axie_ids)

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text[:200]}")

        data = response.json()

        if 'errors' in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        result = {}
        for i, axie_id in enumerate(axie_ids):
            result[axie_id] = data.get('data', {}).get(f'axie{i}')

        return result

    except httpx.RequestError as e:
        raise Exception(f"Request error: {e}")


def get_queue_status(conn) -> dict:
    """Get current queue status."""
    cur = conn.cursor()
    cur.execute("""
        SELECT status, COUNT(*)
        FROM metadata_fetch_queue
        GROUP BY status
        ORDER BY status
    """)
    return dict(cur.fetchall())


def populate_queue(conn, limit: Optional[int] = None):
    """Populate queue with axies missing metadata."""
    cur = conn.cursor()

    # Count how many need to be added
    cur.execute("""
        SELECT COUNT(DISTINCT s.axie_id)
        FROM axie_sales s
        WHERE NOT EXISTS (SELECT 1 FROM axie_metadata m WHERE m.axie_id = s.axie_id)
          AND NOT EXISTS (SELECT 1 FROM metadata_fetch_queue q WHERE q.axie_id = s.axie_id)
    """)
    to_add = cur.fetchone()[0]
    print(f"Axies to add to queue: {to_add:,}")

    if to_add == 0:
        print("Queue already populated.")
        return

    # Insert with limit
    limit_clause = f"LIMIT {limit}" if limit else ""
    cur.execute(f"""
        INSERT INTO metadata_fetch_queue (axie_id, first_seen_in, priority, status)
        SELECT DISTINCT s.axie_id, 'backfill', 5, 'pending'
        FROM axie_sales s
        WHERE NOT EXISTS (SELECT 1 FROM axie_metadata m WHERE m.axie_id = s.axie_id)
          AND NOT EXISTS (SELECT 1 FROM metadata_fetch_queue q WHERE q.axie_id = s.axie_id)
        {limit_clause}
        ON CONFLICT (axie_id) DO NOTHING
    """)
    added = cur.rowcount
    conn.commit()
    print(f"Added {added:,} axies to queue.")


async def process_queue(conn, api_key: str, test_mode: bool = False):
    """Main processing loop."""
    global shutdown_requested

    cur = conn.cursor()

    # Get pending count
    cur.execute("SELECT COUNT(*) FROM metadata_fetch_queue WHERE status = 'pending'")
    total_pending = cur.fetchone()[0]

    if total_pending == 0:
        print("No pending axies in queue.")
        return

    limit = 10 if test_mode else total_pending
    print(f"Processing {'up to 10 (test mode)' if test_mode else f'{total_pending:,}'} pending axies...")
    print(f"Batch size: {BATCH_SIZE} | Request delay: {REQUEST_DELAY}s")
    print()

    stats = {'completed': 0, 'not_found': 0, 'failed': 0}
    t0 = time.time()
    last_progress = t0

    async with httpx.AsyncClient(timeout=30) as client:
        while not shutdown_requested:
            # Get batch from queue
            batch_size = min(BATCH_SIZE, limit - stats['completed'] - stats['not_found'] - stats['failed'])
            if batch_size <= 0:
                break

            cur.execute("SELECT * FROM get_fetch_batch(%s)", (batch_size,))
            batch = [row[0] for row in cur.fetchall()]

            if not batch:
                break

            try:
                # Fetch metadata for batch
                await asyncio.sleep(REQUEST_DELAY)
                results = await fetch_batch(client, api_key, batch)

                # Process each result
                for axie_id, axie_data in results.items():
                    if axie_data:
                        try:
                            axie_class, pure_count = insert_metadata(cur, axie_id, axie_data)
                            cur.execute("CALL process_metadata_complete(%s)", (axie_id,))
                            stats['completed'] += 1

                            if test_mode:
                                print(f"  #{axie_id}: {axie_class} | Breed:{axie_data.get('breedCount')} | Pure:{pure_count}/6")

                        except Exception as e:
                            conn.rollback()
                            cur.execute("SET search_path TO axie, public")
                            cur.execute("SELECT mark_fetch_failed(%s, %s, %s)",
                                        (axie_id, str(e)[:200], False))
                            stats['failed'] += 1
                            if test_mode:
                                print(f"  #{axie_id}: ERROR - {str(e)[:50]}")
                    else:
                        cur.execute("SELECT mark_fetch_failed(%s, %s, %s)",
                                    (axie_id, "Axie not found", True))
                        stats['not_found'] += 1
                        if test_mode:
                            print(f"  #{axie_id}: NOT FOUND")

                conn.commit()

            except Exception as e:
                # Batch-level error - mark all as failed
                conn.rollback()
                cur.execute("SET search_path TO axie, public")
                for axie_id in batch:
                    cur.execute("SELECT mark_fetch_failed(%s, %s, %s)",
                                (axie_id, str(e)[:200], False))
                    stats['failed'] += 1
                conn.commit()
                print(f"[BATCH ERROR] {e}")

            # Progress report
            now = time.time()
            if now - last_progress >= PROGRESS_INTERVAL or test_mode:
                elapsed = now - t0
                processed = stats['completed'] + stats['not_found'] + stats['failed']
                rate = processed / elapsed if elapsed > 0 else 0

                if not test_mode:
                    remaining = total_pending - processed
                    eta = remaining / rate / 60 if rate > 0 else 0
                    print(f"[{processed:,}/{total_pending:,}] "
                          f"{processed/total_pending*100:.1f}% | "
                          f"{rate:.1f} axies/s | "
                          f"ETA: {eta:.1f}m")

                last_progress = now

    # Summary
    elapsed = time.time() - t0
    print()
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Completed: {stats['completed']:,}")
    print(f"Not Found: {stats['not_found']:,}")
    print(f"Failed: {stats['failed']:,}")
    print(f"Time: {elapsed:.1f}s")
    print(f"Rate: {(stats['completed'] + stats['not_found']) / elapsed:.1f} axies/s")

    if shutdown_requested:
        print("\n[SHUTDOWN] Stopped gracefully. Run again to continue.")


def show_status(conn):
    """Show current queue and metadata status."""
    cur = conn.cursor()

    print("=" * 50)
    print("METADATA FETCH STATUS")
    print("=" * 50)

    # Queue status
    print("\nQueue Status:")
    status = get_queue_status(conn)
    for s, count in sorted(status.items()):
        print(f"  {s}: {count:,}")

    # Metadata coverage
    cur.execute("""
        SELECT
            COUNT(DISTINCT s.axie_id) as total,
            COUNT(DISTINCT m.axie_id) as with_metadata
        FROM axie_sales s
        LEFT JOIN axie_metadata m ON s.axie_id = m.axie_id
    """)
    total, with_meta = cur.fetchone()
    pct = with_meta / total * 100 if total > 0 else 0

    print(f"\nMetadata Coverage:")
    print(f"  Total unique axies: {total:,}")
    print(f"  With metadata: {with_meta:,}")
    print(f"  Coverage: {pct:.1f}%")


async def main():
    parser = argparse.ArgumentParser(description='Batch Axie metadata fetcher')
    parser.add_argument('--test', action='store_true', help='Test mode - process 10 axies only')
    parser.add_argument('--populate', action='store_true', help='Populate queue with missing axies')
    parser.add_argument('--populate-limit', type=int, help='Limit for populate')
    parser.add_argument('--status', action='store_true', help='Show queue status')
    args = parser.parse_args()

    print("=" * 50)
    print("AXIE METADATA BATCH FETCHER")
    print("=" * 50)

    # Get secrets
    print("Loading configuration...")
    secrets = get_secrets()
    api_key = secrets.get('SKYMAVIS_API_KEY')

    if not api_key:
        print("ERROR: SKYMAVIS_API_KEY not found in secrets")
        sys.exit(1)

    # Connect to DB
    print("Connecting to database...")
    conn = get_db_connection(secrets)

    try:
        if args.status:
            show_status(conn)
        elif args.populate:
            populate_queue(conn, args.populate_limit)
        else:
            # Show status first
            status = get_queue_status(conn)
            print(f"\nQueue: {status}")

            if args.test:
                print("\n[TEST MODE] Processing up to 10 axies...")

            await process_queue(conn, api_key, test_mode=args.test)

    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
