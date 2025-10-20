"""Planning agent implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

from .context import PlanningContext

LOGGER = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """Represents a single step in a plan."""

    name: str
    description: str
    tool: str | None
    args: List[str] = field(default_factory=list)
    kwargs: Dict[str, str] = field(default_factory=dict)


@dataclass
class Plan:
    """Represents a multi-step plan."""

    goal: str
    context_summary: str
    steps: List[PlanStep]


class Planner:
    """Heuristic planner that incorporates telemetry and memory."""

    def build_plan(self, context: PlanningContext) -> Plan:
        LOGGER.info("Planning for goal: %s", context.goal)

        context_summary = self._summarize_context(context)
        steps: List[PlanStep] = []

        if "system.monitor" in context.available_tools:
            steps.append(
                PlanStep(
                    name="capture-telemetry",
                    description="Capture a fresh telemetry snapshot to ensure up-to-date metrics",
                    tool="system.monitor",
                )
            )

        if context.memory_snippets:
            steps.append(
                PlanStep(
                    name="reflect-on-memories",
                    description="Reflect on similar past tasks and incorporate lessons learned",
                    tool=None,
                )
            )

        if "file.io" in context.available_tools:
            steps.append(
                PlanStep(
                    name="persist-context",
                    description="Persist the planning context for traceability",
                    tool="file.io",
                    kwargs={
                        "action": "write",
                        "path": "reports/context_snapshot.md",
                        "data": context_summary,
                    },
                )
            )

        if "terminal.run" in context.available_tools:
            command = self._derive_command(context.goal)
            steps.append(
                PlanStep(
                    name="execute-goal",
                    description=f"Execute command to satisfy goal: {context.goal}",
                    tool="terminal.run",
                    args=[command],
                )
            )

        LOGGER.debug("Generated %d plan steps", len(steps))
        return Plan(goal=context.goal, context_summary=context_summary, steps=steps)

    def _summarize_context(self, context: PlanningContext) -> str:
        lines = ["# Planning Context", "", f"## Goal\n{context.goal}"]
        if context.telemetry:
            lines.append("\n## Telemetry")
            for key, value in context.telemetry.items():
                lines.append(f"- {key}: {value}")

        if context.memory_snippets:
            lines.append("\n## Relevant Memories")
            for snippet, metadata in zip(context.memory_snippets, context.memory_metadata):
                label = metadata.get("label") if metadata else None
                if label:
                    lines.append(f"- {label}")
                    continue
                first_line = snippet.splitlines()[0] if snippet else ""
                lines.append(f"- {first_line}")

        if context.available_tools:
            lines.append("\n## Available Tools")
            for name, description in context.available_tools.items():
                lines.append(f"- {name}: {description}")

        return "\n".join(lines)

    def _derive_command(self, goal: str) -> str:
        lowered = goal.strip().lower()
        if not lowered:
            return "echo 'No goal provided'"

        known_prefixes = ("ls", "cat", "python", "bash", "sh", "pip", "git")
        if goal.strip().startswith(known_prefixes):
            return goal.strip()

        if any(keyword in lowered for keyword in ["list", "show files", "display directory"]):
            return "ls"

        if any(keyword in lowered for keyword in ["status", "metrics", "telemetry"]):
            return "echo 'Telemetry captured separately'"

        return f"echo \"Goal: {goal}\""
