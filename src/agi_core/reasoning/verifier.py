"""Verifier and reflection agent."""
from __future__ import annotations

import logging
from typing import List

from ..tools.base import ToolResult
from .planner import Plan, PlanStep

LOGGER = logging.getLogger(__name__)


class Verifier:
    """Performs lightweight verification of plan execution results."""

    def evaluate(self, plan: Plan, results: List[ToolResult]) -> bool:
        if not results:
            LOGGER.warning("No results to verify for plan: %s", plan.goal)
            return False

        success = True
        for step, result in zip(plan.steps, results):
            if not result.success:
                self._log_failure(step, result)
                success = False

        if success:
            LOGGER.info("Plan '%s' completed successfully", plan.goal)
        return success

    def _log_failure(self, step: PlanStep, result: ToolResult) -> None:
        LOGGER.warning(
            "Step '%s' failed | Description: %s | Error: %s",
            step.name,
            step.description,
            result.error or "<no error reported>",
        )
