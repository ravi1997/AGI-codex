"""Execution agent."""
from __future__ import annotations

import logging
from typing import List

from ..tools.base import ToolContext, ToolRegistry, ToolResult
from .planner import Plan, PlanStep

LOGGER = logging.getLogger(__name__)


class Executor:
    """Executes plan steps using registered tools."""

    def __init__(self, tools: ToolRegistry, working_directory: str) -> None:
        self._tools = tools
        self._context = ToolContext(working_directory=working_directory)

    def execute(self, plan: Plan) -> List[ToolResult]:
        results: List[ToolResult] = []
        for step in plan.steps:
            result = self._execute_step(step)
            results.append(result)
        return results

    def _execute_step(self, step: PlanStep) -> ToolResult:
        if step.tool is None:
            LOGGER.info("Internal step '%s': %s", step.name, step.description)
            return ToolResult(success=True, output=step.description)

        try:
            tool = self._tools.get(step.tool)
        except KeyError as exc:
            LOGGER.error("Unknown tool: %s", step.tool)
            return ToolResult(success=False, output="", error=str(exc))

        LOGGER.info("Executing step '%s' with tool %s", step.name, step.tool)
        return tool.run(self._context, *step.args, **step.kwargs)
