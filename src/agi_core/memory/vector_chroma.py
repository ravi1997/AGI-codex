"""ChromaDB-backed memory store implementation."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable, List, Sequence
from urllib.parse import urlparse
from uuid import uuid4

from .base import MemoryRecord, MemoryStore

LOGGER = logging.getLogger(__name__)


def _coerce_metadata(metadata: dict | None) -> dict:
    """Return a shallow copy of metadata ensuring a dictionary."""

    return dict(metadata or {})


class ChromaMemory(MemoryStore):
    """Adapter around a Chroma vector store collection."""

    def __init__(self, connection: str, collection: str) -> None:
        try:
            import chromadb
        except ImportError as exc:  # pragma: no cover - exercised in runtime environments
            raise RuntimeError(
                "Chroma vector backend is not installed. Install the 'chromadb' package to "
                "enable this feature."
            ) from exc

        self._client = self._create_client(chromadb, connection)
        self._collection = self._client.get_or_create_collection(
            name=collection,
            metadata={"hnsw:space": "cosine"},
        )

    @staticmethod
    def _create_client(chromadb_module: object, connection: str):
        """Instantiate the most appropriate Chroma client for the connection string."""

        connection = connection or ""
        normalized = connection.strip()

        if not normalized or normalized == ":memory":
            LOGGER.debug("Using ephemeral in-process Chroma client")
            return chromadb_module.EphemeralClient()

        parsed = urlparse(normalized)
        if parsed.scheme in {"http", "https"}:
            host = parsed.hostname or "localhost"
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            LOGGER.debug("Connecting to remote Chroma server at %s:%s", host, port)
            # Prefer the new Settings API but fall back to HttpClient when unavailable
            try:
                from chromadb.config import Settings

                settings = Settings(
                    chroma_api_impl="rest",
                    chroma_server_host=host,
                    chroma_server_http_port=port,
                    chroma_server_ssl=parsed.scheme == "https",
                )
                return chromadb_module.Client(settings)
            except Exception:  # pragma: no cover - defensive for diverse chromadb versions
                LOGGER.debug("Falling back to HttpClient for Chroma connectivity")
                return chromadb_module.HttpClient(host=host, port=port, ssl=parsed.scheme == "https")

        if parsed.scheme == "file":
            path = parsed.path or "chroma"
        else:
            path = normalized
        LOGGER.debug("Using persistent Chroma client at %s", path)
        return chromadb_module.PersistentClient(path=path)

    @staticmethod
    def _serialise_metadata(record: MemoryRecord) -> dict:
        metadata = _coerce_metadata(record.metadata)
        metadata.setdefault("_created_at", record.created_at.isoformat())
        return metadata

    @staticmethod
    def _record_from_payload(content: str, embedding: Sequence[float], metadata: dict | None) -> MemoryRecord:
        metadata_copy = _coerce_metadata(metadata)
        created_at_raw = metadata_copy.pop("_created_at", None)
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.utcnow()
        return MemoryRecord(
            content=content,
            embedding=[float(value) for value in embedding],
            metadata=metadata_copy,
            created_at=created_at,
        )

    def add(self, record: MemoryRecord) -> None:
        metadata = self._serialise_metadata(record)
        self._collection.add(
            ids=[str(uuid4())],
            documents=[record.content],
            embeddings=[list(float(value) for value in record.embedding)],
            metadatas=[metadata],
        )
        LOGGER.debug("Stored record in Chroma collection %s", self._collection.name)

    def query(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        response = self._collection.query(
            query_embeddings=[list(float(value) for value in query_embedding)],
            n_results=max(limit, 1),
            include=["documents", "embeddings", "metadatas"],
        )
        documents = response.get("documents") or [[]]
        embeddings = response.get("embeddings") or [[]]
        metadatas = response.get("metadatas") or [[]]

        records: List[MemoryRecord] = []
        for content, embedding, metadata in zip(documents[0], embeddings[0], metadatas[0]):
            if content is None:
                continue
            records.append(self._record_from_payload(content, embedding, metadata))
        return records[:limit]

    def all_records(self) -> Iterable[MemoryRecord]:
        payload = self._collection.get(include=["documents", "embeddings", "metadatas"])
        documents = payload.get("documents", [])
        embeddings = payload.get("embeddings", [])
        metadatas = payload.get("metadatas", [])

        records: List[MemoryRecord] = []
        for content, embedding, metadata in zip(documents, embeddings, metadatas):
            records.append(self._record_from_payload(content, embedding, metadata))
        return records
