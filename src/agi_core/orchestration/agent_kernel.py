"""Core orchestration logic for the AGI system."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Sequence

from ..config import AgentConfig
from ..logging_config import configure_logging
from ..learning import FeedbackCollector, LearningPipeline, SelfOptimizer
from ..memory.orchestrator import MemoryOrchestrator
from ..reasoning.context import ContextBuilder
from ..reasoning.executor import Executor
from ..reasoning.planner import Plan, Planner
from ..reasoning.verifier import Verifier
from ..system.safety import SafetyGuard
from ..system.telemetry import TelemetryCollector
from ..tools.base import ToolRegistry, ToolResult
from ..tools.browser import BrowserAutomationTool
from ..tools.file_io import FileIOTool
from ..tools.rest_client import RestClientTool
from ..tools.system_monitor import SystemMonitorTool
from ..tools.terminal import TerminalNetworkPolicy, TerminalTool
from .dialogue_manager import DialogueManager
from .task_scheduler import ScheduledTask, TaskScheduler

LOGGER = logging.getLogger(__name__)


@dataclass
class AgentState:
    """Holds runtime state for the agent."""

    last_task: Optional[ScheduledTask] = None
    last_plan: Optional[Plan] = None
    last_results: Optional[List[ToolResult]] = None


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
        allow_network = config.tools.allow_network
        network_allowlist = config.tools.network_allowlist
        terminal_policy = (
            TerminalNetworkPolicy.online(network_allowlist)
            if allow_network
            else TerminalNetworkPolicy.offline()
        )
        self.tools.register(
            TerminalTool(
                sandbox_root=sandbox,
                network_policy=terminal_policy,
            )
        )
        self.tools.register(FileIOTool(sandbox_root=sandbox))
        self.tools.register(SystemMonitorTool(self.telemetry))

        browser_cfg = config.tools.browser
        if browser_cfg.enabled:
            self.tools.register(
                BrowserAutomationTool(
                    sandbox_root=sandbox,
                    allow_network=config.tools.allow_network,
                    allowed_origins=browser_cfg.allowed_origins,
                    headless=browser_cfg.headless,
                    default_timeout_ms=browser_cfg.default_timeout_ms,
                    backend=browser_cfg.backend,
                )
            )

        rest_cfg = config.tools.rest
        if rest_cfg.enabled:
            self.tools.register(
                RestClientTool(
                    allow_network=config.tools.allow_network,
                    allowed_hosts=rest_cfg.allowed_hosts,
                    default_headers=rest_cfg.default_headers,
                    auth_token=rest_cfg.auth_token,
                    default_timeout=rest_cfg.default_timeout_sec,
                    sandbox_root=sandbox,
                )
            )

        self.executor = Executor(self.tools, working_directory=str(sandbox))
        self.verifier = Verifier()
        self.context_builder = ContextBuilder(self.memory)
        self.feedback = FeedbackCollector(config.learning)
        self.learning_pipeline = LearningPipeline(config.learning)
        self.optimizer = SelfOptimizer(config.learning)
        self._is_shutdown = False

        self.dialogue.register_user_message_handler(self._handle_user_message)

    def _handle_user_message(self, message: str) -> None:
        LOGGER.info("Queueing task from user message: %s", message)
        self.scheduler.add_task(message, priority=5, metadata={"source": "user"})

    def _propose_autonomous_task(self) -> None:
        telemetry = self.telemetry.snapshot()
        description = "Review system telemetry trends and refresh health report"
        metadata = {
            "source": "autonomous",
            **{k: f"{v}" for k, v in telemetry.items()},
        }
        self.scheduler.add_task(description, priority=1, metadata=metadata, autonomous=True)
        self.scheduler.mark_autonomous_proposal()
        LOGGER.info("Proposed autonomous task: %s", description)

    def run_once(self) -> bool:
        """Execute a single control loop iteration.

        Returns:
            bool: Whether a task was processed during the iteration.
        """
        if self.scheduler.should_propose_autonomous():
            self._propose_autonomous_task()

        task = self.scheduler.pop_next()
        if task is None:
            LOGGER.debug("No tasks available")
            return False

        self.state.last_task = task
        LOGGER.info("Processing task %s: %s", task.task_id, task.description)

        if not self.safety.approve_goal(task.description):
            self.dialogue.send_output("Task rejected by safety guard")
            return False

        telemetry = self.telemetry.snapshot()
        context = self.context_builder.build(task.description, telemetry, self.tools)
        plan = self.planner.build_plan(context)
        results = self.executor.execute(plan)
        success = self.verifier.evaluate(plan, results)

        self.state.last_plan = plan
        self.state.last_results = results

        summary = self._summarize_execution(task, plan, results, success)
        self.dialogue.send_output(summary)

        embedding = list(context.query_embedding)
        metadata = {
            "success": str(success),
            "task_id": str(task.task_id),
            "source": task.metadata.get("source", "unknown"),
            "label": f"Outcome summary for task {task.task_id}",
        }
        self.memory.add_episode(
            content=summary,
            embedding=embedding,
            metadata=metadata,
        )

        outcome_embedding = self.context_builder.embed(summary)
        semantic_metadata = dict(metadata)
        self.memory.add_semantic(
            content=summary,
            embedding=outcome_embedding,
            metadata=semantic_metadata,
        )

        self.feedback.record_run(
            task_id=str(task.task_id),
            goal=task.description,
            success=success,
            plan=plan,
            results=results,
            telemetry=telemetry,
        )

        self.learning_pipeline.add_example(
            task_id=str(task.task_id),
            goal=task.description,
            success=success,
            plan=plan,
            results=results,
            summary=summary,
        )

        self.optimizer.maybe_optimize(self.scheduler, self.feedback, telemetry)

        if not success:
            follow_up = (
                f"Diagnose failure of task {task.task_id}: {task.description}"
            )
            self.scheduler.add_task(
                follow_up,
                priority=max(1, -task.priority),
                metadata={
                    "source": "autonomous",
                    "origin_task": str(task.task_id),
                },
                autonomous=True,
            )

        return True

    def run_forever(self) -> None:
        LOGGER.info("Starting agent loop")
        try:
            while True:
                processed = self.run_once()
                if not processed:
                    time.sleep(self._config.scheduler.idle_sleep_seconds)
        except KeyboardInterrupt:
            LOGGER.info("Agent loop stopped by user")
        finally:
            self.shutdown()

    def _summarize_execution(
        self,
        task: ScheduledTask,
        plan: Plan,
        results: Sequence[ToolResult],
        success: bool,
    ) -> str:
        status = "SUCCESS" if success else "FAILED"
        lines = [
            f"Task {task.task_id} ({task.metadata.get('source', 'unknown')}): {task.description}",
            f"Status: {status}",
            "",
            "Plan Context:",
            plan.context_summary,
            "",
            "Step Results:",
        ]

        for step, result in zip(plan.steps, results):
            outcome = "ok" if result.success else "error"
            detail = result.output or result.error or ""
            lines.append(f"- {step.name} [{outcome}] -> {detail}")

        return "\n".join(lines)

    def shutdown(self) -> None:
        """Flush buffers and emit final telemetry before exit."""

        if self._is_shutdown:
            return

        self._is_shutdown = True
        LOGGER.info("Shutting down agent kernel")
        self.learning_pipeline.flush()
        metrics = self.feedback.metrics
        LOGGER.info(
            "Final feedback metrics: runs=%s successes=%s failures=%s success_rate=%.2f%%",
            metrics.total_runs,
            metrics.successes,
            metrics.failures,
            metrics.success_rate * 100,
        )
