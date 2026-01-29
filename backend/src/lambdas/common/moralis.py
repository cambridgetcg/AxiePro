"""
Moralis API utilities for Lambda functions.

Provides configuration and helpers for interacting with Moralis Web3 API.
"""

from typing import Optional
from .aws import get_secrets

# Moralis API configuration
MORALIS_API_BASE_URL = "https://deep-index.moralis.io/api/v2.2"
MORALIS_RONIN_CHAIN = "ronin"

# Axie contract addresses
AXIE_CONTRACT = "0x32950db2a7164ae833121501c797d79e7b79d74c"
LAND_CONTRACT = "0x8c811e3c958e190f5ec15fb376533a3398620500"
ITEM_CONTRACT = "0xa96660f0e4a3e9bc7388925d245a6d4d79e21259"


def get_moralis_api_key() -> Optional[str]:
    """Get Moralis API key from secrets."""
    secrets = get_secrets()
    return secrets.get("MORALIS_API_KEY")


def get_moralis_headers(api_key: Optional[str] = None) -> dict:
    """Get headers for Moralis API requests."""
    key = api_key or get_moralis_api_key()
    if not key:
        raise ValueError("Moralis API key not configured")
    return {
        "X-API-Key": key,
        "Accept": "application/json",
    }


def get_moralis_nft_endpoint(token_id: str, contract: str = AXIE_CONTRACT) -> str:
    """Get endpoint URL for fetching NFT metadata."""
    return f"{MORALIS_API_BASE_URL}/nft/{contract}/{token_id}?chain={MORALIS_RONIN_CHAIN}"


def get_moralis_wallet_nfts_endpoint(wallet_address: str, contract: Optional[str] = None) -> str:
    """Get endpoint URL for fetching wallet NFTs."""
    url = f"{MORALIS_API_BASE_URL}/{wallet_address}/nft?chain={MORALIS_RONIN_CHAIN}"
    if contract:
        url += f"&token_addresses[]={contract}"
    return url


def get_moralis_transfers_endpoint(
    contract: str = AXIE_CONTRACT,
    from_block: Optional[int] = None,
    to_block: Optional[int] = None,
) -> str:
    """Get endpoint URL for fetching NFT transfers."""
    url = f"{MORALIS_API_BASE_URL}/nft/{contract}/transfers?chain={MORALIS_RONIN_CHAIN}"
    if from_block:
        url += f"&from_block={from_block}"
    if to_block:
        url += f"&to_block={to_block}"
    return url
