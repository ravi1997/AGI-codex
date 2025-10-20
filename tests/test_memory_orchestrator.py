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

    summary_text = "Task 42 (user): investigate logs\nStatus: SUCCESS\n\nDetails captured"
    orchestrator.add_semantic(
        summary_text,
        [1.0, 0.0],
        {"source": "semantic", "id": "semantic-shared", "label": "Outcome summary"},
    )

    results = orchestrator.retrieve_relevant(query, limit=2)

    assert len(results) == 2
    assert results[0].metadata["source"] == "semantic"
    assert results[0].content == summary_text
    assert sum(1 for record in results if record.content == summary_text) == 1
    assert any(record.metadata["source"] == "episodic" for record in results)


def test_retrieve_relevant_prefers_highest_scoring_duplicate(tmp_path) -> None:
    """When content overlaps, the highest-scoring record is retained."""

    config = MemoryConfig(
        episodic_db_path=tmp_path / "episodic.json",
        semantic_db_path=tmp_path / "semantic.json",
        procedural_repo_path=tmp_path / "procedural",
    )

    orchestrator = MemoryOrchestrator(config)

    query = [0.9, 0.1]

    # Episodic store contains more entries than the limit and includes an overlap.
    orchestrator.add_episode(
        "overlapping insight",
        [0.5, 0.5],
        {"source": "episodic", "id": "episodic-overlap"},
    )
    orchestrator.add_episode(
        "episodic distraction",
        [0.7, 0.3],
        {"source": "episodic", "id": "episodic-distraction"},
    )
    orchestrator.add_episode(
        "episodic filler",
        [0.6, 0.4],
        {"source": "episodic", "id": "episodic-filler"},
    )

    # Semantic store has the same content but with a stronger match to the query.
    orchestrator.add_semantic(
        "overlapping insight",
        [0.95, 0.05],
        {"source": "semantic", "id": "semantic-overlap"},
    )

    results = orchestrator.retrieve_relevant(query, limit=2)

    assert len(results) == 2
    overlap_records = [record for record in results if record.content == "overlapping insight"]
    assert len(overlap_records) == 1
    assert overlap_records[0].metadata["source"] == "semantic"
