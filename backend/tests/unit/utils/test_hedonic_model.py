"""
Unit tests for the Hedonic Valuation Model.

Tests the core valuation logic including:
- OLS regression fitting
- Feature matrix building
- Value prediction
- Confidence interval calculation
"""

import pytest
import numpy as np
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.valuation.hedonic_model import HedonicValuationService
from src.services.valuation.types import (
    ValuationResult,
    TraitCoefficients,
    TraitStatistics,
    AxieFeatures,
    ValuationConfig,
    ValuationMethod,
)


class TestOLSRegression:
    """Test OLS regression implementation."""

    @pytest.fixture
    def service(self) -> HedonicValuationService:
        """Create service with mocked session."""
        mock_session = AsyncMock()
        return HedonicValuationService(mock_session)

    def test_fit_ols_simple(self, service: HedonicValuationService):
        """OLS should fit simple linear data correctly."""
        # Simple 2-feature case: y = 1 + 2*x1 + 3*x2
        X = np.array([
            [1, 0],
            [0, 1],
            [1, 1],
            [2, 1],
            [1, 2],
        ], dtype=np.float32)

        # y = 1 + 2*x1 + 3*x2
        y = np.array([3, 4, 6, 8, 9], dtype=np.float32)

        feature_names = ["x1", "x2"]
        coefficients, intercept, stats = service._fit_ols(X, y, feature_names)

        # Check approximate values (regularization affects exact values)
        assert len(coefficients) == 2
        assert abs(intercept - 1.0) < 0.5  # Intercept ~ 1
        assert stats["r_squared"] > 0.9  # Good fit

    def test_fit_ols_with_noise(self, service: HedonicValuationService):
        """OLS should handle noisy data."""
        np.random.seed(42)
        n_samples = 100
        n_features = 5

        # Generate random features
        X = np.random.randn(n_samples, n_features).astype(np.float32)

        # True coefficients
        true_coef = np.array([1.0, 2.0, -1.5, 0.5, 3.0])
        intercept_true = 2.0

        # Generate target with noise
        y = intercept_true + X @ true_coef + np.random.randn(n_samples) * 0.5
        y = y.astype(np.float32)

        feature_names = [f"f{i}" for i in range(n_features)]
        coefficients, intercept, stats = service._fit_ols(X, y, feature_names)

        # R² should be reasonable with noise
        assert stats["r_squared"] > 0.8

    def test_fit_ols_collinear_features(self, service: HedonicValuationService):
        """OLS should handle collinear features with regularization."""
        # Create collinear features (x2 = 2*x1)
        X = np.array([
            [1, 2],
            [2, 4],
            [3, 6],
            [4, 8],
            [5, 10],
        ], dtype=np.float32)

        y = np.array([1, 2, 3, 4, 5], dtype=np.float32)

        feature_names = ["x1", "x2"]

        # Should not raise error due to regularization
        coefficients, intercept, stats = service._fit_ols(X, y, feature_names)

        assert len(coefficients) == 2
        assert "r_squared" in stats


