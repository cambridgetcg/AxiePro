"""
Listing Factory

Creates marketplace listing test data.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .wallet_factory import WalletFactory


class ListingFactory:
    """Factory for creating test market listings."""

    # Counter for unique listing IDs
    _id_counter: int = 1000

    # ETH/USD conversion rate for tests
    ETH_USD_RATE: Decimal = Decimal("2000.00")

    @classmethod
    def create(
        cls,
        listing_id: Optional[int] = None,
        axie_id: Optional[int] = None,
        price: float = 0.01,
        seller: Optional[str] = None,
        listed_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None,
        status: str = "active",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a test listing.

        Args:
            listing_id: Listing ID (auto-generated if None)
            axie_id: ID of the Axie being listed
            price: Price in ETH
            seller: Seller wallet address
            listed_at: When the listing was created
            expires_at: When the listing expires
            status: Listing status (active, sold, cancelled)
            **kwargs: Additional fields to override

        Returns:
            Dictionary with listing data
        """
        # Generate unique ID
        if listing_id is None:
            cls._id_counter += 1
            listing_id = cls._id_counter

        # Generate axie_id if not provided
        if axie_id is None:
            axie_id = listing_id + 100000

        # Generate seller if not provided
        if seller is None:
            seller = WalletFactory.get_seller()

        # Set timestamps
        if listed_at is None:
            listed_at = datetime.utcnow() - timedelta(hours=1)

        if expires_at is None:
            expires_at = listed_at + timedelta(days=30)

        # Calculate USD price
        price_decimal = Decimal(str(price))
        price_usd = price_decimal * cls.ETH_USD_RATE

        listing = {
            "id": listing_id,
            "axieId": str(axie_id),
            "seller": seller.lower(),
            "price": str(price_decimal),
            "priceEth": str(price_decimal),
            "priceUsd": str(price_usd.quantize(Decimal("0.01"))),
            "listedAt": listed_at.isoformat() + "Z",
            "expiresAt": expires_at.isoformat() + "Z",
            "status": status,
            "marketplace": "official",
        }

        # Apply any overrides
        listing.update(kwargs)

        return listing

    @classmethod
    def create_batch(
        cls,
        count: int,
        min_price: float = 0.001,
        max_price: float = 1.0,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Create multiple listings with varying prices.

        Args:
            count: Number of listings to create
            min_price: Minimum price in ETH
            max_price: Maximum price in ETH
            **kwargs: Additional fields applied to all listings

        Returns:
            List of listing dictionaries
        """
        import random
        listings = []
        for _ in range(count):
            price = random.uniform(min_price, max_price)
            listings.append(cls.create(price=price, **kwargs))
        return listings

    @classmethod
    def create_cheap(cls, **kwargs: Any) -> Dict[str, Any]:
        """Create a cheap listing (0.001 ETH)."""
        return cls.create(price=0.001, **kwargs)

    @classmethod
    def create_expensive(cls, price: float = 10.0, **kwargs: Any) -> Dict[str, Any]:
        """Create an expensive listing."""
        return cls.create(price=price, **kwargs)

    @classmethod
    def create_expired(cls, **kwargs: Any) -> Dict[str, Any]:
        """Create an expired listing."""
        past_date = datetime.utcnow() - timedelta(days=31)
        return cls.create(
            listed_at=past_date,
            expires_at=past_date + timedelta(days=30),
            status="expired",
            **kwargs,
        )

    @classmethod
    def create_sold(cls, **kwargs: Any) -> Dict[str, Any]:
        """Create a sold listing."""
        return cls.create(status="sold", **kwargs)

    @classmethod
    def create_cancelled(cls, **kwargs: Any) -> Dict[str, Any]:
        """Create a cancelled listing."""
        return cls.create(status="cancelled", **kwargs)

    @classmethod
    def reset(cls) -> None:
        """Reset the ID counter."""
        cls._id_counter = 1000
