"""
Sale Factory

Creates historical sale test data.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import secrets

from .wallet_factory import WalletFactory


class SaleFactory:
    """Factory for creating test sales records."""

    # Counter for unique sale IDs
    _id_counter: int = 5000

    # ETH/USD conversion rate for tests
    ETH_USD_RATE: Decimal = Decimal("2000.00")

    @classmethod
    def create(
        cls,
        sale_id: Optional[int] = None,
        axie_id: Optional[int] = None,
        price: float = 0.01,
        buyer: Optional[str] = None,
        seller: Optional[str] = None,
        sold_at: Optional[datetime] = None,
        tx_hash: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a test sale record.

        Args:
            sale_id: Sale ID (auto-generated if None)
            axie_id: ID of the Axie sold
            price: Sale price in ETH
            buyer: Buyer wallet address
            seller: Seller wallet address
            sold_at: When the sale occurred
            tx_hash: Transaction hash
            **kwargs: Additional fields to override

        Returns:
            Dictionary with sale data
        """
        # Generate unique ID
        if sale_id is None:
            cls._id_counter += 1
            sale_id = cls._id_counter

        # Generate axie_id if not provided
        if axie_id is None:
            axie_id = sale_id + 100000

        # Generate addresses if not provided
        if buyer is None:
            buyer = WalletFactory.get_buyer()
        if seller is None:
            seller = WalletFactory.get_seller()

        # Set timestamp
        if sold_at is None:
            sold_at = datetime.utcnow() - timedelta(hours=1)

        # Generate transaction hash
        if tx_hash is None:
            tx_hash = "0x" + secrets.token_hex(32)

        # Calculate USD price
        price_decimal = Decimal(str(price))
        price_usd = price_decimal * cls.ETH_USD_RATE

        sale = {
            "id": sale_id,
            "axieId": str(axie_id),
            "buyer": buyer.lower(),
            "seller": seller.lower(),
            "price": str(price_decimal),
            "priceEth": str(price_decimal),
            "priceUsd": str(price_usd.quantize(Decimal("0.01"))),
            "soldAt": sold_at.isoformat() + "Z",
            "txHash": tx_hash,
            "marketplace": "official",
        }

        # Apply any overrides
        sale.update(kwargs)

        return sale

    @classmethod
    def create_batch(
        cls,
        count: int,
        min_price: float = 0.001,
        max_price: float = 1.0,
        days_back: int = 30,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Create multiple sales distributed over time.

        Args:
            count: Number of sales to create
            min_price: Minimum price in ETH
            max_price: Maximum price in ETH
            days_back: Distribute sales over this many days
            **kwargs: Additional fields applied to all sales

        Returns:
            List of sale dictionaries, sorted by date descending
        """
        import random
        sales = []
        now = datetime.utcnow()

        for i in range(count):
            # Distribute sales over time
            hours_ago = random.uniform(0, days_back * 24)
            sold_at = now - timedelta(hours=hours_ago)

            price = random.uniform(min_price, max_price)
            sales.append(cls.create(
                price=price,
                sold_at=sold_at,
                **kwargs
            ))

        # Sort by date descending (most recent first)
        sales.sort(key=lambda x: x["soldAt"], reverse=True)
        return sales

    @classmethod
    def create_for_axie(
        cls,
        axie_id: int,
        count: int = 3,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Create sale history for a specific Axie.

        Args:
            axie_id: The Axie's ID
            count: Number of historical sales
            **kwargs: Additional fields

        Returns:
            List of sales for the Axie
        """
        return cls.create_batch(count, axie_id=axie_id, **kwargs)

    @classmethod
    def create_recent(cls, hours_ago: int = 1, **kwargs: Any) -> Dict[str, Any]:
        """Create a recent sale."""
        sold_at = datetime.utcnow() - timedelta(hours=hours_ago)
        return cls.create(sold_at=sold_at, **kwargs)

    @classmethod
    def create_old(cls, days_ago: int = 30, **kwargs: Any) -> Dict[str, Any]:
        """Create an old sale."""
        sold_at = datetime.utcnow() - timedelta(days=days_ago)
        return cls.create(sold_at=sold_at, **kwargs)

    @classmethod
    def reset(cls) -> None:
        """Reset the ID counter."""
        cls._id_counter = 5000
