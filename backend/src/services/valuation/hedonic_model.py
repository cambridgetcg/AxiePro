"""
Hedonic Valuation Model

Implements hedonic pricing for Axie valuation using OLS regression.
The model decomposes Axie prices into attribute contributions:

    ln(P_i) = α + Σ β_j * X_ij + ε_i

Where:
- P_i is the price of Axie i
- α is the intercept (base price)
- β_j is the coefficient for trait j
- X_ij is the binary indicator (1 if Axie i has trait j)
- ε_i is the error term
"""

import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import math

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .types import (
    ValuationResult,
    TraitCoefficients,
    TraitStatistics,
    AxieFeatures,
    ValuationConfig,
    ValuationMethod,
)

logger = logging.getLogger(__name__)


class HedonicValuationService:
    """
    Hedonic pricing model for Axie valuation.

    Uses log-linear regression to estimate fair market value based on
    Axie attributes (class, parts, breed count, purity).

    Usage:
        service = HedonicValuationService(db_session)
        result = await service.valuate(axie_id)
        print(f"Fair value: {result.hedonic_value_eth} ETH")
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Optional[ValuationConfig] = None,
    ):
        """
        Initialize hedonic valuation service.

        Args:
            session: Async database session
            config: Valuation configuration (uses defaults if not provided)
        """
        self.session = session
        self.config = config or ValuationConfig()
        self._coefficients: Optional[TraitCoefficients] = None
        self._trait_stats_cache: dict[str, TraitStatistics] = {}

    async def valuate(
        self,
        axie_id: int,
        include_market_context: bool = True,
    ) -> ValuationResult:
        """
        Valuate a single Axie using hedonic pricing.

        Args:
            axie_id: The Axie ID to valuate
            include_market_context: Whether to include floor prices and deal analysis

        Returns:
            ValuationResult with fair value estimate and confidence interval
        """
        # Get Axie features
        features = await self._get_axie_features(axie_id)
        if not features:
            return ValuationResult(
                axie_id=axie_id,
                confidence_score=0.0,
                method=ValuationMethod.HEDONIC,
            )

        # Load coefficients if not cached
        if not self._coefficients:
            self._coefficients = await self._load_active_coefficients()

        # If no trained model, fall back to trait statistics
        if not self._coefficients:
            return await self._valuate_from_statistics(features, include_market_context)

        # Calculate hedonic value
        result = await self._calculate_hedonic_value(features)

        # Add market context if requested
        if include_market_context:
            await self._add_market_context(result, features)

        return result

    async def batch_valuate(
        self,
        axie_ids: list[int],
    ) -> list[ValuationResult]:
        """
        Valuate multiple Axies efficiently.

        Args:
            axie_ids: List of Axie IDs to valuate

        Returns:
            List of ValuationResults
        """
        # Load coefficients once
        if not self._coefficients:
            self._coefficients = await self._load_active_coefficients()

        results = []
        for axie_id in axie_ids:
            try:
                result = await self.valuate(axie_id, include_market_context=False)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to valuate Axie {axie_id}: {e}")
                results.append(ValuationResult(
                    axie_id=axie_id,
                    confidence_score=0.0,
                ))

        return results

    async def compute_coefficients(
        self,
        time_window_days: int = 30,
        min_samples: int = 1000,
    ) -> TraitCoefficients:
        """
        Compute hedonic model coefficients from historical sales data.

        Uses OLS regression on log-transformed prices:
            ln(price) = α + Σ β_j * X_j

        Args:
            time_window_days: Days of historical data to use
            min_samples: Minimum number of sales required

        Returns:
            TraitCoefficients with trained model parameters
        """
        logger.info(f"Computing hedonic coefficients from {time_window_days} days of data")

        # Fetch training data
        train_data = await self._fetch_training_data(time_window_days, min_samples)

        if len(train_data) < min_samples:
            raise ValueError(f"Insufficient data: {len(train_data)} samples (need {min_samples})")

        # Build feature matrix and target vector
        feature_names, X, y = self._build_feature_matrix(train_data)

        # Fit OLS regression
        coefficients, intercept, stats = self._fit_ols(X, y, feature_names)

        # Create coefficient mapping
        coef_dict = {"intercept": float(intercept)}
        for name, coef in zip(feature_names, coefficients):
            coef_dict[name] = float(coef)

        # Generate version string
        version = f"hedonic_v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        train_end = datetime.utcnow()
        train_start = train_end - timedelta(days=time_window_days)

        result = TraitCoefficients(
            model_version=version,
            intercept=float(intercept),
            coefficients=coef_dict,
            r_squared=stats["r_squared"],
            adj_r_squared=stats["adj_r_squared"],
            rmse=stats["rmse"],
            sample_size=len(train_data),
            feature_count=len(feature_names),
            train_start=train_start,
            train_end=train_end,
            trained_at=datetime.utcnow(),
        )

        # Store coefficients in database
        await self._store_coefficients(result)

        # Update cache
        self._coefficients = result

        logger.info(
            f"Trained hedonic model: R²={stats['r_squared']:.4f}, "
            f"RMSE={stats['rmse']:.4f}, features={len(feature_names)}"
        )

        return result

    async def compute_trait_statistics(
        self,
        time_window_hours: int = 168,
    ) -> dict[str, TraitStatistics]:
        """
        Compute price statistics for all traits.

        Args:
            time_window_hours: Hours of data to analyze

        Returns:
            Dictionary mapping trait_key to TraitStatistics
        """
        logger.info(f"Computing trait statistics for {time_window_hours}h window")

        # Compute class statistics
        class_stats = await self._compute_class_statistics(time_window_hours)

        # Compute part statistics
        part_stats = await self._compute_part_statistics(time_window_hours)

        # Compute breed count statistics
        breed_stats = await self._compute_breed_statistics(time_window_hours)

        # Combine all statistics
        all_stats = {**class_stats, **part_stats, **breed_stats}

        # Store in database
        await self._store_trait_statistics(all_stats.values())

        # Update cache
        self._trait_stats_cache = all_stats

        logger.info(f"Computed {len(all_stats)} trait statistics")

        return all_stats

    # =========================================================================
    # Private Methods - Data Access
    # =========================================================================

    async def _get_axie_features(self, axie_id: int) -> Optional[AxieFeatures]:
        """Fetch Axie attributes and extract features."""
        query = text("""
            SELECT
                am.axie_id,
                am.class AS class_,
                am.breed_count,
                am.pure_part_count,
                am.gene_quality,
                am.part_eyes,
                am.part_ears,
                am.part_mouth,
                am.part_horn,
                am.part_back,
                am.part_tail,
                am.parts_json
            FROM axie.axie_metadata am
            WHERE am.axie_id = :axie_id
        """)

        result = await self.session.execute(query, {"axie_id": axie_id})
        row = result.fetchone()

        if not row:
            return None

        # Parse parts JSON for class information
        parts_json = row.parts_json or {}
        part_classes = []
        if isinstance(parts_json, str):
            try:
                parts_json = json.loads(parts_json)
            except json.JSONDecodeError:
                parts_json = {}

        if isinstance(parts_json, list):
            for part in parts_json:
                if isinstance(part, dict):
                    part_classes.append(part.get("class", "").lower())

        axie_class = (row.class_ or "").lower()
        class_match_count = sum(1 for pc in part_classes if pc == axie_class)

        return AxieFeatures(
            axie_id=row.axie_id,
            class_=axie_class,
            breed_count=row.breed_count or 0,
            purity_score=row.pure_part_count or 0,
            gene_purity_score=row.gene_quality or 0,
            part_eyes=row.part_eyes or "",
            part_ears=row.part_ears or "",
            part_mouth=row.part_mouth or "",
            part_horn=row.part_horn or "",
            part_back=row.part_back or "",
            part_tail=row.part_tail or "",
            part_classes=part_classes,
            class_match_count=class_match_count,
        )

    async def _load_active_coefficients(self) -> Optional[TraitCoefficients]:
        """Load active hedonic model coefficients from database."""
        query = text("""
            SELECT
                model_version,
                coefficients,
                r_squared,
                adj_r_squared,
                rmse,
                sample_size,
                feature_count,
                train_start,
                train_end,
                trained_at
            FROM axie.hedonic_coefficients
            WHERE is_active = TRUE
            ORDER BY trained_at DESC
            LIMIT 1
        """)

        result = await self.session.execute(query)
        row = result.fetchone()

        if not row:
            return None

        coef_dict = row.coefficients
        if isinstance(coef_dict, str):
            coef_dict = json.loads(coef_dict)

        intercept = coef_dict.pop("intercept", 0.0)

        return TraitCoefficients(
            model_version=row.model_version,
            intercept=intercept,
            coefficients=coef_dict,
            r_squared=float(row.r_squared or 0),
            adj_r_squared=float(row.adj_r_squared or 0),
            rmse=float(row.rmse or 0),
            sample_size=row.sample_size or 0,
            feature_count=row.feature_count or 0,
            train_start=row.train_start,
            train_end=row.train_end,
            trained_at=row.trained_at,
        )

    async def _fetch_training_data(
        self,
        time_window_days: int,
        min_samples: int,
    ) -> list[dict]:
        """Fetch sales data for training."""
        query = text("""
            SELECT
                s.axie_id,
                s.price_token as price_eth,
                s.class,
                s.breed_count,
                am.pure_part_count,
                am.part_eyes,
                am.part_ears,
                am.part_mouth,
                am.part_horn,
                am.part_back,
                am.part_tail
            FROM axie.axie_sales s
            LEFT JOIN axie.axie_metadata am ON s.axie_id = am.axie_id
            WHERE s.block_timestamp >= NOW() - INTERVAL :days || ' days'
              AND s.price_token > 0.0001
              AND s.price_token < 100
              AND s.token_type IN ('ETH', 'WETH')
              AND am.class IS NOT NULL
            ORDER BY s.block_timestamp DESC
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {"days": str(time_window_days), "limit": min_samples * 2}
        )
        rows = result.fetchall()

        return [
            {
                "axie_id": row.axie_id,
                "price_eth": float(row.price_eth),
                "class": (getattr(row, 'class_', None) or getattr(row, 'class', None) or "").lower(),
                "breed_count": row.breed_count or 0,
                "purity": row.pure_part_count or 0,
                "part_eyes": row.part_eyes or "",
                "part_ears": row.part_ears or "",
                "part_mouth": row.part_mouth or "",
                "part_horn": row.part_horn or "",
                "part_back": row.part_back or "",
                "part_tail": row.part_tail or "",
            }
            for row in rows
        ]

    # =========================================================================
    # Private Methods - Model Computation
    # =========================================================================

    def _build_feature_matrix(
        self,
        train_data: list[dict],
    ) -> tuple[list[str], np.ndarray, np.ndarray]:
        """Build feature matrix X and target vector y from training data."""
        # Collect all unique feature names
        feature_set = set()

        for record in train_data:
            # Class feature
            if record["class"]:
                feature_set.add(f"class:{record['class']}")

            # Breed count (binned)
            breed_bin = min(record["breed_count"], 7)
            feature_set.add(f"breed:{breed_bin}")

            # Purity
            feature_set.add(f"purity:{record['purity']}")

            # Parts (only if not empty)
            for part_type in ["eyes", "ears", "mouth", "horn", "back", "tail"]:
                part_id = record.get(f"part_{part_type}", "")
                if part_id:
                    feature_set.add(f"part:{part_type}:{part_id}")

        feature_names = sorted(list(feature_set))
        feature_idx = {name: i for i, name in enumerate(feature_names)}

        # Build matrices
        n_samples = len(train_data)
        n_features = len(feature_names)

        X = np.zeros((n_samples, n_features), dtype=np.float32)
        y = np.zeros(n_samples, dtype=np.float32)

        for i, record in enumerate(train_data):
            # Log-transform target
            y[i] = np.log(max(record["price_eth"], 0.0001))

            # Set feature values
            if record["class"]:
                feat_name = f"class:{record['class']}"
                if feat_name in feature_idx:
                    X[i, feature_idx[feat_name]] = 1.0

            breed_bin = min(record["breed_count"], 7)
            feat_name = f"breed:{breed_bin}"
            if feat_name in feature_idx:
                X[i, feature_idx[feat_name]] = 1.0

            feat_name = f"purity:{record['purity']}"
            if feat_name in feature_idx:
                X[i, feature_idx[feat_name]] = 1.0

            for part_type in ["eyes", "ears", "mouth", "horn", "back", "tail"]:
                part_id = record.get(f"part_{part_type}", "")
                if part_id:
                    feat_name = f"part:{part_type}:{part_id}"
                    if feat_name in feature_idx:
                        X[i, feature_idx[feat_name]] = 1.0

        return feature_names, X, y

    def _fit_ols(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: list[str],
    ) -> tuple[np.ndarray, float, dict]:
        """
        Fit OLS regression using normal equations.

        β = (X'X)^(-1) X'y

        Args:
            X: Feature matrix (n_samples x n_features)
            y: Target vector (n_samples,)
            feature_names: Feature names for coefficient mapping

        Returns:
            Tuple of (coefficients, intercept, stats_dict)
        """
        n_samples, n_features = X.shape

        # Add intercept column
        X_with_intercept = np.column_stack([np.ones(n_samples), X])

        # Solve normal equations with regularization (ridge)
        lambda_reg = 0.01  # Small regularization to handle collinearity
        XtX = X_with_intercept.T @ X_with_intercept
        XtX += lambda_reg * np.eye(XtX.shape[0])
        Xty = X_with_intercept.T @ y

        try:
            beta = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            # Fall back to pseudo-inverse
            beta = np.linalg.pinv(XtX) @ Xty

        intercept = beta[0]
        coefficients = beta[1:]

        # Calculate fit statistics
        y_pred = X_with_intercept @ beta
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        adj_r_squared = 1 - (1 - r_squared) * (n_samples - 1) / (n_samples - n_features - 1)
        rmse = np.sqrt(ss_res / n_samples)

        stats = {
            "r_squared": float(r_squared),
            "adj_r_squared": float(adj_r_squared),
            "rmse": float(rmse),
        }

        return coefficients, intercept, stats

    async def _calculate_hedonic_value(
        self,
        features: AxieFeatures,
    ) -> ValuationResult:
        """Calculate hedonic value using trained coefficients."""
        if not self._coefficients:
            return ValuationResult(
                axie_id=features.axie_id,
                confidence_score=0.0,
            )

        coeffs = self._coefficients.coefficients
        intercept = self._coefficients.intercept

        # Calculate log(price)
        log_price = intercept
        feature_contributions = {}

        # Class contribution
        class_key = f"class:{features.class_}"
        if class_key in coeffs:
            contrib = coeffs[class_key]
            log_price += contrib
            feature_contributions[class_key] = contrib

        # Breed count contribution
        breed_key = f"breed:{min(features.breed_count, 7)}"
        if breed_key in coeffs:
            contrib = coeffs[breed_key]
            log_price += contrib
            feature_contributions[breed_key] = contrib

        # Purity contribution
        purity_key = f"purity:{features.purity_score}"
        if purity_key in coeffs:
            contrib = coeffs[purity_key]
            log_price += contrib
            feature_contributions[purity_key] = contrib

        # Part contributions
        for part_type, part_id in [
            ("eyes", features.part_eyes),
            ("ears", features.part_ears),
            ("mouth", features.part_mouth),
            ("horn", features.part_horn),
            ("back", features.part_back),
            ("tail", features.part_tail),
        ]:
            if part_id:
                part_key = f"part:{part_type}:{part_id}"
                if part_key in coeffs:
                    contrib = coeffs[part_key]
                    log_price += contrib
                    feature_contributions[part_key] = contrib

        # Convert back from log space
        hedonic_value = Decimal(str(math.exp(log_price)))

        # Calculate confidence interval (using RMSE as std estimate)
        rmse = self._coefficients.rmse
        ci_lower = Decimal(str(math.exp(log_price - 1.96 * rmse)))
        ci_upper = Decimal(str(math.exp(log_price + 1.96 * rmse)))

        # Confidence score based on feature coverage
        total_features = 8  # class + breed + purity + 6 parts (but only count 5 non-empty)
        covered_features = len(feature_contributions)
        confidence_score = min(1.0, covered_features / total_features)

        return ValuationResult(
            axie_id=features.axie_id,
            hedonic_value_eth=hedonic_value,
            ensemble_value_eth=hedonic_value,  # For now, ensemble = hedonic
            confidence_lower_eth=ci_lower,
            confidence_upper_eth=ci_upper,
            confidence_score=confidence_score,
            feature_contributions=feature_contributions,
            method=ValuationMethod.HEDONIC,
            model_version=self._coefficients.model_version,
            computed_at=datetime.utcnow(),
        )

    async def _valuate_from_statistics(
        self,
        features: AxieFeatures,
        include_market_context: bool,
    ) -> ValuationResult:
        """
        Fallback valuation using trait statistics when no model is trained.
        Uses simple averaging of trait prices.
        """
        # Get class average as baseline
        class_stats = await self._get_trait_stats(f"class:{features.class_}")

        if not class_stats or not class_stats.avg_price_eth:
            return ValuationResult(
                axie_id=features.axie_id,
                confidence_score=0.0,
            )

        base_value = class_stats.avg_price_eth

        # Adjust for purity (rough multiplier)
        purity_multiplier = 1.0 + (features.purity_score * 0.05)

        # Adjust for breed count (virgin premium)
        breed_multiplier = 1.0
        if features.breed_count == 0:
            breed_multiplier = 1.15
        elif features.breed_count >= 5:
            breed_multiplier = 0.90

        estimated_value = base_value * Decimal(str(purity_multiplier * breed_multiplier))

        # Rough confidence interval
        std_dev = class_stats.std_dev_eth or (base_value * Decimal("0.3"))
        ci_lower = estimated_value - (std_dev * Decimal("1.96"))
        ci_upper = estimated_value + (std_dev * Decimal("1.96"))

        result = ValuationResult(
            axie_id=features.axie_id,
            hedonic_value_eth=estimated_value,
            ensemble_value_eth=estimated_value,
            confidence_lower_eth=max(ci_lower, Decimal("0.0001")),
            confidence_upper_eth=ci_upper,
            confidence_score=0.5,  # Lower confidence for stats-based
            method=ValuationMethod.HEDONIC,
            computed_at=datetime.utcnow(),
        )

        if include_market_context:
            await self._add_market_context(result, features)

        return result

    async def _add_market_context(
        self,
        result: ValuationResult,
        features: AxieFeatures,
    ) -> None:
        """Add market context (floor prices, deal analysis) to result."""
        # Get class floor and average
        class_stats = await self._get_trait_stats(f"class:{features.class_}")

        if class_stats:
            result.class_avg_eth = class_stats.avg_price_eth
            result.class_floor_eth = class_stats.min_price_eth

        # Check for current listing
        listing_query = text("""
            SELECT price_eth
            FROM axie.axie_listings
            WHERE axie_id = :axie_id
            LIMIT 1
        """)

        listing_result = await self.session.execute(
            listing_query,
            {"axie_id": features.axie_id}
        )
        listing_row = listing_result.fetchone()

        if listing_row and listing_row.price_eth:
            result.current_listing_eth = Decimal(str(listing_row.price_eth))

            # Calculate deal metrics
            if result.ensemble_value_eth and result.ensemble_value_eth > 0:
                fmv = result.ensemble_value_eth
                listing = result.current_listing_eth

                discount = (fmv - listing) / fmv * 100
                result.discount_percent = float(discount)

                # Calculate Z-score if we have std dev
                if class_stats and class_stats.std_dev_eth and class_stats.std_dev_eth > 0:
                    z_score = (float(listing) - float(fmv)) / float(class_stats.std_dev_eth)
                    result.z_score = z_score

                    # Determine deal status
                    if z_score <= self.config.snipe_z_threshold:
                        result.is_snipe = True
                        result.is_deal = True
                        result.deal_score = min(100, int(abs(z_score) * 30))
                    elif z_score <= self.config.deal_z_threshold:
                        result.is_deal = True
                        result.deal_score = min(80, int(abs(z_score) * 25))

    async def _get_trait_stats(self, trait_key: str) -> Optional[TraitStatistics]:
        """Get trait statistics from cache or database."""
        # Check cache
        if trait_key in self._trait_stats_cache:
            stats = self._trait_stats_cache[trait_key]
            # Check if still fresh (1 hour)
            if (datetime.utcnow() - stats.computed_at).total_seconds() < 3600:
                return stats

        # Query database
        query = text("""
            SELECT
                trait_key, trait_type, class,
                avg_price_eth, median_price_eth, std_dev_eth,
                min_price_eth, max_price_eth,
                sample_count, time_window_hours, computed_at
            FROM axie.trait_statistics
            WHERE trait_key = :trait_key
            ORDER BY computed_at DESC
            LIMIT 1
        """)

        result = await self.session.execute(query, {"trait_key": trait_key})
        row = result.fetchone()

        if not row:
            return None

        stats = TraitStatistics(
            trait_key=row.trait_key,
            trait_type=row.trait_type,
            class_=row.class_,
            avg_price_eth=Decimal(str(row.avg_price_eth)) if row.avg_price_eth else None,
            median_price_eth=Decimal(str(row.median_price_eth)) if row.median_price_eth else None,
            std_dev_eth=Decimal(str(row.std_dev_eth)) if row.std_dev_eth else None,
            min_price_eth=Decimal(str(row.min_price_eth)) if row.min_price_eth else None,
            max_price_eth=Decimal(str(row.max_price_eth)) if row.max_price_eth else None,
            sample_count=row.sample_count,
            time_window_hours=row.time_window_hours,
            computed_at=row.computed_at,
        )

        # Update cache
        self._trait_stats_cache[trait_key] = stats

        return stats

    # =========================================================================
    # Private Methods - Statistics Computation
    # =========================================================================

    async def _compute_class_statistics(
        self,
        time_window_hours: int,
    ) -> dict[str, TraitStatistics]:
        """Compute price statistics by class."""
        query = text("""
            SELECT
                class,
                AVG(price_token) as avg_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_token) as median_price,
                STDDEV(price_token) as std_dev,
                MIN(price_token) as min_price,
                MAX(price_token) as max_price,
                COUNT(*) as sample_count
            FROM axie.axie_sales
            WHERE block_timestamp >= NOW() - INTERVAL :hours || ' hours'
              AND price_token > 0.0001
              AND price_token < 100
              AND token_type IN ('ETH', 'WETH')
              AND class IS NOT NULL
            GROUP BY class
        """)

        result = await self.session.execute(query, {"hours": str(time_window_hours)})
        rows = result.fetchall()

        stats = {}
        for row in rows:
            class_lower = (getattr(row, 'class_', None) or getattr(row, 'class', None) or "").lower()
            trait_key = f"class:{class_lower}"
            stats[trait_key] = TraitStatistics(
                trait_key=trait_key,
                trait_type="class",
                class_=class_lower,
                avg_price_eth=Decimal(str(row.avg_price)) if row.avg_price else None,
                median_price_eth=Decimal(str(row.median_price)) if row.median_price else None,
                std_dev_eth=Decimal(str(row.std_dev)) if row.std_dev else None,
                min_price_eth=Decimal(str(row.min_price)) if row.min_price else None,
                max_price_eth=Decimal(str(row.max_price)) if row.max_price else None,
                sample_count=row.sample_count,
                time_window_hours=time_window_hours,
                computed_at=datetime.utcnow(),
            )

        return stats

    async def _compute_part_statistics(
        self,
        time_window_hours: int,
    ) -> dict[str, TraitStatistics]:
        """Compute price statistics by part."""
        # This would require joining with metadata
        # For now, return empty - implement when part data is available
        return {}

    async def _compute_breed_statistics(
        self,
        time_window_hours: int,
    ) -> dict[str, TraitStatistics]:
        """Compute price statistics by breed count."""
        query = text("""
            SELECT
                breed_count,
                AVG(price_token) as avg_price,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_token) as median_price,
                STDDEV(price_token) as std_dev,
                MIN(price_token) as min_price,
                MAX(price_token) as max_price,
                COUNT(*) as sample_count
            FROM axie.axie_sales
            WHERE block_timestamp >= NOW() - INTERVAL :hours || ' hours'
              AND price_token > 0.0001
              AND price_token < 100
              AND token_type IN ('ETH', 'WETH')
              AND breed_count IS NOT NULL
            GROUP BY breed_count
        """)

        result = await self.session.execute(query, {"hours": str(time_window_hours)})
        rows = result.fetchall()

        stats = {}
        for row in rows:
            trait_key = f"breed:{row.breed_count}"
            stats[trait_key] = TraitStatistics(
                trait_key=trait_key,
                trait_type="breed_count",
                class_=None,
                avg_price_eth=Decimal(str(row.avg_price)) if row.avg_price else None,
                median_price_eth=Decimal(str(row.median_price)) if row.median_price else None,
                std_dev_eth=Decimal(str(row.std_dev)) if row.std_dev else None,
                min_price_eth=Decimal(str(row.min_price)) if row.min_price else None,
                max_price_eth=Decimal(str(row.max_price)) if row.max_price else None,
                sample_count=row.sample_count,
                time_window_hours=time_window_hours,
                computed_at=datetime.utcnow(),
            )

        return stats

    # =========================================================================
    # Private Methods - Storage
    # =========================================================================

    async def _store_coefficients(self, coefficients: TraitCoefficients) -> None:
        """Store trained coefficients in database."""
        # Deactivate previous models
        await self.session.execute(text("""
            UPDATE axie.hedonic_coefficients SET is_active = FALSE
        """))

        # Insert new model
        coef_json = json.dumps({
            "intercept": coefficients.intercept,
            **coefficients.coefficients
        })

        await self.session.execute(text("""
            INSERT INTO axie.hedonic_coefficients (
                model_version, coefficients, r_squared, adj_r_squared, rmse,
                sample_size, feature_count, train_start, train_end, is_active
            ) VALUES (
                :version, :coefficients, :r2, :adj_r2, :rmse,
                :samples, :features, :start, :end, TRUE
            )
        """), {
            "version": coefficients.model_version,
            "coefficients": coef_json,
            "r2": coefficients.r_squared,
            "adj_r2": coefficients.adj_r_squared,
            "rmse": coefficients.rmse,
            "samples": coefficients.sample_size,
            "features": coefficients.feature_count,
            "start": coefficients.train_start,
            "end": coefficients.train_end,
        })

        await self.session.commit()

    async def _store_trait_statistics(
        self,
        statistics,  # list[TraitStatistics] or dict_values
    ) -> None:
        """Store trait statistics in database."""
        for stat in statistics:
            await self.session.execute(text("""
                INSERT INTO axie.trait_statistics (
                    trait_key, trait_type, class,
                    avg_price_eth, median_price_eth, std_dev_eth,
                    min_price_eth, max_price_eth,
                    sample_count, time_window_hours, computed_at
                ) VALUES (
                    :key, :type, :class,
                    :avg, :median, :std,
                    :min, :max,
                    :count, :window, :computed
                )
                ON CONFLICT (trait_key, class, time_window_hours)
                DO UPDATE SET
                    avg_price_eth = EXCLUDED.avg_price_eth,
                    median_price_eth = EXCLUDED.median_price_eth,
                    std_dev_eth = EXCLUDED.std_dev_eth,
                    min_price_eth = EXCLUDED.min_price_eth,
                    max_price_eth = EXCLUDED.max_price_eth,
                    sample_count = EXCLUDED.sample_count,
                    computed_at = EXCLUDED.computed_at
            """), {
                "key": stat.trait_key,
                "type": stat.trait_type,
                "class": stat.class_,
                "avg": float(stat.avg_price_eth) if stat.avg_price_eth else None,
                "median": float(stat.median_price_eth) if stat.median_price_eth else None,
                "std": float(stat.std_dev_eth) if stat.std_dev_eth else None,
                "min": float(stat.min_price_eth) if stat.min_price_eth else None,
                "max": float(stat.max_price_eth) if stat.max_price_eth else None,
                "count": stat.sample_count,
                "window": stat.time_window_hours,
                "computed": stat.computed_at,
            })

        await self.session.commit()
