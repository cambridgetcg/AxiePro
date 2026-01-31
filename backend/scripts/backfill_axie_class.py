#!/usr/bin/env python3
"""
Backfill script to populate Axie class metadata for sales records.

This script:
1. Finds sales with missing Axie class data
2. Fetches Axie metadata from Sky Mavis API
3. Inserts/updates Axie records with class information

Usage:
    python scripts/backfill_axie_class.py --limit 1000 --batch-size 50
"""

import asyncio
import argparse
import logging
from datetime import datetime
from typing import Optional

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.database import async_session_factory, engine
from src.models.axie import Axie, AxieClass
from src.models.market import Sale
from src.services.skymavis_client import SkyMavisClient, AxieData

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_axie_ids_missing_class(limit: int = 1000) -> list[int]:
    """Get axie_ids from sales that don't have class data in axies table."""
    async with async_session_factory() as session:
        # Find axie_ids in sales that either:
        # - Don't exist in axies table
        # - Exist but have NULL class
        query = text("""
            SELECT DISTINCT s.axie_id
            FROM sales s
            LEFT JOIN axies a ON s.axie_id = a.id
            WHERE a.id IS NULL OR a.class IS NULL
            LIMIT :limit
        """)
        result = await session.execute(query, {"limit": limit})
        return [row[0] for row in result.fetchall()]


async def get_backfill_stats() -> dict:
    """Get statistics about the backfill progress."""
    async with async_session_factory() as session:
        # Total sales
        total_sales = await session.execute(
            text("SELECT COUNT(*) FROM sales")
        )
        total = total_sales.scalar()

        # Sales with axie class
        with_class = await session.execute(
            text("""
                SELECT COUNT(DISTINCT s.axie_id)
                FROM sales s
                JOIN axies a ON s.axie_id = a.id
                WHERE a.class IS NOT NULL
            """)
        )
        has_class = with_class.scalar()

        # Sales without axie class
        without_class = await session.execute(
            text("""
                SELECT COUNT(DISTINCT s.axie_id)
                FROM sales s
                LEFT JOIN axies a ON s.axie_id = a.id
                WHERE a.id IS NULL OR a.class IS NULL
            """)
        )
        missing_class = without_class.scalar()

        # Total unique axies in sales
        unique_axies = await session.execute(
            text("SELECT COUNT(DISTINCT axie_id) FROM sales")
        )
        total_unique = unique_axies.scalar()

        return {
            "total_sales": total,
            "unique_axies_in_sales": total_unique,
            "axies_with_class": has_class,
            "axies_missing_class": missing_class,
            "coverage_percent": round(has_class / total_unique * 100, 2) if total_unique > 0 else 0,
        }


async def upsert_axie(session, axie_data: AxieData) -> bool:
    """Upsert an Axie record."""
    try:
        # Map class string to enum
        class_map = {
            "Beast": AxieClass.BEAST,
            "Bug": AxieClass.BUG,
            "Bird": AxieClass.BIRD,
            "Plant": AxieClass.PLANT,
            "Aquatic": AxieClass.AQUATIC,
            "Reptile": AxieClass.REPTILE,
            "Mech": AxieClass.MECH,
            "Dawn": AxieClass.DAWN,
            "Dusk": AxieClass.DUSK,
        }

        axie_class = class_map.get(axie_data.class_)
        if not axie_class:
            logger.warning(f"Unknown class '{axie_data.class_}' for axie {axie_data.id}")
            return False

        # Get stats
        stats = axie_data.stats or {}

        # Prepare upsert
        stmt = pg_insert(Axie).values(
            id=axie_data.id,
            name=axie_data.name or f"Axie #{axie_data.id}",
            class_=axie_class,
            breed_count=axie_data.breedCount,
            genes=axie_data.genes or "",
            image_url=axie_data.image,
            owner_address=axie_data.owner or "0x0000000000000000000000000000000000000000",
            birth_date=axie_data.birthDate,
            matron_id=axie_data.matronId,
            sire_id=axie_data.sireId,
            hp=stats.get("hp"),
            speed=stats.get("speed"),
            skill=stats.get("skill"),
            morale=stats.get("morale"),
            updated_at=datetime.utcnow(),
        ).on_conflict_do_update(
            index_elements=["id"],
            set_={
                "class_": axie_class,
                "name": axie_data.name or f"Axie #{axie_data.id}",
                "breed_count": axie_data.breedCount,
                "genes": axie_data.genes or "",
                "image_url": axie_data.image,
                "owner_address": axie_data.owner or "0x0000000000000000000000000000000000000000",
                "hp": stats.get("hp"),
                "speed": stats.get("speed"),
                "skill": stats.get("skill"),
                "morale": stats.get("morale"),
                "updated_at": datetime.utcnow(),
            }
        )

        await session.execute(stmt)
        return True

    except Exception as e:
        logger.error(f"Error upserting axie {axie_data.id}: {e}")
        return False


