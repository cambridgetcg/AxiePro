"""
Test Data Factories

Provides factory classes for creating realistic test data with sensible defaults
and easy customization. All factories follow the same pattern:
- create(**kwargs) - Create a single instance
- create_batch(count, **kwargs) - Create multiple instances

Usage:
    from tests.factories import AxieFactory, ListingFactory

    # Create single Axie
    axie = AxieFactory.create(class_name="Beast", purity=6)

    # Create multiple Axies
    axies = AxieFactory.create_batch(5, class_name="Plant")

    # Create with listing
    listed_axie = AxieFactory.create(price=0.05)

    # Create listing
    listing = ListingFactory.create(axie_id=123, price=0.01)
"""

from .axie_factory import AxieFactory
from .listing_factory import ListingFactory
from .sale_factory import SaleFactory
from .wallet_factory import WalletFactory
from .gene_factory import GeneFactory

__all__ = [
    "AxieFactory",
    "ListingFactory",
    "SaleFactory",
    "WalletFactory",
    "GeneFactory",
]
