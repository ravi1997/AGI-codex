"""Scheduler hooks for autonomous training jobs."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import LearningConfig
from ..orchestration.task_scheduler import TaskScheduler
from .jobs import TrainingJobRunner


@dataclass(frozen=True)
class ScheduledTrainingTask:
    """Result of attempting to queue a training job."""

    triggered: bool
    sample_count: int
    threshold: int
    task_id: Optional[int] = None
    command: Optional[str] = None


def schedule_training_if_ready(
    scheduler: TaskScheduler,
    config: LearningConfig,
    *,
    strategy: Optional[str] = None,
    dataset_path: Optional[Path] = None,
    min_samples: Optional[int] = None,
    dry_run: bool = False,
    priority: int = 4,
) -> ScheduledTrainingTask:
    """Queue a fine-tuning task when the dataset meets the sample threshold."""

    runner = TrainingJobRunner(config)
    path = dataset_path or config.dataset_path
    min_required = min_samples or config.min_samples_for_training
    ready, sample_count, threshold = runner.readiness(
        dataset_path=path, min_samples=min_required
    )
    if not ready:
        return ScheduledTrainingTask(False, sample_count, threshold, None, None)

    chosen_strategy = (strategy or config.training_strategy).lower()
    command_parts = [
        "agi-core-train",
        f"--strategy={chosen_strategy}",
        f"--dataset={path}",
        "--require-threshold",
        f"--min-samples={threshold}",
    ]
    if dry_run:
        command_parts.append("--dry-run")

    command_str = " ".join(command_parts)

    task_id = scheduler.add_task(
        "Run fine-tuning pipeline on accumulated experience dataset",
        priority=priority,
        metadata={
            "source": "optimizer",
            "action": "fine_tune",
            "strategy": chosen_strategy,
            "command": command_str,
            "samples": str(sample_count),
            "threshold": str(threshold),
            "dry_run": str(dry_run).lower(),
        },
        autonomous=True,
    )

    return ScheduledTrainingTask(True, sample_count, threshold, task_id, command_str)
