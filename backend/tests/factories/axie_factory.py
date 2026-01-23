"""
Axie Factory

Creates realistic Axie test data including:
- Basic info (id, class, name)
- Genes and parts
- Stats
- Optional listing data
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import random

from .gene_factory import GeneFactory
from .wallet_factory import WalletFactory


class AxieFactory:
    """Factory for creating test Axie data."""

    # Counter for unique IDs
    _id_counter: int = 100000

    # Axie class configurations
    CLASSES = ["Beast", "Aquatic", "Plant", "Bird", "Bug", "Reptile", "Mech", "Dawn", "Dusk"]

    # Base stats by class
    BASE_STATS = {
        "Beast": {"hp": 31, "speed": 35, "skill": 31, "morale": 43},
        "Aquatic": {"hp": 39, "speed": 39, "skill": 35, "morale": 27},
        "Plant": {"hp": 61, "speed": 31, "skill": 31, "morale": 41},
        "Bird": {"hp": 27, "speed": 43, "skill": 35, "morale": 35},
        "Bug": {"hp": 35, "speed": 35, "skill": 35, "morale": 35},
        "Reptile": {"hp": 39, "speed": 35, "skill": 31, "morale": 35},
        "Mech": {"hp": 31, "speed": 39, "skill": 43, "morale": 27},
        "Dawn": {"hp": 35, "speed": 35, "skill": 39, "morale": 31},
        "Dusk": {"hp": 43, "speed": 39, "skill": 27, "morale": 31},
    }

    # Part names by type (simplified)
    PART_NAMES = {
        "eyes": ["Chubby", "Clear", "Confused", "Sleepy", "Blossom", "Kawaii"],
        "ears": ["Zen", "Puppy", "Nut Cracker", "Leafy", "Gill", "Larva"],
        "mouth": ["Goda", "Axie Kiss", "Piranha", "Serious", "Zigzag", "Mosquito"],
        "horn": ["Imp", "Little Branch", "Cactus", "Kestrel", "Antenna", "Scaly Spear"],
        "back": ["Ronin", "Goldfish", "Pumpkin", "Balloon", "Sandal", "Bone Sail"],
        "tail": ["Hare", "Nimo", "Carrot", "Post Fight", "Gravel Ant", "Wall Gecko"],
    }

    @classmethod
    def create(
        cls,
        axie_id: Optional[int] = None,
        class_name: str = "Beast",
        genes: Optional[str] = None,
        purity: int = 6,
        breed_count: int = 0,
        price: Optional[float] = None,
        owner: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Create a test Axie.

        Args:
            axie_id: Axie ID (auto-generated if None)
            class_name: Axie class (Beast, Aquatic, Plant, etc.)
            genes: Gene string (auto-generated if None)
            purity: Number of pure parts (0-6), used for gene generation
            breed_count: Number of times bred (0-7)
            price: If provided, includes listing data
            owner: Owner wallet address (auto-generated if None)
            name: Axie name (auto-generated if None)
            **kwargs: Additional fields to override

        Returns:
            Dictionary with Axie data (matching API response format)
        """
        # Generate unique ID
        if axie_id is None:
            cls._id_counter += 1
            axie_id = cls._id_counter

        # Normalize class name
        class_name = class_name.capitalize()
        if class_name not in cls.CLASSES:
            class_name = "Beast"

        # Generate genes if not provided
        if genes is None:
            genes = GeneFactory.create(class_name=class_name, purity=purity)

        # Generate owner if not provided
        if owner is None:
            owner = WalletFactory.create_deterministic()

        # Generate name if not provided
        if name is None:
            name = f"Axie #{axie_id}"

        # Get base stats
        stats = cls.BASE_STATS.get(class_name, cls.BASE_STATS["Beast"]).copy()

        # Generate parts
        parts = cls._generate_parts(class_name, purity)

        # Build the Axie object
        axie = {
            "id": str(axie_id),
            "name": name,
            "class": class_name.lower(),
            "genes": genes,
            "breedCount": breed_count,
            "image": f"https://axiecdn.axieinfinity.com/axies/{axie_id}/axie/axie-full-transparent.png",
            "stats": stats,
            "parts": parts,
            "owner": owner,
            "purity": purity,
            "birthDate": int((datetime.utcnow() - timedelta(days=random.randint(30, 365))).timestamp()),
        }

        # Add listing data if price provided
        if price is not None:
            from .listing_factory import ListingFactory
            axie["listing"] = ListingFactory.create(
                axie_id=axie_id,
                price=price,
                seller=owner,
            )

        # Apply any overrides
        axie.update(kwargs)

        return axie

    @classmethod
    def create_batch(
        cls,
        count: int,
        class_name: Optional[str] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Create multiple Axies.

        Args:
            count: Number of Axies to create
            class_name: Optional class for all Axies (random if None)
            **kwargs: Additional fields applied to all Axies

        Returns:
            List of Axie dictionaries
        """
        axies = []
        for _ in range(count):
            axie_class = class_name or random.choice(cls.CLASSES)
            axies.append(cls.create(class_name=axie_class, **kwargs))
        return axies

    @classmethod
    def create_pure_beast(cls, **kwargs: Any) -> Dict[str, Any]:
        """Convenience method for creating a pure Beast Axie."""
        return cls.create(class_name="Beast", purity=6, **kwargs)

    @classmethod
    def create_pure_aquatic(cls, **kwargs: Any) -> Dict[str, Any]:
        """Convenience method for creating a pure Aquatic Axie."""
        return cls.create(class_name="Aquatic", purity=6, **kwargs)

    @classmethod
    def create_pure_plant(cls, **kwargs: Any) -> Dict[str, Any]:
        """Convenience method for creating a pure Plant Axie."""
        return cls.create(class_name="Plant", purity=6, **kwargs)

    @classmethod
    def create_virgin(cls, class_name: str = "Beast", **kwargs: Any) -> Dict[str, Any]:
        """Create an Axie with 0 breed count (virgin)."""
        return cls.create(class_name=class_name, breed_count=0, **kwargs)

    @classmethod
    def create_maxbred(cls, class_name: str = "Beast", **kwargs: Any) -> Dict[str, Any]:
        """Create an Axie with max breed count (7)."""
        return cls.create(class_name=class_name, breed_count=7, **kwargs)

    @classmethod
    def create_listed(cls, price: float = 0.01, **kwargs: Any) -> Dict[str, Any]:
        """Create an Axie with active listing."""
        return cls.create(price=price, **kwargs)

    @classmethod
    def _generate_parts(cls, class_name: str, purity: int) -> List[Dict[str, Any]]:
        """
        Generate Axie body parts.

        Args:
            class_name: Axie class
            purity: Number of parts matching the class

        Returns:
            List of part dictionaries
        """
        part_types = ["eyes", "ears", "mouth", "horn", "back", "tail"]
        parts = []

        for i, part_type in enumerate(part_types):
            # Determine if this part should be "pure" (match the class)
            is_pure = i < purity

            if is_pure:
                part_class = class_name.lower()
            else:
                # Pick a random different class
                other_classes = [c.lower() for c in cls.CLASSES if c != class_name]
                part_class = random.choice(other_classes)

            # Get a part name
            part_names = cls.PART_NAMES.get(part_type, ["Unknown"])
            part_name = random.choice(part_names)

            parts.append({
                "id": f"{part_type}-{part_name.lower().replace(' ', '-')}",
                "name": part_name,
                "class": part_class,
                "type": part_type,
            })

        return parts

    @classmethod
    def reset(cls) -> None:
        """Reset the ID counter."""
        cls._id_counter = 100000
