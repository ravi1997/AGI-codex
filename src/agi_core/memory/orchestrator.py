"""Memory orchestration utilities."""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence

from ..config import MemoryConfig
from .base import MemoryRecord
from .episodic import EpisodicMemory
from .procedural import ProceduralMemory
from .semantic import SemanticMemory
from .vector_chroma import ChromaMemory
from .vector_pg import PgVectorMemory

LOGGER = logging.getLogger(__name__)


class MemoryOrchestrator:
    """Coordinates interactions across memory subsystems."""

    def __init__(self, config: MemoryConfig) -> None:
        backend = (config.vector_backend or "").strip().lower()

        self.episodic = self._build_store(
            backend,
            store_name="episodic",
            default_factory=lambda: EpisodicMemory(config.episodic_db_path),
            vector_factory=lambda: self._build_vector_store(
                backend,
                collection=config.vector_episodic_collection,
                config=config,
            ),
        )
        self.semantic = self._build_store(
            backend,
            store_name="semantic",
            default_factory=lambda: SemanticMemory(config.semantic_db_path),
            vector_factory=lambda: self._build_vector_store(
                backend,
                collection=config.vector_semantic_collection,
                config=config,
            ),
        )
        self.procedural = ProceduralMemory(config.procedural_repo_path)

    def _build_store(
        self,
        backend: str,
        *,
        store_name: str,
        default_factory,
        vector_factory,
    ):
        if not backend:
            LOGGER.info("Using file-backed %s memory store", store_name)
            return default_factory()
        try:
            store = vector_factory()
            LOGGER.info(
                "Initialised %s vector memory backend for %s store", backend, store_name
            )
            return store
        except Exception as exc:  # pragma: no cover - depends on optional dependencies
            LOGGER.warning(
                (
                    "Vector backend '%s' unavailable for %s store (%s). "
                    "Falling back to file-backed store."
                ),
                backend,
                store_name,
                exc,
            )
            return default_factory()

    @staticmethod
    def _build_vector_store(backend: str, *, collection: str, config: MemoryConfig):
        if backend == "chromadb":
            return ChromaMemory(connection=config.chroma_connection, collection=collection)
        if backend == "pgvector":
            return PgVectorMemory(
                dsn=config.pgvector_dsn,
                namespace=collection,
                table=config.pgvector_table,
                namespace_column=config.pgvector_namespace_column,
                dimension=config.pgvector_dimension,
            )
        raise ValueError(f"Unsupported vector backend '{backend}'")

    def add_episode(self, content: str, embedding: Sequence[float], metadata: Dict[str, str]) -> None:
        record = MemoryRecord(content=content, embedding=embedding, metadata=metadata)
        self.episodic.add(record)
        LOGGER.debug("Added episodic memory: %s", metadata)

    def add_semantic(self, content: str, embedding: Sequence[float], metadata: Dict[str, str]) -> None:
        record = MemoryRecord(content=content, embedding=embedding, metadata=metadata)
        self.semantic.add(record)
        LOGGER.debug("Added semantic memory: %s", metadata)

    def retrieve_relevant(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        limit = max(int(limit), 1)
        per_store_limit = max(limit * 2, limit)
        candidates: List[MemoryRecord] = []

        for store_name, store in (("episodic", self.episodic), ("semantic", self.semantic)):
            try:
                records = store.query(query_embedding, limit=per_store_limit)
            except Exception as exc:  # pragma: no cover - defensive logging
                LOGGER.warning(
                    (
                        "Query against %s memory store failed (%s); "
                        "falling back to linear scan."
                    ),
                    store_name,
                    exc,
                )
                records = list(store.all_records())
            candidates.extend(records)

        scored_records = sorted(
            ((record.similarity(query_embedding), record) for record in candidates),
            key=lambda item: item[0],
            reverse=True,
        )

        seen_contents = set()
        unique: List[MemoryRecord] = []
        for _, record in scored_records:
            if record.content in seen_contents:
                continue
            seen_contents.add(record.content)
            unique.append(record)
            if len(unique) >= limit:
                break

        LOGGER.debug("Retrieved %d relevant memories", len(unique))
        return unique
