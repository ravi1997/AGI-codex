"""Feedback collection utilities."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Sequence

from ..config import LearningConfig
from ..reasoning.planner import Plan
from ..tools.base import ToolResult

LOGGER = logging.getLogger(__name__)


@dataclass
class FeedbackMetrics:
    """Aggregate metrics derived from recorded runs."""

    total_runs: int = 0
    successes: int = 0
    failures: int = 0
    success_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeedbackMetrics":
        metrics = cls()
        metrics.total_runs = int(data.get("total_runs", 0))
        metrics.successes = int(data.get("successes", 0))
        metrics.failures = int(data.get("failures", 0))
        metrics.success_rate = float(data.get("success_rate", 0.0))
        return metrics


class FeedbackCollector:
    """Persists execution outcomes and computes rolling metrics."""

    def __init__(self, config: LearningConfig) -> None:
        self._path = config.feedback_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_history = config.max_feedback_history
        self._history: List[Dict[str, Any]] = []
        self._metrics = FeedbackMetrics()
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            LOGGER.debug("No existing feedback file at %s", self._path)
            return

        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            LOGGER.warning("Failed to load feedback history (%s); starting fresh", exc)
            return

        self._history = list(payload.get("history", []))[-self._max_history :]
        self._metrics = FeedbackMetrics.from_dict(payload.get("metrics", {}))
        LOGGER.info("Loaded %d feedback entries", len(self._history))

    def _persist(self) -> None:
        payload = {
            "history": self._history[-self._max_history :],
            "metrics": self._metrics.to_dict(),
        }
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        LOGGER.debug("Persisted feedback history (%d entries)", len(self._history))

    @property
    def metrics(self) -> FeedbackMetrics:
        return self._metrics

    @property
    def history(self) -> Sequence[Dict[str, Any]]:
        return tuple(self._history[-self._max_history :])

    def record_run(
        self,
        *,
        task_id: str,
        goal: str,
        success: bool,
        plan: Plan,
        results: Sequence[ToolResult],
        telemetry: Dict[str, float],
    ) -> Dict[str, Any]:
        """Record the outcome of a completed run."""

        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "goal": goal,
            "success": success,
            "context_summary": plan.context_summary,
            "telemetry": telemetry,
            "steps": [
                {
                    "name": step.name,
                    "tool": step.tool,
                    "description": step.description,
                    "args": list(step.args),
                    "kwargs": dict(step.kwargs),
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
                for step, result in zip(plan.steps, results)
            ],
        }

        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        self._metrics.total_runs += 1
        if success:
            self._metrics.successes += 1
        else:
            self._metrics.failures += 1

        if self._metrics.total_runs:
            self._metrics.success_rate = self._metrics.successes / self._metrics.total_runs

        self._persist()
        LOGGER.debug(
            "Recorded run for task %s (success=%s). Success rate now %.2f%%",
            task_id,
            success,
            self._metrics.success_rate * 100,
        )
        return entry

    def recent_failures(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent failed runs."""

        failures = [entry for entry in reversed(self._history) if not entry.get("success", False)]
        return failures[:limit]
