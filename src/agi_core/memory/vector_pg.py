"""PostgreSQL pgvector-backed memory store implementation."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Iterable, List, Sequence
from uuid import uuid4

from .base import MemoryRecord, MemoryStore

if TYPE_CHECKING:  # pragma: no cover - for static typing only
    from ..config import MemoryConfig

LOGGER = logging.getLogger(__name__)


class PgVectorMemory(MemoryStore):
    """Adapter for pgvector-backed similarity search."""

    def __init__(
        self,
        dsn: str,
        namespace: str,
        *,
        table: str,
        namespace_column: str,
        dimension: int,
    ) -> None:
        try:
            import psycopg
            from psycopg import sql
            from psycopg.types.json import Json
        except ImportError as exc:  # pragma: no cover - runtime safeguard
            raise RuntimeError(
                "pgvector backend requested but psycopg is not installed. Install the 'psycopg' "
                "package (or psycopg[binary]) to enable this feature."
            ) from exc

        self._psycopg = psycopg
        self._sql = sql
        self._Json = Json

        self._namespace = namespace
        self._table = table
        self._namespace_column = namespace_column
        self._dimension = dimension
        self._connection = psycopg.connect(dsn, autocommit=True)
        self._initialise_schema()

    def _initialise_schema(self) -> None:
        sql = self._sql
        with self._connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {table} (
                        id UUID PRIMARY KEY,
                        {namespace} TEXT NOT NULL,
                        content TEXT NOT NULL,
                        embedding vector({dimension}) NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                ).format(
                    table=sql.Identifier(self._table),
                    namespace=sql.Identifier(self._namespace_column),
                    dimension=sql.SQL(str(self._dimension)),
                )
            )
            cursor.execute(
                sql.SQL(
                    """
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table} ({namespace})
                    """
                ).format(
                    index_name=sql.Identifier(f"{self._table}_{self._namespace_column}_idx"),
                    table=sql.Identifier(self._table),
                    namespace=sql.Identifier(self._namespace_column),
                )
            )

    @staticmethod
    def _format_vector(values: Sequence[float]) -> str:
        return "[" + ",".join(str(float(value)) for value in values) + "]"

    @staticmethod
    def _parse_vector(raw: str | Sequence[float]) -> List[float]:
        if isinstance(raw, (list, tuple)):
            return [float(value) for value in raw]
        cleaned = raw.strip().lstrip("[").rstrip("]")
        if not cleaned:
            return []
        return [float(value) for value in cleaned.split(",")]

    def add(self, record: MemoryRecord) -> None:
        sql = self._sql
        vector_literal = self._format_vector(record.embedding)
        payload = self._Json(record.metadata)
        with self._connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    """
                    INSERT INTO {table} (id, {namespace}, content, embedding, metadata, created_at)
                    VALUES (%s, %s, %s, %s::vector, %s, %s)
                    """
                ).format(
                    table=sql.Identifier(self._table),
                    namespace=sql.Identifier(self._namespace_column),
                ),
                (
                    str(uuid4()),
                    self._namespace,
                    record.content,
                    vector_literal,
                    payload,
                    record.created_at,
                ),
            )
        LOGGER.debug("Stored record in pgvector namespace %s", self._namespace)

    def query(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        sql = self._sql
        vector_literal = self._format_vector(query_embedding)
        with self._connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    """
                    SELECT content, embedding, metadata, created_at
                    FROM {table}
                    WHERE {namespace} = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """
                ).format(
                    table=sql.Identifier(self._table),
                    namespace=sql.Identifier(self._namespace_column),
                ),
                (self._namespace, vector_literal, limit),
            )
            rows = cursor.fetchall()

        records: List[MemoryRecord] = []
        for content, embedding, metadata, created_at in rows:
            metadata = metadata or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            created_at_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
            records.append(
                MemoryRecord(
                    content=content,
                    embedding=self._parse_vector(embedding),
                    metadata=metadata,
                    created_at=created_at_dt,
                )
            )
        return records

    def all_records(self) -> Iterable[MemoryRecord]:
        sql = self._sql
        with self._connection.cursor() as cursor:
            cursor.execute(
                sql.SQL(
                    """
                    SELECT content, embedding, metadata, created_at
                    FROM {table}
                    WHERE {namespace} = %s
                    ORDER BY created_at ASC
                    """
                ).format(
                    table=sql.Identifier(self._table),
                    namespace=sql.Identifier(self._namespace_column),
                ),
                (self._namespace,),
            )
            rows = cursor.fetchall()

        for content, embedding, metadata, created_at in rows:
            metadata = metadata or {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            created_at_dt = created_at if isinstance(created_at, datetime) else datetime.fromisoformat(str(created_at))
            yield MemoryRecord(
                content=content,
                embedding=self._parse_vector(embedding),
                metadata=metadata,
                created_at=created_at_dt,
            )

    @classmethod
    def from_config(
        cls,
        config: "MemoryConfig",
        *,
        namespace: str,
    ) -> "PgVectorMemory":
        """Instantiate the adapter using connection details from ``MemoryConfig``."""

        return cls(
            dsn=config.pgvector_dsn,
            namespace=namespace,
            table=config.pgvector_table,
            namespace_column=config.pgvector_namespace_column,
            dimension=config.pgvector_dimension,
        )
