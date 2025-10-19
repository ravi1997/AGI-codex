"""Command-line entry points for the learning pipeline."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import AgentConfig, load_config
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

    result = pipeline.run(
        strategy=parsed.strategy,
        dataset_path=parsed.dataset,
        output_dir=parsed.output_dir,
        dry_run=parsed.dry_run,
    )

    payload = {
        "output_dir": str(result.output_dir),
        "dataset_size": result.dataset_size,
        "strategy": result.strategy,
        "dry_run": result.dry_run,
    }
    print(json.dumps(payload, indent=2))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    run_training()


if __name__ == "__main__":
    main()
