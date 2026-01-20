"""
Normalized Deal Scoring Service

Provides multi-factor percentile-based deal scoring that normalizes
raw deal metrics into a consistent 0-100 scale with user-friendly tiers.

Scoring Formula:
    normalized_score = (D*0.4 + C*0.25 + L*0.2 + T*0.15) * 100

Where:
    D = Discount percentile (how good is the discount vs recent deals)
    C = Confidence percentile (model confidence in valuation)
    L = Liquidity score (how quickly similar Axies sell)
    T = Time factor (freshness of the listing)

Tiers:
    SNIPE (80-100): Exceptional deal, act immediately
    ELITE (60-79): High value deal, strong buy
    GOOD (40-59): Above average deal
    FAIR (20-39): Marginal deal, evaluate carefully
    PASS (0-19): Below threshold, likely not worth it
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List
import statistics


class DealTier(str, Enum):
    """User-friendly deal tier classification."""
    SNIPE = "snipe"      # 80-100: Red/urgent
    ELITE = "elite"      # 60-79: Orange
    GOOD = "good"        # 40-59: Yellow
    FAIR = "fair"        # 20-39: Green
    PASS = "pass"        # 0-19: Gray


@dataclass
class NormalizedDealScore:
    """Result of normalized deal scoring."""
    # Raw inputs
    discount_percent: float
    confidence_score: float
    time_since_listing_hours: float

    # Percentile components (0-1)
    discount_percentile: float
    confidence_percentile: float
    liquidity_score: float
    time_score: float

    # Final scores
    normalized_score: int  # 0-100
    legacy_score: int  # Backward compatible with existing deal_score
    tier: DealTier
    tier_label: str
    tier_color: str

    # Metadata
    scoring_version: str = "2.0"
    computed_at: str = ""

    def __post_init__(self):
        if not self.computed_at:
            self.computed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "normalized_score": self.normalized_score,
            "legacy_score": self.legacy_score,
            "tier": self.tier.value,
            "tier_label": self.tier_label,
            "tier_color": self.tier_color,
            "components": {
                "discount_percentile": round(self.discount_percentile, 3),
                "confidence_percentile": round(self.confidence_percentile, 3),
                "liquidity_score": round(self.liquidity_score, 3),
                "time_score": round(self.time_score, 3),
            },
            "raw_inputs": {
                "discount_percent": round(self.discount_percent, 2),
                "confidence_score": round(self.confidence_score, 2),
                "time_since_listing_hours": round(self.time_since_listing_hours, 1),
            },
            "scoring_version": self.scoring_version,
            "computed_at": self.computed_at,
        }


class NormalizedDealScorer:
    """
    Multi-factor deal scorer with percentile normalization.

    Maintains historical deal data to compute percentile rankings,
    ensuring scores are relative to recent market conditions.
    """

    # Scoring weights
    WEIGHT_DISCOUNT = 0.40
    WEIGHT_CONFIDENCE = 0.25
    WEIGHT_LIQUIDITY = 0.20
    WEIGHT_TIME = 0.15

    # Tier thresholds
    TIER_THRESHOLDS = {
        DealTier.SNIPE: (80, 100),
        DealTier.ELITE: (60, 79),
        DealTier.GOOD: (40, 59),
        DealTier.FAIR: (20, 39),
        DealTier.PASS: (0, 19),
    }

    # Tier display settings
    TIER_LABELS = {
        DealTier.SNIPE: "SNIPE",
        DealTier.ELITE: "Elite Deal",
        DealTier.GOOD: "Good Deal",
        DealTier.FAIR: "Fair Deal",
        DealTier.PASS: "Below Threshold",
    }

    TIER_COLORS = {
        DealTier.SNIPE: "#DC2626",  # Red
        DealTier.ELITE: "#EA580C",  # Orange
        DealTier.GOOD: "#CA8A04",   # Yellow
        DealTier.FAIR: "#16A34A",   # Green
        DealTier.PASS: "#6B7280",   # Gray
    }

    # Time decay parameters (hours)
    TIME_DECAY_HALF_LIFE = 4  # Score halves every 4 hours
    MAX_FRESHNESS_HOURS = 0.5  # Full score for listings under 30 min

    # Confidence thresholds
    MIN_CONFIDENCE = 0.50  # Below this, confidence percentile = 0
    HIGH_CONFIDENCE = 0.90  # Above this, confidence percentile = 1

    def __init__(
        self,
        recent_discounts: Optional[List[float]] = None,
        default_liquidity: float = 0.5,
    ):
        """
        Initialize scorer with historical context.

        Args:
            recent_discounts: List of recent deal discount percentages
                              for percentile calculation. If None, uses
                              static thresholds.
            default_liquidity: Default liquidity score when not available.
        """
        self.recent_discounts = recent_discounts or []
        self.default_liquidity = default_liquidity

        # Precompute percentile thresholds if we have historical data
        if self.recent_discounts and len(self.recent_discounts) >= 10:
            sorted_discounts = sorted(self.recent_discounts)
            self._p25 = sorted_discounts[len(sorted_discounts) // 4]
            self._p50 = statistics.median(sorted_discounts)
            self._p75 = sorted_discounts[3 * len(sorted_discounts) // 4]
            self._p90 = sorted_discounts[9 * len(sorted_discounts) // 10]
        else:
            # Default thresholds based on deal detection (20% deal, 40% snipe)
            self._p25 = 20.0
            self._p50 = 25.0
            self._p75 = 35.0
            self._p90 = 45.0

    def compute_discount_percentile(self, discount_percent: float) -> float:
        """
        Compute percentile ranking for a discount.

        Returns value between 0-1 indicating how this discount
        compares to recent deals.
        """
        if discount_percent < self._p25:
            # Below 25th percentile - linear scale 0 to 0.25
            return max(0, (discount_percent / self._p25) * 0.25)
        elif discount_percent < self._p50:
            # 25th to 50th percentile
            return 0.25 + ((discount_percent - self._p25) / (self._p50 - self._p25)) * 0.25
        elif discount_percent < self._p75:
            # 50th to 75th percentile
            return 0.50 + ((discount_percent - self._p50) / (self._p75 - self._p50)) * 0.25
        elif discount_percent < self._p90:
            # 75th to 90th percentile
            return 0.75 + ((discount_percent - self._p75) / (self._p90 - self._p75)) * 0.15
        else:
            # Above 90th percentile - caps at 1.0
            return min(1.0, 0.90 + ((discount_percent - self._p90) / 20) * 0.10)

    def compute_confidence_percentile(self, confidence: float) -> float:
        """
        Compute percentile for model confidence.

        Higher confidence = more reliable valuation = better deal signal.
        """
        if confidence < self.MIN_CONFIDENCE:
            return 0.0
        elif confidence >= self.HIGH_CONFIDENCE:
            return 1.0
        else:
            # Linear scale between min and high confidence
            return (confidence - self.MIN_CONFIDENCE) / (self.HIGH_CONFIDENCE - self.MIN_CONFIDENCE)

    def compute_time_score(self, hours_since_listing: float) -> float:
        """
        Compute time freshness score with exponential decay.

        Fresh listings get higher scores - deals disappear fast.
        """
        if hours_since_listing <= self.MAX_FRESHNESS_HOURS:
            return 1.0

        # Exponential decay
        decay_factor = 0.5 ** (hours_since_listing / self.TIME_DECAY_HALF_LIFE)
        return max(0.0, decay_factor)

    def get_tier(self, score: int) -> DealTier:
        """Get tier for a score."""
        for tier, (low, high) in self.TIER_THRESHOLDS.items():
            if low <= score <= high:
                return tier
        return DealTier.PASS

    def compute_legacy_score(self, discount_percent: float, part_boost: bool = False) -> int:
        """
        Compute backward-compatible legacy score.

        This matches the original deal_detector.py logic:
        deal_score = min(100, int(discount_percent * 1.5))
        + 10 if part_boost
        """
        score = min(100, int(discount_percent * 1.5))
        if part_boost:
            score = min(100, score + 10)
        return score

    def score(
        self,
        discount_percent: float,
        confidence_score: float = 0.80,
        liquidity_score: Optional[float] = None,
        time_since_listing_hours: float = 0.0,
        has_rare_part_discount: bool = False,
    ) -> NormalizedDealScore:
        """
        Compute normalized deal score.

        Args:
            discount_percent: How far below fair value (e.g., 25 for 25% off)
            confidence_score: Model confidence in valuation (0-1)
            liquidity_score: How quickly similar Axies sell (0-1), None for default
            time_since_listing_hours: Hours since listing was posted
            has_rare_part_discount: Whether a rare part has >30% discount (for legacy boost)

        Returns:
            NormalizedDealScore with all scoring components and tier
        """
        # Compute percentile components
        discount_pctl = self.compute_discount_percentile(discount_percent)
        confidence_pctl = self.compute_confidence_percentile(confidence_score)
        time_score = self.compute_time_score(time_since_listing_hours)
        liq_score = liquidity_score if liquidity_score is not None else self.default_liquidity

        # Weighted combination
        raw_score = (
            discount_pctl * self.WEIGHT_DISCOUNT +
            confidence_pctl * self.WEIGHT_CONFIDENCE +
            liq_score * self.WEIGHT_LIQUIDITY +
            time_score * self.WEIGHT_TIME
        )

        # Scale to 0-100
        normalized_score = int(round(raw_score * 100))
        normalized_score = max(0, min(100, normalized_score))

        # Get tier
        tier = self.get_tier(normalized_score)

        # Compute legacy score for backward compatibility
        legacy_score = self.compute_legacy_score(discount_percent, has_rare_part_discount)

        return NormalizedDealScore(
            discount_percent=discount_percent,
            confidence_score=confidence_score,
            time_since_listing_hours=time_since_listing_hours,
            discount_percentile=discount_pctl,
            confidence_percentile=confidence_pctl,
            liquidity_score=liq_score,
            time_score=time_score,
            normalized_score=normalized_score,
            legacy_score=legacy_score,
            tier=tier,
            tier_label=self.TIER_LABELS[tier],
            tier_color=self.TIER_COLORS[tier],
        )

    def score_deal(self, deal: dict) -> NormalizedDealScore:
        """
        Score a deal dict from deal_detector.

        Expects deal dict with:
        - discount_percent
        - confidence_score (optional, from valuation)
        - detected_at (ISO timestamp)
        - part_analysis (for rare part boost)
        """
        discount = deal.get("discount_percent", 0)
        confidence = deal.get("confidence_score", 0.80)

        # Calculate time since detection
        detected_at = deal.get("detected_at")
        hours_since = 0.0
        if detected_at:
            try:
                detected_dt = datetime.fromisoformat(detected_at.replace("Z", "+00:00"))
                hours_since = (datetime.now(timezone.utc) - detected_dt).total_seconds() / 3600
            except (ValueError, AttributeError):
                pass

        # Check for rare part discount
        part_analysis = deal.get("part_analysis", [])
        has_rare_part = False
        if part_analysis:
            best_part_discount = max(
                (p.get("discount_percent", 0) for p in part_analysis),
                default=0
            )
            has_rare_part = best_part_discount > 30

        return self.score(
            discount_percent=discount,
            confidence_score=confidence,
            time_since_listing_hours=hours_since,
            has_rare_part_discount=has_rare_part,
        )


def create_scorer_from_recent_deals(deals: List[dict]) -> NormalizedDealScorer:
    """
    Factory function to create a scorer from recent deal history.

    Args:
        deals: List of recent deal dicts with discount_percent

    Returns:
        Configured NormalizedDealScorer with historical percentiles
    """
    discounts = [
        d.get("discount_percent", 0)
        for d in deals
        if d.get("discount_percent", 0) > 0
    ]
    return NormalizedDealScorer(recent_discounts=discounts)
