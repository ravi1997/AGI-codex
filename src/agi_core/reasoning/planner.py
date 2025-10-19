"""Planning agent implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

LOGGER = logging.getLogger(__name__)


@dataclass
class PlanStep:
    """Represents a single step in a plan."""

    description: str
    tool: str
    arguments: List[str]


@dataclass
class Plan:
    """Represents a multi-step plan."""

    goal: str
    steps: List[PlanStep]


class Planner:
    """Simple heuristic planner."""

    def build_plan(self, goal: str) -> Plan:
        LOGGER.info("Planning for goal: %s", goal)
        # Minimal heuristic: treat goal as needing reasoning summary and execution step
        steps = [
            PlanStep(
                description="Summarize goal and gather context",
                tool="file.io",
                arguments=["read", "context.txt"],
            ),
            PlanStep(
                description="Attempt to execute requested command",
                tool="terminal.run",
                arguments=[goal],
            ),
        ]
        LOGGER.debug("Generated %d plan steps", len(steps))
        return Plan(goal=goal, steps=steps)
