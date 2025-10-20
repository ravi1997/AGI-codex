"""Self-optimization heuristics for the agent."""
from __future__ import annotations

import logging
from typing import Dict, Set

from pathlib import Path

from ..config import LearningConfig
from ..orchestration.task_scheduler import TaskScheduler
from .feedback import FeedbackCollector
from .jobs import TrainingJobRunner
from .scheduling import ScheduledTrainingTask, schedule_training_if_ready

LOGGER = logging.getLogger(__name__)


class SelfOptimizer:
    """Analyzes feedback and telemetry to tune runtime behaviour."""

    def __init__(self, config: LearningConfig) -> None:
        self._config = config
        self._cooldown_remaining = 0
        self._active_alerts: Set[str] = set()
        self._last_training_sample_count = 0
        self._training_runner = TrainingJobRunner(config)

    def maybe_optimize(
        self,
        scheduler: TaskScheduler,
        feedback: FeedbackCollector,
        telemetry: Dict[str, float],
    ) -> None:
        """Adjust scheduler cadence and enqueue diagnostic work if needed."""

        metrics = feedback.metrics
        if metrics.total_runs < self._config.min_samples_for_optimization:
            LOGGER.debug(
                "Skipping optimization - only %s runs recorded (need %s)",
                metrics.total_runs,
                self._config.min_samples_for_optimization,
            )
            return

        if self._cooldown_remaining > 0:
            LOGGER.debug("Optimizer on cooldown for %d iterations", self._cooldown_remaining)
            self._cooldown_remaining -= 1
        else:
            self._tune_scheduler(scheduler, metrics.success_rate)

        self._process_telemetry_alerts(scheduler, telemetry)
        self._maybe_enqueue_training(scheduler)

    def _tune_scheduler(self, scheduler: TaskScheduler, success_rate: float) -> None:
        current_interval = scheduler.autonomous_interval
        target_interval = current_interval

        if success_rate < self._config.success_rate_floor:
            target_interval = max(
                self._config.min_autonomous_interval_sec,
                int(current_interval * 0.5) or self._config.min_autonomous_interval_sec,
            )
        elif success_rate > self._config.success_rate_ceiling:
            target_interval = min(
                self._config.max_autonomous_interval_sec,
                int(current_interval * 1.5) or current_interval,
            )

        if target_interval != current_interval:
            scheduler.update_autonomous_interval(target_interval)
            self._cooldown_remaining = self._config.optimizer_cooldown
            LOGGER.info(
                "Adjusted autonomous task interval from %s to %s seconds based on success rate %.2f%%",
                current_interval,
                target_interval,
                success_rate * 100,
            )

    def _process_telemetry_alerts(self, scheduler: TaskScheduler, telemetry: Dict[str, float]) -> None:
        cpu = telemetry.get("cpu_percent", 0.0)
        memory = telemetry.get("memory_mb", 0.0)

        if cpu > self._config.telemetry_cpu_threshold:
            self._raise_alert(
                scheduler,
                reason="cpu",
                description="Investigate sustained high CPU usage",
                priority=3,
            )
        else:
            self._active_alerts.discard("cpu")

        if memory > self._config.telemetry_memory_threshold_mb:
            self._raise_alert(
                scheduler,
                reason="memory",
                description="Review memory footprint and purge caches if necessary",
                priority=3,
            )
        else:
            self._active_alerts.discard("memory")

    def _raise_alert(
        self,
        scheduler: TaskScheduler,
        *,
        reason: str,
        description: str,
        priority: int,
    ) -> None:
        if reason in self._active_alerts:
            return

        scheduler.add_task(
            description,
            priority=priority,
            metadata={"source": "optimizer", "reason": reason},
            autonomous=True,
        )
        self._active_alerts.add(reason)
        LOGGER.warning("Queued optimizer task for reason '%s'", reason)

    def _maybe_enqueue_training(self, scheduler: TaskScheduler) -> None:
        dataset_path: Path = self._config.dataset_path
        sample_count = self._training_runner.sample_count(dataset_path)
        threshold = self._config.min_samples_for_training
        if sample_count < threshold:
            self._last_training_sample_count = sample_count
            return

        if sample_count == self._last_training_sample_count:
            return

        decision: ScheduledTrainingTask = schedule_training_if_ready(
            scheduler,
            self._config,
            strategy=self._config.training_strategy,
            dataset_path=dataset_path,
            min_samples=threshold,
        )

        if decision.triggered:
            LOGGER.info(
                "Queued fine-tuning job request with %d samples using %s strategy",
                decision.sample_count,
                self._config.training_strategy,
            )
        else:
            LOGGER.debug(
                "Training not enqueued despite threshold met (samples=%d, threshold=%d)",
                decision.sample_count,
                decision.threshold,
            )

        self._last_training_sample_count = sample_count
