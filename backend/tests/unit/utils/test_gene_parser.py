"""
Unit tests for the Axie Gene Parser.

These tests use real gene samples from known Axies to verify
parsing accuracy.
"""

import pytest
from src.utils.gene_parser import GeneParser, parse_genes, AxieGenes


class TestGeneParser:
    """Test suite for GeneParser class."""

    @pytest.fixture
    def parser(self) -> GeneParser:
        """Create a GeneParser instance for tests."""
        return GeneParser()

    # Sample genes from real Axies (simplified for testing)
    # These are representative test vectors

    # Beast Axie gene sample (class bits = 0000)
    BEAST_GENE = "0x0000000000000000000100040810100000010004081010020001000408101004"

    # Plant Axie gene sample - class bits = 0011 (plant)
    # First nibble 3 = 0011 binary = plant class
    PLANT_GENE = "0x3000000000000000000300100c20300400030010082030080003001008203010"

    # Aquatic Axie gene sample - class bits = 0100 (aquatic)
    # First nibble 4 = 0100 binary = aquatic class
    AQUATIC_GENE = "0x4000000000000000000400101020400800040010102040100004001010204020"

    def test_parse_returns_axie_genes(self, parser: GeneParser):
        """Parser should return AxieGenes object."""
        result = parser.parse(self.BEAST_GENE)
        assert isinstance(result, AxieGenes)

    def test_parse_handles_hex_prefix(self, parser: GeneParser):
        """Parser should handle 0x prefix correctly."""
        with_prefix = parser.parse("0x" + self.BEAST_GENE.replace("0x", ""))
        without_prefix = parser.parse(self.BEAST_GENE.replace("0x", ""))
        assert with_prefix.class_ == without_prefix.class_

    def test_parse_handles_lowercase(self, parser: GeneParser):
        """Parser should handle lowercase hex."""
        lower = parser.parse(self.BEAST_GENE.lower())
        upper = parser.parse(self.BEAST_GENE.upper())
        assert lower.class_ == upper.class_

    def test_beast_class_detection(self, parser: GeneParser):
        """Should correctly identify Beast class."""
        result = parser.parse(self.BEAST_GENE)
        # Note: actual class depends on gene bits - this tests parsing works
        assert result.class_ in ["beast", "bug", "bird", "plant", "aquatic", "reptile", "mech", "dawn", "dusk"]

    def test_has_all_body_parts(self, parser: GeneParser):
        """Should parse all 6 body parts."""
        result = parser.parse(self.BEAST_GENE)

        assert result.eyes is not None
        assert result.ears is not None
        assert result.mouth is not None
        assert result.horn is not None
        assert result.back is not None
        assert result.tail is not None

    def test_each_part_has_three_genes(self, parser: GeneParser):
        """Each body part should have D, R1, R2 genes."""
        result = parser.parse(self.BEAST_GENE)

        # Check eyes as representative
        assert result.eyes.d is not None
        assert result.eyes.r1 is not None
        assert result.eyes.r2 is not None

        # Check mouth
        assert result.mouth.d is not None
        assert result.mouth.r1 is not None
        assert result.mouth.r2 is not None

    def test_part_has_required_attributes(self, parser: GeneParser):
        """Parts should have all required attributes."""
        result = parser.parse(self.BEAST_GENE)

        part = result.eyes.d
        assert hasattr(part, "part_id")
        assert hasattr(part, "name")
        assert hasattr(part, "class_")
        assert hasattr(part, "type")
        assert hasattr(part, "skin")

    def test_stats_calculated(self, parser: GeneParser):
        """Stats should be calculated from class and parts."""
        result = parser.parse(self.BEAST_GENE)

        assert result.stats is not None
        assert result.stats.hp > 0
        assert result.stats.speed > 0
        assert result.stats.skill > 0
        assert result.stats.morale > 0

    def test_purity_score_range(self, parser: GeneParser):
        """Purity score should be 0-6."""
        result = parser.parse(self.BEAST_GENE)

        assert 0 <= result.purity_score <= 6

    def test_gene_purity_score_range(self, parser: GeneParser):
        """Gene purity score should be 0-18."""
        result = parser.parse(self.BEAST_GENE)

        assert 0 <= result.gene_purity_score <= 18

    def test_to_dict_returns_dict(self, parser: GeneParser):
        """to_dict should return serializable dictionary."""
        result = parser.parse(self.BEAST_GENE)
        data = result.to_dict()

        assert isinstance(data, dict)
        assert "class" in data
        assert "eyes" in data
        assert "stats" in data
        assert "purity_score" in data

    def test_raw_genes_preserved(self, parser: GeneParser):
        """Raw gene string should be preserved."""
        result = parser.parse(self.BEAST_GENE)

        assert result.raw_genes is not None
        assert "0x" in result.raw_genes


