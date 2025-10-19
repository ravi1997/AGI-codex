"""Configuration utilities for the AGI system."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import yaml
from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """Settings for memory backends."""

    vector_backend: str = Field(
        "chromadb", description="Vector store backend identifier (e.g., chromadb, pgvector)."
    )
    episodic_db_path: Path = Field(
        Path("storage/episodic/memory.json"), description="Location for episodic memory persistence."
    )
    semantic_db_path: Path = Field(
        Path("storage/semantic/knowledge.json"), description="Location for semantic memory database file."
    )
    procedural_repo_path: Path = Field(
        Path("storage/procedural"), description="Directory containing procedural artifacts."
    )


class ToolConfig(BaseModel):
    """Configuration for tool execution."""

    sandbox_root: Path = Field(
        Path("sandbox"), description="Directory where sandboxed operations are allowed."
    )
    allow_network: bool = Field(
        False, description="Whether network-enabled tools are permitted by default."
    )


class SchedulerConfig(BaseModel):
    """Task scheduling configuration."""

    max_concurrent_tasks: int = Field(1, ge=1)
    autonomous_task_interval_sec: int = Field(
        900, description="Interval for proposing autonomous tasks."
    )
    idle_sleep_seconds: float = Field(
        1.0,
        ge=0.1,
        description="Delay applied when the scheduler is idle to avoid busy-waiting.",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field("INFO", description="Root logging level.")
    log_dir: Path = Field(Path("logs"), description="Directory for log files.")


class LearningConfig(BaseModel):
    """Settings controlling feedback capture and self-optimization."""

    feedback_path: Path = Field(
        Path("storage/analytics/feedback.json"),
        description="Path where feedback metrics are stored.",
    )
    max_feedback_history: int = Field(200, ge=1)
    dataset_path: Path = Field(
        Path("storage/learning/dataset.jsonl"),
        description="JSONL dataset destination for fine-tuning records.",
    )
    dataset_flush_batch: int = Field(5, ge=1)
    min_samples_for_optimization: int = Field(10, ge=1)
    min_samples_for_training: int = Field(
        50,
        ge=1,
        description="Number of collected experiences required before fine-tuning is triggered.",
    )
    success_rate_floor: float = Field(0.6, ge=0.0, le=1.0)
    success_rate_ceiling: float = Field(0.9, ge=0.0, le=1.0)
    optimizer_cooldown: int = Field(5, ge=0)
    min_autonomous_interval_sec: int = Field(300, ge=1)
    max_autonomous_interval_sec: int = Field(3600, ge=1)
    telemetry_cpu_threshold: float = Field(85.0, ge=0.0)
    telemetry_memory_threshold_mb: float = Field(1024.0, ge=0.0)
    training_strategy: Literal["lora", "dpo"] = Field(
        "lora", description="Fine-tuning approach to execute when training is triggered."
    )
    training_base_model: str = Field(
        "gpt2",
        description="Base model identifier used as the starting point for fine-tuning.",
    )
    training_output_dir: Path = Field(
        Path("storage/learning/models"),
        description="Root directory where fine-tuned adapters are stored.",
    )
    training_metadata_path: Path = Field(
        Path("storage/learning/models/latest.json"),
        description="Location for the latest fine-tuning metadata blob.",
    )
    training_overrides_path: Path = Field(
        Path("config/overrides.yaml"),
        description="Configuration overrides file updated after successful training runs.",
    )
    training_epochs: int = Field(
        1,
        ge=1,
        description="Number of epochs to run during fine-tuning when using PEFT adapters.",
    )
    max_train_steps: int = Field(
        1000,
        ge=1,
        description="Maximum number of optimizer steps to perform during fine-tuning.",
    )
    learning_rate: float = Field(
        5e-5,
        gt=0.0,
        description="Learning rate supplied to the Hugging Face trainer components.",
    )
    lora_rank: int = Field(
        8,
        ge=1,
        description="Rank parameter for PEFT LoRA adapters.",
    )
    dpo_beta: float = Field(
        0.1,
        gt=0.0,
        description="Beta parameter forwarded to the TRL DPO trainer when applicable.",
    )
    active_adapter_path: Optional[Path] = Field(
        None,
        description="Path to the most recently produced adapter artifact ready for loading.",
    )


class AgentConfig(BaseModel):
    """Top-level configuration object."""

    memory: MemoryConfig = MemoryConfig()
    tools: ToolConfig = ToolConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    logging: LoggingConfig = LoggingConfig()
    learning: LearningConfig = LearningConfig()

    class Config:
        arbitrary_types_allowed = True


def load_config(path: Optional[os.PathLike[str]] = None) -> AgentConfig:
    """Load configuration from a YAML file.

    Args:
        path: Optional path to a configuration file. If not provided, the default
            configuration bundled with the project is used.

    Returns:
        AgentConfig: Parsed configuration model.
    """

    project_root = Path(__file__).resolve().parents[2]
    default_path = project_root / "config" / "default.yaml"
    config_path = Path(path) if path else default_path

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = yaml.safe_load(handle) or {}

    overrides_path = project_root / "config" / "overrides.yaml"
    if overrides_path.exists():
        with overrides_path.open("r", encoding="utf-8") as handle:
            overrides: Dict[str, Any] = yaml.safe_load(handle) or {}
        data = _deep_update(data, overrides)

    return AgentConfig(**data)


def _deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge update mapping into base mapping."""

    merged = dict(base)
    for key, value in updates.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_update(merged[key], value)
        else:
            merged[key] = value
    return merged