async def backfill_batch(
    client: SkyMavisClient,
    axie_ids: list[int],
) -> tuple[int, int]:
    """Backfill a batch of axies. Returns (success_count, fail_count)."""
    success = 0
    failed = 0

    async with async_session_factory() as session:
        for axie_id in axie_ids:
            try:
                # Fetch from Sky Mavis
                axie_data = await client.get_axie(axie_id)

                if axie_data:
                    if await upsert_axie(session, axie_data):
                        success += 1
                    else:
                        failed += 1
                else:
                    logger.warning(f"Axie {axie_id} not found in API")
                    failed += 1

                # Small delay to respect rate limits
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Error processing axie {axie_id}: {e}")
                failed += 1

        # Commit the batch
        await session.commit()

    return success, failed


async def run_backfill(
    limit: int = 1000,
    batch_size: int = 50,
    dry_run: bool = False,
):
    """Run the backfill process."""

    # Get initial stats
    logger.info("Getting backfill statistics...")
    stats = await get_backfill_stats()
    logger.info(f"Initial stats: {stats}")

    if stats["axies_missing_class"] == 0:
        logger.info("No axies missing class data. Nothing to backfill.")
        return

    # Get axie IDs to backfill
    logger.info(f"Finding up to {limit} axies missing class data...")
    axie_ids = await get_axie_ids_missing_class(limit)
    logger.info(f"Found {len(axie_ids)} axies to backfill")

    if dry_run:
        logger.info("Dry run - not making any changes")
        logger.info(f"Would backfill axies: {axie_ids[:10]}...")
        return

    if not axie_ids:
        logger.info("No axies to backfill")
        return

    # Process in batches
    total_success = 0
    total_failed = 0

    async with SkyMavisClient() as client:
        for i in range(0, len(axie_ids), batch_size):
            batch = axie_ids[i:i + batch_size]
            logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} axies)...")

            success, failed = await backfill_batch(client, batch)
            total_success += success
            total_failed += failed

            logger.info(f"Batch complete: {success} success, {failed} failed")

            # Small delay between batches
            await asyncio.sleep(1)

    # Final stats
    logger.info(f"\n=== Backfill Complete ===")
    logger.info(f"Total processed: {total_success + total_failed}")
    logger.info(f"Success: {total_success}")
    logger.info(f"Failed: {total_failed}")

    # Get updated stats
    final_stats = await get_backfill_stats()
    logger.info(f"Final stats: {final_stats}")
    logger.info(f"Coverage improved: {stats['coverage_percent']}% -> {final_stats['coverage_percent']}%")


def main():
    parser = argparse.ArgumentParser(description="Backfill Axie class metadata")
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of axies to process (default: 1000)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Batch size for processing (default: 50)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't backfill"
    )

    args = parser.parse_args()

    if args.stats_only:
        asyncio.run(show_stats())
    else:
        asyncio.run(run_backfill(
            limit=args.limit,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        ))


async def show_stats():
    """Just show statistics."""
    stats = await get_backfill_stats()
    print("\n=== Axie Class Data Statistics ===")
    print(f"Total sales records: {stats['total_sales']:,}")
    print(f"Unique axies in sales: {stats['unique_axies_in_sales']:,}")
    print(f"Axies with class data: {stats['axies_with_class']:,}")
    print(f"Axies missing class: {stats['axies_missing_class']:,}")
    print(f"Coverage: {stats['coverage_percent']}%")


if __name__ == "__main__":
    main()
