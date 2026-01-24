"""
Flow Runner - Orchestrates synthetic flow execution.

Provides convenience methods for running single or multiple flows,
both sequentially and in parallel.
"""

import asyncio
import logging
from typing import Optional, List
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.instrumentation import SyntheticFlowRun, FlowType
from .base import SyntheticFlow
from .deal_hunter import DealHunterFlow
from .breeding_planner import BreedingPlannerFlow
from .meta_scout import MetaScoutFlow

logger = logging.getLogger(__name__)


class FlowRunner:
    """
    Orchestrates synthetic flow execution.

    Provides methods to run individual flows or all flows,
    with support for parallel execution.

    Usage:
        runner = FlowRunner(api_base_url, db_session)

        # Run single flow
        result = await runner.run_flow(FlowType.DEAL_HUNTER)

        # Run all flows in parallel
        results = await runner.run_all_flows()

        # Run specific flows
        results = await runner.run_flows([
            FlowType.DEAL_HUNTER,
            FlowType.META_SCOUT,
        ])
    """

    def __init__(
        self,
        api_base_url: str,
        db_session: AsyncSession,
        timeout: int = 30,
    ):
        """
        Initialize flow runner.

        Args:
            api_base_url: Base URL for AxiePro API
            db_session: Database session
            timeout: HTTP timeout in seconds
        """
        self.api_base_url = api_base_url
        self.db_session = db_session
        self.timeout = timeout

    def _create_flow(self, flow_type: FlowType) -> SyntheticFlow:
        """Create a flow instance by type."""
        if flow_type == FlowType.DEAL_HUNTER:
            return DealHunterFlow(
                self.api_base_url,
                self.db_session,
                self.timeout,
            )
        elif flow_type == FlowType.BREEDING_PLANNER:
            return BreedingPlannerFlow(
                self.api_base_url,
                self.db_session,
                self.timeout,
            )
        elif flow_type == FlowType.META_SCOUT:
            return MetaScoutFlow(
                self.api_base_url,
                self.db_session,
                self.timeout,
            )
        else:
            raise ValueError(f"Unknown flow type: {flow_type}")

    async def run_flow(self, flow_type: FlowType) -> SyntheticFlowRun:
        """
        Run a single flow.

        Args:
            flow_type: Type of flow to run

        Returns:
            SyntheticFlowRun database record with results
        """
        logger.info(f"Running flow: {flow_type.value}")

        flow = self._create_flow(flow_type)
        result = await flow.run()

        logger.info(
            f"Flow {flow_type.value} completed: "
            f"status={result.status.value}, "
            f"score={result.validation_score}"
        )

        return result

    async def run_flows(
        self,
        flow_types: List[FlowType],
        parallel: bool = True,
    ) -> List[SyntheticFlowRun]:
        """
        Run multiple flows.

        Args:
            flow_types: List of flow types to run
            parallel: If True, run flows in parallel (default)

        Returns:
            List of SyntheticFlowRun database records
        """
        logger.info(
            f"Running {len(flow_types)} flows "
            f"({'parallel' if parallel else 'sequential'})"
        )

        if parallel:
            # Run all flows concurrently
            tasks = [self.run_flow(ft) for ft in flow_types]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to failed runs
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Flow {flow_types[i].value} failed with exception: {result}"
                    )
                    # Exception handling - would need to create error record
                    # For now, skip
                    continue
                final_results.append(result)

            return final_results
        else:
            # Run flows sequentially
            results = []
            for flow_type in flow_types:
                try:
                    result = await self.run_flow(flow_type)
                    results.append(result)
                except Exception as e:
                    logger.exception(f"Flow {flow_type.value} failed")

            return results

    async def run_all_flows(self, parallel: bool = True) -> List[SyntheticFlowRun]:
        """
        Run all available flows.

        Args:
            parallel: If True, run flows in parallel (default)

        Returns:
            List of SyntheticFlowRun database records
        """
        all_flow_types = [
            FlowType.DEAL_HUNTER,
            FlowType.BREEDING_PLANNER,
            FlowType.META_SCOUT,
        ]

        return await self.run_flows(all_flow_types, parallel=parallel)

    async def get_recent_runs(
        self,
        flow_type: Optional[FlowType] = None,
        limit: int = 10,
    ) -> List[SyntheticFlowRun]:
        """
        Get recent flow runs from database.

        Args:
            flow_type: Optional filter by flow type
            limit: Maximum number of runs to return

        Returns:
            List of SyntheticFlowRun records
        """
        from sqlalchemy import select, desc

        query = select(SyntheticFlowRun)

        if flow_type:
            query = query.where(SyntheticFlowRun.flow_type == flow_type)

        query = query.order_by(desc(SyntheticFlowRun.started_at)).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_flow_health(self, flow_type: FlowType) -> dict:
        """
        Get health metrics for a flow.

        Args:
            flow_type: Flow type to check

        Returns:
            Dictionary with health metrics
        """
        recent_runs = await self.get_recent_runs(flow_type, limit=10)

        if not recent_runs:
            return {
                "flow_type": flow_type.value,
                "status": "no_data",
                "recent_runs": 0,
            }

        # Calculate metrics
        passed = sum(1 for r in recent_runs if r.status.value == "passed")
        failed = sum(1 for r in recent_runs if r.status.value == "failed")
        errors = sum(1 for r in recent_runs if r.status.value == "error")

        avg_score = sum(
            float(r.validation_score or 0) for r in recent_runs
        ) / len(recent_runs)

        success_rate = (passed / len(recent_runs)) * 100

        return {
            "flow_type": flow_type.value,
            "status": "healthy" if success_rate >= 80 else "degraded",
            "recent_runs": len(recent_runs),
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success_rate": round(success_rate, 1),
            "avg_validation_score": round(avg_score, 1),
        }

    async def get_overall_health(self) -> dict:
        """
        Get overall health across all flows.

        Returns:
            Dictionary with overall health metrics
        """
        all_flow_types = [
            FlowType.DEAL_HUNTER,
            FlowType.BREEDING_PLANNER,
            FlowType.META_SCOUT,
        ]

        flow_healths = []
        for flow_type in all_flow_types:
            health = await self.get_flow_health(flow_type)
            flow_healths.append(health)

        # Calculate overall metrics
        healthy_flows = sum(1 for h in flow_healths if h.get("status") == "healthy")
        degraded_flows = sum(
            1 for h in flow_healths if h.get("status") == "degraded"
        )

        overall_status = "healthy"
        if degraded_flows >= 2:
            overall_status = "degraded"
        elif degraded_flows >= 1:
            overall_status = "warning"

        return {
            "overall_status": overall_status,
            "healthy_flows": healthy_flows,
            "degraded_flows": degraded_flows,
            "total_flows": len(all_flow_types),
            "flows": flow_healths,
        }
