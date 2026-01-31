"""
Wallet Balance Service

Aggregates wallet token balances from Ronin RPC and provides caching.
Supports real-time balance fetching with configurable cache TTL.

Cache Strategy:
- wallet_balances:{address} -> Dict of token balances (TTL: 5 min)
- Token prices fetched from config (future: external price oracle)
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict
from dataclasses import dataclass

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.wallet import Wallet, WalletTokenBalance, TokenType
from src.services.ronin_rpc_client import RoninRPCClient
from src.services.cache import RedisCacheManager

logger = logging.getLogger(__name__)


@dataclass
class BalanceData:
    """Single token balance data."""

    token: str
    balance: Decimal
    balance_usd: Optional[Decimal]
    token_price_usd: Optional[Decimal]
    last_updated: datetime


@dataclass
class WalletBalanceConfig:
    """Configuration for wallet balance service."""

    cache_ttl: int = 300  # 5 minutes
    stale_threshold_minutes: int = 5  # Refresh if older than 5 min
    default_token_prices: dict[str, float] = None  # USD prices

    def __post_init__(self):
        if self.default_token_prices is None:
            # Default token prices (should be fetched from price oracle in production)
            self.default_token_prices = {
                "RON": 0.15,
                "WETH": 3800.0,
                "WRON": 0.15,
                "AXS": 7.0,
                "SLP": 0.003,
            }


class WalletBalanceService:
    """
    Service for fetching and caching wallet token balances.

    Responsibilities:
    - Fetch balances from Ronin RPC
    - Cache balances in database and Redis
    - Convert balances to USD using price oracle
    - Handle cache invalidation and refresh

    Usage:
        service = WalletBalanceService(db, rpc_client, cache)
        balances = await service.get_balances(wallet_address)
    """

    def __init__(
        self,
        db: AsyncSession,
        rpc_client: Optional[RoninRPCClient] = None,
        cache: Optional[RedisCacheManager] = None,
        config: Optional[WalletBalanceConfig] = None,
    ):
        self.db = db
        self.rpc_client = rpc_client
        self.cache = cache
        self.config = config or WalletBalanceConfig()

    async def get_balances(
        self,
        wallet_address: str,
        force_refresh: bool = False,
        use_cache: bool = True,
    ) -> Dict[str, BalanceData]:
        """
        Get token balances for a wallet.

        Args:
            wallet_address: Wallet address (0x... or ronin:...)
            force_refresh: Force fetch from blockchain (skip cache)
            use_cache: Use Redis cache if available

        Returns:
            Dict mapping token name to BalanceData
        """
        wallet_address = self._normalize_address(wallet_address)

        # Step 1: Try Redis cache
        if use_cache and not force_refresh and self.cache:
            cached = await self._get_from_redis(wallet_address)
            if cached:
                logger.debug(f"Balances for {wallet_address} from Redis cache")
                return cached

        # Step 2: Try database (if not stale)
        if not force_refresh:
            db_balances = await self._get_from_db(wallet_address)
            if db_balances and not self._is_stale(db_balances):
                logger.debug(f"Balances for {wallet_address} from database")
                # Cache in Redis for next request
                if self.cache:
                    await self._cache_in_redis(wallet_address, db_balances)
                return db_balances

        # Step 3: Fetch from blockchain
        logger.info(f"Fetching fresh balances for {wallet_address} from RPC")
        balances = await self._fetch_from_blockchain(wallet_address)

        # Step 4: Update database
        await self._update_database(wallet_address, balances)

        # Step 5: Cache in Redis
        if self.cache:
            await self._cache_in_redis(wallet_address, balances)

        return balances

    async def refresh_balances(
        self,
        wallet_address: str,
    ) -> Dict[str, BalanceData]:
        """
        Force refresh balances from blockchain.

        Useful for triggered updates (e.g., after a transaction).
        """
        return await self.get_balances(wallet_address, force_refresh=True)

    async def batch_refresh(
        self,
        wallet_addresses: list[str],
        max_concurrent: int = 5,
    ) -> Dict[str, Dict[str, BalanceData]]:
        """
        Refresh balances for multiple wallets in parallel.

        Args:
            wallet_addresses: List of wallet addresses
            max_concurrent: Max parallel RPC calls

        Returns:
            Dict mapping wallet address to balances
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_one(address: str):
            async with semaphore:
                return address, await self.refresh_balances(address)

        tasks = [fetch_one(addr) for addr in wallet_addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Failed to refresh balance: {result}")
                continue
            address, balances = result
            output[address] = balances

        return output

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _normalize_address(self, address: str) -> str:
        """Normalize address to 0x format."""
        if address.startswith("ronin:"):
            return "0x" + address[6:]
        return address.lower()

    async def _get_from_redis(
        self, wallet_address: str
    ) -> Optional[Dict[str, BalanceData]]:
        """Get balances from Redis cache."""
        if not self.cache or not self.cache.is_connected:
            return None

        try:
            key = self.cache._key("wallet_balances", wallet_address)
            data = await self.cache._get(key)

            if data:
                # Deserialize BalanceData objects
                balances = {}
                for token, balance_dict in data.items():
                    balances[token] = BalanceData(
                        token=balance_dict["token"],
                        balance=Decimal(str(balance_dict["balance"])),
                        balance_usd=(
                            Decimal(str(balance_dict["balance_usd"]))
                            if balance_dict.get("balance_usd")
                            else None
                        ),
                        token_price_usd=(
                            Decimal(str(balance_dict["token_price_usd"]))
                            if balance_dict.get("token_price_usd")
                            else None
                        ),
                        last_updated=datetime.fromisoformat(
                            balance_dict["last_updated"]
                        ),
                    )
                return balances
        except Exception as e:
            logger.warning(f"Failed to get balances from Redis: {e}")

        return None

    async def _cache_in_redis(
        self, wallet_address: str, balances: Dict[str, BalanceData]
    ):
        """Cache balances in Redis."""
        if not self.cache or not self.cache.is_connected:
            return

        try:
            # Serialize BalanceData objects
            serializable = {}
            for token, balance_data in balances.items():
                serializable[token] = {
                    "token": balance_data.token,
                    "balance": float(balance_data.balance),
                    "balance_usd": (
                        float(balance_data.balance_usd)
                        if balance_data.balance_usd
                        else None
                    ),
                    "token_price_usd": (
                        float(balance_data.token_price_usd)
                        if balance_data.token_price_usd
                        else None
                    ),
                    "last_updated": balance_data.last_updated.isoformat(),
                }

            key = self.cache._key("wallet_balances", wallet_address)
            await self.cache._set(key, serializable, self.config.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache balances in Redis: {e}")

    async def _get_from_db(
        self, wallet_address: str
    ) -> Optional[Dict[str, BalanceData]]:
        """Get balances from database."""
        result = await self.db.execute(
            select(WalletTokenBalance).where(
                WalletTokenBalance.wallet_address == wallet_address
            )
        )
        rows = result.scalars().all()

        if not rows:
            return None

        balances = {}
        for row in rows:
            balances[row.token_type.value] = BalanceData(
                token=row.token_type.value,
                balance=row.balance,
                balance_usd=row.balance_usd,
                token_price_usd=row.token_price_usd,
                last_updated=row.last_updated,
            )

        return balances

    def _is_stale(self, balances: Dict[str, BalanceData]) -> bool:
        """Check if any balance is stale."""
        now = datetime.now(timezone.utc)
        threshold = self.config.stale_threshold_minutes * 60

        for balance_data in balances.values():
            # Ensure balance_data.last_updated is timezone-aware
            last_updated = balance_data.last_updated
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)

            age_seconds = (now - last_updated).total_seconds()
            if age_seconds > threshold:
                return True

        return False

    async def _fetch_from_blockchain(
        self, wallet_address: str
    ) -> Dict[str, BalanceData]:
        """Fetch balances from Ronin blockchain."""
        if not self.rpc_client:
            raise RuntimeError("RPC client not configured")

        # Fetch all token balances
        raw_balances = await self.rpc_client.get_wallet_balances(wallet_address)

        # Get current block number for metadata
        block_number = await self.rpc_client.get_block_number()

        # Convert to BalanceData with USD values
        now = datetime.now(timezone.utc)
        balances = {}

        for token, balance in raw_balances.items():
            price_usd = Decimal(str(self.config.default_token_prices.get(token, 0)))
            balance_usd = balance * price_usd if price_usd > 0 else None

            balances[token] = BalanceData(
                token=token,
                balance=balance,
                balance_usd=balance_usd,
                token_price_usd=price_usd if price_usd > 0 else None,
                last_updated=now,
            )

        return balances

    async def _update_database(
        self, wallet_address: str, balances: Dict[str, BalanceData]
    ):
        """Update database with fresh balances."""
        # Ensure wallet exists
        wallet_result = await self.db.execute(
            select(Wallet).where(Wallet.address == wallet_address)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            # Create wallet record
            wallet = Wallet(address=wallet_address)
            self.db.add(wallet)

        # Get current block number for metadata
        block_number = (
            await self.rpc_client.get_block_number() if self.rpc_client else None
        )

        # Upsert balances
        for token, balance_data in balances.items():
            # Try to find existing record
            result = await self.db.execute(
                select(WalletTokenBalance).where(
                    and_(
                        WalletTokenBalance.wallet_address == wallet_address,
                        WalletTokenBalance.token_type == TokenType(token),
                    )
                )
            )
            record = result.scalar_one_or_none()

            if record:
                # Update existing
                record.balance = balance_data.balance
                record.balance_usd = balance_data.balance_usd
                record.token_price_usd = balance_data.token_price_usd
                record.last_updated = balance_data.last_updated
                record.block_number = block_number
            else:
                # Insert new
                record = WalletTokenBalance(
                    wallet_address=wallet_address,
                    token_type=TokenType(token),
                    balance=balance_data.balance,
                    balance_usd=balance_data.balance_usd,
                    token_price_usd=balance_data.token_price_usd,
                    last_updated=balance_data.last_updated,
                    block_number=block_number,
                )
                self.db.add(record)

        await self.db.commit()


# Dependency injection helper
async def get_wallet_balance_service(
    db: AsyncSession,
) -> WalletBalanceService:
    """
    Get WalletBalanceService instance with dependencies.

    Usage in FastAPI:
        service: WalletBalanceService = Depends(get_wallet_balance_service)
    """
    from src.services.cache import get_cache_manager

    cache = await get_cache_manager()
    rpc_client = RoninRPCClient()  # Uses default public RPC

    async with rpc_client:
        service = WalletBalanceService(
            db=db,
            rpc_client=rpc_client,
            cache=cache,
        )
        yield service
