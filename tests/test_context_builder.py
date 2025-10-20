from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agi_core.reasoning.context import ContextBuilder
from agi_core.tools.base import Tool, ToolContext, ToolRegistry, ToolResult


@dataclass
class _MemoryRecord:
    content: str
    metadata: Dict[str, str]


class _DummyMemory:
    def __init__(self, record: _MemoryRecord | None = None) -> None:
        self._record = record or _MemoryRecord(
            content="Previous observation", metadata={}
        )

    def retrieve_relevant(self, query_embedding: List[float], limit: int = 5):
        return [self._record]


class _EchoTool(Tool):
    name = "echo"
    description = "Echo text back to the user."

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:  # pragma: no cover - unused
        return ToolResult(True, " ".join(args))


def test_context_includes_tool_descriptions():
    registry = ToolRegistry()
    registry.register(_EchoTool())

    builder = ContextBuilder(_DummyMemory())
    context = builder.build("Summarise logs", telemetry={"cpu_usage": 0.5}, tools=registry)

    assert context.available_tools == {"echo": "Echo text back to the user."}
    assert context.memory_snippets == ["Previous observation"]
    assert context.memory_metadata == [{}]
    assert len(context.query_embedding) == builder._embedding_dim


def test_context_uses_full_semantic_summary() -> None:
    summary = "Task 9 (user): inspect logs\nStatus: SUCCESS\n\nFull summary body"
    record = _MemoryRecord(
        content=summary,
        metadata={"label": "Outcome summary for task 9"},
    )
    builder = ContextBuilder(_DummyMemory(record))

    context = builder.build("Review logs", telemetry={}, tools=ToolRegistry())

    assert context.memory_snippets == [summary]
    assert context.memory_metadata == [{"label": "Outcome summary for task 9"}]
