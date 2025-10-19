"""Verifier and reflection agent."""
from __future__ import annotations

import logging
from typing import List

from ..tools.base import ToolResult
from .planner import Plan

LOGGER = logging.getLogger(__name__)


class Verifier:
    """Performs lightweight verification of plan execution results."""

    def evaluate(self, plan: Plan, results: List[ToolResult]) -> bool:
        if not results:
            LOGGER.warning("No results to verify for plan: %s", plan.goal)
            return False

        for step, result in zip(plan.steps, results):
            if not result.success:
                LOGGER.warning("Step failed: %s | Error: %s", step.description, result.error)
                return False

        LOGGER.info("Plan '%s' completed successfully", plan.goal)
        return True
