"""
Goldrush (Covalent) API Client for Ronin/Axie data.

Goldrush provides unified blockchain data APIs including NFT data for Ronin chain.
Docs: https://goldrush.dev/docs/api/
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class NFTMetadata:
    """NFT metadata from Goldrush."""
    token_id: str
    contract_address: str
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    external_url: Optional[str] = None
    attributes: list[dict] = field(default_factory=list)
    owner: Optional[str] = None


@dataclass
class TokenBalance:
    """Token balance from Goldrush."""
    contract_address: str
    contract_name: Optional[str] = None
    contract_ticker: Optional[str] = None
    balance: Decimal = Decimal(0)
    quote: Optional[Decimal] = None  # USD value
    logo_url: Optional[str] = None


@dataclass
class Transaction:
    """Transaction from Goldrush."""
    tx_hash: str
    block_height: int
    block_signed_at: datetime
    from_address: str
    to_address: Optional[str] = None
    value: Decimal = Decimal(0)
    gas_spent: int = 0
    successful: bool = True


class GoldrushAPIError(Exception):
    """Goldrush API error."""
    def __init__(self, message: str, response: Optional[dict] = None):
        super().__init__(message)
        self.response = response


class GoldrushClient:
    """
    Async client for Goldrush API.

    Usage:
        async with GoldrushClient() as client:
            nfts = await client.get_nfts_for_address("0x...")
    """

    # Ronin/Axie chain identifier in Goldrush
    RONIN_CHAIN = "axie-mainnet"

    # Known Axie contract addresses on Ronin
    AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
    LAND_CONTRACT = "0x8c811e3c958e190f5ec15fb376533a3398620500"
    ITEM_CONTRACT = "0xa96660f0e4a3e9bc7388925d245a6d4d79e21259"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Goldrush client.

        Args:
            api_key: Goldrush API key. If not provided, uses settings.
        """
        settings = get_settings()
        self.api_key = api_key or settings.goldrush_api_key
        self.base_url = settings.goldrush_base_url
        self.rate_limit = settings.goldrush_rate_limit
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_reset = datetime.now()

    async def __aenter__(self) -> "GoldrushClient":
        """Async context manager entry."""
        if not self.api_key:
            raise GoldrushAPIError("Goldrush API key not configured")

        self._client = httpx.AsyncClient(
            timeout=30.0,
            auth=(self.api_key, ""),  # Goldrush uses basic auth with key as username
            headers={
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _check_rate_limit(self):
        """Check and enforce rate limiting."""
        now = datetime.now()
        if (now - self._last_reset).seconds >= 60:
            self._request_count = 0
            self._last_reset = now

        if self._request_count >= self.rate_limit:
            sleep_time = 60 - (now - self._last_reset).seconds
            logger.warning(f"Rate limit reached, sleeping {sleep_time}s")
            await asyncio.sleep(sleep_time)
            self._request_count = 0
            self._last_reset = datetime.now()

        self._request_count += 1

    async def _request(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Make API request.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response data
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")

        await self._check_rate_limit()

        url = f"{self.base_url}/{endpoint}"

        try:
            response = await self._client.get(url, params=params)

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await self._request(endpoint, params)

            if response.status_code >= 400:
                raise GoldrushAPIError(
                    f"HTTP {response.status_code}: {response.text}"
                )

            data = response.json()

            if data.get("error"):
                raise GoldrushAPIError(
                    data.get("error_message", "Unknown error"),
                    data
                )

            return data.get("data", data)

        except httpx.RequestError as e:
            raise GoldrushAPIError(str(e))

    # ==================== NFT Endpoints ====================

    async def get_nfts_for_address(
        self,
        address: str,
        contract_address: Optional[str] = None,
    ) -> list[NFTMetadata]:
        """
        Get NFTs owned by an address.

        Args:
            address: Wallet address
            contract_address: Filter by specific NFT contract (e.g., Axie contract)

        Returns:
            List of NFT metadata
        """
        endpoint = f"{self.RONIN_CHAIN}/address/{address}/balances_nft/"
        params = {"with-uncached": "true"}

        data = await self._request(endpoint, params)

        nfts = []
        for item in data.get("items", []):
            # Filter by contract if specified
            if contract_address and item.get("contract_address", "").lower() != contract_address.lower():
                continue

            for nft_data in item.get("nft_data", []):
                nft = NFTMetadata(
                    token_id=nft_data.get("token_id", ""),
                    contract_address=item.get("contract_address", ""),
                    name=nft_data.get("external_data", {}).get("name"),
                    description=nft_data.get("external_data", {}).get("description"),
                    image_url=nft_data.get("external_data", {}).get("image"),
                    external_url=nft_data.get("external_data", {}).get("external_url"),
                    attributes=nft_data.get("external_data", {}).get("attributes", []),
                    owner=address,
                )
                nfts.append(nft)

        return nfts

    async def get_axies_for_address(self, address: str) -> list[NFTMetadata]:
        """Get Axies owned by an address."""
        return await self.get_nfts_for_address(address, self.AXIE_CONTRACT)

    async def get_nft_token_ids(
        self,
        contract_address: str,
        page_size: int = 100,
    ) -> list[str]:
        """
        Get all token IDs for an NFT contract.

        Args:
            contract_address: NFT contract address
            page_size: Number of results per page

        Returns:
            List of token IDs
        """
        endpoint = f"{self.RONIN_CHAIN}/nft/{contract_address}/token_ids/"
        params = {"page-size": page_size}

        data = await self._request(endpoint, params)

        return [item.get("token_id") for item in data.get("items", [])]

    async def get_nft_metadata(
        self,
        contract_address: str,
        token_id: str,
    ) -> Optional[NFTMetadata]:
        """
        Get metadata for a specific NFT.

        Args:
            contract_address: NFT contract address
            token_id: Token ID

        Returns:
            NFT metadata or None if not found
        """
        endpoint = f"{self.RONIN_CHAIN}/nft/{contract_address}/metadata/{token_id}/"

        try:
            data = await self._request(endpoint)

            if not data.get("items"):
                return None

            item = data["items"][0]
            nft_data = item.get("nft_data", {})
            external_data = nft_data.get("external_data", {})

            return NFTMetadata(
                token_id=token_id,
                contract_address=contract_address,
                name=external_data.get("name"),
                description=external_data.get("description"),
                image_url=external_data.get("image"),
                external_url=external_data.get("external_url"),
                attributes=external_data.get("attributes", []),
                owner=nft_data.get("owner"),
            )
        except GoldrushAPIError:
            return None

    async def get_axie_metadata(self, axie_id: str) -> Optional[NFTMetadata]:
        """Get metadata for a specific Axie."""
        return await self.get_nft_metadata(self.AXIE_CONTRACT, axie_id)

    # ==================== Balance Endpoints ====================

    async def get_token_balances(self, address: str) -> list[TokenBalance]:
        """
        Get token balances for an address.

        Args:
            address: Wallet address

        Returns:
            List of token balances
        """
        endpoint = f"{self.RONIN_CHAIN}/address/{address}/balances_v2/"
        params = {"quote-currency": "USD"}

        data = await self._request(endpoint, params)

        balances = []
        for item in data.get("items", []):
            balance = TokenBalance(
                contract_address=item.get("contract_address", ""),
                contract_name=item.get("contract_name"),
                contract_ticker=item.get("contract_ticker_symbol"),
                balance=Decimal(str(item.get("balance", 0))) / Decimal(10 ** item.get("contract_decimals", 18)),
                quote=Decimal(str(item.get("quote", 0))) if item.get("quote") else None,
                logo_url=item.get("logo_url"),
            )
            balances.append(balance)

        return balances

    # ==================== Transaction Endpoints ====================

    async def get_transactions(
        self,
        address: str,
        page_size: int = 100,
    ) -> list[Transaction]:
        """
        Get transactions for an address.

        Args:
            address: Wallet address
            page_size: Number of results per page

        Returns:
            List of transactions
        """
        endpoint = f"{self.RONIN_CHAIN}/address/{address}/transactions_v3/"
        params = {"page-size": page_size}

        data = await self._request(endpoint, params)

        transactions = []
        for item in data.get("items", []):
            tx = Transaction(
                tx_hash=item.get("tx_hash", ""),
                block_height=item.get("block_height", 0),
                block_signed_at=datetime.fromisoformat(
                    item.get("block_signed_at", "").replace("Z", "+00:00")
                ),
                from_address=item.get("from_address", ""),
                to_address=item.get("to_address"),
                value=Decimal(str(item.get("value", 0))) / Decimal(10 ** 18),
                gas_spent=item.get("gas_spent", 0),
                successful=item.get("successful", True),
            )
            transactions.append(tx)

        return transactions

    async def get_nft_transactions(
        self,
        contract_address: str,
        token_id: str,
    ) -> list[Transaction]:
        """
        Get transaction history for a specific NFT.

        Args:
            contract_address: NFT contract address
            token_id: Token ID

        Returns:
            List of transactions
        """
        endpoint = f"{self.RONIN_CHAIN}/nft/{contract_address}/transactions/{token_id}/"

        data = await self._request(endpoint)

        transactions = []
        for item in data.get("items", []):
            tx = Transaction(
                tx_hash=item.get("tx_hash", ""),
                block_height=item.get("block_height", 0),
                block_signed_at=datetime.fromisoformat(
                    item.get("block_signed_at", "").replace("Z", "+00:00")
                ),
                from_address=item.get("from_address", ""),
                to_address=item.get("to_address"),
                value=Decimal(str(item.get("value", 0))) / Decimal(10 ** 18),
                gas_spent=item.get("gas_spent", 0),
                successful=item.get("successful", True),
            )
            transactions.append(tx)

        return transactions

    # ==================== Market Data ====================

    async def get_nft_market_stats(
        self,
        contract_address: str,
    ) -> dict[str, Any]:
        """
        Get market statistics for an NFT collection.

        Args:
            contract_address: NFT contract address

        Returns:
            Market stats dict
        """
        endpoint = f"{self.RONIN_CHAIN}/nft_market/{contract_address}/"

        data = await self._request(endpoint)

        return {
            "floor_price": data.get("floor_price_quote"),
            "total_volume": data.get("total_volume_quote"),
            "avg_volume_24h": data.get("avg_volume_quote_24h"),
            "unique_holders": data.get("unique_token_owners"),
            "total_supply": data.get("total_token_count"),
        }


# Test function
async def _test():
    """Test the Goldrush client."""
    async with GoldrushClient() as client:
        # Test getting Axie market stats
        stats = await client.get_nft_market_stats(GoldrushClient.AXIE_CONTRACT)
        print(f"Axie Market Stats: {stats}")


if __name__ == "__main__":
    asyncio.run(_test())
