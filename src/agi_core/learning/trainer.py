"""Fine-tuning pipeline orchestration."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..config import LearningConfig
from .dataset import (
    DPOExample,
    LoRAExample,
    format_dpo_examples,
    format_lora_examples,
    load_jsonl_records,
)

LOGGER = logging.getLogger(__name__)


@dataclass
class TrainingResult:
    """Metadata emitted after a training job concludes."""

    output_dir: Path
    dataset_size: int
    strategy: str
    dry_run: bool
    metadata: Dict[str, object]


class FineTuningPipeline:
    """Loads datasets and executes LoRA/DPO fine-tuning jobs."""

    def __init__(self, config: LearningConfig) -> None:
        self._config = config

    def run(
        self,
        *,
        strategy: Optional[str] = None,
        dataset_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        dry_run: bool = False,
    ) -> TrainingResult:
        """Execute the configured fine-tuning strategy."""

        strategy = (strategy or self._config.training_strategy).lower()
        dataset_path = dataset_path or self._config.dataset_path
        LOGGER.info("Preparing %s training from %s", strategy.upper(), dataset_path)

        records = load_jsonl_records(dataset_path)
        if not records:
            raise ValueError(f"No data found at {dataset_path}")

        if strategy == "lora":
            examples = format_lora_examples(records)
            dataset_size = len(examples)
            metadata = self._run_lora(examples, output_dir=output_dir, dry_run=dry_run)
        elif strategy == "dpo":
            examples = format_dpo_examples(records)
            if not examples:
                raise ValueError("Insufficient success/failure pairs to run DPO training")
            dataset_size = len(examples)
            metadata = self._run_dpo(examples, output_dir=output_dir, dry_run=dry_run)
        else:
            raise ValueError(f"Unsupported training strategy: {strategy}")

        metadata.update(
            {
                "strategy": strategy,
                "dataset_path": str(dataset_path),
                "dataset_size": dataset_size,
                "dry_run": dry_run,
            }
        )
        self._write_metadata(metadata)
        self._update_overrides(metadata)
        LOGGER.info("Completed %s training run (dry_run=%s)", strategy, dry_run)
        return TrainingResult(
            output_dir=Path(metadata["output_dir"]),
            dataset_size=dataset_size,
            strategy=strategy,
            dry_run=dry_run,
            metadata=metadata,
        )

    def _prepare_output_dir(self, output_dir: Optional[Path]) -> Path:
        base_dir = output_dir or self._config.training_output_dir
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        destination = base_dir / timestamp if base_dir == self._config.training_output_dir else base_dir
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "adapter").mkdir(exist_ok=True)
        (destination / "tokenizer").mkdir(exist_ok=True)
        return destination

    def _run_lora(
        self, examples: List[LoRAExample], *, output_dir: Optional[Path], dry_run: bool
    ) -> Dict[str, object]:
        destination = self._prepare_output_dir(output_dir)
        if dry_run:
            LOGGER.info("Dry-run: skipping Hugging Face PEFT training")
        else:
            self._execute_lora_training(examples, destination)
        return {
            "output_dir": str(destination),
            "adapter_path": str(destination / "adapter"),
            "tokenizer_path": str(destination / "tokenizer"),
        }

    def _run_dpo(
        self, examples: List[DPOExample], *, output_dir: Optional[Path], dry_run: bool
    ) -> Dict[str, object]:
        destination = self._prepare_output_dir(output_dir)
        if dry_run:
            LOGGER.info("Dry-run: skipping TRL DPO training")
        else:
            self._execute_dpo_training(examples, destination)
        return {
            "output_dir": str(destination),
            "adapter_path": str(destination / "adapter"),
            "tokenizer_path": str(destination / "tokenizer"),
        }

    def _execute_lora_training(self, examples: List[LoRAExample], destination: Path) -> None:
        from datasets import Dataset
        from peft import LoraConfig, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )

        def to_text(example: LoRAExample) -> str:
            return f"{example.input}\n\nResponse:\n{example.output}".strip()

        dataset = Dataset.from_list([{"text": to_text(example)} for example in examples])

        tokenizer = AutoTokenizer.from_pretrained(self._config.training_base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        tokenized = dataset.map(
            lambda sample: tokenizer(sample["text"]),
            batched=True,
            remove_columns=["text"],
        )

        model = AutoModelForCausalLM.from_pretrained(self._config.training_base_model)
        lora_config = LoraConfig(r=self._config.lora_rank)
        model = get_peft_model(model, lora_config)

        args = TrainingArguments(
            output_dir=str(destination),
            overwrite_output_dir=True,
            num_train_epochs=self._config.training_epochs,
            max_steps=self._config.max_train_steps,
            learning_rate=self._config.learning_rate,
            per_device_train_batch_size=1,
            logging_steps=10,
            save_strategy="no",
        )

        data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
        trainer = Trainer(
            model=model,
            args=args,
            train_dataset=tokenized,
            tokenizer=tokenizer,
            data_collator=data_collator,
        )
        trainer.train()
        model.save_pretrained(destination / "adapter")
        tokenizer.save_pretrained(destination / "tokenizer")

    def _execute_dpo_training(self, examples: List[DPOExample], destination: Path) -> None:
        from datasets import Dataset
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
        from trl import DPOTrainer

        dataset = Dataset.from_list(
            [
                {
                    "prompt": example.prompt,
                    "chosen": example.chosen,
                    "rejected": example.rejected,
                }
                for example in examples
            ]
        )

        tokenizer = AutoTokenizer.from_pretrained(self._config.training_base_model)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(self._config.training_base_model)
        reference_model = AutoModelForCausalLM.from_pretrained(
            self._config.training_base_model
        )

        args = TrainingArguments(
            output_dir=str(destination),
            overwrite_output_dir=True,
            max_steps=self._config.max_train_steps,
            learning_rate=self._config.learning_rate,
            per_device_train_batch_size=1,
            logging_steps=10,
            save_strategy="no",
        )

        trainer = DPOTrainer(
            model=model,
            ref_model=reference_model,
            args=args,
            beta=self._config.dpo_beta,
            train_dataset=dataset,
            tokenizer=tokenizer,
        )
        trainer.train()
        model.save_pretrained(destination / "adapter")
        tokenizer.save_pretrained(destination / "tokenizer")

    def _write_metadata(self, metadata: Dict[str, object]) -> None:
        metadata_path = Path(metadata["output_dir"]) / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        latest_path = self._config.training_metadata_path
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    def _update_overrides(self, metadata: Dict[str, object]) -> None:
        overrides_path = self._config.training_overrides_path
        overrides_path = overrides_path if overrides_path.is_absolute() else Path(overrides_path)
        overrides_path.parent.mkdir(parents=True, exist_ok=True)

        overrides: Dict[str, object] = {}
        if overrides_path.exists():
            overrides = yaml.safe_load(overrides_path.read_text(encoding="utf-8")) or {}

        overrides.setdefault("learning", {})
        overrides["learning"].update(
            {
                "active_adapter_path": metadata.get("adapter_path"),
            }
        )

        overrides_path.write_text(
            yaml.safe_dump(overrides, sort_keys=False),
            encoding="utf-8",
        )
