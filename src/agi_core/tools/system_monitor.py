"""Tool that exposes telemetry snapshots to plans."""
from __future__ import annotations

import json
import logging

from ..system.telemetry import TelemetryCollector
from .base import Tool, ToolContext, ToolResult

LOGGER = logging.getLogger(__name__)


class SystemMonitorTool(Tool):
    """Expose telemetry metrics as a callable tool."""

    name = "system.monitor"
    description = "Return a JSON payload containing the latest telemetry snapshot."

    def __init__(self, telemetry: TelemetryCollector) -> None:
        self._telemetry = telemetry

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:
        LOGGER.debug("Collecting telemetry via tool")
        metrics = self._telemetry.snapshot()
        payload = json.dumps(metrics, indent=2)
        return ToolResult(success=True, output=payload)
