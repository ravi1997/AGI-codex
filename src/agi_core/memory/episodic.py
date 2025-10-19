"""Episodic memory implementation."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

from .base import MemoryRecord, MemoryStore

LOGGER = logging.getLogger(__name__)


class EpisodicMemory(MemoryStore):
    """File-backed episodic memory."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[MemoryRecord] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            LOGGER.debug("No episodic memory file found at %s", self._path)
            return

        with self._path.open("r", encoding="utf-8") as handle:
            raw_records = json.load(handle)
        self._records = []
        for item in raw_records:
            created_at = (
                datetime.fromisoformat(item["created_at"]) if "created_at" in item else datetime.utcnow()
            )
            record = MemoryRecord(
                content=item["content"],
                embedding=item["embedding"],
                metadata=item.get("metadata", {}),
                created_at=created_at,
            )
            self._records.append(record)
        LOGGER.info("Loaded %d episodic memories", len(self._records))

    def _persist(self) -> None:
        serializable = [
            {
                "content": record.content,
                "embedding": list(record.embedding),
                "metadata": record.metadata,
                "created_at": record.created_at.isoformat(),
            }
            for record in self._records
        ]
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, indent=2)
        LOGGER.debug("Persisted %d episodic memories", len(self._records))

    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)
        self._persist()

    def query(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        ranked = sorted(
            self._records,
            key=lambda record: record.similarity(query_embedding),
            reverse=True,
        )
        return ranked[:limit]

    def all_records(self) -> Iterable[MemoryRecord]:
        return list(self._records)
