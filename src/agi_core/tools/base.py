"""Tool interfaces and registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

LOGGER = logging.getLogger(__name__)


class ToolError(Exception):
    """Exception raised when a tool encounters an error."""
    pass


@dataclass
class ToolResult:
    """Result returned by a tool."""

    success: bool
    output: str
    error: Optional[str] = None


@dataclass
class ToolContext:
    """Execution context supplied to tools."""

    working_directory: str


class BaseTool:
    """Base class for executable tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def run(self, **kwargs) -> ToolResult:
        """Execute the tool with the given arguments."""
        try:
            result = self._run(**kwargs)
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _run(self, **kwargs):
        """Internal run method to be implemented by subclasses."""
        raise NotImplementedError


class ToolRegistry:
    """Registry for tool plugins."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        LOGGER.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def list_tools(self) -> Dict[str, BaseTool]:
        return dict(self._tools)
