"""Tool that exposes telemetry snapshots to plans."""
from __future__ import annotations

import json
import logging

from ..system.telemetry import TelemetryCollector
from .base import BaseTool, ToolContext, ToolResult, ToolError

LOGGER = logging.getLogger(__name__)


class SystemMonitorTool(BaseTool):
    """Expose telemetry metrics as a callable tool."""

    def __init__(self, telemetry: TelemetryCollector) -> None:
        super().__init__("system.monitor", "Return a JSON payload containing the latest telemetry snapshot.")
        self._telemetry = telemetry

    def _run(self, *args: str, **kwargs: str) -> str:
        LOGGER.debug("Collecting telemetry via tool")
        metrics = self._telemetry.snapshot()
        return json.dumps(metrics, indent=2)
