"""Core orchestration logic for the AGI system."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from ..config import AgentConfig
from ..logging_config import configure_logging
from ..memory.orchestrator import MemoryOrchestrator
from ..reasoning.executor import Executor
from ..reasoning.planner import Planner
from ..reasoning.verifier import Verifier
from ..system.safety import SafetyGuard
from ..system.telemetry import TelemetryCollector
from ..tools.base import ToolRegistry
from ..tools.file_io import FileIOTool
from ..tools.terminal import TerminalTool
from .dialogue_manager import DialogueManager
from .task_scheduler import ScheduledTask, TaskScheduler

LOGGER = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Holds runtime state for the agent."""

    last_task: Optional[ScheduledTask] = None


class AgentKernel:
    """Main orchestrator of planning, execution, and reflection."""

    def __init__(self, config: AgentConfig) -> None:
        configure_logging(config)
        self._config = config
        self.state = AgentState()

        self.dialogue = DialogueManager()
        self.scheduler = TaskScheduler(config.scheduler)
        self.memory = MemoryOrchestrator(config.memory)
        self.telemetry = TelemetryCollector()
        self.safety = SafetyGuard()
        self.planner = Planner()

        self.tools = ToolRegistry()
        sandbox = config.tools.sandbox_root
        self.tools.register(TerminalTool(sandbox_root=sandbox))
        self.tools.register(FileIOTool(sandbox_root=sandbox))

        self.executor = Executor(self.tools, working_directory=str(sandbox))
        self.verifier = Verifier()

        self.dialogue.register_user_message_handler(self._handle_user_message)

    def _handle_user_message(self, message: str) -> None:
        LOGGER.info("Queueing task from user message: %s", message)
        self.scheduler.add_task(message, priority=5, metadata={"source": "user"})

    def _propose_autonomous_task(self) -> None:
        telemetry = self.telemetry.snapshot()
        description = (
            "Review system telemetry and update health report"
        )
        metadata = {"source": "autonomous", **{k: f"{v}" for k, v in telemetry.items()}}
        self.scheduler.add_task(description, priority=1, metadata=metadata, autonomous=True)
        self.scheduler.mark_autonomous_proposal()
        LOGGER.info("Proposed autonomous task: %s", description)

    def run_once(self) -> None:
        """Execute a single control loop iteration."""
        if self.scheduler.should_propose_autonomous():
            self._propose_autonomous_task()

        task = self.scheduler.pop_next()
        if task is None:
            LOGGER.debug("No tasks available")
            return

        self.state.last_task = task
        LOGGER.info("Processing task %s: %s", task.task_id, task.description)

        if not self.safety.approve_goal(task.description):
            self.dialogue.send_output("Task rejected by safety guard")
            return

        plan = self.planner.build_plan(task.description)
        results = self.executor.execute(plan)
        success = self.verifier.evaluate(plan, results)

        summary = "Task completed successfully" if success else "Task execution encountered issues"
        self.dialogue.send_output(summary)

        # Record episodic memory placeholder embedding (zeros) for now
        embedding = [0.0 for _ in range(16)]
        self.memory.add_episode(
            content=f"Task {task.task_id}: {task.description}",
            embedding=embedding,
            metadata={"success": str(success)},
        )

    def run_forever(self) -> None:
        LOGGER.info("Starting agent loop")
        try:
            while True:
                self.run_once()
        except KeyboardInterrupt:
            LOGGER.info("Agent loop stopped by user")
