"""
Moralis API Client for Ronin blockchain data.

Provides access to:
- NFT metadata and transfers
- Wallet balances and holdings
- Token prices and data
- Transaction history
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class NFTTransfer:
    """Represents an NFT transfer event."""
    transaction_hash: str
    from_address: str
    to_address: str
    token_id: str
    contract_address: str
    block_number: int
    block_timestamp: datetime
    value: Optional[str] = None

    @classmethod
    def from_moralis(cls, data: dict) -> "NFTTransfer":
        return cls(
            transaction_hash=data.get("transaction_hash", ""),
            from_address=data.get("from_address", ""),
            to_address=data.get("to_address", ""),
            token_id=data.get("token_id", ""),
            contract_address=data.get("token_address", ""),
            block_number=int(data.get("block_number", 0)),
            block_timestamp=datetime.fromisoformat(
                data.get("block_timestamp", "").replace("Z", "+00:00")
            ) if data.get("block_timestamp") else datetime.now(),
            value=data.get("value"),
        )


@dataclass
class NFTMetadata:
    """NFT metadata from Moralis."""
    token_id: str
    contract_address: str
    name: Optional[str]
    symbol: Optional[str]
    token_uri: Optional[str]
    metadata: Optional[dict]
    owner: Optional[str]

    @classmethod
    def from_moralis(cls, data: dict) -> "NFTMetadata":
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None

        return cls(
            token_id=data.get("token_id", ""),
            contract_address=data.get("token_address", ""),
            name=data.get("name"),
            symbol=data.get("symbol"),
            token_uri=data.get("token_uri"),
            metadata=metadata,
            owner=data.get("owner_of"),
        )


@dataclass
class WalletNFTBalance:
    """NFT balance for a wallet."""
    token_id: str
    contract_address: str
    name: Optional[str]
    symbol: Optional[str]
    amount: int
    metadata: Optional[dict]

    @classmethod
    def from_moralis(cls, data: dict) -> "WalletNFTBalance":
        metadata = data.get("metadata")
        if isinstance(metadata, str):
            import json
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None

        return cls(
            token_id=data.get("token_id", ""),
            contract_address=data.get("token_address", ""),
            name=data.get("name"),
            symbol=data.get("symbol"),
            amount=int(data.get("amount", 1)),
            metadata=metadata,
        )


class MoralisAPIError(Exception):
    """Raised when Moralis API returns an error."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Moralis API error ({status_code}): {message}")


