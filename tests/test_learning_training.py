"""Dry-run coverage for the fine-tuning pipeline."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agi_core.config import LearningConfig  # type: ignore  # noqa: E402
from agi_core.learning.dataset import format_dpo_examples, format_lora_examples  # type: ignore  # noqa: E402
from agi_core.learning.jobs import TrainingJobRunner  # type: ignore  # noqa: E402


def _sample_record(task_id: str, *, success: bool, summary: str) -> dict:
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "task_id": task_id,
        "goal": "Draft an incident report",
        "success": success,
        "context_summary": "System observed unusual CPU usage and network spikes.",
        "plan": [
            {
                "name": "gather_metrics",
                "tool": "terminal",
                "description": "Collect monitoring data",
                "args": [],
                "kwargs": {},
            }
        ],
        "execution": [
            {
                "success": success,
                "output": "All metrics captured" if success else "command failed",
                "error": None if success else "timeout",
            }
        ],
        "summary": summary,
    }


class FineTuningPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dataset_path = Path(self.tmp.name) / "dataset.jsonl"
        records = [
            _sample_record("1", success=True, summary="Incident resolved."),
            _sample_record("2", success=False, summary="Further analysis required."),
        ]
        with self.dataset_path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

        self.output_dir = Path(self.tmp.name) / "models"
        self.overrides_path = Path(self.tmp.name) / "overrides.yaml"

        self.config = LearningConfig(
            dataset_path=self.dataset_path,
            dataset_flush_batch=1,
            min_samples_for_optimization=1,
            min_samples_for_training=1,
            training_output_dir=self.output_dir,
            training_metadata_path=self.output_dir / "latest.json",
            training_overrides_path=self.overrides_path,
            training_strategy="lora",
            training_base_model="gpt2",
        )
        self.runner = TrainingJobRunner(self.config)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_formatters_generate_examples(self) -> None:
        records = [json.loads(line) for line in self.dataset_path.read_text().splitlines()]
        lora_examples = format_lora_examples(records)
        dpo_examples = format_dpo_examples(records)

        self.assertEqual(len(lora_examples), 2)
        self.assertEqual(len(dpo_examples), 1)
        self.assertIn("Incident resolved", lora_examples[0].output)
        self.assertTrue(dpo_examples[0].chosen)

    def test_dry_run_pipeline_emits_metadata(self) -> None:
        status = self.runner.run_if_ready(dry_run=True, min_samples=1)

        self.assertTrue(status.triggered)
        self.assertIsNotNone(status.result)
        assert status.result is not None
        result = status.result

        self.assertTrue(result.dry_run)
        metadata_file = result.output_dir / "metadata.json"
        self.assertTrue(metadata_file.exists())

        latest_metadata = json.loads((self.output_dir / "latest.json").read_text())
        self.assertEqual(latest_metadata["dataset_size"], 2)
        overrides = yaml.safe_load(self.overrides_path.read_text())
        self.assertEqual(
            Path(overrides["learning"]["active_adapter_path"]).resolve(),
            (result.output_dir / "adapter").resolve(),
        )

    def test_training_runner_skips_when_threshold_not_met(self) -> None:
        status = self.runner.run_if_ready(dry_run=True, min_samples=5)

        self.assertFalse(status.triggered)
        self.assertIsNone(status.result)
        self.assertEqual(status.sample_count, 2)
        self.assertEqual(status.threshold, 5)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
