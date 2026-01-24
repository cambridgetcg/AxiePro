"""
Base flow interface for synthetic validation flows.

All synthetic flows inherit from SyntheticFlow and implement:
- execute(): Run the validation logic
- validate_results(): Check if results meet success criteria
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.instrumentation import (
    SyntheticFlowRun,
    FlowType,
    FlowStatus,
    Feature,
)

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a validation check."""

    def __init__(
        self,
        passed: bool,
        check_name: str,
        actual_value: Any,
        expected_value: Any,
        message: str = "",
    ):
        self.passed = passed
        self.check_name = check_name
        self.actual_value = actual_value
        self.expected_value = expected_value
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "check_name": self.check_name,
            "actual_value": self.actual_value,
            "expected_value": self.expected_value,
            "message": self.message,
        }


class FlowResult:
    """Result of a complete flow execution."""

    def __init__(self, flow_type: FlowType, feature: Feature):
        self.flow_type = flow_type
        self.feature = feature
        self.started_at = datetime.utcnow()
        self.validations: list[ValidationResult] = []
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def add_validation(self, result: ValidationResult) -> None:
        """Add a validation result."""
        self.validations.append(result)

    def set_error(self, error: str) -> None:
        """Set error message."""
        self.error = error

    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to results."""
        self.metadata[key] = value

    @property
    def checks_passed(self) -> int:
        """Number of checks that passed."""
        return sum(1 for v in self.validations if v.passed)

    @property
    def checks_total(self) -> int:
        """Total number of checks."""
        return len(self.validations)

    @property
    def validation_score(self) -> float:
        """Validation score (0-100)."""
        if self.checks_total == 0:
            return 0.0
        return (self.checks_passed / self.checks_total) * 100

    @property
    def status(self) -> FlowStatus:
        """Overall status."""
        if self.error:
            return FlowStatus.ERROR
        if self.checks_total == 0:
            return FlowStatus.ERROR
        if self.checks_passed == self.checks_total:
            return FlowStatus.PASSED
        return FlowStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "validations": [v.to_dict() for v in self.validations],
            "metadata": self.metadata,
            "error": self.error,
        }


class SyntheticFlow(ABC):
    """
    Base class for synthetic validation flows.

    Provides:
    - HTTP client for API calls
    - Database session management
    - Result tracking and storage
    - Common validation utilities

    Usage:
        class MyFlow(SyntheticFlow):
            async def execute(self) -> FlowResult:
                result = FlowResult(...)
                # Run validations
                result.add_validation(...)
                return result

        flow = MyFlow(api_base_url, db_session)
        await flow.run()
    """

    def __init__(
        self,
        api_base_url: str,
        db_session: AsyncSession,
        timeout: int = 30,
    ):
        """
        Initialize flow.

        Args:
            api_base_url: Base URL for AxiePro API
            db_session: Database session
            timeout: HTTP timeout in seconds
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.db_session = db_session
        self.timeout = timeout
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def flow_type(self) -> FlowType:
        """Flow type identifier."""
        pass

    @property
    @abstractmethod
    def feature(self) -> Feature:
        """Feature being validated."""
        pass

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.api_base_url,
                timeout=self.timeout,
            )
        return self._http_client

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    @abstractmethod
    async def execute(self) -> FlowResult:
        """
        Execute the flow validation logic.

        Returns:
            FlowResult with validation checks and results
        """
        pass

    async def run(self) -> SyntheticFlowRun:
        """
        Run the flow and store results.

        Returns:
            SyntheticFlowRun database record
        """
        # Create database record
        db_run = SyntheticFlowRun(
            flow_type=self.flow_type,
            feature=self.feature,
            status=FlowStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        self.db_session.add(db_run)
        await self.db_session.flush()

        try:
            # Execute flow
            logger.info(f"Starting {self.flow_type.value} flow")
            result = await self.execute()

            # Update database record
            db_run.status = result.status
            db_run.validation_score = result.validation_score
            db_run.checks_passed = result.checks_passed
            db_run.checks_total = result.checks_total
            db_run.results = result.to_dict()
            db_run.completed_at = datetime.utcnow()

            await self.db_session.commit()

            logger.info(
                f"Completed {self.flow_type.value} flow: "
                f"{result.checks_passed}/{result.checks_total} checks passed "
                f"(score: {result.validation_score:.1f}%)"
            )

            return db_run

        except Exception as e:
            logger.exception(f"Error in {self.flow_type.value} flow")
            db_run.status = FlowStatus.ERROR
            db_run.error_message = str(e)
            db_run.completed_at = datetime.utcnow()
            await self.db_session.commit()
            raise

        finally:
            await self.close()

    # Helper validation methods

    def validate_response_status(
        self,
        response: httpx.Response,
        expected_status: int = 200,
    ) -> ValidationResult:
        """Validate HTTP response status."""
        passed = response.status_code == expected_status
        return ValidationResult(
            passed=passed,
            check_name="http_status",
            actual_value=response.status_code,
            expected_value=expected_status,
            message=f"Expected {expected_status}, got {response.status_code}",
        )

    def validate_response_time(
        self,
        response: httpx.Response,
        max_ms: int = 1000,
    ) -> ValidationResult:
        """Validate API response time."""
        elapsed_ms = int(response.elapsed.total_seconds() * 1000)
        passed = elapsed_ms <= max_ms
        return ValidationResult(
            passed=passed,
            check_name="response_time",
            actual_value=elapsed_ms,
            expected_value=f"<= {max_ms}ms",
            message=f"Response took {elapsed_ms}ms",
        )

    def validate_data_count(
        self,
        actual_count: int,
        min_count: int,
        max_count: Optional[int] = None,
    ) -> ValidationResult:
        """Validate data count is within range."""
        if max_count:
            passed = min_count <= actual_count <= max_count
            expected = f"{min_count}-{max_count}"
        else:
            passed = actual_count >= min_count
            expected = f">= {min_count}"

        return ValidationResult(
            passed=passed,
            check_name="data_count",
            actual_value=actual_count,
            expected_value=expected,
            message=f"Found {actual_count} items",
        )

    def validate_threshold(
        self,
        actual_value: float,
        threshold: float,
        operator: str = ">=",
        check_name: str = "threshold",
    ) -> ValidationResult:
        """Validate value meets threshold."""
        if operator == ">=":
            passed = actual_value >= threshold
        elif operator == "<=":
            passed = actual_value <= threshold
        elif operator == ">":
            passed = actual_value > threshold
        elif operator == "<":
            passed = actual_value < threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")

        return ValidationResult(
            passed=passed,
            check_name=check_name,
            actual_value=actual_value,
            expected_value=f"{operator} {threshold}",
            message=f"Value {actual_value} vs threshold {threshold}",
        )
