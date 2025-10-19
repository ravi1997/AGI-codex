"""Utilities for building planning context and lightweight embeddings."""
from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence

from ..memory.orchestrator import MemoryOrchestrator
from ..tools.base import ToolRegistry

LOGGER = logging.getLogger(__name__)


@dataclass
class PlanningContext:
    """Aggregated context information supplied to the planner."""

    goal: str
    memory_snippets: List[str]
    telemetry: Dict[str, float]
    available_tools: Dict[str, str]
    query_embedding: Sequence[float]


class ContextBuilder:
    """Constructs planning context and deterministic embeddings."""

    def __init__(self, memory: MemoryOrchestrator, embedding_dim: int = 64) -> None:
        self._memory = memory
        self._embedding_dim = embedding_dim

    def embed(self, text: str) -> List[float]:
        """Generate a deterministic embedding using hashed token features."""

        tokens = [token for token in text.lower().split() if token]
        vector = [0.0] * self._embedding_dim
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self._embedding_dim):
                byte = digest[index % len(digest)]
                vector[index] += 1.0 if byte % 2 == 0 else -1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def build(
        self,
        goal: str,
        telemetry: Dict[str, float],
        tools: ToolRegistry,
        *,
        limit: int = 5,
    ) -> PlanningContext:
        """Compose the planning context for a given goal."""

        embedding = self.embed(goal)
        memories = self._memory.retrieve_relevant(embedding, limit=limit)
        memory_snippets = [record.content for record in memories]
        available_tools = {name: tool.description for name, tool in tools.list_tools().items()}

        LOGGER.debug(
            "Planning context built with %d memories and %d tools", len(memory_snippets), len(available_tools)
        )

        return PlanningContext(
            goal=goal,
            memory_snippets=memory_snippets,
            telemetry=telemetry,
            available_tools=available_tools,
            query_embedding=embedding,
        )
