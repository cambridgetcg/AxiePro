"""
Breeding Planner Synthetic Flow

Validates breeding simulation accuracy by:
1. Running breeding simulations with known parent pairs
2. Verifying cost calculations (SLP, AXS)
3. Checking class probability predictions
4. Validating expected purity calculations
5. Monitoring API performance
"""

import logging
from typing import Optional

from src.models.instrumentation import FlowType, Feature
from .base import SyntheticFlow, FlowResult, ValidationResult

logger = logging.getLogger(__name__)


# Test parent pairs (well-known Axies for consistent testing)
TEST_PAIRS = [
    (1, 2),      # Pure Beast pair
    (100, 101),  # Mixed class pair
    (500, 501),  # High breed count pair
]


class BreedingPlannerFlow(SyntheticFlow):
    """
    Validates breeding simulation feature.

    Flow:
    1. Call /breeding/simulate with test parent pairs
    2. For each simulation:
       - Verify cost calculation (SLP + AXS)
       - Check class probabilities sum to 1.0
       - Validate expected purity range (0-6)
       - Verify part probabilities structure
    3. Check API performance
    4. Validate response format
    """

    @property
    def flow_type(self) -> FlowType:
        return FlowType.BREEDING_PLANNER

    @property
    def feature(self) -> Feature:
        return Feature.BREEDING

    async def execute(self) -> FlowResult:
        """Execute Breeding Planner validation flow."""
        result = FlowResult(self.flow_type, self.feature)

        simulations_passed = 0

        try:
            # Test multiple parent pairs
            for i, (matron_id, sire_id) in enumerate(TEST_PAIRS):
                try:
                    sim_result = await self._test_simulation(matron_id, sire_id, i)
                    for validation in sim_result:
                        result.add_validation(validation)

                    # Count successful simulations
                    if all(v.passed for v in sim_result):
                        simulations_passed += 1

                except Exception as e:
                    logger.warning(
                        f"Simulation {i} failed for pair ({matron_id}, {sire_id}): {e}"
                    )
                    result.add_validation(
                        ValidationResult(
                            passed=False,
                            check_name=f"simulation_{i}_error",
                            actual_value=str(e),
                            expected_value="success",
                            message=f"Simulation {i} encountered error",
                        )
                    )

            # Overall success rate
            success_rate = (simulations_passed / len(TEST_PAIRS)) * 100
            result.add_metadata("simulations_passed", simulations_passed)
            result.add_metadata("simulations_total", len(TEST_PAIRS))
            result.add_metadata("success_rate", round(success_rate, 1))

        except Exception as e:
            logger.exception("Error in Breeding Planner flow")
            result.set_error(str(e))

        return result

    async def _test_simulation(
        self,
        matron_id: int,
        sire_id: int,
        index: int,
    ) -> list[ValidationResult]:
        """Test a single breeding simulation."""
        validations = []

        # Call breeding simulation API
        response = await self.http_client.post(
            "/breeding/simulate",
            json={"matron_id": matron_id, "sire_id": sire_id},
        )

        # Validate response status
        validations.append(
            self.validate_response_status(response, expected_status=200)
        )

        if response.status_code != 200:
            return validations

        # Validate response time
        validations.append(
            self.validate_response_time(response, max_ms=1500)
        )

        # Parse response
        data = response.json()

        # Validate response structure
        validations.append(
            self._validate_response_structure(data, index)
        )

        if "data" not in data:
            return validations

        sim_data = data["data"]

        # Validate breeding cost
        validations.extend(
            self._validate_breeding_cost(sim_data, index)
        )

        # Validate class probabilities
        validations.extend(
            self._validate_class_probabilities(sim_data, index)
        )

        # Validate expected purity
        validations.append(
            self._validate_expected_purity(sim_data, index)
        )

        # Validate part probabilities structure
        validations.append(
            self._validate_part_probabilities(sim_data, index)
        )

        return validations

    def _validate_response_structure(
        self,
        data: dict,
        index: int,
    ) -> ValidationResult:
        """Validate response has expected structure."""
        required_fields = ["data"]
        has_all_fields = all(field in data for field in required_fields)

        if has_all_fields and "data" in data:
            sim_fields = [
                "cost",
                "expected_purity",
                "class_probabilities",
                "part_probabilities",
            ]
            has_sim_fields = all(field in data["data"] for field in sim_fields)
        else:
            has_sim_fields = False

        return ValidationResult(
            passed=has_all_fields and has_sim_fields,
            check_name=f"simulation_{index}_structure",
            actual_value=list(data.get("data", {}).keys()) if "data" in data else [],
            expected_value=["cost", "expected_purity", "class_probabilities", "part_probabilities"],
            message=f"Simulation {index} response structure",
        )

    def _validate_breeding_cost(
        self,
        sim_data: dict,
        index: int,
    ) -> list[ValidationResult]:
        """Validate breeding cost calculation."""
        validations = []

        cost = sim_data.get("cost", {})

        # SLP cost should be present and reasonable
        slp = cost.get("slp", 0)
        slp_valid = 0 < slp < 10000  # Sanity check
        validations.append(
            ValidationResult(
                passed=slp_valid,
                check_name=f"simulation_{index}_slp_cost",
                actual_value=slp,
                expected_value="0-10000",
                message=f"Simulation {index} SLP cost is reasonable",
            )
        )

        # AXS cost should be present and reasonable
        axs = cost.get("axs", 0)
        axs_valid = 0 <= axs < 10  # Sanity check
        validations.append(
            ValidationResult(
                passed=axs_valid,
                check_name=f"simulation_{index}_axs_cost",
                actual_value=axs,
                expected_value="0-10",
                message=f"Simulation {index} AXS cost is reasonable",
            )
        )

        return validations

    def _validate_class_probabilities(
        self,
        sim_data: dict,
        index: int,
    ) -> list[ValidationResult]:
        """Validate class probabilities."""
        validations = []

        class_probs = sim_data.get("class_probabilities", {})

        # Should have probabilities
        has_probs = len(class_probs) > 0
        validations.append(
            ValidationResult(
                passed=has_probs,
                check_name=f"simulation_{index}_has_class_probs",
                actual_value=len(class_probs),
                expected_value="> 0",
                message=f"Simulation {index} has class probabilities",
            )
        )

        if has_probs:
            # Probabilities should sum to ~1.0
            total_prob = sum(class_probs.values())
            prob_sum_valid = 0.99 <= total_prob <= 1.01
            validations.append(
                ValidationResult(
                    passed=prob_sum_valid,
                    check_name=f"simulation_{index}_class_prob_sum",
                    actual_value=round(total_prob, 4),
                    expected_value="~1.0",
                    message=f"Simulation {index} class probabilities sum to 1",
                )
            )

            # All probabilities should be 0-1
            all_valid = all(0 <= p <= 1 for p in class_probs.values())
            validations.append(
                ValidationResult(
                    passed=all_valid,
                    check_name=f"simulation_{index}_class_prob_range",
                    actual_value=[round(p, 3) for p in class_probs.values()],
                    expected_value="0-1",
                    message=f"Simulation {index} class probabilities in range",
                )
            )

        return validations

    def _validate_expected_purity(
        self,
        sim_data: dict,
        index: int,
    ) -> ValidationResult:
        """Validate expected purity."""
        purity = sim_data.get("expected_purity", -1)
        purity_valid = 0 <= purity <= 6

        return ValidationResult(
            passed=purity_valid,
            check_name=f"simulation_{index}_purity",
            actual_value=purity,
            expected_value="0-6",
            message=f"Simulation {index} expected purity in range",
        )

    def _validate_part_probabilities(
        self,
        sim_data: dict,
        index: int,
    ) -> ValidationResult:
        """Validate part probabilities structure."""
        part_probs = sim_data.get("part_probabilities", {})
        expected_parts = ["eyes", "ears", "mouth", "horn", "back", "tail"]

        has_all_parts = all(part in part_probs for part in expected_parts)

        return ValidationResult(
            passed=has_all_parts,
            check_name=f"simulation_{index}_part_structure",
            actual_value=list(part_probs.keys()),
            expected_value=expected_parts,
            message=f"Simulation {index} has all part probabilities",
        )
