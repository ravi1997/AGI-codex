"""Command-line entry points for the learning pipeline."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import AgentConfig, load_config
from .jobs import TrainingJobRunner, TrainingJobStatus
from .trainer import FineTuningPipeline

LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run agent fine-tuning jobs")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Configuration file to load (defaults to config/default.yaml)",
    )
    parser.add_argument(
        "--strategy",
        choices=["lora", "dpo"],
        default=None,
        help="Override the configured fine-tuning strategy",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to a dataset JSONL file to use instead of the configured path",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where the adapter artifacts should be written",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip heavy training and only exercise the orchestration logic",
    )
    parser.add_argument(
        "--require-threshold",
        action="store_true",
        help=(
            "Only launch training when the dataset meets the configured sample threshold."
        ),
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=None,
        help="Override the minimum sample threshold used when --require-threshold is set",
    )
    return parser


def load_learning_config(config_path: Optional[Path]) -> AgentConfig:
    config = load_config(config_path)
    LOGGER.debug("Loaded configuration from %s", config_path or "default bundle")
    return config


def run_training(args: Optional[argparse.Namespace] = None) -> None:
    parser = build_parser()
    parsed = args or parser.parse_args()
    if not isinstance(parsed, argparse.Namespace):
        parsed = parser.parse_args(parsed)

    agent_config = load_learning_config(parsed.config)
    learning_config = agent_config.learning
    pipeline = FineTuningPipeline(learning_config)
    runner = TrainingJobRunner(learning_config, pipeline)

    dataset_path = parsed.dataset or learning_config.dataset_path
    strategy = parsed.strategy or learning_config.training_strategy
    threshold_override = parsed.min_samples

    if parsed.require_threshold:
        status = runner.run_if_ready(
            strategy=strategy,
            dataset_path=dataset_path,
            output_dir=parsed.output_dir,
            dry_run=parsed.dry_run,
            min_samples=threshold_override,
        )
    else:
        result = runner.run(
            strategy=strategy,
            dataset_path=dataset_path,
            output_dir=parsed.output_dir,
            dry_run=parsed.dry_run,
        )
        threshold = threshold_override or learning_config.min_samples_for_training
        status = TrainingJobStatus(True, result.dataset_size, threshold, result)

    payload = {
        "triggered": status.triggered,
        "dataset_size": status.sample_count,
        "threshold": status.threshold,
        "strategy": strategy,
        "dry_run": parsed.dry_run,
    }

    if status.triggered and status.result:
        payload.update(
            {
                "output_dir": str(status.result.output_dir),
            }
        )
    else:
        payload.update(
            {
                "output_dir": None,
                "message": (
                    "Not enough samples collected for training"
                    if status.sample_count < status.threshold
                    else "Training skipped"
                ),
            }
        )

    print(json.dumps(payload, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_training()


if __name__ == "__main__":
    main()
