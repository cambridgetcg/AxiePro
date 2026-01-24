"""
Synthetic validation flows for automated feature testing.

Provides automated flows that simulate real trader scenarios
to validate feature effectiveness:
- Deal Hunter: Validates deal quality
- Breeding Planner: Validates breeding simulation accuracy
- Meta Scout: Validates meta shift detection timeliness
"""

from .base import SyntheticFlow, FlowResult, ValidationResult
from .deal_hunter import DealHunterFlow
from .breeding_planner import BreedingPlannerFlow
from .meta_scout import MetaScoutFlow
from .runner import FlowRunner

__all__ = [
    "SyntheticFlow",
    "FlowResult",
    "ValidationResult",
    "DealHunterFlow",
    "BreedingPlannerFlow",
    "MetaScoutFlow",
    "FlowRunner",
]
