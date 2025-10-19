"""Execution agent."""
from __future__ import annotations

import logging
from typing import List

from ..tools.base import ToolContext, ToolRegistry, ToolResult
from .planner import Plan

LOGGER = logging.getLogger(__name__)


class Executor:
    """Executes plan steps using registered tools."""

    def __init__(self, tools: ToolRegistry, working_directory: str) -> None:
        self._tools = tools
        self._context = ToolContext(working_directory=working_directory)

    def execute(self, plan: Plan) -> List[ToolResult]:
        results: List[ToolResult] = []
        for step in plan.steps:
            try:
                tool = self._tools.get(step.tool)
            except KeyError as exc:
                LOGGER.error("Unknown tool: %s", step.tool)
                results.append(ToolResult(success=False, output="", error=str(exc)))
                continue

            LOGGER.info("Executing step: %s", step.description)
            result = tool.run(self._context, *step.arguments)
            results.append(result)
        return results
