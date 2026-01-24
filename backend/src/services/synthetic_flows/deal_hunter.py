"""
Deal Hunter Synthetic Flow

Validates deal detection accuracy by:
1. Fetching current deals from /valuation/deals/live
2. Verifying deals are actually undervalued vs market
3. Checking deal quality scores are accurate
4. Monitoring API performance
"""

import logging
from typing import Optional

from src.models.instrumentation import FlowType, Feature
from .base import SyntheticFlow, FlowResult, ValidationResult

logger = logging.getLogger(__name__)


class DealHunterFlow(SyntheticFlow):
    """
    Validates deal detection feature.

    Flow:
    1. Call /valuation/deals/live endpoint
    2. For each deal:
       - Verify actual_price < estimated_value
       - Check deal_score is reasonable (50-100)
       - Verify all required fields present
    3. Check API performance
    4. Validate response format
    """

    @property
    def flow_type(self) -> FlowType:
        return FlowType.DEAL_HUNTER

    @property
    def feature(self) -> Feature:
        return Feature.DEALS

    async def execute(self) -> FlowResult:
        """Execute Deal Hunter validation flow."""
        result = FlowResult(self.flow_type, self.feature)

        try:
            # Step 1: Call deals API
            response = await self.http_client.get(
                "/valuation/deals/live",
                params={"min_score": 60, "limit": 20},
            )

            # Validate response status
            result.add_validation(
                self.validate_response_status(response, expected_status=200)
            )

            if response.status_code != 200:
                result.set_error(f"API returned {response.status_code}")
                return result

            # Validate response time
            result.add_validation(
                self.validate_response_time(response, max_ms=2000)
            )

            # Parse response
            data = response.json()

            # Step 2: Validate response structure
            result.add_validation(
                self._validate_response_structure(data)
            )

            if "data" not in data:
                result.set_error("Missing 'data' field in response")
                return result

            deals = data["data"]

            # Validate deal count
            result.add_validation(
                self.validate_data_count(
                    actual_count=len(deals),
                    min_count=1,
                    max_count=20,
                )
            )

            if len(deals) == 0:
                result.add_metadata("warning", "No deals found")
                return result

            # Step 3: Validate individual deals
            for i, deal in enumerate(deals[:5]):  # Check first 5 deals
                deal_validations = self._validate_deal(deal, i)
                for validation in deal_validations:
                    result.add_validation(validation)

            # Step 4: Aggregate metrics
            result.add_metadata("deals_checked", min(5, len(deals)))
            result.add_metadata("total_deals", len(deals))

            if len(deals) > 0:
                avg_score = sum(d.get("deal_score", 0) for d in deals) / len(deals)
                result.add_metadata("avg_deal_score", round(avg_score, 2))

        except Exception as e:
            logger.exception("Error in Deal Hunter flow")
            result.set_error(str(e))

        return result

    def _validate_response_structure(self, data: dict) -> ValidationResult:
        """Validate response has expected structure."""
        required_fields = ["data", "meta"]
        has_all_fields = all(field in data for field in required_fields)

        return ValidationResult(
            passed=has_all_fields,
            check_name="response_structure",
            actual_value=list(data.keys()),
            expected_value=required_fields,
            message="Response structure validation",
        )

    def _validate_deal(self, deal: dict, index: int) -> list[ValidationResult]:
        """Validate individual deal data."""
        validations = []

        # Required fields
        required_fields = [
            "axie_id",
            "listing_price_eth",
            "estimated_value_eth",
            "deal_score",
            "deal_type",
        ]

        has_required = all(field in deal for field in required_fields)
        validations.append(
            ValidationResult(
                passed=has_required,
                check_name=f"deal_{index}_fields",
                actual_value=list(deal.keys()),
                expected_value=required_fields,
                message=f"Deal {index} has required fields",
            )
        )

        if not has_required:
            return validations

        # Validate price relationship
        listing_price = float(deal.get("listing_price_eth", 0))
        estimated_value = float(deal.get("estimated_value_eth", 0))

        is_undervalued = listing_price < estimated_value
        validations.append(
            ValidationResult(
                passed=is_undervalued,
                check_name=f"deal_{index}_undervalued",
                actual_value=listing_price,
                expected_value=f"< {estimated_value}",
                message=f"Deal {index} is undervalued",
            )
        )

        # Validate deal score range
        deal_score = deal.get("deal_score", 0)
        score_valid = 50 <= deal_score <= 100
        validations.append(
            ValidationResult(
                passed=score_valid,
                check_name=f"deal_{index}_score",
                actual_value=deal_score,
                expected_value="50-100",
                message=f"Deal {index} score in valid range",
            )
        )

        # Validate discount percentage
        if estimated_value > 0:
            discount = ((estimated_value - listing_price) / estimated_value) * 100
            discount_reasonable = 0 < discount < 80  # Sanity check
            validations.append(
                ValidationResult(
                    passed=discount_reasonable,
                    check_name=f"deal_{index}_discount",
                    actual_value=round(discount, 1),
                    expected_value="0-80%",
                    message=f"Deal {index} discount is reasonable",
                )
            )

        return validations
