"""Base classes for memory systems."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

import numpy as np


@dataclass
class MemoryRecord:
    """Representation of a memory record."""

    content: str
    embedding: Sequence[float]
    metadata: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def similarity(self, query_embedding: Sequence[float]) -> float:
        """Compute cosine similarity to a query embedding."""
        vector = np.array(self.embedding, dtype=float)
        query = np.array(query_embedding, dtype=float)

        if np.linalg.norm(vector) == 0 or np.linalg.norm(query) == 0:
            return 0.0
        return float(np.dot(vector, query) / (np.linalg.norm(vector) * np.linalg.norm(query)))


class MemoryStore:
    """Abstract base class for memory stores."""

    def add(self, record: MemoryRecord) -> None:
        raise NotImplementedError

    def query(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        raise NotImplementedError

    def all_records(self) -> Iterable[MemoryRecord]:
        raise NotImplementedError
