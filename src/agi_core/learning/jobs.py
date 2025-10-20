"""Training job helpers for autonomous fine-tuning triggers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from ..config import AgentConfig, LearningConfig, load_config
from .dataset import count_non_empty_lines
from .trainer import FineTuningPipeline, TrainingResult


@dataclass(frozen=True)
class TrainingJobStatus:
    """Represents the outcome of a conditional training run."""

    triggered: bool
    sample_count: int
    threshold: int
    result: Optional[TrainingResult] = None


class TrainingJobRunner:
    """Coordinates threshold checks and fine-tuning execution."""

    def __init__(self, config: LearningConfig, pipeline: Optional[FineTuningPipeline] = None) -> None:
        self._config = config
        self._pipeline = pipeline or FineTuningPipeline(config)

    @property
    def config(self) -> LearningConfig:
        return self._config

    @classmethod
    def from_agent_config(
        cls, agent_config: Optional[AgentConfig] = None, *, config_path: Optional[Path] = None
    ) -> "TrainingJobRunner":
        """Instantiate a runner from an optional config bundle or file."""

        if agent_config is None:
            agent_config = load_config(config_path)
        return cls(agent_config.learning)

    def sample_count(self, dataset_path: Optional[Path] = None) -> int:
        """Return the number of collected training samples."""

        path = dataset_path or self._config.dataset_path
        return count_non_empty_lines(path)

    def readiness(
        self,
        *,
        dataset_path: Optional[Path] = None,
        min_samples: Optional[int] = None,
    ) -> Tuple[bool, int, int]:
        """Determine whether enough samples exist for training."""

        path = dataset_path or self._config.dataset_path
        threshold = min_samples or self._config.min_samples_for_training
        count = self.sample_count(path)
        return count >= threshold, count, threshold

    def run(
        self,
        *,
        strategy: Optional[str] = None,
        dataset_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dry_run: bool = False,
    ) -> TrainingResult:
        """Execute the fine-tuning pipeline regardless of sample count."""

        return self._pipeline.run(
            strategy=strategy,
            dataset_path=dataset_path,
            output_dir=output_dir,
            dry_run=dry_run,
        )

    def run_if_ready(
        self,
        *,
        strategy: Optional[str] = None,
        dataset_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dry_run: bool = False,
        min_samples: Optional[int] = None,
    ) -> TrainingJobStatus:
        """Execute training only when the dataset meets the sample threshold."""

        ready, count, threshold = self.readiness(
            dataset_path=dataset_path,
            min_samples=min_samples,
        )
        if not ready:
            return TrainingJobStatus(False, count, threshold, None)

        result = self.run(
            strategy=strategy,
            dataset_path=dataset_path,
            output_dir=output_dir,
            dry_run=dry_run,
        )
        return TrainingJobStatus(True, result.dataset_size, threshold, result)
