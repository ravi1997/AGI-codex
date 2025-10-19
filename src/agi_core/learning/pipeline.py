"""Utilities for preparing fine-tuning datasets."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Sequence

from ..config import LearningConfig
from ..reasoning.planner import Plan
from ..tools.base import ToolResult

LOGGER = logging.getLogger(__name__)


class LearningPipeline:
    """Collects experiences and writes JSONL datasets for fine-tuning."""

    def __init__(self, config: LearningConfig) -> None:
        self._path = config.dataset_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._batch_size = max(1, config.dataset_flush_batch)
        self._buffer: List[Dict[str, Any]] = []

    def add_example(
        self,
        *,
        task_id: str,
        goal: str,
        success: bool,
        plan: Plan,
        results: Sequence[ToolResult],
        summary: str,
    ) -> None:
        """Accumulate an experience record destined for the fine-tuning dataset."""

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "goal": goal,
            "success": success,
            "context_summary": plan.context_summary,
            "plan": [
                {
                    "name": step.name,
                    "tool": step.tool,
                    "description": step.description,
                    "args": list(step.args),
                    "kwargs": dict(step.kwargs),
                }
                for step in plan.steps
            ],
            "execution": [
                {
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
                for result in results
            ],
            "summary": summary,
        }
        self._buffer.append(record)
        LOGGER.debug("Buffered dataset example for task %s", task_id)

        if len(self._buffer) >= self._batch_size:
            self.flush()

    def flush(self) -> None:
        """Persist buffered records to disk."""

        if not self._buffer:
            return

        with self._path.open("a", encoding="utf-8") as handle:
            for record in self._buffer:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        LOGGER.info("Flushed %d learning examples to %s", len(self._buffer), self._path)
        self._buffer.clear()

    def pending_examples(self) -> int:
        return len(self._buffer)
