"""
Meta Scout Synthetic Flow

Validates meta shift detection by:
1. Fetching current meta shifts from /meta/shifts
2. Verifying shifts represent real market changes
3. Checking detection timeliness
4. Validating shift quality scores
5. Monitoring API performance
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from src.models.instrumentation import FlowType, Feature
from .base import SyntheticFlow, FlowResult, ValidationResult

logger = logging.getLogger(__name__)


class MetaScoutFlow(SyntheticFlow):
    """
    Validates meta shift detection feature.

    Flow:
    1. Call /meta/shifts endpoint
    2. For each shift:
       - Verify price change magnitude is significant
       - Check detection happened within reasonable timeframe
       - Validate shift quality score
       - Verify all required fields present
    3. Check API performance
    4. Validate response format
    """

    @property
    def flow_type(self) -> FlowType:
        return FlowType.META_SCOUT

    @property
    def feature(self) -> Feature:
        return Feature.META

    async def execute(self) -> FlowResult:
        """Execute Meta Scout validation flow."""
        result = FlowResult(self.flow_type, self.feature)

        try:
            # Step 1: Call meta shifts API
            response = await self.http_client.get(
                "/meta/shifts",
                params={"lookback_hours": 24, "min_confidence": 0.7},
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
                self.validate_response_time(response, max_ms=1500)
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

            shifts = data["data"]

            # Validate shift count (may be 0 if no shifts detected)
            result.add_validation(
                ValidationResult(
                    passed=isinstance(shifts, list),
                    check_name="shifts_is_list",
                    actual_value=type(shifts).__name__,
                    expected_value="list",
                    message="Shifts data is a list",
                )
            )

            if len(shifts) == 0:
                # No shifts is valid - market may be stable
                result.add_metadata("warning", "No meta shifts detected in lookback period")
                result.add_metadata("shifts_count", 0)
                return result

            # Step 3: Validate individual shifts
            for i, shift in enumerate(shifts[:5]):  # Check first 5 shifts
                shift_validations = self._validate_shift(shift, i)
                for validation in shift_validations:
                    result.add_validation(validation)

            # Step 4: Aggregate metrics
            result.add_metadata("shifts_checked", min(5, len(shifts)))
            result.add_metadata("total_shifts", len(shifts))

            if len(shifts) > 0:
                avg_confidence = sum(
                    s.get("confidence", 0) for s in shifts
                ) / len(shifts)
                result.add_metadata("avg_confidence", round(avg_confidence, 3))

                # Check detection timing
                now = datetime.utcnow()
                detection_times = []
                for shift in shifts:
                    if "detected_at" in shift:
                        try:
                            detected = datetime.fromisoformat(
                                shift["detected_at"].replace("Z", "+00:00")
                            )
                            hours_ago = (now - detected).total_seconds() / 3600
                            detection_times.append(hours_ago)
                        except Exception:
                            pass

                if detection_times:
                    avg_detection_hours = sum(detection_times) / len(detection_times)
                    result.add_metadata(
                        "avg_detection_delay_hours",
                        round(avg_detection_hours, 2),
                    )

        except Exception as e:
            logger.exception("Error in Meta Scout flow")
            result.set_error(str(e))

        return result

    def _validate_response_structure(self, data: dict) -> ValidationResult:
        """Validate response has expected structure."""
        required_fields = ["data"]
        has_all_fields = all(field in data for field in required_fields)

        return ValidationResult(
            passed=has_all_fields,
            check_name="response_structure",
            actual_value=list(data.keys()),
            expected_value=required_fields,
            message="Response structure validation",
        )

    def _validate_shift(self, shift: dict, index: int) -> list[ValidationResult]:
        """Validate individual meta shift data."""
        validations = []

        # Required fields
        required_fields = [
            "trait_key",
            "class",
            "shift_type",
            "magnitude",
            "confidence",
        ]

        has_required = all(field in shift for field in required_fields)
        validations.append(
            ValidationResult(
                passed=has_required,
                check_name=f"shift_{index}_fields",
                actual_value=list(shift.keys()),
                expected_value=required_fields,
                message=f"Shift {index} has required fields",
            )
        )

        if not has_required:
            return validations

        # Validate magnitude is significant
        magnitude = abs(shift.get("magnitude", 0))
        magnitude_significant = magnitude >= 0.05  # At least 5% change
        validations.append(
            ValidationResult(
                passed=magnitude_significant,
                check_name=f"shift_{index}_magnitude",
                actual_value=round(magnitude, 3),
                expected_value=">= 0.05",
                message=f"Shift {index} magnitude is significant",
            )
        )

        # Validate confidence score
        confidence = shift.get("confidence", 0)
        confidence_valid = 0 <= confidence <= 1
        validations.append(
            ValidationResult(
                passed=confidence_valid,
                check_name=f"shift_{index}_confidence_range",
                actual_value=confidence,
                expected_value="0-1",
                message=f"Shift {index} confidence in range",
            )
        )

        # High confidence shifts should be reliable
        if confidence >= 0.7:
            high_confidence_valid = magnitude >= 0.10  # Expect larger magnitude
            validations.append(
                ValidationResult(
                    passed=high_confidence_valid,
                    check_name=f"shift_{index}_high_confidence",
                    actual_value=round(magnitude, 3),
                    expected_value=">= 0.10",
                    message=f"Shift {index} high confidence matches magnitude",
                )
            )

        # Validate shift type
        shift_type = shift.get("shift_type")
        valid_types = ["spike", "crash", "trend_up", "trend_down", "volatility"]
        type_valid = shift_type in valid_types
        validations.append(
            ValidationResult(
                passed=type_valid,
                check_name=f"shift_{index}_type",
                actual_value=shift_type,
                expected_value=valid_types,
                message=f"Shift {index} type is valid",
            )
        )

        # Validate detection timing (if present)
        if "detected_at" in shift:
            try:
                detected = datetime.fromisoformat(
                    shift["detected_at"].replace("Z", "+00:00")
                )
                now = datetime.utcnow()

                # Should be detected recently (within lookback period)
                hours_ago = (now - detected).total_seconds() / 3600
                timing_valid = 0 <= hours_ago <= 48  # Within 48 hours
                validations.append(
                    ValidationResult(
                        passed=timing_valid,
                        check_name=f"shift_{index}_timing",
                        actual_value=f"{round(hours_ago, 1)}h ago",
                        expected_value="0-48h ago",
                        message=f"Shift {index} detected recently",
                    )
                )
            except Exception:
                pass

        return validations
