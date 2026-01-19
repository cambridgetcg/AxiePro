#!/usr/bin/env python3
"""Fetch Axie metadata using the queue-based workflow.

Workflow:
1. Get batch from metadata_fetch_queue (pending or retry)
2. Fetch details from GraphQL API
3. Insert into axie_metadata
4. Call process_metadata_complete() to:
   - Mark queue as completed
   - Backfill denormalized columns in axie_sales
   - Populate parts mapping table
"""

import json
import subprocess
import urllib.request
import psycopg2
import time
from datetime import datetime

# Get API key
result = subprocess.run(['aws', 'secretsmanager', 'get-secret-value', '--secret-id', 'axie-explorer/api-keys', '--query', 'SecretString', '--output', 'text'], capture_output=True, text=True)
secrets = json.loads(result.stdout)
api_key = secrets.get('SKYMAVIS_API_KEY', '')

gql_url = 'https://api-gateway.skymavis.com/graphql/marketplace'
headers = {'X-API-Key': api_key, 'Content-Type': 'application/json'}

DB_CONFIG = {
    'host': secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
    'port': 5432,
    'dbname': secrets.get('RDS_DATABASE', 'postgres'),
    'user': secrets.get('RDS_USER', 'postgres'),
    'password': secrets.get('RDS_PASSWORD', '12345Cardforum')
}


def gql_call(query):
    req = urllib.request.Request(gql_url, data=json.dumps({"query": query}).encode(), headers=headers)
    response = urllib.request.urlopen(req, timeout=30)
    return json.loads(response.read())


def fetch_axie_details(axie_id):
    """Fetch single Axie details from GraphQL."""
    query = f'''{{
        axie(axieId: "{axie_id}") {{
            id
            name
            class
            breedCount
            genes
            image
            birthDate
            owner
            stats {{ hp speed skill morale }}
            parts {{
                id
                name
                class
                type
                specialGenes
            }}
        }}
    }}'''

    try:
        result = gql_call(query)
        return result.get('data', {}).get('axie')
    except Exception as e:
        raise Exception(f"GraphQL error: {e}")


def count_pure_parts(axie_class, parts):
    """Count parts matching the Axie's class."""
    if not parts or not axie_class:
        return 0
    return sum(1 for p in parts if p.get('class') == axie_class)


def get_part_by_type(parts, part_type):
    """Get part ID by type."""
    if not parts:
        return None
    for p in parts:
        if p.get('type') == part_type:
            return p.get('id')
    return None


def get_pending_batch(cur, batch_size=50):
    """Get batch of pending Axies from queue."""
    cur.execute("SELECT * FROM get_fetch_batch(%s)", (batch_size,))
    return [row[0] for row in cur.fetchall()]


def get_retry_batch(cur, batch_size=20):
    """Get batch of failed Axies ready for retry."""
    cur.execute("SELECT * FROM get_retry_batch(%s)", (batch_size,))
    return [row[0] for row in cur.fetchall()]


def insert_metadata(cur, axie_id, axie):
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


def process_batch(conn, cur, axie_ids, stats):
    """Process a batch of Axie IDs."""
    for axie_id in axie_ids:
        print(f"  Fetching #{axie_id}...", end=" ")

        try:
            axie = fetch_axie_details(axie_id)

            if not axie:
                # Axie not found (burned/invalid)
                cur.execute("SELECT mark_fetch_failed(%s, %s, %s)", (axie_id, "Axie not found", True))
                conn.commit()
                print("NOT FOUND")
                stats['not_found'] += 1
                continue

            # Insert metadata
            axie_class, pure_count = insert_metadata(cur, axie_id, axie)

            # Complete workflow (backfill sales, populate parts mapping)
            cur.execute("CALL process_metadata_complete(%s)", (axie_id,))
            conn.commit()

            print(f"{axie_class} | Breed:{axie.get('breedCount')} | Pure:{pure_count}/6")
            stats['completed'] += 1

        except Exception as e:
            conn.rollback()
            error_msg = str(e)[:200]
            cur.execute("SELECT mark_fetch_failed(%s, %s, %s)", (axie_id, error_msg, False))
            conn.commit()
            print(f"FAILED: {error_msg[:50]}")
            stats['failed'] += 1

        # Rate limiting
        time.sleep(0.1)


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SET search_path TO axie, public")

    print("=" * 60)
    print("AXIE METADATA FETCHER (Queue-Based Workflow)")
    print("=" * 60)

    # Show queue status
    cur.execute("SELECT status, COUNT(*) FROM metadata_fetch_queue GROUP BY status ORDER BY status")
    queue_status = cur.fetchall()
    print("\nQueue Status:")
    for status, count in queue_status:
        print(f"  {status}: {count}")

    stats = {'completed': 0, 'failed': 0, 'not_found': 0}

    # Process pending batch
    print("\n--- Processing Pending ---")
    pending = get_pending_batch(cur, batch_size=100)
    if pending:
        print(f"Got {len(pending)} pending Axies")
        process_batch(conn, cur, pending, stats)
    else:
        print("No pending Axies in queue")

    # Process retry batch
    print("\n--- Processing Retries ---")
    retries = get_retry_batch(cur, batch_size=20)
    if retries:
        print(f"Got {len(retries)} Axies to retry")
        process_batch(conn, cur, retries, stats)
    else:
        print("No retries needed")

    # Final status
    cur.execute("SELECT status, COUNT(*) FROM metadata_fetch_queue GROUP BY status ORDER BY status")
    final_status = cur.fetchall()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Completed: {stats['completed']}")
    print(f"Failed: {stats['failed']}")
    print(f"Not Found: {stats['not_found']}")
    print("\nFinal Queue Status:")
    for status, count in final_status:
        print(f"  {status}: {count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
