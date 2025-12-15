"""
Axie Gene Parser

Parses 256-bit Axie genes into readable trait data and calculates
breeding probabilities.

Gene structure (256 bits, read from right to left):
- Each body part uses 32 bits
- Parts order: Tail, Back, Horn, Ears, Mouth, Eyes
- Then class, region, pattern, color information
"""

from dataclasses import dataclass, field
from typing import Optional
from decimal import Decimal

from .gene_data import (
    CLASS_GENE_MAP,
    REGION_GENE_MAP,
    TAG_GENE_MAP,
    PART_CLASS_MAP,
    PART_SKIN_MAP,
    PARTS_BY_TYPE,
    CLASS_STATS,
    PART_STAT_BONUSES,
    SECRET_CLASS_COMBINATIONS,
)


@dataclass
class Part:
    """Represents a body part with its attributes."""
    part_id: str
    name: str
    class_: str
    type: str  # eyes, ears, mouth, horn, back, tail
    skin: str = "normal"

    def to_dict(self) -> dict:
        return {
            "part_id": self.part_id,
            "name": self.name,
            "class": self.class_,
            "type": self.type,
            "skin": self.skin,
        }


@dataclass
class PartGene:
    """Genes for a single body part (D, R1, R2)."""
    d: Part
    r1: Part
    r2: Part

    def to_dict(self) -> dict:
        return {
            "d": self.d.to_dict(),
            "r1": self.r1.to_dict(),
            "r2": self.r2.to_dict(),
        }


@dataclass
class AxieStats:
    """Axie base stats calculated from class and parts."""
    hp: int
    speed: int
    skill: int
    morale: int

    def to_dict(self) -> dict:
        return {
            "hp": self.hp,
            "speed": self.speed,
            "skill": self.skill,
            "morale": self.morale,
        }


@dataclass
class AxieGenes:
    """Complete parsed gene data for an Axie."""
    class_: str
    region: str
    tag: str
    pattern: str
    color: str
    eyes: PartGene
    ears: PartGene
    mouth: PartGene
    horn: PartGene
    back: PartGene
    tail: PartGene
    stats: AxieStats
    purity_score: int  # 0-6, how many dominant parts match class
    gene_purity_score: int  # 0-18, including R1 and R2
    raw_genes: str = ""

    def to_dict(self) -> dict:
        return {
            "class": self.class_,
            "region": self.region,
            "tag": self.tag,
            "pattern": self.pattern,
            "color": self.color,
            "eyes": self.eyes.to_dict(),
            "ears": self.ears.to_dict(),
            "mouth": self.mouth.to_dict(),
            "horn": self.horn.to_dict(),
            "back": self.back.to_dict(),
            "tail": self.tail.to_dict(),
            "stats": self.stats.to_dict(),
            "purity_score": self.purity_score,
            "gene_purity_score": self.gene_purity_score,
        }

    def get_dominant_parts(self) -> list[Part]:
        """Get list of all dominant parts."""
        return [
            self.eyes.d,
            self.ears.d,
            self.mouth.d,
            self.horn.d,
            self.back.d,
            self.tail.d,
        ]


@dataclass
class BreedingProbability:
    """Probability for a specific part outcome."""
    part: Part
    probability: float

    def to_dict(self) -> dict:
        return {
            "part": self.part.to_dict(),
            "probability": self.probability,
        }


@dataclass
class BreedingOutcome:
    """Complete breeding simulation results."""
    matron_id: Optional[int]
    sire_id: Optional[int]
    class_probabilities: dict[str, float]
    part_probabilities: dict[str, list[BreedingProbability]]
    expected_purity: float

    def to_dict(self) -> dict:
        return {
            "matron_id": self.matron_id,
            "sire_id": self.sire_id,
            "class_probabilities": self.class_probabilities,
            "part_probabilities": {
                part_type: [p.to_dict() for p in probs]
                for part_type, probs in self.part_probabilities.items()
            },
            "expected_purity": self.expected_purity,
        }


