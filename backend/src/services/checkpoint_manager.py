"""
Checkpoint Manager for resumable sales fetching.

Provides progress persistence to allow resuming long-running
historical data fetches after interruption.

Uses the axie.sync_state table for persistent storage.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    import asyncpg
except ImportError:
    asyncpg = None

try:
    import psycopg2
except ImportError:
    psycopg2 = None

logger = logging.getLogger(__name__)


@dataclass
class SyncState:
    """Current sync state for a job."""
    id: str
    last_block: int
    last_timestamp: Optional[datetime]
    records_synced: int
    error_count: int
    last_error: Optional[str]
    processing_rate: Optional[float]
    updated_at: datetime


class CheckpointManager:
    """
    Manages checkpoint persistence for resumable sync operations.

    Features:
    - Save progress every N blocks
    - Track error counts and rates
    - Resume from last checkpoint
    - Support both sync and async database access

    Usage:
        manager = CheckpointManager(db_config)
        await manager.connect()

        # Check for existing progress
        state = await manager.get_state("axie_sales_june2025")
        if state:
            start_block = state.last_block + 1
        else:
            start_block = JUNE_START_BLOCK

        # Save checkpoints during processing
        await manager.save_checkpoint(
            "axie_sales_june2025",
            current_block=46500000,
            records_synced=1500,
            processing_rate=3500.0
        )
    """

    DEFAULT_CHECKPOINT_INTERVAL = 1000  # blocks
    SYNC_STATE_TABLE = "axie.sync_state"

    def __init__(
        self,
        db_config: Dict[str, Any],
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
    ):
        """
        Initialize checkpoint manager.

        Args:
            db_config: Database configuration dict with host, port, dbname, user, password
            checkpoint_interval: Blocks between automatic checkpoints
        """
        self.db_config = db_config
        self.checkpoint_interval = checkpoint_interval
        self._pool: Optional[Any] = None
        self._sync_conn = None
        self._last_checkpoint_block = 0
        self._last_checkpoint_time = 0

    async def connect(self):
        """Establish async database connection pool."""
        if asyncpg is None:
            raise ImportError("asyncpg required for async checkpoint manager")

        self._pool = await asyncpg.create_pool(
            host=self.db_config.get("host"),
            port=self.db_config.get("port", 5432),
            database=self.db_config.get("dbname") or self.db_config.get("database"),
            user=self.db_config.get("user"),
            password=self.db_config.get("password"),
            min_size=1,
            max_size=5,
        )
        logger.info("Checkpoint manager connected to database")

    async def close(self):
        """Close database connections."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def connect_sync(self):
        """Establish synchronous database connection."""
        if psycopg2 is None:
            raise ImportError("psycopg2 required for sync checkpoint manager")

        self._sync_conn = psycopg2.connect(**self.db_config)
        logger.info("Checkpoint manager connected to database (sync)")

    def close_sync(self):
        """Close sync database connection."""
        if self._sync_conn:
            self._sync_conn.close()
            self._sync_conn = None

    async def get_state(self, sync_id: str) -> Optional[SyncState]:
        """Get current sync state for an ID."""
        if not self._pool:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                SELECT id, last_block, last_timestamp, records_synced,
                       COALESCE(error_count, 0) as error_count,
                       last_error, processing_rate, updated_at
                FROM {self.SYNC_STATE_TABLE}
                WHERE id = $1
                """,
                sync_id
            )

            if row:
                return SyncState(
                    id=row["id"],
                    last_block=row["last_block"] or 0,
                    last_timestamp=row["last_timestamp"],
                    records_synced=row["records_synced"] or 0,
                    error_count=row["error_count"],
                    last_error=row["last_error"],
                    processing_rate=float(row["processing_rate"]) if row["processing_rate"] else None,
                    updated_at=row["updated_at"],
                )
            return None

    def get_state_sync(self, sync_id: str) -> Optional[SyncState]:
        """Get current sync state (synchronous)."""
        if not self._sync_conn:
            raise RuntimeError("Not connected. Call connect_sync() first.")

        with self._sync_conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, last_block, last_timestamp, records_synced,
                       COALESCE(error_count, 0) as error_count,
                       last_error, processing_rate, updated_at
                FROM {self.SYNC_STATE_TABLE}
                WHERE id = %s
                """,
                (sync_id,)
            )
            row = cur.fetchone()

            if row:
                return SyncState(
                    id=row[0],
                    last_block=row[1] or 0,
                    last_timestamp=row[2],
                    records_synced=row[3] or 0,
                    error_count=row[4],
                    last_error=row[5],
                    processing_rate=float(row[6]) if row[6] else None,
                    updated_at=row[7],
                )
            return None

    async def save_checkpoint(
        self,
        sync_id: str,
        current_block: int,
        records_synced: int,
        processing_rate: Optional[float] = None,
        last_error: Optional[str] = None,
    ) -> bool:
        """
        Save checkpoint to database.

        Args:
            sync_id: Unique identifier for this sync job
            current_block: Last processed block number
            records_synced: Total records synced so far
            processing_rate: Blocks per second
            last_error: Last error message if any

        Returns:
            True if checkpoint saved successfully
        """
        if not self._pool:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self.SYNC_STATE_TABLE}
                        (id, last_block, last_timestamp, records_synced, processing_rate, last_error, updated_at)
                    VALUES ($1, $2, NOW(), $3, $4, $5, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        last_block = EXCLUDED.last_block,
                        last_timestamp = NOW(),
                        records_synced = EXCLUDED.records_synced,
                        processing_rate = EXCLUDED.processing_rate,
                        last_error = EXCLUDED.last_error,
                        updated_at = NOW()
                    """,
                    sync_id, current_block, records_synced, processing_rate, last_error
                )

            self._last_checkpoint_block = current_block
            self._last_checkpoint_time = time.time()
            logger.debug(f"Checkpoint saved: {sync_id} @ block {current_block:,}")
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return False

    def save_checkpoint_sync(
        self,
        sync_id: str,
        current_block: int,
        records_synced: int,
        processing_rate: Optional[float] = None,
        last_error: Optional[str] = None,
    ) -> bool:
        """Save checkpoint (synchronous version)."""
        if not self._sync_conn:
            raise RuntimeError("Not connected. Call connect_sync() first.")

        try:
            with self._sync_conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self.SYNC_STATE_TABLE}
                        (id, last_block, last_timestamp, records_synced, processing_rate, last_error, updated_at)
                    VALUES (%s, %s, NOW(), %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        last_block = EXCLUDED.last_block,
                        last_timestamp = NOW(),
                        records_synced = EXCLUDED.records_synced,
                        processing_rate = EXCLUDED.processing_rate,
                        last_error = EXCLUDED.last_error,
                        updated_at = NOW()
                    """,
                    (sync_id, current_block, records_synced, processing_rate, last_error)
                )
            self._sync_conn.commit()

            self._last_checkpoint_block = current_block
            self._last_checkpoint_time = time.time()
            logger.debug(f"Checkpoint saved: {sync_id} @ block {current_block:,}")
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            self._sync_conn.rollback()
            return False

    async def increment_error_count(self, sync_id: str, error_message: str) -> int:
        """Increment error count and record last error."""
        if not self._pool:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"""
                UPDATE {self.SYNC_STATE_TABLE}
                SET error_count = COALESCE(error_count, 0) + 1,
                    last_error = $2,
                    updated_at = NOW()
                WHERE id = $1
                RETURNING error_count
                """,
                sync_id, error_message
            )
            return row["error_count"] if row else 0

    async def reset_errors(self, sync_id: str):
        """Reset error count for a sync job."""
        if not self._pool:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            await conn.execute(
                f"""
                UPDATE {self.SYNC_STATE_TABLE}
                SET error_count = 0, last_error = NULL, updated_at = NOW()
                WHERE id = $1
                """,
                sync_id
            )

    async def list_jobs(self) -> List[SyncState]:
        """List all sync jobs."""
        if not self._pool:
            raise RuntimeError("Not connected. Call connect() first.")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, last_block, last_timestamp, records_synced,
                       COALESCE(error_count, 0) as error_count,
                       last_error, processing_rate, updated_at
                FROM {self.SYNC_STATE_TABLE}
                ORDER BY updated_at DESC
                """
            )

            return [
                SyncState(
                    id=row["id"],
                    last_block=row["last_block"] or 0,
                    last_timestamp=row["last_timestamp"],
                    records_synced=row["records_synced"] or 0,
                    error_count=row["error_count"],
                    last_error=row["last_error"],
                    processing_rate=float(row["processing_rate"]) if row["processing_rate"] else None,
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def should_checkpoint(self, current_block: int) -> bool:
        """Check if we should save a checkpoint now."""
        blocks_since = current_block - self._last_checkpoint_block
        return blocks_since >= self.checkpoint_interval

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class ProgressTracker:
    """
    Helper class for tracking and reporting progress.

    Provides formatted progress output with ETA calculation.
    """

    def __init__(self, total_blocks: int, start_block: int):
        self.total_blocks = total_blocks
        self.start_block = start_block
        self.start_time = time.time()
        self.last_report_time = 0
        self.report_interval = 10  # seconds

    def report(
        self,
        current_block: int,
        sales_found: int,
        force: bool = False
    ) -> Optional[str]:
        """
        Generate progress report if interval has passed.

        Returns formatted progress string or None.
        """
        now = time.time()
        if not force and (now - self.last_report_time) < self.report_interval:
            return None

        self.last_report_time = now

        elapsed = now - self.start_time
        blocks_done = current_block - self.start_block
        progress_pct = (blocks_done / self.total_blocks) * 100 if self.total_blocks > 0 else 0
        blocks_per_sec = blocks_done / elapsed if elapsed > 0 else 0

        blocks_remaining = self.total_blocks - blocks_done
        eta_seconds = blocks_remaining / blocks_per_sec if blocks_per_sec > 0 else 0
        eta_minutes = eta_seconds / 60

        return (
            f"[{progress_pct:5.1f}%] Block {current_block:,} | "
            f"Sales: {sales_found:,} | "
            f"{blocks_per_sec:.0f} blk/s | "
            f"ETA: {eta_minutes:.1f}m"
        )


async def test_checkpoint_manager():
    """Test the checkpoint manager."""
    import json
    import subprocess

    # Get config from AWS secrets
    result = subprocess.run(
        ['aws', 'secretsmanager', 'get-secret-value',
         '--secret-id', 'axie-explorer/api-keys',
         '--query', 'SecretString', '--output', 'text',
         '--region', 'us-east-1'],
        capture_output=True, text=True
    )
    secrets = json.loads(result.stdout)

    db_config = {
        'host': secrets.get('RDS_HOST', 'cardforum.cn4c2su0o42n.us-east-1.rds.amazonaws.com'),
        'port': 5432,
        'dbname': secrets.get('RDS_DATABASE', 'postgres'),
        'user': secrets.get('RDS_USER', 'postgres'),
        'password': secrets.get('RDS_PASSWORD', '12345Cardforum')
    }

    async with CheckpointManager(db_config) as manager:
        # List existing jobs
        jobs = await manager.list_jobs()
        print(f"Existing sync jobs: {len(jobs)}")
        for job in jobs:
            print(f"  {job.id}: block {job.last_block:,}, {job.records_synced:,} records")

        # Test checkpoint
        await manager.save_checkpoint(
            "test_checkpoint",
            current_block=47000000,
            records_synced=100,
            processing_rate=3500.0
        )

        # Read back
        state = await manager.get_state("test_checkpoint")
        print(f"\nTest checkpoint: {state}")


if __name__ == "__main__":
    asyncio.run(test_checkpoint_manager())
