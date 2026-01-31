"""
One-time Lambda to query metadata coverage.
Can be invoked manually via AWS CLI.
"""

from src.lambdas.common import logger, get_db_connection

def handler(event, context):
    """Query metadata coverage statistics."""
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            # Total axies with metadata
            cur.execute("SELECT COUNT(*) FROM axie_metadata;")
            total_metadata = cur.fetchone()[0]

            # Total active listings
            cur.execute("SELECT COUNT(DISTINCT axie_id) FROM listings WHERE status = 'active';")
            total_active_listings = cur.fetchone()[0]

            # Coverage percentage
            coverage_pct = (total_metadata * 100.0 / total_active_listings) if total_active_listings > 0 else 0

            # Missing metadata
            cur.execute("""
                SELECT COUNT(DISTINCT l.axie_id)
                FROM listings l
                LEFT JOIN axie_metadata m ON l.axie_id = m.axie_id
                WHERE l.status = 'active' AND m.axie_id IS NULL;
            """)
            missing_metadata = cur.fetchone()[0]

            # Added in last 24h
            cur.execute("""
                SELECT COUNT(*) FROM axie_metadata
                WHERE created_at > NOW() - INTERVAL '24 hours';
            """)
            added_24h = cur.fetchone()[0]

            # Added in last 2h
            cur.execute("""
                SELECT COUNT(*) FROM axie_metadata
                WHERE created_at > NOW() - INTERVAL '2 hours';
            """)
            added_2h = cur.fetchone()[0]

            result = {
                "total_with_metadata": total_metadata,
                "total_active_listings": total_active_listings,
                "coverage_percentage": round(coverage_pct, 2),
                "missing_metadata": missing_metadata,
                "added_last_24h": added_24h,
                "added_last_2h": added_2h,
            }

            logger.info(f"Coverage stats: {result}")
            return result

    finally:
        conn.close()
