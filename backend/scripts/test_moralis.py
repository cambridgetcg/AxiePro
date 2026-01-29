#!/usr/bin/env python3
"""
Quick test script to verify Moralis API connectivity.

Run locally with: python -m scripts.test_moralis
Or in Lambda environment.
"""

import asyncio
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.moralis_client import MoralisClient, MoralisAPIError


async def test_moralis():
    """Test Moralis API connectivity."""
    print("Testing Moralis API connectivity...")

    # Test with a known Axie ID
    test_axie_id = "123456"

    try:
        async with MoralisClient() as client:
            print(f"✓ Client initialized with API key")

            # Test getting NFT metadata
            print(f"\nFetching metadata for Axie #{test_axie_id}...")
            metadata = await client.get_nft_metadata(test_axie_id)

            print(f"✓ Got metadata:")
            print(f"  - Token ID: {metadata.token_id}")
            print(f"  - Contract: {metadata.contract_address}")
            print(f"  - Name: {metadata.name}")
            print(f"  - Owner: {metadata.owner}")

            if metadata.metadata:
                print(f"  - Class: {metadata.metadata.get('class', 'N/A')}")
                parts = metadata.metadata.get('parts', [])
                print(f"  - Parts: {len(parts)} parts")

            print("\n✓ Moralis API is working correctly!")
            return True

    except MoralisAPIError as e:
        print(f"\n✗ Moralis API error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    # Check for API key in environment
    api_key = os.environ.get("MORALIS_API_KEY")
    if not api_key:
        print("Note: MORALIS_API_KEY not in environment, will try from settings")

    success = asyncio.run(test_moralis())
    sys.exit(0 if success else 1)