class TestFeatureMatrixBuilding:
    """Test feature matrix construction."""

    @pytest.fixture
    def service(self) -> HedonicValuationService:
        mock_session = AsyncMock()
        return HedonicValuationService(mock_session)

    @pytest.fixture
    def sample_training_data(self) -> list[dict]:
        """Create sample training data."""
        return [
            {
                "axie_id": 1,
                "price_eth": 0.02,
                "class": "beast",
                "breed_count": 0,
                "purity": 5,
                "part_eyes": "eyes-kotaro",
                "part_ears": "",
                "part_mouth": "mouth-nut-cracker",
                "part_horn": "",
                "part_back": "",
                "part_tail": "",
            },
            {
                "axie_id": 2,
                "price_eth": 0.015,
                "class": "plant",
                "breed_count": 2,
                "purity": 3,
                "part_eyes": "eyes-leafy",
                "part_ears": "",
                "part_mouth": "",
                "part_horn": "",
                "part_back": "",
                "part_tail": "",
            },
            {
                "axie_id": 3,
                "price_eth": 0.05,
                "class": "beast",
                "breed_count": 0,
                "purity": 6,
                "part_eyes": "eyes-kotaro",
                "part_ears": "",
                "part_mouth": "mouth-nut-cracker",
                "part_horn": "",
                "part_back": "",
                "part_tail": "",
            },
        ]

    def test_build_feature_matrix_shape(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Feature matrix should have correct shape."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        assert X.shape[0] == 3  # 3 samples
        assert X.shape[1] == len(feature_names)  # Features
        assert y.shape[0] == 3  # 3 targets

    def test_build_feature_matrix_log_transform(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Target should be log-transformed."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        # y should be log(price)
        expected_y0 = np.log(0.02)
        assert abs(y[0] - expected_y0) < 0.001

    def test_build_feature_matrix_includes_class(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Feature matrix should include class features."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        assert "class:beast" in feature_names
        assert "class:plant" in feature_names

    def test_build_feature_matrix_includes_breed(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Feature matrix should include breed count features."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        assert "breed:0" in feature_names
        assert "breed:2" in feature_names

    def test_build_feature_matrix_includes_purity(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Feature matrix should include purity features."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        assert "purity:5" in feature_names or any("purity" in f for f in feature_names)

    def test_build_feature_matrix_includes_parts(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Feature matrix should include part features."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        # Should include non-empty parts
        part_features = [f for f in feature_names if f.startswith("part:")]
        assert len(part_features) > 0

    def test_build_feature_matrix_binary_encoding(
        self,
        service: HedonicValuationService,
        sample_training_data: list[dict],
    ):
        """Features should be binary encoded (0 or 1)."""
        feature_names, X, y = service._build_feature_matrix(sample_training_data)

        # All values should be 0 or 1
        unique_values = np.unique(X)
        assert all(v in [0, 1] for v in unique_values)


class TestValueCalculation:
    """Test hedonic value calculation."""

    @pytest.fixture
    def service_with_coefficients(self) -> HedonicValuationService:
        """Create service with pre-loaded coefficients."""
        mock_session = AsyncMock()
        service = HedonicValuationService(mock_session)

        # Set up mock coefficients
        service._coefficients = TraitCoefficients(
            model_version="test_v1",
            intercept=-3.5,  # exp(-3.5) ≈ 0.03 ETH base price
            coefficients={
                "class:beast": 0.2,
                "class:plant": 0.1,
                "breed:0": 0.15,  # Virgin premium
                "breed:2": -0.05,
                "purity:5": 0.3,
                "purity:6": 0.5,
                "part:eyes:eyes-kotaro": 0.1,
                "part:mouth:mouth-nut-cracker": 0.2,
            },
            r_squared=0.75,
            adj_r_squared=0.74,
            rmse=0.4,
            sample_size=5000,
            feature_count=100,
            train_start=datetime(2025, 1, 1),
            train_end=datetime(2025, 1, 31),
            trained_at=datetime(2025, 1, 31),
        )

        return service

    @pytest.mark.asyncio
    async def test_calculate_hedonic_value(
        self,
        service_with_coefficients: HedonicValuationService,
    ):
        """Should calculate hedonic value from features."""
        features = AxieFeatures(
            axie_id=12345,
            class_="beast",
            breed_count=0,
            purity_score=5,
            gene_purity_score=14,
            part_eyes="eyes-kotaro",
            part_ears="",
            part_mouth="mouth-nut-cracker",
            part_horn="",
            part_back="",
            part_tail="",
        )

        result = await service_with_coefficients._calculate_hedonic_value(features)

        # Check result structure
        assert isinstance(result, ValuationResult)
        assert result.axie_id == 12345
        assert result.hedonic_value_eth is not None
        assert result.method == ValuationMethod.HEDONIC

        # Value should be reasonable
        # intercept=-3.5, class=0.2, breed=0.15, purity=0.3, eyes=0.1, mouth=0.2
        # log_price = -3.5 + 0.2 + 0.15 + 0.3 + 0.1 + 0.2 = -2.55
        # exp(-2.55) ≈ 0.078
        value = float(result.hedonic_value_eth)
        assert 0.01 < value < 1.0  # Reasonable range

    @pytest.mark.asyncio
    async def test_calculate_hedonic_value_confidence_interval(
        self,
        service_with_coefficients: HedonicValuationService,
    ):
        """Should calculate confidence intervals."""
        features = AxieFeatures(
            axie_id=12345,
            class_="beast",
            breed_count=0,
            purity_score=5,
            gene_purity_score=14,
            part_eyes="eyes-kotaro",
            part_ears="",
            part_mouth="",
            part_horn="",
            part_back="",
            part_tail="",
        )

        result = await service_with_coefficients._calculate_hedonic_value(features)

        assert result.confidence_lower_eth is not None
        assert result.confidence_upper_eth is not None

        # Lower < value < upper
        assert result.confidence_lower_eth < result.hedonic_value_eth
        assert result.hedonic_value_eth < result.confidence_upper_eth

    @pytest.mark.asyncio
    async def test_calculate_hedonic_value_feature_contributions(
        self,
        service_with_coefficients: HedonicValuationService,
    ):
        """Should track feature contributions."""
        features = AxieFeatures(
            axie_id=12345,
            class_="beast",
            breed_count=0,
            purity_score=5,
            gene_purity_score=14,
            part_eyes="eyes-kotaro",
            part_ears="",
            part_mouth="mouth-nut-cracker",
            part_horn="",
            part_back="",
            part_tail="",
        )

        result = await service_with_coefficients._calculate_hedonic_value(features)

        assert len(result.feature_contributions) > 0
        assert "class:beast" in result.feature_contributions
        assert result.feature_contributions["class:beast"] == 0.2

    @pytest.mark.asyncio
    async def test_calculate_hedonic_value_unknown_features(
        self,
        service_with_coefficients: HedonicValuationService,
    ):
        """Should handle unknown features gracefully."""
        features = AxieFeatures(
            axie_id=12345,
            class_="mech",  # Not in coefficients
            breed_count=5,  # Not in coefficients
            purity_score=2,  # Not in coefficients
            gene_purity_score=6,
            part_eyes="eyes-unknown",
            part_ears="",
            part_mouth="",
            part_horn="",
            part_back="",
            part_tail="",
        )

        result = await service_with_coefficients._calculate_hedonic_value(features)

        # Should still produce a result (using intercept only)
        assert result.hedonic_value_eth is not None
        # Confidence should be lower due to missing features
        assert result.confidence_score < 0.5


class TestDealDetection:
    """Test deal detection logic."""

    @pytest.fixture
    def config(self) -> ValuationConfig:
        return ValuationConfig(
            deal_z_threshold=-1.5,
            snipe_z_threshold=-2.5,
        )

    def test_deal_z_score_threshold(self, config: ValuationConfig):
        """Deals should be detected at z < -1.5."""
        # This would be tested in the full integration test
        assert config.deal_z_threshold == -1.5

    def test_snipe_z_score_threshold(self, config: ValuationConfig):
        """Snipes should be detected at z < -2.5."""
        assert config.snipe_z_threshold == -2.5


class TestServiceIntegration:
    """Integration tests for the valuation service (with mocked DB)."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create mock database session."""
        session = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_valuate_returns_result(self, mock_session: AsyncMock):
        """valuate should return ValuationResult."""
        # Mock the database queries
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # Axie not found

        mock_session.execute.return_value = mock_result

        service = HedonicValuationService(mock_session)
        result = await service.valuate(99999)

        assert isinstance(result, ValuationResult)
        assert result.axie_id == 99999
        # No data, so confidence should be 0
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_batch_valuate_returns_list(self, mock_session: AsyncMock):
        """batch_valuate should return list of results."""
        # Mock the database queries
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None

        mock_session.execute.return_value = mock_result

        service = HedonicValuationService(mock_session)
        results = await service.batch_valuate([1, 2, 3])

        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, ValuationResult) for r in results)


# Run with: pytest tests/test_hedonic_model.py -v
