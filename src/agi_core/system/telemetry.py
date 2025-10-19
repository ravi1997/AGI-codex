"""Telemetry utilities."""
from __future__ import annotations

import logging
import os
import psutil
from typing import Dict

LOGGER = logging.getLogger(__name__)


class TelemetryCollector:
    """Collects lightweight system metrics."""

    def snapshot(self) -> Dict[str, float]:
        process = psutil.Process(os.getpid())
        metrics = {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "open_files": len(process.open_files()),
        }
        LOGGER.debug("Telemetry snapshot: %s", metrics)
        return metrics
