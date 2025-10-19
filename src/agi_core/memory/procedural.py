"""Procedural memory for storing automation workflows."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

LOGGER = logging.getLogger(__name__)


class ProceduralMemory:
    """Manages procedural knowledge as JSON workflows."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)

    def _workflow_path(self, name: str) -> Path:
        return self._path / f"{name}.json"

    def list_workflows(self) -> List[str]:
        return [file.stem for file in self._path.glob("*.json")]

    def save_workflow(self, name: str, steps: List[Dict[str, str]]) -> None:
        with self._workflow_path(name).open("w", encoding="utf-8") as handle:
            json.dump({"steps": steps}, handle, indent=2)
        LOGGER.info("Saved workflow %s", name)

    def load_workflow(self, name: str) -> List[Dict[str, str]]:
        path = self._workflow_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Workflow not found: {name}")
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data.get("steps", [])
