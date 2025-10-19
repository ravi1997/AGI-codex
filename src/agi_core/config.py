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


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field("INFO", description="Root logging level.")
    log_dir: Path = Field(Path("logs"), description="Directory for log files.")


class AgentConfig(BaseModel):
    """Top-level configuration object."""

    memory: MemoryConfig = MemoryConfig()
    tools: ToolConfig = ToolConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    logging: LoggingConfig = LoggingConfig()

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

    default_path = Path(__file__).resolve().parent.parent / "config" / "default.yaml"
    config_path = Path(path) if path else default_path

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = yaml.safe_load(handle) or {}

    return AgentConfig(**data)
