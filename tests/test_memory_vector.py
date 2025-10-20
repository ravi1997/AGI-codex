"""Integration-style checks for vector-backed memory orchestration."""
from __future__ import annotations

import sys
import types
import unittest
from math import sqrt
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agi_core.config import MemoryConfig
from agi_core.memory.orchestrator import MemoryOrchestrator
from agi_core.memory.vector_chroma import ChromaMemory
from agi_core.memory.vector_pg import PgVectorMemory
from agi_core.memory.episodic import EpisodicMemory
from agi_core.memory.semantic import SemanticMemory


class _FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name
        self._records: list[dict[str, object]] = []

    def add(self, ids, documents, embeddings, metadatas):
        for document, embedding, metadata in zip(documents, embeddings, metadatas):
            self._records.append(
                {
                    "document": document,
                    "embedding": list(embedding),
                    "metadata": dict(metadata),
                }
            )

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sqrt(sum(x * x for x in a))
        norm_b = sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def query(self, query_embeddings, n_results, include):
        query = list(query_embeddings[0])
        ranked = sorted(
            self._records,
            key=lambda item: self._cosine(query, list(item["embedding"])),
            reverse=True,
        )[:n_results]
        return {
            "documents": [[item["document"] for item in ranked]],
            "embeddings": [[list(item["embedding"]) for item in ranked]],
            "metadatas": [[dict(item["metadata"]) for item in ranked]],
        }

    def get(self, include):
        return {
            "documents": [item["document"] for item in self._records],
            "embeddings": [list(item["embedding"]) for item in self._records],
            "metadatas": [dict(item["metadata"]) for item in self._records],
        }


class _FakeClient:
    def __init__(self, registry: dict[str, _FakeCollection]) -> None:
        self._registry = registry

    def get_or_create_collection(self, name: str, metadata=None):  # noqa: ARG002
        if name not in self._registry:
            self._registry[name] = _FakeCollection(name)
        return self._registry[name]


