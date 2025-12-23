"""
Valuation Services

Provides fair market value estimation for Axies using:
- Hedonic pricing models (OLS regression)
- ML ensemble models (XGBoost + LightGBM)
- Confidence interval estimation
"""

from .hedonic_model import HedonicValuationService
from .types import (
    ValuationResult,
    TraitCoefficients,
    ValuationConfig,
)

__all__ = [
    "HedonicValuationService",
    "ValuationResult",
    "TraitCoefficients",
    "ValuationConfig",
]
