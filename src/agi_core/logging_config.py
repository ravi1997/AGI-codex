"""Logging utilities."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import AgentConfig


def configure_logging(config: AgentConfig) -> None:
    """Configure the logging subsystem based on configuration."""
    log_dir = config.logging.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "agi-core.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handlers = []

    rotating_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=5)
    rotating_handler.setFormatter(formatter)
    handlers.append(rotating_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)

    logging.basicConfig(level=config.logging.level, handlers=handlers)

    logging.getLogger(__name__).debug("Logging configured with path %s", log_path)