class _FakeChroma(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("chromadb")
        self._registry: dict[str, _FakeCollection] = {}

    def EphemeralClient(self) -> _FakeClient:  # noqa: N802 - matches chromadb API
        return _FakeClient(self._registry)


class _FakeSQLString:
    def __init__(self, template: str) -> None:
        self._template = template

    def format(self, **params: object) -> "_FakeSQLString":
        formatted = self._template
        for key, value in params.items():
            formatted = formatted.replace("{" + key + "}", str(value))
        return _FakeSQLString(formatted)

    def __str__(self) -> str:
        return self._template


class _FakeIdentifier:
    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self._value


class _FakeSQLModule(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("psycopg.sql")

    @staticmethod
    def SQL(template: str) -> _FakeSQLString:  # noqa: N802 - align with psycopg API
        return _FakeSQLString(template)

    @staticmethod
    def Identifier(value: str) -> _FakeIdentifier:  # noqa: N802 - align with psycopg API
        return _FakeIdentifier(value)


class _FakeJson:
    def __init__(self, payload: dict | None) -> None:
        self.payload = payload or {}


class _FakeJsonModule(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("psycopg.types.json")
        self.Json = _FakeJson


def _parse_vector_literal(raw: str) -> list[float]:
    cleaned = raw.strip().lstrip("[").rstrip("]")
    if not cleaned:
        return []
    return [float(value) for value in cleaned.split(",")]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class _FakeCursor:
    def __init__(self, connection: "_FakeConnection") -> None:
        self._connection = connection
        self._last_result: list[tuple] = []

    def __enter__(self) -> "_FakeCursor":  # pragma: no cover - trivial
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - trivial
        self._last_result = []

    def execute(self, statement, params=None):  # noqa: ANN001 - match psycopg signature
        sql_text = str(statement).strip()
        normalized = sql_text.upper()

        if normalized.startswith("CREATE"):
            return

        if normalized.startswith("INSERT"):
            (
                _row_id,
                namespace,
                content,
                vector_literal,
                payload,
                created_at,
            ) = params
            embedding = _parse_vector_literal(vector_literal)
            metadata = payload.payload if isinstance(payload, _FakeJson) else dict(payload or {})
            self._connection.records.setdefault(namespace, []).append(
                {
                    "content": content,
                    "embedding": embedding,
                    "metadata": metadata,
                    "created_at": created_at,
                }
            )
            return

        if "ORDER BY EMBEDDING <=>" in normalized:
            namespace, vector_literal, limit = params
            query_vector = _parse_vector_literal(vector_literal)
            ranked = sorted(
                self._connection.records.get(namespace, []),
                key=lambda item: _cosine_similarity(query_vector, item["embedding"]),
                reverse=True,
            )[: int(limit)]
            self._last_result = [
                (
                    item["content"],
                    list(item["embedding"]),
                    dict(item["metadata"]),
                    item["created_at"],
                )
                for item in ranked
            ]
            return

        if "ORDER BY CREATED_AT" in normalized:
            (namespace,) = params
            ranked = sorted(
                self._connection.records.get(namespace, []),
                key=lambda item: item["created_at"],
            )
            self._last_result = [
                (
                    item["content"],
                    list(item["embedding"]),
                    dict(item["metadata"]),
                    item["created_at"],
                )
                for item in ranked
            ]

    def fetchall(self) -> list[tuple]:  # pragma: no cover - trivial
        return list(self._last_result)


class _FakeConnection:
    def __init__(self) -> None:
        self.records: dict[str, list[dict[str, object]]] = {}

    def cursor(self) -> _FakeCursor:  # pragma: no cover - trivial
        return _FakeCursor(self)


class _FakePsycopg(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("psycopg")
        self.sql = _FakeSQLModule()
        self.types = types.ModuleType("psycopg.types")
        self.types.json = _FakeJsonModule()

    def connect(self, dsn: str, autocommit: bool = False):  # noqa: D401
        return _FakeConnection()


class VectorMemoryIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._original_chromadb = sys.modules.get("chromadb")
        sys.modules["chromadb"] = _FakeChroma()

    def tearDown(self) -> None:
        if self._original_chromadb is None:
            sys.modules.pop("chromadb", None)
        else:
            sys.modules["chromadb"] = self._original_chromadb

    def test_chromadb_adapter_round_trip(self) -> None:
        with TemporaryDirectory() as tmpdir:
            storage_root = Path(tmpdir) / "storage"
            storage_root.mkdir(parents=True, exist_ok=True)

            config = MemoryConfig(
                vector_backend="chromadb",
                chroma_connection=":memory",
                vector_episodic_collection="test_episodic",
                vector_semantic_collection="test_semantic",
                episodic_db_path=storage_root / "episodic.json",
                semantic_db_path=storage_root / "semantic.json",
                procedural_repo_path=storage_root / "procedural",
            )

            orchestrator = MemoryOrchestrator(config)

            self.assertIsInstance(orchestrator.episodic, ChromaMemory)
            self.assertIsInstance(orchestrator.semantic, ChromaMemory)

            orchestrator.add_episode("hello world", [1.0, 0.0], {"kind": "episode"})
            orchestrator.add_semantic("goodbye", [0.0, 1.0], {"kind": "semantic"})

            results = orchestrator.retrieve_relevant([1.0, 0.0], limit=2)
            self.assertGreaterEqual(len(results), 1)
            self.assertEqual(results[0].content, "hello world")
            self.assertEqual(results[0].metadata["kind"], "episode")

            semantic_records = list(orchestrator.semantic.all_records())
            self.assertTrue(semantic_records)
            self.assertEqual(semantic_records[0].metadata["kind"], "semantic")

    def test_vector_backend_falls_back_when_adapter_unavailable(self) -> None:
        with TemporaryDirectory() as tmpdir:
            storage_root = Path(tmpdir) / "storage"
            storage_root.mkdir(parents=True, exist_ok=True)

            config = MemoryConfig(
                vector_backend="chromadb",
                chroma_connection=":memory",
                episodic_db_path=storage_root / "episodic.json",
                semantic_db_path=storage_root / "semantic.json",
                procedural_repo_path=storage_root / "procedural",
            )

            with patch("agi_core.memory.orchestrator.ChromaMemory.from_config", side_effect=RuntimeError("boom")):
                orchestrator = MemoryOrchestrator(config)

            self.assertIsInstance(orchestrator.episodic, EpisodicMemory)
            self.assertIsInstance(orchestrator.semantic, SemanticMemory)

    def test_pgvector_adapter_round_trip(self) -> None:
        fake_psycopg = _FakePsycopg()
        module_overrides = {
            "psycopg": fake_psycopg,
            "psycopg.sql": fake_psycopg.sql,
            "psycopg.types": fake_psycopg.types,
            "psycopg.types.json": fake_psycopg.types.json,
        }

        with TemporaryDirectory() as tmpdir, patch.dict(sys.modules, module_overrides, clear=False):
            storage_root = Path(tmpdir) / "storage"
            storage_root.mkdir(parents=True, exist_ok=True)

            config = MemoryConfig(
                vector_backend="pgvector",
                vector_episodic_collection="pg_episode",
                vector_semantic_collection="pg_semantic",
                pgvector_dsn="postgresql://agi:agi@localhost:5432/agi",
                pgvector_table="memory_records",
                pgvector_namespace_column="namespace",
                pgvector_dimension=2,
                episodic_db_path=storage_root / "episodic.json",
                semantic_db_path=storage_root / "semantic.json",
                procedural_repo_path=storage_root / "procedural",
            )

            orchestrator = MemoryOrchestrator(config)

            self.assertIsInstance(orchestrator.episodic, PgVectorMemory)
            self.assertIsInstance(orchestrator.semantic, PgVectorMemory)

            orchestrator.add_episode("vector hello", [0.9, 0.1], {"kind": "episode"})
            orchestrator.add_semantic("vector goodbye", [0.1, 0.9], {"kind": "semantic"})

            results = orchestrator.retrieve_relevant([0.9, 0.1], limit=2)
            self.assertTrue(results)
            self.assertEqual(results[0].content, "vector hello")
            self.assertEqual(results[0].metadata["kind"], "episode")

            semantic_records = list(orchestrator.semantic.all_records())
            self.assertEqual(len(semantic_records), 1)
            self.assertEqual(semantic_records[0].metadata["kind"], "semantic")


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
