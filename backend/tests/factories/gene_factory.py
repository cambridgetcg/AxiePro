"""
Gene Factory

Creates realistic Axie gene strings for testing.
Axie genes are 256-bit values that encode:
- Class
- Body parts (6 parts: eyes, ears, mouth, horn, back, tail)
- Each part has D (dominant), R1, R2 (recessive) genes
- Stats modifications
"""

from typing import Optional
import random


class GeneFactory:
    """Factory for creating Axie gene data."""

    # Pre-generated gene strings by class (256-bit hex values)
    # These are realistic gene patterns for each class
    PURE_GENES = {
        "Beast": "0x0000000000000001000308a042080004200100a04208000c200100a0420c0010",
        "Aquatic": "0x0000000000000002001008a842080004210100a84208000c210100a8420c0010",
        "Plant": "0x0000000000000003002008b042080004220100b04208000c220100b0420c0010",
        "Bird": "0x0000000000000004003008b842080004230100b84208000c230100b8420c0010",
        "Bug": "0x0000000000000005004008c042080004240100c04208000c240100c0420c0010",
        "Reptile": "0x0000000000000006005008c842080004250100c84208000c250100c8420c0010",
        "Mech": "0x0000000000000007000308a04208000c200100a042080010200100a0420c0014",
        "Dawn": "0x0000000000000008002008b04208000c220100b042080010220100b0420c0014",
        "Dusk": "0x0000000000000009005008c84208000c250100c842080010250100c8420c0014",
    }

    # Class IDs for gene encoding
    CLASS_IDS = {
        "Beast": 0x0001,
        "Bug": 0x0002,
        "Bird": 0x0003,
        "Plant": 0x0004,
        "Aquatic": 0x0005,
        "Reptile": 0x0006,
        "Mech": 0x0101,  # Beast + Aquatic
        "Dawn": 0x0102,  # Plant + Bird
        "Dusk": 0x0103,  # Reptile + Bug
    }

    @classmethod
    def create(
        cls,
        class_name: str = "Beast",
        purity: int = 6,
        seed: Optional[int] = None,
    ) -> str:
        """
        Create a gene string for testing.

        Args:
            class_name: Axie class (Beast, Aquatic, Plant, etc.)
            purity: Number of parts matching the base class (0-6)
            seed: Optional random seed for reproducibility

        Returns:
            256-bit gene string (hex with 0x prefix)
        """
        if seed is not None:
            random.seed(seed)

        # Normalize class name
        class_name = class_name.capitalize()
        if class_name not in cls.PURE_GENES:
            class_name = "Beast"

        # For purity=6, return pure genes
        if purity >= 6:
            return cls.PURE_GENES[class_name]

        # For lower purity, we modify the pure genes
        # This is a simplification - real genes are more complex
        base_genes = cls.PURE_GENES[class_name]

        # For testing, we just vary the last few characters
        if purity <= 3:
            # Mix in some other class genes
            return base_genes[:-8] + format(random.randint(0, 0xFFFFFFFF), '08x')

        return base_genes

    @classmethod
    def create_for_class(cls, class_name: str, purity: int = 6) -> str:
        """
        Alias for create() with class_name focus.

        Args:
            class_name: Target Axie class
            purity: Number of pure parts (0-6)

        Returns:
            Gene string for specified class
        """
        return cls.create(class_name=class_name, purity=purity)

    @classmethod
    def create_mixed(cls, primary_class: str, secondary_class: str) -> str:
        """
        Create genes for a mixed-class Axie.

        Args:
            primary_class: Primary class (determines body)
            secondary_class: Secondary class (some parts from this)

        Returns:
            Mixed gene string
        """
        primary_genes = cls.PURE_GENES.get(primary_class.capitalize(), cls.PURE_GENES["Beast"])
        secondary_genes = cls.PURE_GENES.get(secondary_class.capitalize(), cls.PURE_GENES["Plant"])

        # Mix genes - take first half from primary, second half from secondary
        return primary_genes[:40] + secondary_genes[40:]

    @classmethod
    def get_class_from_genes(cls, genes: str) -> str:
        """
        Determine the Axie class from gene string.

        Args:
            genes: 256-bit gene string

        Returns:
            Class name
        """
        # Simplified class detection from gene pattern
        for class_name, pure_genes in cls.PURE_GENES.items():
            if genes.startswith(pure_genes[:20]):
                return class_name
        return "Beast"  # Default