class GeneParser:
    """
    Parser for Axie 256-bit genes.

    Usage:
        parser = GeneParser()
        genes = parser.parse("0x000000000000000000...")
        print(genes.class_)  # "beast"
        print(genes.mouth.d.name)  # "Nut Cracker"
    """

    # Gene inheritance probabilities
    PROB_D = 0.375      # 37.5% - Dominant gene
    PROB_R1 = 0.09375   # 9.375% - Recessive 1
    PROB_R2 = 0.03125   # 3.125% - Recessive 2

    def __init__(self):
        self._part_cache: dict[str, Part] = {}

    def parse(self, gene_hex: str) -> AxieGenes:
        """
        Parse a hex gene string into structured AxieGenes.

        Args:
            gene_hex: 256-bit gene as hex string (with or without 0x prefix)

        Returns:
            AxieGenes object with all decoded trait data
        """
        # Normalize hex string
        gene_hex = gene_hex.lower().replace("0x", "")

        # Pad to 64 characters (256 bits)
        gene_hex = gene_hex.zfill(64)

        # Convert to binary string (256 bits)
        gene_binary = bin(int(gene_hex, 16))[2:].zfill(256)

        # Parse class (bits 252-255, reading from right)
        class_bits = gene_binary[0:4]
        axie_class = CLASS_GENE_MAP.get(class_bits, "beast")

        # Parse region (bits 240-244)
        region_bits = gene_binary[8:13]
        region = REGION_GENE_MAP.get(region_bits, "global")

        # Parse tag (bits 236-239)
        tag_bits = gene_binary[13:17]
        tag = TAG_GENE_MAP.get(tag_bits, "normal")

        # Parse pattern (bits 214-217)
        pattern_bits = gene_binary[38:42]
        pattern = f"pattern_{int(pattern_bits, 2)}"

        # Parse color (simplified - just store hex)
        color_bits = gene_binary[42:60]
        color = f"#{int(color_bits, 2):06x}"

        # Parse body parts (each 32 bits)
        # Order in binary: eyes, mouth, ears, horn, back, tail
        eyes = self._parse_part(gene_binary[64:96], "eyes")
        mouth = self._parse_part(gene_binary[96:128], "mouth")
        ears = self._parse_part(gene_binary[128:160], "ears")
        horn = self._parse_part(gene_binary[160:192], "horn")
        back = self._parse_part(gene_binary[192:224], "back")
        tail = self._parse_part(gene_binary[224:256], "tail")

        # Calculate purity scores
        purity_score = self._calculate_purity(
            axie_class, [eyes, ears, mouth, horn, back, tail], dominant_only=True
        )
        gene_purity_score = self._calculate_purity(
            axie_class, [eyes, ears, mouth, horn, back, tail], dominant_only=False
        )

        # Calculate stats
        stats = self._calculate_stats(
            axie_class, [eyes, ears, mouth, horn, back, tail]
        )

        return AxieGenes(
            class_=axie_class,
            region=region,
            tag=tag,
            pattern=pattern,
            color=color,
            eyes=eyes,
            ears=ears,
            mouth=mouth,
            horn=horn,
            back=back,
            tail=tail,
            stats=stats,
            purity_score=purity_score,
            gene_purity_score=gene_purity_score,
            raw_genes=f"0x{gene_hex}",
        )

    def _parse_part(self, binary_32: str, part_type: str) -> PartGene:
        """
        Parse 32-bit part gene into D, R1, R2 parts.

        Structure (32 bits):
        - bits 0-1: reserved
        - bits 2-5: D skin (4 bits)
        - bits 6-9: D class (4 bits)
        - bits 10-15: D part (6 bits)
        - bits 12-15: R1 skin (4 bits)
        - bits 16-19: R1 class (4 bits)
        - bits 20-25: R1 part (6 bits)
        - bits 22-25: R2 skin (4 bits)
        - bits 26-29: R2 class (4 bits)
        - bits 30-35: R2 part (6 bits) -- wraps but handled
        """
        # Dominant gene (bits 2-11)
        d_skin_bits = binary_32[2:6]
        d_class_bits = binary_32[6:10]
        d_part_bits = binary_32[10:16]
        d_part = self._decode_part(d_class_bits, d_part_bits, d_skin_bits, part_type)

        # Recessive 1 (bits 12-21)
        r1_skin_bits = binary_32[12:16]
        r1_class_bits = binary_32[16:20]
        r1_part_bits = binary_32[20:26]
        r1_part = self._decode_part(r1_class_bits, r1_part_bits, r1_skin_bits, part_type)

        # Recessive 2 (bits 22-31)
        r2_skin_bits = binary_32[22:26]
        r2_class_bits = binary_32[26:30]
        r2_part_bits = binary_32[30:32] + "0000"  # Pad remaining bits
        # Actually R2 uses bits 26-31, need to handle wrap
        r2_part_bits = binary_32[26:32]
        r2_part = self._decode_part(r2_class_bits, r2_part_bits, r2_skin_bits, part_type)

        return PartGene(d=d_part, r1=r1_part, r2=r2_part)

    def _decode_part(
        self,
        class_bits: str,
        part_bits: str,
        skin_bits: str,
        part_type: str
    ) -> Part:
        """Decode binary to actual part."""
        # Get class from class bits
        part_class = PART_CLASS_MAP.get(class_bits, "beast")

        # Get skin type
        skin = PART_SKIN_MAP.get(skin_bits, "normal")

        # Look up part in mapping
        parts_for_type = PARTS_BY_TYPE.get(part_type, {})
        parts_for_class = parts_for_type.get(part_class, {})

        # Try exact match first
        part_data = parts_for_class.get(part_bits)

        # If not found, try truncating/padding
        if not part_data:
            # Try with leading zeros stripped or added
            for variant in [part_bits.lstrip("0") or "0", part_bits[:4], part_bits[:6].zfill(6)]:
                part_data = parts_for_class.get(variant)
                if part_data:
                    break

        # Default fallback
        if not part_data:
            part_data = (f"{part_type}-unknown", "Unknown")

        part_id, part_name = part_data

        return Part(
            part_id=part_id,
            name=part_name,
            class_=part_class,
            type=part_type,
            skin=skin,
        )

    def _calculate_purity(
        self,
        axie_class: str,
        parts: list[PartGene],
        dominant_only: bool = True
    ) -> int:
        """
        Calculate purity score.

        Args:
            axie_class: The Axie's class
            parts: List of PartGene objects
            dominant_only: If True, only count D genes (0-6 score)
                          If False, count all genes (0-18 score)

        Returns:
            Purity score
        """
        score = 0
        for part_gene in parts:
            if part_gene.d.class_ == axie_class:
                score += 1
            if not dominant_only:
                if part_gene.r1.class_ == axie_class:
                    score += 1
                if part_gene.r2.class_ == axie_class:
                    score += 1
        return score

    def _calculate_stats(
        self,
        axie_class: str,
        parts: list[PartGene]
    ) -> AxieStats:
        """
        Calculate Axie stats from class and parts.

        Base stats come from class, then each part adds bonuses
        based on its class.
        """
        base = CLASS_STATS.get(axie_class, CLASS_STATS["beast"])
        stats = {
            "hp": base["hp"],
            "speed": base["speed"],
            "skill": base["skill"],
            "morale": base["morale"],
        }

        # Add bonuses from each dominant part
        for part_gene in parts:
            part_class = part_gene.d.class_
            if part_class in PART_STAT_BONUSES:
                bonuses = PART_STAT_BONUSES[part_class]
                for stat, bonus in bonuses.items():
                    stats[stat] += bonus

        return AxieStats(**stats)

    def calculate_breeding_probabilities(
        self,
        parent_a: AxieGenes,
        parent_b: AxieGenes,
    ) -> BreedingOutcome:
        """
        Calculate breeding outcome probabilities.

        Each gene has the following inheritance probability:
        - D (Dominant): 37.5%
        - R1 (Recessive 1): 9.375%
        - R2 (Recessive 2): 3.125%

        Args:
            parent_a: First parent's genes (matron)
            parent_b: Second parent's genes (sire)

        Returns:
            BreedingOutcome with all probabilities
        """
        # Calculate class probabilities
        class_probs = self._calculate_class_probabilities(parent_a, parent_b)

        # Calculate part probabilities for each position
        part_probs = {}
        part_types = ["eyes", "ears", "mouth", "horn", "back", "tail"]

        for part_type in part_types:
            parent_a_part = getattr(parent_a, part_type)
            parent_b_part = getattr(parent_b, part_type)
            part_probs[part_type] = self._calculate_part_probabilities(
                parent_a_part, parent_b_part
            )

        # Calculate expected purity (simplified - assumes most likely class)
        most_likely_class = max(class_probs, key=class_probs.get)
        expected_purity = self._calculate_expected_purity(
            part_probs, most_likely_class
        )

        return BreedingOutcome(
            matron_id=None,
            sire_id=None,
            class_probabilities=class_probs,
            part_probabilities=part_probs,
            expected_purity=expected_purity,
        )

    def _calculate_class_probabilities(
        self,
        parent_a: AxieGenes,
        parent_b: AxieGenes
    ) -> dict[str, float]:
        """Calculate offspring class probabilities."""
        probs: dict[str, float] = {}

        # Base classes from parents
        class_a = parent_a.class_
        class_b = parent_b.class_

        if class_a == class_b:
            # Same class parents - very high chance of same class
            probs[class_a] = 0.9375  # 93.75%
            # Small chance of secret class from recessive genes
            # (simplified - would need more gene analysis)
        else:
            # Different class parents
            probs[class_a] = 0.46875  # 46.875%
            probs[class_b] = 0.46875  # 46.875%

            # Check for secret class combinations
            combo = (class_a, class_b)
            if combo in SECRET_CLASS_COMBINATIONS:
                secret_class = SECRET_CLASS_COMBINATIONS[combo]
                # Redistribute probability
                probs[class_a] = 0.4375
                probs[class_b] = 0.4375
                probs[secret_class] = 0.125  # 12.5% for secret class

        # Ensure probabilities sum to ~1
        total = sum(probs.values())
        if total < 1.0:
            # Add remaining to most likely class
            most_likely = max(probs, key=probs.get)
            probs[most_likely] += (1.0 - total)

        return probs

    def _calculate_part_probabilities(
        self,
        parent_a_part: PartGene,
        parent_b_part: PartGene
    ) -> list[BreedingProbability]:
        """
        Calculate probabilities for each possible part outcome.

        Gene pool from both parents:
        - Parent A: D (37.5%), R1 (9.375%), R2 (3.125%)
        - Parent B: D (37.5%), R1 (9.375%), R2 (3.125%)
        """
        # Collect all possible parts with their probabilities
        gene_pool: dict[str, tuple[Part, float]] = {}

        # Parent A genes
        self._add_to_gene_pool(gene_pool, parent_a_part.d, self.PROB_D)
        self._add_to_gene_pool(gene_pool, parent_a_part.r1, self.PROB_R1)
        self._add_to_gene_pool(gene_pool, parent_a_part.r2, self.PROB_R2)

        # Parent B genes
        self._add_to_gene_pool(gene_pool, parent_b_part.d, self.PROB_D)
        self._add_to_gene_pool(gene_pool, parent_b_part.r1, self.PROB_R1)
        self._add_to_gene_pool(gene_pool, parent_b_part.r2, self.PROB_R2)

        # Convert to BreedingProbability list, sorted by probability
        results = [
            BreedingProbability(part=part, probability=prob)
            for part, prob in gene_pool.values()
        ]
        results.sort(key=lambda x: x.probability, reverse=True)

        return results

    def _add_to_gene_pool(
        self,
        pool: dict[str, tuple[Part, float]],
        part: Part,
        probability: float
    ) -> None:
        """Add a part to the gene pool, combining duplicates."""
        key = part.part_id
        if key in pool:
            existing_part, existing_prob = pool[key]
            pool[key] = (existing_part, existing_prob + probability)
        else:
            pool[key] = (part, probability)

    def _calculate_expected_purity(
        self,
        part_probs: dict[str, list[BreedingProbability]],
        target_class: str
    ) -> float:
        """Calculate expected purity score for offspring."""
        expected = 0.0

        for part_type, probs in part_probs.items():
            for prob in probs:
                if prob.part.class_ == target_class:
                    expected += prob.probability

        return round(expected, 2)

    def get_purity_score(self, genes: AxieGenes) -> int:
        """Get purity score (dominant parts matching class)."""
        return genes.purity_score

    def get_gene_purity_score(self, genes: AxieGenes) -> int:
        """Get full gene purity score (all genes matching class)."""
        return genes.gene_purity_score


# Convenience function for quick parsing
def parse_genes(gene_hex: str) -> AxieGenes:
    """Quick function to parse genes without instantiating parser."""
    return GeneParser().parse(gene_hex)
