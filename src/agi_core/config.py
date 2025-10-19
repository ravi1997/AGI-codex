"""Configuration utilities for the AGI system."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

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
    success_rate_floor: float = Field(0.6, ge=0.0, le=1.0)
    success_rate_ceiling: float = Field(0.9, ge=0.0, le=1.0)
    optimizer_cooldown: int = Field(5, ge=0)
    min_autonomous_interval_sec: int = Field(300, ge=1)
    max_autonomous_interval_sec: int = Field(3600, ge=1)
    telemetry_cpu_threshold: float = Field(85.0, ge=0.0)
    telemetry_memory_threshold_mb: float = Field(1024.0, ge=0.0)


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

    return AgentConfig(**data)
