"""Tool interfaces and registry."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

LOGGER = logging.getLogger(__name__)


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


class Tool:
    """Base class for executable tools."""

    name: str
    description: str

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:
        raise NotImplementedError


class ToolRegistry:
    """Registry for tool plugins."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        LOGGER.info("Registered tool: %s", tool.name)

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def list_tools(self) -> Dict[str, Tool]:
        return dict(self._tools)
