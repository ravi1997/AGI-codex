"""Main configuration file for the personalized AGI Codex system."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from .config import AgentConfig, load_config as base_load_config


class PersonalizationConfig(BaseModel):
    """Configuration for personalization features."""
    
    enabled: bool = Field(
        True,
        description="Enable all personalization features"
    )
    learning_enabled: bool = Field(
        True,
        description="Enable learning from user interactions"
    )
    adaptation_enabled: bool = Field(
        True,
        description="Enable adaptation to user preferences"
    )
    context_awareness_enabled: bool = Field(
        True,
        description="Enable context awareness for personalization"
    )
    feedback_collection_enabled: bool = Field(
        True,
        description="Enable feedback collection for learning"
    )
    autonomous_operations_enabled: bool = Field(
        True,
        description="Enable autonomous operations with safety checks"
    )
    safety_level: Literal["low", "medium", "high"] = Field(
        "medium",
        description="Safety level for autonomous operations"
    )
    personalization_depth: Literal["shallow", "moderate", "deep"] = Field(
        "moderate",
        description="How deeply to personalize the experience"
    )


class PersonalizedAgentConfig(AgentConfig):
    """Extended configuration with personalization features."""
    
    personalization: PersonalizationConfig = PersonalizationConfig()


def load_personalized_config(path: Optional[os.PathLike[str]] = None) -> PersonalizedAgentConfig:
    """Load personalized configuration from a YAML file.
    
    Args:
        path: Optional path to a configuration file. If not provided, the default
            personalized configuration is used.
    
    Returns:
        PersonalizedAgentConfig: Parsed personalized configuration model.
    """
    
    project_root = Path(__file__).resolve().parents[2]
    default_path = project_root / "config" / "personalized_learning.yaml"
    config_path = project_root / Path(path) if path else default_path
    
    if not config_path.exists():
        # Fall back to default config if personalized config doesn't exist
        default_config = base_load_config()
        return PersonalizedAgentConfig(
            memory=default_config.memory,
            tools=default_config.tools,
            scheduler=default_config.scheduler,
            logging=default_config.logging,
            learning=default_config.learning,
            personalization=PersonalizationConfig()
        )
    
    with config_path.open("r", encoding="utf-8") as handle:
        data: Dict[str, Any] = yaml.safe_load(handle) or {}
    
    overrides_path = project_root / "config" / "personalized_overrides.yaml"
    if overrides_path.exists():
        with overrides_path.open("r", encoding="utf-8") as handle:
            overrides: Dict[str, Any] = yaml.safe_load(handle) or {}
        data = _deep_update(data, overrides)
    
    return PersonalizedAgentConfig(**data)


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