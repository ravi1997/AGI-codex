# Fine-tuning and Adapter Operations

This document outlines how operators can drive the learning pipeline once the
agent has accumulated a sufficient dataset of executions. The pipeline relies on
LoRA/PEFT adapters by default, but can also be configured for Direct Preference
Optimisation (DPO) experiments when success/failure pairs are available.

## Dataset preparation

* Execution summaries are appended to `storage/learning/dataset.jsonl` by the
  `LearningPipeline` during normal agent runs.
* Records contain:
  * `goal` – the original user/autonomous task description.
  * `context_summary` – planner context injected into the prompt.
  * `plan` – ordered tool steps with arguments.
  * `execution` – success/error payloads per step.
  * `summary` – verifier feedback that becomes the target response.
* The `agi_core.learning.dataset` module converts these records into
  instruction-tuning or DPO formats.

## Automatic scheduling

The `SelfOptimizer` monitors `dataset.jsonl` and, after
`min_samples_for_training` examples (50 by default), queues an autonomous task
asking operators to run:

```bash
agi-core-train --strategy=<lora|dpo> --dataset=storage/learning/dataset.jsonl
```

The scheduler metadata includes the suggested command, the current sample
count, and the target threshold so the task can be triggered via cron or by the
agent’s terminal tool. The helper lives in
`agi_core.learning.scheduling.schedule_training_if_ready`, so external
automation can reuse the same hook to enqueue training jobs without duplicating
the readiness logic. Operators who prefer unattended execution can call the CLI
with `--require-threshold`, which internally uses the `TrainingJobRunner`
helper to confirm the dataset is ready before invoking the LoRA/DPO trainers.

## Running the fine-tuning CLI

```bash
agi-core-train \
  --config config/default.yaml \
  --strategy lora \
  --dataset storage/learning/dataset.jsonl \
  --output-dir storage/learning/models/manual-run
```

Flags:

* `--dry-run` skips actual Hugging Face training and only exercises orchestration
  (ideal for quick validation or CI).
* `--require-threshold` consults the configured minimum sample count and exits
  early if the dataset is too small (combine with `--min-samples` to override the
  threshold for ad-hoc experiments).
* Omitting `--output-dir` creates a timestamped folder under
  `storage/learning/models/`.
* Results are summarised in `metadata.json` within the run directory and also in
  `storage/learning/models/latest.json`.

### Dependencies

Actual fine-tuning requires additional packages:

```bash
pip install transformers datasets peft trl accelerate bitsandbytes
```

Installers may vary based on GPU/CPU availability. The CLI defers imports until
training is requested, so dry-runs do not require these packages.

## Configuration updates

After each run the CLI writes/updates `config/overrides.yaml` with
`learning.active_adapter_path` pointing to the most recent adapter directory.
`load_config` automatically merges this file with the base configuration so the
agent can load the new adapter on restart.

## Monitoring runs

* Inspect the CLI JSON output or `metadata.json` for dataset size, strategy, and
  run location.
* Training logs are emitted to STDOUT and can be redirected to a file if needed.
* Adapter artifacts live under `storage/learning/models/<timestamp>/` (or the
  custom output directory provided).

## Dry-run unit test

`tests/test_learning_training.py` executes a miniature dataset through the
pipeline in dry-run mode. It verifies metadata generation and configuration
overrides, ensuring operators have a reliable smoke test before running
full-scale jobs.
