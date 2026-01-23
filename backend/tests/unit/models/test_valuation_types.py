"""
Unit tests for valuation type definitions.

Tests the data classes and type definitions used by the valuation system.
"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.services.valuation.types import (
    ValuationResult,
    TraitCoefficients,
    TraitStatistics,
    AxieFeatures,
    DealAlert,
    ValuationConfig,
    ValuationMethod,
)


class TestValuationConfig:
    """Test ValuationConfig defaults and configuration."""

    def test_default_config(self):
        """Config should have sensible defaults."""
        config = ValuationConfig()

        assert config.default_time_window_hours == 168  # 7 days
        assert config.short_time_window_hours == 24
        assert config.min_samples_for_coefficient == 10
        assert config.confidence_level == 0.95
        assert config.deal_z_threshold == -1.5
        assert config.snipe_z_threshold == -2.5

    def test_custom_config(self):
        """Config should accept custom values."""
        config = ValuationConfig(
            default_time_window_hours=48,
            deal_z_threshold=-2.0,
        )

        assert config.default_time_window_hours == 48
        assert config.deal_z_threshold == -2.0

    def test_ensemble_weights_sum_to_one(self):
        """Ensemble weights should sum to approximately 1."""
        config = ValuationConfig()
        total = config.hedonic_weight + config.xgboost_weight + config.lightgbm_weight
        assert 0.99 <= total <= 1.01


class TestValuationMethod:
    """Test ValuationMethod enum."""

    def test_method_values(self):
        """Should have expected method types."""
        assert ValuationMethod.HEDONIC.value == "hedonic"
        assert ValuationMethod.XGBOOST.value == "xgboost"
        assert ValuationMethod.LIGHTGBM.value == "lightgbm"
        assert ValuationMethod.ENSEMBLE.value == "ensemble"


class TestTraitStatistics:
    """Test TraitStatistics data class."""

    @pytest.fixture
    def sample_stats(self) -> TraitStatistics:
        """Create sample trait statistics."""
        return TraitStatistics(
            trait_key="class:beast",
            trait_type="class",
            class_="beast",
            avg_price_eth=Decimal("0.025"),
            median_price_eth=Decimal("0.022"),
            std_dev_eth=Decimal("0.008"),
            min_price_eth=Decimal("0.008"),
            max_price_eth=Decimal("0.150"),
            sample_count=1500,
            time_window_hours=168,
            computed_at=datetime.utcnow(),
        )

    def test_to_dict_returns_dict(self, sample_stats: TraitStatistics):
        """to_dict should return serializable dictionary."""
        data = sample_stats.to_dict()

        assert isinstance(data, dict)
        assert data["trait_key"] == "class:beast"
        assert data["trait_type"] == "class"
        assert data["class"] == "beast"
        assert isinstance(data["avg_price_eth"], float)
        assert isinstance(data["computed_at"], str)

    def test_handles_none_values(self):
        """Should handle None for optional fields."""
        stats = TraitStatistics(
            trait_key="class:unknown",
            trait_type="class",
            class_=None,
            avg_price_eth=None,
            median_price_eth=None,
            std_dev_eth=None,
            min_price_eth=None,
            max_price_eth=None,
            sample_count=0,
            time_window_hours=168,
            computed_at=datetime.utcnow(),
        )

        data = stats.to_dict()
        assert data["avg_price_eth"] is None
        assert data["class"] is None


class TestTraitCoefficients:
    """Test TraitCoefficients data class."""

    @pytest.fixture
    def sample_coefficients(self) -> TraitCoefficients:
        """Create sample coefficients."""
        return TraitCoefficients(
            model_version="hedonic_v20250101_120000",
            intercept=-2.5,
            coefficients={
                "class:beast": 0.15,
                "class:plant": 0.12,
                "purity:6": 0.45,
                "breed:0": 0.08,
            },
            r_squared=0.72,
            adj_r_squared=0.71,
            rmse=0.35,
            sample_size=5000,
            feature_count=150,
            train_start=datetime(2025, 1, 1),
            train_end=datetime(2025, 1, 31),
            trained_at=datetime(2025, 1, 31, 12, 0, 0),
        )

    def test_to_dict_returns_dict(self, sample_coefficients: TraitCoefficients):
        """to_dict should return serializable dictionary."""
        data = sample_coefficients.to_dict()

        assert isinstance(data, dict)
        assert data["model_version"] == "hedonic_v20250101_120000"
        assert data["intercept"] == -2.5
        assert data["r_squared"] == 0.72
        assert isinstance(data["coefficients"], dict)
        assert data["coefficients"]["class:beast"] == 0.15

    def test_coefficient_values(self, sample_coefficients: TraitCoefficients):
        """Coefficient values should be accessible."""
        assert sample_coefficients.coefficients["class:beast"] == 0.15
        assert sample_coefficients.coefficients.get("nonexistent") is None


class TestAxieFeatures:
    """Test AxieFeatures data class."""

    @pytest.fixture
    def sample_features(self) -> AxieFeatures:
        """Create sample Axie features."""
        return AxieFeatures(
            axie_id=12345,
            class_="beast",
            breed_count=0,
            purity_score=5,
            gene_purity_score=14,
            part_eyes="eyes-kotaro",
            part_ears="ears-nut-cracker",
            part_mouth="mouth-nut-cracker",
            part_horn="horn-imp",
            part_back="back-ronin",
            part_tail="tail-nut-cracker",
            part_classes=["beast", "beast", "beast", "beast", "beast", "beast"],
            class_match_count=5,
            synergy_score=0.8,
        )

    def test_to_feature_dict(self, sample_features: AxieFeatures):
        """to_feature_dict should return model input features."""
        features = sample_features.to_feature_dict()

        assert isinstance(features, dict)
        assert features["class:beast"] == 1.0
        assert features["breed_count:0"] == 1.0
        assert features["purity:5"] == 1.0
        assert features["part:eyes:eyes-kotaro"] == 1.0
        assert features["gene_purity_score"] == 14.0
        assert features["class_match_count"] == 5.0

    def test_virgin_breed_count(self, sample_features: AxieFeatures):
        """Virgin Axie should have breed_count 0."""
        assert sample_features.breed_count == 0
        features = sample_features.to_feature_dict()
        assert features["breed_count:0"] == 1.0


class TestValuationResult:
    """Test ValuationResult data class."""

    @pytest.fixture
    def sample_result(self) -> ValuationResult:
        """Create sample valuation result."""
        return ValuationResult(
            axie_id=12345,
            hedonic_value_eth=Decimal("0.025"),
            ml_value_eth=None,
            ensemble_value_eth=Decimal("0.025"),
            confidence_lower_eth=Decimal("0.018"),
            confidence_upper_eth=Decimal("0.034"),
            confidence_score=0.85,
            current_listing_eth=Decimal("0.020"),
            class_floor_eth=Decimal("0.008"),
            class_avg_eth=Decimal("0.022"),
            discount_percent=20.0,
            z_score=-1.8,
            deal_score=65,
            is_deal=True,
            is_snipe=False,
            feature_contributions={"class:beast": 0.15, "purity:5": 0.22},
            method=ValuationMethod.HEDONIC,
            model_version="hedonic_v20250101",
            computed_at=datetime.utcnow(),
        )

    def test_to_dict_structure(self, sample_result: ValuationResult):
        """to_dict should have expected structure."""
        data = sample_result.to_dict()

        assert "axie_id" in data
        assert "valuation" in data
        assert "market_context" in data
        assert "deal_analysis" in data
        assert "feature_contributions" in data
        assert "metadata" in data

    def test_to_dict_valuation_fields(self, sample_result: ValuationResult):
        """Valuation section should have all fields."""
        data = sample_result.to_dict()
        valuation = data["valuation"]

        assert valuation["hedonic_eth"] == 0.025
        assert valuation["ensemble_eth"] == 0.025
        assert valuation["confidence_lower_eth"] == 0.018
        assert valuation["confidence_upper_eth"] == 0.034
        assert valuation["confidence_score"] == 0.85

    def test_to_dict_deal_analysis(self, sample_result: ValuationResult):
        """Deal analysis section should have all fields."""
        data = sample_result.to_dict()
        deal = data["deal_analysis"]

        assert deal["discount_percent"] == 20.0
        assert deal["z_score"] == -1.8
        assert deal["deal_score"] == 65
        assert deal["is_deal"] is True
        assert deal["is_snipe"] is False

    def test_empty_result(self):
        """Empty result should have zero confidence."""
        result = ValuationResult(axie_id=99999)

        assert result.confidence_score == 0.0
        assert result.hedonic_value_eth is None
        assert result.is_deal is False

    def test_deal_detection_logic(self):
        """Deal detection should work correctly."""
        # Non-deal (no significant discount)
        non_deal = ValuationResult(
            axie_id=1,
            ensemble_value_eth=Decimal("0.020"),
            current_listing_eth=Decimal("0.019"),
            is_deal=False,
            is_snipe=False,
        )
        assert non_deal.is_deal is False
        assert non_deal.is_snipe is False

        # Deal
        deal = ValuationResult(
            axie_id=2,
            ensemble_value_eth=Decimal("0.025"),
            current_listing_eth=Decimal("0.018"),
            discount_percent=28.0,
            z_score=-1.8,
            deal_score=65,
            is_deal=True,
            is_snipe=False,
        )
        assert deal.is_deal is True
        assert deal.is_snipe is False

        # Snipe
        snipe = ValuationResult(
            axie_id=3,
            ensemble_value_eth=Decimal("0.030"),
            current_listing_eth=Decimal("0.012"),
            discount_percent=60.0,
            z_score=-3.2,
            deal_score=95,
            is_deal=True,
            is_snipe=True,
        )
        assert snipe.is_deal is True
        assert snipe.is_snipe is True


class TestDealAlert:
    """Test DealAlert data class."""

    @pytest.fixture
    def sample_alert(self) -> DealAlert:
        """Create sample deal alert."""
        return DealAlert(
            axie_id=12345,
            class_="beast",
            listing_price_eth=Decimal("0.018"),
            fair_value_eth=Decimal("0.025"),
            discount_percent=28.0,
            z_score=-1.8,
            deal_score=65,
            deal_type="deal",
            seller="0x1234567890abcdef",
            marketplace_url="https://app.axieinfinity.com/marketplace/axies/12345",
            detected_at=datetime.utcnow(),
        )

    def test_to_dict_returns_dict(self, sample_alert: DealAlert):
        """to_dict should return serializable dictionary."""
        data = sample_alert.to_dict()

        assert isinstance(data, dict)
        assert data["axie_id"] == 12345
        assert data["class"] == "beast"
        assert data["discount_percent"] == 28.0
        assert data["deal_type"] == "deal"
        assert "marketplace_url" in data
        assert isinstance(data["detected_at"], str)

    def test_deal_vs_snipe_type(self):
        """Deal type should correctly indicate deal vs snipe."""
        deal = DealAlert(
            axie_id=1,
            class_="beast",
            listing_price_eth=Decimal("0.018"),
            fair_value_eth=Decimal("0.025"),
            discount_percent=28.0,
            z_score=-1.8,
            deal_score=65,
            deal_type="deal",
            seller="0x123",
            marketplace_url="https://example.com/1",
        )
        assert deal.deal_type == "deal"

        snipe = DealAlert(
            axie_id=2,
            class_="beast",
            listing_price_eth=Decimal("0.010"),
            fair_value_eth=Decimal("0.030"),
            discount_percent=66.0,
            z_score=-3.5,
            deal_score=95,
            deal_type="snipe",
            seller="0x456",
            marketplace_url="https://example.com/2",
        )
        assert snipe.deal_type == "snipe"


# Run with: pytest tests/test_valuation_types.py -v
