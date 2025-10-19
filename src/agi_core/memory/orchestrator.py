"""Memory orchestration utilities."""
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Sequence

from ..config import MemoryConfig
from .base import MemoryRecord
from .episodic import EpisodicMemory
from .procedural import ProceduralMemory
from .semantic import SemanticMemory

LOGGER = logging.getLogger(__name__)


class MemoryOrchestrator:
    """Coordinates interactions across memory subsystems."""

    def __init__(self, config: MemoryConfig) -> None:
        self.episodic = EpisodicMemory(config.episodic_db_path)
        self.semantic = SemanticMemory(config.semantic_db_path)
        self.procedural = ProceduralMemory(config.procedural_repo_path)

    def add_episode(self, content: str, embedding: Sequence[float], metadata: Dict[str, str]) -> None:
        record = MemoryRecord(content=content, embedding=embedding, metadata=metadata)
        self.episodic.add(record)
        LOGGER.debug("Added episodic memory: %s", metadata)

    def add_semantic(self, content: str, embedding: Sequence[float], metadata: Dict[str, str]) -> None:
        record = MemoryRecord(content=content, embedding=embedding, metadata=metadata)
        self.semantic.add(record)
        LOGGER.debug("Added semantic memory: %s", metadata)

    def retrieve_relevant(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        episodic = self.episodic.query(query_embedding, limit=limit)
        semantic = self.semantic.query(query_embedding, limit=limit)
        combined = episodic + semantic
        # Deduplicate by content while preserving order
        seen = set()
        unique: List[MemoryRecord] = []
        for record in combined:
            if record.content not in seen:
                seen.add(record.content)
                unique.append(record)
        LOGGER.debug("Retrieved %d relevant memories", len(unique))
        return unique[:limit]
