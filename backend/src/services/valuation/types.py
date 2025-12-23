"""
Valuation Type Definitions

Data classes and types for valuation services.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class ValuationMethod(str, Enum):
    """Valuation method types."""
    HEDONIC = "hedonic"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    ENSEMBLE = "ensemble"


@dataclass
class ValuationConfig:
    """Configuration for valuation service."""
    # Time windows for price statistics
    default_time_window_hours: int = 168  # 7 days
    short_time_window_hours: int = 24     # 1 day
    long_time_window_hours: int = 720     # 30 days

    # Minimum samples for statistical significance
    min_samples_for_coefficient: int = 10
    min_samples_for_trait: int = 5

    # Confidence interval settings
    confidence_level: float = 0.95
    default_std_multiplier: float = 1.96  # For 95% CI

    # Model weights for ensemble
    hedonic_weight: float = 0.4
    xgboost_weight: float = 0.36
    lightgbm_weight: float = 0.24

    # Deal detection thresholds
    deal_z_threshold: float = -1.5
    snipe_z_threshold: float = -2.5


@dataclass
class TraitStatistics:
    """Statistics for a single trait."""
    trait_key: str
    trait_type: str  # "class", "part", "breed_count", "purity"
    class_: Optional[str]

    avg_price_eth: Optional[Decimal]
    median_price_eth: Optional[Decimal]
    std_dev_eth: Optional[Decimal]
    min_price_eth: Optional[Decimal]
    max_price_eth: Optional[Decimal]

    sample_count: int
    time_window_hours: int
    computed_at: datetime

    def to_dict(self) -> dict:
        return {
            "trait_key": self.trait_key,
            "trait_type": self.trait_type,
            "class": self.class_,
            "avg_price_eth": float(self.avg_price_eth) if self.avg_price_eth else None,
            "median_price_eth": float(self.median_price_eth) if self.median_price_eth else None,
            "std_dev_eth": float(self.std_dev_eth) if self.std_dev_eth else None,
            "sample_count": self.sample_count,
            "time_window_hours": self.time_window_hours,
            "computed_at": self.computed_at.isoformat(),
        }


@dataclass
class TraitCoefficients:
    """Hedonic model coefficients."""
    model_version: str
    intercept: float
    coefficients: dict[str, float]  # trait_key -> coefficient

    # Model fit statistics
    r_squared: float
    adj_r_squared: float
    rmse: float
    sample_size: int
    feature_count: int

    # Training metadata
    train_start: datetime
    train_end: datetime
    trained_at: datetime

    def to_dict(self) -> dict:
        return {
            "model_version": self.model_version,
            "intercept": self.intercept,
            "coefficients": self.coefficients,
            "r_squared": self.r_squared,
            "adj_r_squared": self.adj_r_squared,
            "rmse": self.rmse,
            "sample_size": self.sample_size,
            "feature_count": self.feature_count,
            "trained_at": self.trained_at.isoformat(),
        }


@dataclass
class ValuationResult:
    """Result of valuating an Axie."""
    axie_id: int

    # Primary valuations
    hedonic_value_eth: Optional[Decimal] = None
    ml_value_eth: Optional[Decimal] = None
    ensemble_value_eth: Optional[Decimal] = None

    # Confidence interval (95%)
    confidence_lower_eth: Optional[Decimal] = None
    confidence_upper_eth: Optional[Decimal] = None
    confidence_score: float = 0.0  # 0-1, how confident we are

    # Market context
    current_listing_eth: Optional[Decimal] = None
    class_floor_eth: Optional[Decimal] = None
    class_avg_eth: Optional[Decimal] = None

    # Deal metrics
    discount_percent: Optional[float] = None
    z_score: Optional[float] = None
    deal_score: int = 0  # 0-100
    is_deal: bool = False
    is_snipe: bool = False

    # Feature breakdown (for explainability)
    feature_contributions: dict[str, float] = field(default_factory=dict)

    # Metadata
    method: ValuationMethod = ValuationMethod.HEDONIC
    model_version: Optional[str] = None
    computed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "axie_id": self.axie_id,
            "valuation": {
                "hedonic_eth": float(self.hedonic_value_eth) if self.hedonic_value_eth else None,
                "ml_eth": float(self.ml_value_eth) if self.ml_value_eth else None,
                "ensemble_eth": float(self.ensemble_value_eth) if self.ensemble_value_eth else None,
                "confidence_lower_eth": float(self.confidence_lower_eth) if self.confidence_lower_eth else None,
                "confidence_upper_eth": float(self.confidence_upper_eth) if self.confidence_upper_eth else None,
                "confidence_score": self.confidence_score,
            },
            "market_context": {
                "current_listing_eth": float(self.current_listing_eth) if self.current_listing_eth else None,
                "class_floor_eth": float(self.class_floor_eth) if self.class_floor_eth else None,
                "class_avg_eth": float(self.class_avg_eth) if self.class_avg_eth else None,
            },
            "deal_analysis": {
                "discount_percent": self.discount_percent,
                "z_score": self.z_score,
                "deal_score": self.deal_score,
                "is_deal": self.is_deal,
                "is_snipe": self.is_snipe,
            },
            "feature_contributions": self.feature_contributions,
            "metadata": {
                "method": self.method.value,
                "model_version": self.model_version,
                "computed_at": self.computed_at.isoformat(),
            },
        }


@dataclass
class AxieFeatures:
    """Extracted features for valuation model."""
    axie_id: int
    class_: str
    breed_count: int
    purity_score: int
    gene_purity_score: int

    # Part IDs (dominant genes)
    part_eyes: str
    part_ears: str
    part_mouth: str
    part_horn: str
    part_back: str
    part_tail: str

    # Part classes (for synergy calculation)
    part_classes: list[str] = field(default_factory=list)

    # Derived features
    class_match_count: int = 0  # Parts matching axie class
    synergy_score: float = 0.0

    def to_feature_dict(self) -> dict[str, float]:
        """Convert to feature dictionary for model input."""
        features = {
            f"class:{self.class_}": 1.0,
            f"breed_count:{self.breed_count}": 1.0,
            f"purity:{self.purity_score}": 1.0,
            f"part:eyes:{self.part_eyes}": 1.0,
            f"part:ears:{self.part_ears}": 1.0,
            f"part:mouth:{self.part_mouth}": 1.0,
            f"part:horn:{self.part_horn}": 1.0,
            f"part:back:{self.part_back}": 1.0,
            f"part:tail:{self.part_tail}": 1.0,
            "gene_purity_score": float(self.gene_purity_score),
            "class_match_count": float(self.class_match_count),
            "synergy_score": self.synergy_score,
        }
        return features


@dataclass
class DealAlert:
    """Deal alert for notification."""
    axie_id: int
    class_: str
    listing_price_eth: Decimal
    fair_value_eth: Decimal
    discount_percent: float
    z_score: float
    deal_score: int
    deal_type: str  # "deal", "snipe"

    seller: str
    marketplace_url: str

    detected_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "axie_id": self.axie_id,
            "class": self.class_,
            "listing_price_eth": float(self.listing_price_eth),
            "fair_value_eth": float(self.fair_value_eth),
            "discount_percent": self.discount_percent,
            "z_score": self.z_score,
            "deal_score": self.deal_score,
            "deal_type": self.deal_type,
            "seller": self.seller,
            "marketplace_url": self.marketplace_url,
            "detected_at": self.detected_at.isoformat(),
        }
