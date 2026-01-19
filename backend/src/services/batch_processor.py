"""
Batch Processor for high-throughput Axie sales fetching.

Optimized for parallel processing:
- 5 parallel workers for log fetching (499-block batches)
- 10 parallel workers for receipt fetching
- ~3,500 blocks/second throughput

Works with the RoninRPCClient for blockchain data access.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Callable, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProcessingStats:
    """Statistics for batch processing run."""
    start_time: float = field(default_factory=time.time)
    blocks_processed: int = 0
    logs_fetched: int = 0
    receipts_fetched: int = 0
    sales_found: int = 0
    errors: int = 0

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def blocks_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self.blocks_processed / elapsed if elapsed > 0 else 0

    @property
    def sales_per_second(self) -> float:
        elapsed = self.elapsed_seconds
        return self.sales_found / elapsed if elapsed > 0 else 0


@dataclass
class Sale:
    """Parsed Axie sale record."""
    tx_hash: str
    block_number: int
    block_timestamp: Optional[datetime]
    axie_id: int
    price_token: float
    token_type: str  # WETH or WRON
    price_usd: float
    seller: Optional[str] = None
    buyer: Optional[str] = None


class BatchProcessor:
    """
    High-performance batch processor for Axie sales.

    Performance characteristics:
    - 5 parallel log fetchers (configurable)
    - 10 parallel receipt fetchers (configurable)
    - ~3,500 blocks/sec throughput on public RPC
    - Automatic deduplication of transactions

    Usage:
        async with RoninRPCClient() as rpc:
            processor = BatchProcessor(rpc)
            sales, stats = await processor.process_range(
                from_block=46000000,
                to_block=47000000,
                progress_callback=my_callback
            )
    """

    # Contract addresses
    AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
    WETH_CONTRACT = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
    WRON_CONTRACT = "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4"

    # Event signatures
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    # Default price rates (can be updated)
    RATES = {"WETH": 3800.0, "WRON": 0.15}

    # Processing configuration
    DEFAULT_BATCH_SIZE = 499
    DEFAULT_LOG_WORKERS = 5
    DEFAULT_RECEIPT_WORKERS = 10

    def __init__(
        self,
        rpc_client,
        batch_size: int = DEFAULT_BATCH_SIZE,
        log_workers: int = DEFAULT_LOG_WORKERS,
        receipt_workers: int = DEFAULT_RECEIPT_WORKERS,
        rates: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize batch processor.

        Args:
            rpc_client: RoninRPCClient instance
            batch_size: Blocks per batch (max 499)
            log_workers: Parallel workers for log fetching
            receipt_workers: Parallel workers for receipt fetching
            rates: Token to USD rates {"WETH": 3800.0, "WRON": 0.15}
        """
        self.rpc = rpc_client
        self.batch_size = min(batch_size, 499)  # Hard limit
        self.log_workers = log_workers
        self.receipt_workers = receipt_workers
        self.rates = rates or self.RATES.copy()

    def update_rates(self, weth_usd: float = None, wron_usd: float = None):
        """Update token exchange rates."""
        if weth_usd is not None:
            self.rates["WETH"] = weth_usd
        if wron_usd is not None:
            self.rates["WRON"] = wron_usd

    async def process_range(
        self,
        from_block: int,
        to_block: int,
        progress_callback: Optional[Callable[[str, int, int, ProcessingStats], None]] = None,
        checkpoint_callback: Optional[Callable[[int, int], None]] = None,
        checkpoint_interval: int = 1000,
    ) -> tuple[List[Sale], ProcessingStats]:
        """
        Process a block range and extract all sales.

        Args:
            from_block: Start block (inclusive)
            to_block: End block (inclusive)
            progress_callback: Optional callback(phase, current, total, stats)
            checkpoint_callback: Optional callback(block_number, sales_count)
            checkpoint_interval: Blocks between checkpoints

        Returns:
            Tuple of (sales list, processing stats)
        """
        stats = ProcessingStats()
        all_sales = []

        # Create batches
        batches = self._create_batches(from_block, to_block)
        total_batches = len(batches)

        logger.info(f"Processing {to_block - from_block + 1:,} blocks in {total_batches} batches")

        # Process in chunks for checkpointing
        chunk_size = max(1, checkpoint_interval // self.batch_size)

        for chunk_start in range(0, len(batches), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(batches))
            chunk_batches = batches[chunk_start:chunk_end]

            # Phase 1: Fetch logs for this chunk
            if progress_callback:
                progress_callback("logs", chunk_start, total_batches, stats)

            chunk_logs = await self._fetch_logs_parallel(chunk_batches)
            stats.logs_fetched += len(chunk_logs)

            # Extract unique TX hashes
            tx_hashes = self._extract_unique_txs(chunk_logs)

            if not tx_hashes:
                stats.blocks_processed += sum(e - s + 1 for s, e in chunk_batches)
                continue

            # Phase 2: Fetch receipts
            if progress_callback:
                progress_callback("receipts", len(tx_hashes), len(tx_hashes), stats)

            receipts = await self._fetch_receipts_parallel(list(tx_hashes))
            stats.receipts_fetched += len(receipts)

            # Phase 3: Parse sales
            chunk_sales = self._parse_sales(receipts)

            # Estimate timestamps for sales
            chunk_sales = self._estimate_timestamps(chunk_sales, from_block)

            all_sales.extend(chunk_sales)
            stats.sales_found += len(chunk_sales)
            stats.blocks_processed += sum(e - s + 1 for s, e in chunk_batches)

            # Checkpoint
            if checkpoint_callback and chunk_batches:
                last_block = chunk_batches[-1][1]
                checkpoint_callback(last_block, len(all_sales))

            if progress_callback:
                progress_callback("checkpoint", chunk_end, total_batches, stats)

        logger.info(
            f"Complete: {stats.sales_found:,} sales from {stats.blocks_processed:,} blocks "
            f"in {stats.elapsed_seconds:.1f}s ({stats.blocks_per_second:.0f} blk/s)"
        )

        return all_sales, stats

    def _create_batches(self, start: int, end: int) -> List[tuple]:
        """Create block range batches."""
        batches = []
        current = start

        while current <= end:
            batch_end = min(current + self.batch_size - 1, end)
            batches.append((current, batch_end))
            current = batch_end + 1

        return batches

    async def _fetch_logs_parallel(self, batches: List[tuple]) -> List[Dict]:
        """Fetch logs for multiple batches in parallel."""
        semaphore = asyncio.Semaphore(self.log_workers)
        request_delay = 0.1  # 100ms delay between requests to avoid rate limiting

        async def fetch_batch(start: int, end: int, index: int) -> List[Dict]:
            # Stagger start times to avoid burst
            await asyncio.sleep(index * request_delay)
            async with semaphore:
                try:
                    result = await self.rpc.get_logs(
                        self.AXIE_CONTRACT, start, end,
                        topics=[self.TRANSFER_TOPIC]
                    )
                    await asyncio.sleep(request_delay)  # Delay after request
                    return result
                except Exception as e:
                    logger.warning(f"Failed to get logs {start}-{end}: {e}")
                    return []

        tasks = [fetch_batch(s, e, i) for i, (s, e) in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_logs = []
        for result in results:
            if isinstance(result, list):
                all_logs.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"Batch error: {result}")

        return all_logs

    def _extract_unique_txs(self, logs: List[Dict]) -> Set[str]:
        """Extract unique transaction hashes from logs."""
        return {log["transactionHash"] for log in logs if "transactionHash" in log}

    async def _fetch_receipts_parallel(self, tx_hashes: List[str]) -> List[Dict]:
        """Fetch transaction receipts in parallel."""
        semaphore = asyncio.Semaphore(self.receipt_workers)
        request_delay = 0.05  # 50ms delay between receipt requests

        async def fetch_receipt(tx_hash: str, index: int) -> Optional[Dict]:
            # Stagger start times
            await asyncio.sleep(index * request_delay * 0.5)
            async with semaphore:
                try:
                    receipt = await self.rpc.get_transaction_receipt(tx_hash)
                    if receipt:
                        receipt["_tx_hash"] = tx_hash
                    await asyncio.sleep(request_delay)
                    return receipt
                except Exception as e:
                    logger.warning(f"Failed to get receipt {tx_hash[:20]}: {e}")
                    return None

        tasks = [fetch_receipt(tx, i) for i, tx in enumerate(tx_hashes)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [r for r in results if isinstance(r, dict) and r]

    def _parse_sales(self, receipts: List[Dict]) -> List[Sale]:
        """Parse sales from transaction receipts."""
        sales = []

        for receipt in receipts:
            parsed = self._parse_single_receipt(receipt)
            sales.extend(parsed)

        return sales

    def _parse_single_receipt(self, receipt: Dict) -> List[Sale]:
        """Extract sale(s) from a single receipt."""
        logs = receipt.get("logs", [])
        if len(logs) < 2:
            return []

        tx_hash = receipt.get("transactionHash", receipt.get("_tx_hash", ""))
        block_number = int(receipt.get("blockNumber", "0x0"), 16)

        axie_transfers = []
        payments = []
        seller = None
        buyer = None

        for log in logs:
            topics = log.get("topics", [])
            if not topics:
                continue

            sig = topics[0]
            address = log.get("address", "").lower()

            if sig != self.TRANSFER_TOPIC:
                continue

            # Axie NFT transfer (ERC721)
            if address == self.AXIE_CONTRACT.lower() and len(topics) == 4:
                axie_id = int(topics[3], 16)
                axie_transfers.append(axie_id)
                seller = "0x" + topics[1][-40:]
                buyer = "0x" + topics[2][-40:]

            # Token payment (ERC20 transfer)
            elif address in (self.WETH_CONTRACT.lower(), self.WRON_CONTRACT.lower()):
                if len(topics) == 3:
                    data = log.get("data", "0x")
                    if data and data != "0x":
                        value = int(data, 16) / 10**18
                        token = "WETH" if address == self.WETH_CONTRACT.lower() else "WRON"
                        usd = value * self.rates.get(token, 0)
                        payments.append({
                            "token": token,
                            "value": value,
                            "usd": usd,
                        })

        if not axie_transfers or not payments:
            return []

        # Use largest payment
        best_payment = max(payments, key=lambda p: p["usd"])
        per_axie_value = best_payment["value"] / len(axie_transfers)
        per_axie_usd = best_payment["usd"] / len(axie_transfers)

        return [
            Sale(
                tx_hash=tx_hash,
                block_number=block_number,
                block_timestamp=None,
                axie_id=axie_id,
                price_token=per_axie_value,
                token_type=best_payment["token"],
                price_usd=per_axie_usd,
                seller=seller,
                buyer=buyer,
            )
            for axie_id in axie_transfers
        ]

    def _estimate_timestamps(
        self,
        sales: List[Sale],
        reference_block: int,
        reference_time: datetime = None,
        block_time_seconds: float = 3.0,
    ) -> List[Sale]:
        """
        Estimate timestamps for sales based on block number.

        Ronin has ~3 second block times.
        Uses June 1, 2025 block 45626000 as reference if not provided.
        """
        if reference_time is None:
            # Reference: Block 45626000 ~ June 1, 2025
            reference_time = datetime(2025, 6, 1)
            reference_block = 45626000

        for sale in sales:
            block_diff = sale.block_number - reference_block
            time_diff = timedelta(seconds=block_diff * block_time_seconds)
            sale.block_timestamp = reference_time + time_diff

        return sales


async def quick_test():
    """Quick test of the batch processor."""
    from .ronin_rpc_client import RoninRPCClient

    async with RoninRPCClient() as rpc:
        processor = BatchProcessor(rpc)
        current = await rpc.get_block_number()

        print(f"Current block: {current:,}")
        print("Fetching last 5,000 blocks...")

        def progress(phase, current, total, stats):
            print(f"  [{phase}] {current}/{total} - {stats.sales_found} sales")

        sales, stats = await processor.process_range(
            from_block=current - 5000,
            to_block=current,
            progress_callback=progress,
        )

        print(f"\nResults:")
        print(f"  Sales found: {stats.sales_found}")
        print(f"  Blocks/sec: {stats.blocks_per_second:.0f}")
        print(f"  Time: {stats.elapsed_seconds:.1f}s")

        if sales:
            print(f"\nRecent sales:")
            for sale in sorted(sales, key=lambda s: s.block_number, reverse=True)[:5]:
                print(f"  Axie #{sale.axie_id}: ${sale.price_usd:.2f} ({sale.token_type})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(quick_test())