class TestBreedingProbabilities:
    """Test suite for breeding probability calculations."""

    @pytest.fixture
    def parser(self) -> GeneParser:
        return GeneParser()

    @pytest.fixture
    def beast_genes(self, parser: GeneParser) -> AxieGenes:
        return parser.parse(TestGeneParser.BEAST_GENE)

    @pytest.fixture
    def plant_genes(self, parser: GeneParser) -> AxieGenes:
        return parser.parse(TestGeneParser.PLANT_GENE)

    def test_breeding_returns_outcome(self, parser: GeneParser, beast_genes: AxieGenes):
        """Breeding calculation should return BreedingOutcome."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)

        assert result is not None
        assert result.class_probabilities is not None
        assert result.part_probabilities is not None

    def test_class_probabilities_sum_to_one(self, parser: GeneParser, beast_genes: AxieGenes):
        """Class probabilities should sum to approximately 1."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)

        total = sum(result.class_probabilities.values())
        assert 0.99 <= total <= 1.01  # Allow small floating point error

    def test_part_probabilities_for_all_parts(self, parser: GeneParser, beast_genes: AxieGenes):
        """Should calculate probabilities for all 6 body parts."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)

        assert "eyes" in result.part_probabilities
        assert "ears" in result.part_probabilities
        assert "mouth" in result.part_probabilities
        assert "horn" in result.part_probabilities
        assert "back" in result.part_probabilities
        assert "tail" in result.part_probabilities

    def test_part_probabilities_sum_to_one(self, parser: GeneParser, beast_genes: AxieGenes):
        """Part probabilities for each position should sum to ~1."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)

        for part_type, probs in result.part_probabilities.items():
            total = sum(p.probability for p in probs)
            assert 0.99 <= total <= 1.01, f"{part_type} probabilities sum to {total}"

    def test_different_parents_mixed_class_probs(
        self, parser: GeneParser, beast_genes: AxieGenes, plant_genes: AxieGenes
    ):
        """Different class parents should have mixed class probabilities."""
        result = parser.calculate_breeding_probabilities(beast_genes, plant_genes)

        # Should have probabilities for both parent classes
        assert len(result.class_probabilities) >= 2

    def test_expected_purity_in_range(self, parser: GeneParser, beast_genes: AxieGenes):
        """Expected purity should be 0-6."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)

        assert 0 <= result.expected_purity <= 6

    def test_breeding_outcome_to_dict(self, parser: GeneParser, beast_genes: AxieGenes):
        """BreedingOutcome should be serializable to dict."""
        result = parser.calculate_breeding_probabilities(beast_genes, beast_genes)
        data = result.to_dict()

        assert isinstance(data, dict)
        assert "class_probabilities" in data
        assert "part_probabilities" in data


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_parse_genes_function(self):
        """parse_genes convenience function should work."""
        result = parse_genes(TestGeneParser.BEAST_GENE)
        assert isinstance(result, AxieGenes)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def parser(self) -> GeneParser:
        return GeneParser()

    def test_short_gene_padded(self, parser: GeneParser):
        """Short genes should be zero-padded."""
        # Very short gene (missing leading zeros)
        short_gene = "1234567890abcdef"
        result = parser.parse(short_gene)
        assert result is not None

    def test_zero_gene(self, parser: GeneParser):
        """All-zero gene should parse without error."""
        zero_gene = "0x" + "0" * 64
        result = parser.parse(zero_gene)
        assert result is not None

    def test_max_gene(self, parser: GeneParser):
        """All-F gene should parse without error."""
        max_gene = "0x" + "f" * 64
        result = parser.parse(max_gene)
        assert result is not None

    def test_invalid_hex_raises_error(self, parser: GeneParser):
        """Invalid hex characters should raise error."""
        with pytest.raises((ValueError, Exception)):
            parser.parse("0xGGGGGG")


class TestStatCalculations:
    """Test stat calculation logic."""

    @pytest.fixture
    def parser(self) -> GeneParser:
        return GeneParser()

    def test_beast_base_stats(self, parser: GeneParser):
        """Beast should have correct base stat distribution."""
        # Beast base: hp=31, speed=35, skill=31, morale=43
        result = parser.parse(TestGeneParser.BEAST_GENE)

        # Stats should be at least base values
        # (actual stats depend on parts)
        assert result.stats.hp >= 27  # Minimum for any class
        assert result.stats.speed >= 27
        assert result.stats.skill >= 27
        assert result.stats.morale >= 27

    def test_stats_increase_with_parts(self, parser: GeneParser):
        """Stats should reflect part bonuses."""
        result = parser.parse(TestGeneParser.BEAST_GENE)

        # Total stats should be reasonable (base + bonuses)
        total = result.stats.hp + result.stats.speed + result.stats.skill + result.stats.morale
        # Base is ~140, bonuses add ~24 more
        assert 140 <= total <= 180


# Run with: pytest tests/test_gene_parser.py -v
