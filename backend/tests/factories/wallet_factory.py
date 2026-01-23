"""
Wallet Factory

Creates Ethereum/Ronin wallet addresses for testing.
Can generate addresses with known private keys for signature testing.
"""

from typing import Optional, Tuple
from eth_account import Account
import secrets


class WalletFactory:
    """Factory for creating test wallet addresses."""

    # Counter for deterministic address generation
    _counter: int = 0

    # Pre-defined test wallets for consistent testing
    KNOWN_WALLETS = {
        "seller": ("0x" + "a" * 40, "0x" + "a" * 64),
        "buyer": ("0x" + "b" * 40, "0x" + "b" * 64),
        "owner": ("0x" + "c" * 40, "0x" + "c" * 64),
        "contract": ("0x213073989821f738a7ba3520c3d31a1f9ad31bbd", None),  # Marketplace
    }

    @classmethod
    def create(cls, prefix: Optional[str] = None) -> str:
        """
        Create a random Ethereum address.

        Args:
            prefix: Optional prefix for the address (after 0x)

        Returns:
            Ethereum address (lowercase, with 0x prefix)
        """
        if prefix:
            # Create address with specific prefix (for readability in tests)
            remaining = 40 - len(prefix)
            return ("0x" + prefix + secrets.token_hex(remaining // 2)[:remaining]).lower()

        # Generate from random private key
        private_key = "0x" + secrets.token_hex(32)
        account = Account.from_key(private_key)
        return account.address.lower()

    @classmethod
    def create_deterministic(cls) -> str:
        """
        Create a deterministic address (sequential).

        Useful for tests that need consistent, predictable addresses.

        Returns:
            Deterministic Ethereum address
        """
        cls._counter += 1
        private_key = f"0x{cls._counter:064x}"
        account = Account.from_key(private_key)
        return account.address.lower()

    @classmethod
    def create_with_key(cls, seed: Optional[int] = None) -> Tuple[str, str]:
        """
        Create a wallet address with its private key.

        Useful for tests that need to sign messages.

        Args:
            seed: Optional seed for reproducible key generation

        Returns:
            Tuple of (address, private_key)
        """
        if seed is not None:
            private_key = f"0x{seed:064x}"
        else:
            private_key = "0x" + secrets.token_hex(32)

        account = Account.from_key(private_key)
        return account.address.lower(), private_key

    @classmethod
    def create_batch(cls, count: int) -> list[str]:
        """
        Create multiple unique addresses.

        Args:
            count: Number of addresses to create

        Returns:
            List of unique Ethereum addresses
        """
        return [cls.create() for _ in range(count)]

    @classmethod
    def get_seller(cls) -> str:
        """Get pre-defined seller address."""
        return cls.KNOWN_WALLETS["seller"][0]

    @classmethod
    def get_buyer(cls) -> str:
        """Get pre-defined buyer address."""
        return cls.KNOWN_WALLETS["buyer"][0]

    @classmethod
    def get_owner(cls) -> str:
        """Get pre-defined owner address."""
        return cls.KNOWN_WALLETS["owner"][0]

    @classmethod
    def get_marketplace_contract(cls) -> str:
        """Get the Axie marketplace contract address."""
        return cls.KNOWN_WALLETS["contract"][0]

    @classmethod
    def reset(cls) -> None:
        """Reset the counter for deterministic generation."""
        cls._counter = 0
