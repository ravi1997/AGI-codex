"""Tests for the memory orchestrator retrieval logic."""
from __future__ import annotations

from agi_core.config import MemoryConfig
from agi_core.memory.orchestrator import MemoryOrchestrator


def test_retrieve_relevant_includes_semantic_with_overlap(tmp_path) -> None:
    """Semantic memories remain in the results even when episodic items exceed the limit."""

    config = MemoryConfig(
        episodic_db_path=tmp_path / "episodic.json",
        semantic_db_path=tmp_path / "semantic.json",
        procedural_repo_path=tmp_path / "procedural",
    )

    orchestrator = MemoryOrchestrator(config)

    query = [1.0, 0.0]

    orchestrator.add_episode(
        "shared memory",
        [0.85, 0.15],
        {"source": "episodic", "id": "episodic-shared"},
    )
    orchestrator.add_episode(
        "episodic highlight",
        [0.95, 0.05],
        {"source": "episodic", "id": "episodic-highlight"},
    )
    orchestrator.add_episode(
        "episodic supporting",
        [0.9, 0.1],
        {"source": "episodic", "id": "episodic-supporting"},
    )
    orchestrator.add_episode(
        "episodic filler",
        [0.6, 0.4],
        {"source": "episodic", "id": "episodic-filler"},
    )

    orchestrator.add_semantic(
        "shared memory",
        [1.0, 0.0],
        {"source": "semantic", "id": "semantic-shared"},
    )

    results = orchestrator.retrieve_relevant(query, limit=2)

    assert len(results) == 2
    assert results[0].metadata["source"] == "semantic"
    assert results[0].content == "shared memory"
    assert sum(1 for record in results if record.content == "shared memory") == 1
    assert any(record.metadata["source"] == "episodic" for record in results)