class MoralisClient:
    """
    Async client for Moralis Web3 API.

    Usage:
        async with MoralisClient() as client:
            nfts = await client.get_wallet_nfts("0x...")
    """

    # Ronin chain ID in Moralis
    RONIN_CHAIN = "ronin"

    # Axie NFT contract address on Ronin
    AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Moralis client.

        Args:
            api_key: Moralis API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.moralis_api_key
        self.base_url = settings.moralis_base_url
        self.rate_limit = settings.moralis_rate_limit
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_reset = datetime.now()

    async def __aenter__(self) -> "MoralisClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_headers(),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with API key."""
        if not self.api_key:
            raise MoralisAPIError(401, "Moralis API key not configured")
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
        }

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        **kwargs
    ) -> dict[str, Any]:
        """
        Make an API request with rate limiting.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            **kwargs: Additional request arguments

        Returns:
            JSON response data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        # Simple rate limiting
        await self._check_rate_limit()

        url = f"{self.base_url}{endpoint}"

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                **kwargs
            )

            if response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._request(method, endpoint, params, **kwargs)

            if response.status_code >= 400:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except Exception:
                    pass
                raise MoralisAPIError(response.status_code, error_msg)

            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise MoralisAPIError(0, str(e))

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        elapsed = (now - self._last_reset).total_seconds()

        if elapsed >= 60:
            self._request_count = 0
            self._last_reset = now

        if self._request_count >= self.rate_limit:
            wait_time = 60 - elapsed
            if wait_time > 0:
                logger.info(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._request_count = 0
                self._last_reset = datetime.now()

        self._request_count += 1

    # =========================================================================
    # NFT Endpoints
    # =========================================================================

    async def get_nft_metadata(
        self,
        token_id: str,
        contract_address: str = AXIE_CONTRACT,
    ) -> NFTMetadata:
        """
        Get metadata for a specific NFT.

        Args:
            token_id: The NFT token ID
            contract_address: NFT contract address (defaults to Axie)

        Returns:
            NFTMetadata object
        """
        endpoint = f"/nft/{contract_address}/{token_id}"
        params = {"chain": self.RONIN_CHAIN}

        data = await self._request("GET", endpoint, params=params)
        return NFTMetadata.from_moralis(data)

    async def get_wallet_nfts(
        self,
        wallet_address: str,
        contract_address: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[list[WalletNFTBalance], Optional[str]]:
        """
        Get NFTs owned by a wallet.

        Args:
            wallet_address: Wallet address to query
            contract_address: Filter by specific NFT contract
            cursor: Pagination cursor
            limit: Results per page (max 100)

        Returns:
            Tuple of (NFT list, next cursor)
        """
        endpoint = f"/{wallet_address}/nft"
        params = {
            "chain": self.RONIN_CHAIN,
            "limit": min(limit, 100),
        }

        if contract_address:
            params["token_addresses[]"] = contract_address

        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", endpoint, params=params)

        nfts = [
            WalletNFTBalance.from_moralis(item)
            for item in data.get("result", [])
        ]
        next_cursor = data.get("cursor")

        return nfts, next_cursor

    async def get_all_wallet_nfts(
        self,
        wallet_address: str,
        contract_address: Optional[str] = None,
        max_pages: int = 10,
    ) -> list[WalletNFTBalance]:
        """
        Get all NFTs for a wallet (auto-pagination).

        Args:
            wallet_address: Wallet address
            contract_address: Optional contract filter
            max_pages: Maximum pages to fetch

        Returns:
            List of all NFTs
        """
        all_nfts = []
        cursor = None

        for _ in range(max_pages):
            nfts, cursor = await self.get_wallet_nfts(
                wallet_address,
                contract_address=contract_address,
                cursor=cursor,
            )
            all_nfts.extend(nfts)

            if not cursor:
                break

        return all_nfts

    async def get_nft_transfers(
        self,
        wallet_address: Optional[str] = None,
        contract_address: str = AXIE_CONTRACT,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[list[NFTTransfer], Optional[str]]:
        """
        Get NFT transfer events.

        Args:
            wallet_address: Filter by wallet (optional)
            contract_address: NFT contract address
            from_block: Start block number
            to_block: End block number
            cursor: Pagination cursor
            limit: Results per page

        Returns:
            Tuple of (transfers list, next cursor)
        """
        if wallet_address:
            endpoint = f"/{wallet_address}/nft/transfers"
        else:
            endpoint = f"/nft/{contract_address}/transfers"

        params = {
            "chain": self.RONIN_CHAIN,
            "limit": min(limit, 100),
        }

        if from_block:
            params["from_block"] = from_block
        if to_block:
            params["to_block"] = to_block
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", endpoint, params=params)

        transfers = [
            NFTTransfer.from_moralis(item)
            for item in data.get("result", [])
        ]
        next_cursor = data.get("cursor")

        return transfers, next_cursor

    # =========================================================================
    # Wallet Endpoints
    # =========================================================================

    async def get_native_balance(self, wallet_address: str) -> dict:
        """
        Get native token (RON) balance for a wallet.

        Args:
            wallet_address: Wallet address

        Returns:
            Balance data with 'balance' in wei
        """
        endpoint = f"/{wallet_address}/balance"
        params = {"chain": self.RONIN_CHAIN}

        return await self._request("GET", endpoint, params=params)

    async def get_token_balances(
        self,
        wallet_address: str,
        token_addresses: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Get ERC20 token balances for a wallet.

        Args:
            wallet_address: Wallet address
            token_addresses: Filter by specific tokens

        Returns:
            List of token balance data
        """
        endpoint = f"/{wallet_address}/erc20"
        params = {"chain": self.RONIN_CHAIN}

        if token_addresses:
            params["token_addresses[]"] = token_addresses

        data = await self._request("GET", endpoint, params=params)
        return data if isinstance(data, list) else data.get("result", [])

    # =========================================================================
    # Transaction Endpoints
    # =========================================================================

    async def get_wallet_transactions(
        self,
        wallet_address: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> tuple[list[dict], Optional[str]]:
        """
        Get transactions for a wallet.

        Args:
            wallet_address: Wallet address
            from_block: Start block
            to_block: End block
            cursor: Pagination cursor
            limit: Results per page

        Returns:
            Tuple of (transactions list, next cursor)
        """
        endpoint = f"/{wallet_address}"
        params = {
            "chain": self.RONIN_CHAIN,
            "limit": min(limit, 100),
        }

        if from_block:
            params["from_block"] = from_block
        if to_block:
            params["to_block"] = to_block
        if cursor:
            params["cursor"] = cursor

        data = await self._request("GET", endpoint, params=params)

        return data.get("result", []), data.get("cursor")


# Convenience function for one-off requests
async def get_axie_owner(token_id: str) -> Optional[str]:
    """Quick function to get current owner of an Axie."""
    settings = get_settings()
    if not settings.moralis_api_key:
        return None

    async with MoralisClient() as client:
        try:
            metadata = await client.get_nft_metadata(token_id)
            return metadata.owner
        except MoralisAPIError:
            return None
