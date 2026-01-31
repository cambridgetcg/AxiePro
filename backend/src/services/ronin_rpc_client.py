"""
Ronin RPC Client for blockchain data.

Provides direct access to Ronin blockchain via JSON-RPC:
- Event logs (eth_getLogs)
- Transaction receipts
- Block data
- Account balances

Supports multiple providers with automatic failover:
- Public Ronin RPC (primary, no API key)
- Chainstack (fallback)
- Custom providers

Performance optimized:
- Connection pooling
- Parallel batch processing
- Exponential backoff
- Circuit breaker pattern
"""

import asyncio
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, List, Dict, Set
from dataclasses import dataclass, field
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    """Provider health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class RPCProvider:
    """RPC provider configuration."""
    name: str
    url: str
    api_key: Optional[str] = None
    max_blocks_per_query: int = 499
    priority: int = 0  # Lower = higher priority

    # Runtime state
    status: ProviderStatus = ProviderStatus.HEALTHY
    consecutive_errors: int = 0
    last_error_time: Optional[datetime] = None
    total_requests: int = 0
    total_errors: int = 0

    def record_success(self):
        """Record a successful request."""
        self.consecutive_errors = 0
        self.status = ProviderStatus.HEALTHY
        self.total_requests += 1

    def record_error(self):
        """Record a failed request."""
        self.consecutive_errors += 1
        self.total_requests += 1
        self.total_errors += 1
        self.last_error_time = datetime.now()

        if self.consecutive_errors >= 5:
            self.status = ProviderStatus.UNHEALTHY
        elif self.consecutive_errors >= 2:
            self.status = ProviderStatus.DEGRADED


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


class RoninRPCError(Exception):
    """Raised when RPC request fails."""
    def __init__(self, message: str, provider: Optional[str] = None, code: Optional[int] = None):
        self.message = message
        self.provider = provider
        self.code = code
        super().__init__(f"RPC error ({provider}): {message}")


class RoninRPCClient:
    """
    Async RPC client for Ronin blockchain.

    Features:
    - Multiple provider support with failover
    - Connection pooling via httpx
    - Automatic retry with exponential backoff
    - Circuit breaker for unhealthy providers

    Usage:
        async with RoninRPCClient() as client:
            block = await client.get_block_number()
            logs = await client.get_logs(address, from_block, to_block)
    """

    # Contract addresses
    AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
    WETH_CONTRACT = "0xc99a6a985ed2cac1ef41640596c5a5f9f4e19ef5"
    WRON_CONTRACT = "0xe514d9deb7966c8be0ca922de8a064264ea6bcd4"
    AXS_CONTRACT = "0x97a9107c1793bc407d6f527b77e7fff4d812bece"
    SLP_CONTRACT = "0xa8754b9fa15fc18bb59458815510e40a12cd2014"
    RON_NATIVE = "NATIVE"  # RON is native token, no contract address

    # Event signatures
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    # ERC20 function signatures
    BALANCE_OF_SIGNATURE = "0x70a08231"  # balanceOf(address)

    # Price rates (can be updated dynamically)
    RATES = {"WETH": 3800.0, "WRON": 0.15}

    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAYS = [0.5, 1.0, 2.0, 4.0]  # Exponential backoff

    def __init__(
        self,
        providers: Optional[List[RPCProvider]] = None,
        timeout: float = 30.0,
        max_connections: int = 20,
    ):
        """
        Initialize RPC client.

        Args:
            providers: List of RPC providers (defaults to public Ronin RPC)
            timeout: Request timeout in seconds
            max_connections: Maximum concurrent connections
        """
        self.providers = providers or [
            RPCProvider(
                name="public",
                url="https://api.roninchain.com/rpc",
                priority=0,
            ),
        ]
        self.timeout = timeout
        self.max_connections = max_connections
        self._client: Optional[httpx.AsyncClient] = None
        self._current_provider_idx = 0

    async def __aenter__(self) -> "RoninRPCClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_connections,
            ),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def provider(self) -> RPCProvider:
        """Get current active provider."""
        return self.providers[self._current_provider_idx]

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers for current provider."""
        headers = {"Content-Type": "application/json"}
        if self.provider.api_key:
            headers["X-API-Key"] = self.provider.api_key
        return headers

    def _rotate_provider(self):
        """Rotate to next healthy provider."""
        original_idx = self._current_provider_idx

        for _ in range(len(self.providers)):
            self._current_provider_idx = (self._current_provider_idx + 1) % len(self.providers)

            if self.providers[self._current_provider_idx].status != ProviderStatus.UNHEALTHY:
                logger.info(f"Rotated to provider: {self.provider.name}")
                return

        # All providers unhealthy, reset the first one
        self._current_provider_idx = original_idx
        self.providers[self._current_provider_idx].status = ProviderStatus.DEGRADED
        logger.warning("All providers unhealthy, resetting primary")

    async def _call(
        self,
        method: str,
        params: List[Any],
        retries: int = None,
    ) -> Any:
        """
        Make RPC call with retry and failover.

        Args:
            method: RPC method name
            params: Method parameters
            retries: Number of retries (default: MAX_RETRIES)

        Returns:
            RPC result data

        Raises:
            RoninRPCError: If all retries fail
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        retries = retries if retries is not None else self.MAX_RETRIES
        last_error = None

        for attempt in range(retries + 1):
            provider = self.provider

            try:
                response = await self._client.post(
                    provider.url,
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": 1,
                    },
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    data = response.json()

                    if "error" in data:
                        error_msg = data["error"].get("message", "Unknown error")
                        error_code = data["error"].get("code")

                        # Block range too large - not a provider error
                        if "500 blocks" in error_msg.lower() or "invalid param" in error_msg.lower():
                            raise RoninRPCError(error_msg, provider.name, error_code)

                        provider.record_error()
                        last_error = RoninRPCError(error_msg, provider.name, error_code)
                    else:
                        provider.record_success()
                        return data.get("result")

                elif response.status_code == 429:
                    # Rate limited
                    provider.record_error()
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited by {provider.name}, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    self._rotate_provider()
                    continue

                elif response.status_code >= 500:
                    # Server error
                    provider.record_error()
                    last_error = RoninRPCError(
                        f"HTTP {response.status_code}",
                        provider.name,
                        response.status_code,
                    )

                else:
                    provider.record_error()
                    last_error = RoninRPCError(
                        f"HTTP {response.status_code}: {response.text[:200]}",
                        provider.name,
                        response.status_code,
                    )

            except httpx.RequestError as e:
                provider.record_error()
                last_error = RoninRPCError(str(e), provider.name)
                logger.warning(f"Request error: {e}")

            # Exponential backoff before retry
            if attempt < retries:
                delay = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)]
                await asyncio.sleep(delay)

                # Rotate provider if current one is unhealthy
                if provider.status == ProviderStatus.UNHEALTHY:
                    self._rotate_provider()

        raise last_error or RoninRPCError("All retries exhausted")

    # =========================================================================
    # Block Methods
    # =========================================================================

    async def get_block_number(self) -> int:
        """Get current block number."""
        result = await self._call("eth_blockNumber", [])
        return int(result, 16)

    async def get_block(self, block_number: int, full_transactions: bool = False) -> Dict:
        """Get block by number."""
        return await self._call(
            "eth_getBlockByNumber",
            [hex(block_number), full_transactions],
        )

    async def get_block_timestamp(self, block_number: int) -> datetime:
        """Get timestamp for a block."""
        block = await self.get_block(block_number)
        if block and block.get("timestamp"):
            return datetime.fromtimestamp(int(block["timestamp"], 16))
        return datetime.now()

    # =========================================================================
    # Log Methods
    # =========================================================================

    async def get_logs(
        self,
        address: str,
        from_block: int,
        to_block: int,
        topics: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Get event logs for address in block range.

        Args:
            address: Contract address
            from_block: Start block (inclusive)
            to_block: End block (inclusive)
            topics: Optional topic filters

        Returns:
            List of log entries

        Note:
            Block range is limited to 499 blocks per query.
        """
        params = {
            "address": address,
            "fromBlock": hex(from_block),
            "toBlock": hex(to_block),
        }

        if topics:
            params["topics"] = topics

        return await self._call("eth_getLogs", [params])

    async def get_logs_batched(
        self,
        address: str,
        from_block: int,
        to_block: int,
        topics: Optional[List[str]] = None,
        batch_size: int = 499,
        max_workers: int = 5,
    ) -> List[Dict]:
        """
        Get logs in parallel batches.

        Args:
            address: Contract address
            from_block: Start block
            to_block: End block
            topics: Optional topic filters
            batch_size: Blocks per batch (max 499)
            max_workers: Parallel workers

        Returns:
            All logs from the range
        """
        batches = []
        current = from_block

        while current <= to_block:
            batch_end = min(current + batch_size - 1, to_block)
            batches.append((current, batch_end))
            current = batch_end + 1

        semaphore = asyncio.Semaphore(max_workers)

        async def fetch_batch(start: int, end: int) -> List[Dict]:
            async with semaphore:
                try:
                    return await self.get_logs(address, start, end, topics)
                except RoninRPCError as e:
                    logger.warning(f"Failed to get logs {start}-{end}: {e}")
                    return []

        tasks = [fetch_batch(s, e) for s, e in batches]
        results = await asyncio.gather(*tasks)

        all_logs = []
        for result in results:
            all_logs.extend(result)

        return all_logs

    # =========================================================================
    # Transaction Methods
    # =========================================================================

    async def get_transaction_receipt(self, tx_hash: str) -> Optional[Dict]:
        """Get transaction receipt by hash."""
        return await self._call("eth_getTransactionReceipt", [tx_hash])

    async def get_receipts_parallel(
        self,
        tx_hashes: List[str],
        max_workers: int = 10,
    ) -> List[Dict]:
        """
        Get multiple transaction receipts in parallel.

        Args:
            tx_hashes: List of transaction hashes
            max_workers: Parallel workers

        Returns:
            List of receipts (excluding None results)
        """
        semaphore = asyncio.Semaphore(max_workers)

        async def fetch_receipt(tx_hash: str) -> Optional[Dict]:
            async with semaphore:
                try:
                    receipt = await self.get_transaction_receipt(tx_hash)
                    if receipt:
                        receipt["_tx_hash"] = tx_hash  # Preserve hash
                    return receipt
                except RoninRPCError as e:
                    logger.warning(f"Failed to get receipt {tx_hash[:20]}: {e}")
                    return None

        tasks = [fetch_receipt(tx) for tx in tx_hashes]
        results = await asyncio.gather(*tasks)

        return [r for r in results if r is not None]

    # =========================================================================
    # Axie-Specific Methods
    # =========================================================================

    async def get_axie_transfers(
        self,
        from_block: int,
        to_block: int,
        max_workers: int = 5,
    ) -> List[Dict]:
        """
        Get Axie NFT transfer events in block range.

        Args:
            from_block: Start block
            to_block: End block
            max_workers: Parallel workers

        Returns:
            List of transfer logs
        """
        return await self.get_logs_batched(
            address=self.AXIE_CONTRACT,
            from_block=from_block,
            to_block=to_block,
            batch_size=499,
            max_workers=max_workers,
        )

    def parse_sale_from_receipt(self, receipt: Dict) -> List[Sale]:
        """
        Extract sale information from transaction receipt.

        Args:
            receipt: Transaction receipt

        Returns:
            List of Sale objects (one per Axie in bundle)
        """
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

            # Token payment (ERC20)
            elif address in (self.WETH_CONTRACT.lower(), self.WRON_CONTRACT.lower()):
                if len(topics) == 3:
                    data = log.get("data", "0x")
                    if data and data != "0x":
                        value = int(data, 16) / 10**18
                        token = "WETH" if address == self.WETH_CONTRACT.lower() else "WRON"
                        usd = value * self.RATES.get(token, 0)
                        payments.append({
                            "token": token,
                            "value": value,
                            "usd": usd,
                        })

        if not axie_transfers or not payments:
            return []

        # Use largest payment (in case of multiple transfers)
        best_payment = max(payments, key=lambda p: p["usd"])
        per_axie_value = best_payment["value"] / len(axie_transfers)
        per_axie_usd = best_payment["usd"] / len(axie_transfers)

        return [
            Sale(
                tx_hash=tx_hash,
                block_number=block_number,
                block_timestamp=None,  # Can be filled in later
                axie_id=axie_id,
                price_token=per_axie_value,
                token_type=best_payment["token"],
                price_usd=per_axie_usd,
                seller=seller,
                buyer=buyer,
            )
            for axie_id in axie_transfers
        ]

    async def fetch_sales(
        self,
        from_block: int,
        to_block: int,
        log_workers: int = 5,
        receipt_workers: int = 10,
        progress_callback: Optional[callable] = None,
    ) -> List[Sale]:
        """
        Fetch all Axie sales in block range.

        Args:
            from_block: Start block
            to_block: End block
            log_workers: Parallel workers for log fetching
            receipt_workers: Parallel workers for receipt fetching
            progress_callback: Optional callback(phase, current, total)

        Returns:
            List of Sale objects
        """
        # Phase 1: Get all transfer logs
        if progress_callback:
            progress_callback("logs", 0, to_block - from_block)

        logs = await self.get_axie_transfers(from_block, to_block, log_workers)

        # Filter to Transfer events only
        transfer_logs = [
            log for log in logs
            if log.get("topics") and log["topics"][0] == self.TRANSFER_TOPIC
        ]

        # Extract unique TX hashes
        tx_hashes = list(set(log["transactionHash"] for log in transfer_logs))

        if progress_callback:
            progress_callback("logs", to_block - from_block, to_block - from_block)

        if not tx_hashes:
            return []

        # Phase 2: Fetch receipts
        if progress_callback:
            progress_callback("receipts", 0, len(tx_hashes))

        receipts = await self.get_receipts_parallel(tx_hashes, receipt_workers)

        if progress_callback:
            progress_callback("receipts", len(tx_hashes), len(tx_hashes))

        # Phase 3: Parse sales
        sales = []
        for receipt in receipts:
            parsed = self.parse_sale_from_receipt(receipt)
            sales.extend(parsed)

        return sales

    # =========================================================================
    # Balance Methods (ERC20 + Native)
    # =========================================================================

    async def get_native_balance(self, address: str) -> Decimal:
        """
        Get native RON balance for an address.

        Args:
            address: Wallet address (0x... or ronin:...)

        Returns:
            Balance in RON (e.g., Decimal("123.456"))
        """
        # Normalize address format (ronin:xxx or 0x...)
        if address.startswith("ronin:"):
            address = "0x" + address[6:]

        result = await self._call("eth_getBalance", [address, "latest"])

        # Convert wei to RON
        balance_wei = int(result, 16)
        balance_ron = Decimal(balance_wei) / Decimal(10**18)

        return balance_ron

    async def get_erc20_balance(
        self,
        token_address: str,
        wallet_address: str,
    ) -> Decimal:
        """
        Get ERC20 token balance using eth_call.

        Args:
            token_address: Token contract address (0x...)
            wallet_address: Wallet address (0x... or ronin:...)

        Returns:
            Balance in token units (e.g., Decimal("0.05") for 0.05 WETH)

        Note:
            Uses balanceOf(address) function call via eth_call.
        """
        # Normalize addresses
        if wallet_address.startswith("ronin:"):
            wallet_address = "0x" + wallet_address[6:]
        if token_address.startswith("ronin:"):
            token_address = "0x" + token_address[6:]

        # Encode balanceOf(address) call
        # balanceOf signature: 0x70a08231
        # Padded address parameter (32 bytes)
        padded_address = wallet_address[2:].lower().zfill(64)
        data = f"{self.BALANCE_OF_SIGNATURE}{padded_address}"

        # eth_call parameters
        call_params = {
            "to": token_address,
            "data": data,
        }

        result = await self._call("eth_call", [call_params, "latest"])

        # Parse uint256 result
        if not result or result == "0x":
            return Decimal(0)

        balance_raw = int(result, 16)
        balance_tokens = Decimal(balance_raw) / Decimal(10**18)

        return balance_tokens

    async def get_wallet_balances(
        self,
        wallet_address: str,
        token_contracts: Optional[dict[str, str]] = None,
    ) -> dict[str, Decimal]:
        """
        Get all token balances for a wallet in a single batch.

        Args:
            wallet_address: Wallet address (0x... or ronin:...)
            token_contracts: Optional custom token mapping
                           Default: {RON, WETH, WRON, AXS, SLP}

        Returns:
            Dict mapping token name to balance
            Example: {"RON": Decimal("123.456"), "WETH": Decimal("0.05"), ...}
        """
        if token_contracts is None:
            token_contracts = {
                "RON": self.RON_NATIVE,
                "WETH": self.WETH_CONTRACT,
                "WRON": self.WRON_CONTRACT,
                "AXS": self.AXS_CONTRACT,
                "SLP": self.SLP_CONTRACT,
            }

        balances = {}

        # Fetch all balances in parallel
        tasks = []
        token_names = []

        for token_name, contract_address in token_contracts.items():
            if contract_address == self.RON_NATIVE:
                tasks.append(self.get_native_balance(wallet_address))
            else:
                tasks.append(self.get_erc20_balance(contract_address, wallet_address))
            token_names.append(token_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for token_name, result in zip(token_names, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {token_name} balance: {result}")
                balances[token_name] = Decimal(0)
            else:
                balances[token_name] = result

        return balances

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_provider_stats(self) -> List[Dict]:
        """Get statistics for all providers."""
        return [
            {
                "name": p.name,
                "status": p.status.value,
                "total_requests": p.total_requests,
                "total_errors": p.total_errors,
                "error_rate": p.total_errors / max(p.total_requests, 1),
                "consecutive_errors": p.consecutive_errors,
            }
            for p in self.providers
        ]


# Convenience function for quick lookups
async def get_current_block() -> int:
    """Get current block number."""
    async with RoninRPCClient() as client:
        return await client.get_block_number()
