"""Integration-style checks for vector-backed memory orchestration."""
from __future__ import annotations

import sys
import types
import unittest
from math import sqrt
from pathlib import Path
from tempfile import TemporaryDirectory

from agi_core.config import MemoryConfig
from agi_core.memory.orchestrator import MemoryOrchestrator
from agi_core.memory.vector_chroma import ChromaMemory


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


if __name__ == "__main__":  # pragma: no cover - convenience for direct execution
    unittest.main()
