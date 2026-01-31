#!/usr/bin/env python3
"""
Check metadata coverage for AxiePro database.

Queries:
1. Total axies with metadata
2. Total active listings
3. Coverage percentage
4. Missing metadata count
"""

import os
import sys
import json
import psycopg2
from datetime import datetime

# Database connection from environment or AWS Secrets
DB_HOST = os.getenv("DB_HOST", "axiepro-aurora-cluster-dev.cluster-cn4c2su0o42n.us-east-1.rds.amazonaws.com")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "axiepro_db")
DB_USER = os.getenv("DB_USER", "axiepro_admin")
DB_PASSWORD = os.getenv("DB_PASSWORD")  # Required


def get_coverage_stats(conn):
    """Query database for metadata coverage statistics."""
    with conn.cursor() as cur:
        # Query 1: Total axies with metadata
        cur.execute("SELECT COUNT(*) FROM axie_metadata;")
        total_metadata = cur.fetchone()[0]

        # Query 2: Total active listings
        cur.execute("SELECT COUNT(DISTINCT axie_id) FROM listings WHERE status = 'active';")
        total_active_listings = cur.fetchone()[0]

        # Query 3: Coverage percentage
        if total_active_listings > 0:
            coverage_pct = (total_metadata * 100.0) / total_active_listings
        else:
            coverage_pct = 0.0

        # Query 4: Missing metadata for active listings
        cur.execute("""
            SELECT COUNT(DISTINCT l.axie_id)
            FROM listings l
            LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
            WHERE l.status = 'active' AND m.axie_id IS NULL;
        """)
        missing_metadata = cur.fetchone()[0]

        # Query 5: Metadata added in last 24 hours
        cur.execute("""
            SELECT COUNT(*)
            FROM axie_metadata
            WHERE created_at > NOW() - INTERVAL '24 hours';
        """)
        added_last_24h = cur.fetchone()[0]

        # Query 6: Metadata added in last 2 hours (since last run)
        cur.execute("""
            SELECT COUNT(*)
            FROM axie_metadata
            WHERE created_at > NOW() - INTERVAL '2 hours';
        """)
        added_last_2h = cur.fetchone()[0]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_with_metadata": total_metadata,
            "total_active_listings": total_active_listings,
            "coverage_percentage": round(coverage_pct, 2),
            "missing_metadata": missing_metadata,
            "added_last_24h": added_last_24h,
            "added_last_2h": added_last_2h,
        }


def main():
    """Main function."""
    if not DB_PASSWORD:
        print("ERROR: DB_PASSWORD environment variable required", file=sys.stderr)
        print("Usage: DB_PASSWORD=<password> python check_metadata_coverage.py", file=sys.stderr)
        sys.exit(1)

    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=10,
        )

        print(f"Connected to database: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        print()

        # Get coverage stats
        stats = get_coverage_stats(conn)

        # Display results
        print("=" * 60)
        print("METADATA COVERAGE REPORT")
        print("=" * 60)
        print(f"Timestamp:              {stats['timestamp']}")
        print()
        print(f"Total Axies with Metadata:    {stats['total_with_metadata']:,}")
        print(f"Total Active Listings:        {stats['total_active_listings']:,}")
        print(f"Coverage Percentage:          {stats['coverage_percentage']:.2f}%")
        print(f"Missing Metadata:             {stats['missing_metadata']:,}")
        print()
        print(f"Added (Last 24 Hours):        {stats['added_last_24h']:,}")
        print(f"Added (Last 2 Hours):         {stats['added_last_2h']:,}")
        print()

        # W1 Status
        if stats['coverage_percentage'] >= 80:
            print("✅ W1 CRITERION MET: Coverage >80%")
        else:
            needed = stats['missing_metadata']
            if stats['added_last_24h'] > 0:
                rate_per_day = stats['added_last_24h']
                days_to_80 = needed / rate_per_day if rate_per_day > 0 else 999
                print(f"⏳ W1 IN PROGRESS: Need {needed:,} more axies")
                print(f"   Current rate: {rate_per_day:,} axies/day")
                print(f"   Estimated time to 80%: {days_to_80:.1f} days")
            else:
                print(f"⏳ W1 IN PROGRESS: Need {needed:,} more axies")
                print(f"   No metadata added in last 24h - check Lambda execution")

        print("=" * 60)

        # Output JSON for programmatic use
        print()
        print("JSON OUTPUT:")
        print(json.dumps(stats, indent=2))

        conn.close()
        return 0

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
