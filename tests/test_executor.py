from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from agi_core.reasoning.executor import Executor
from agi_core.reasoning.planner import Plan, PlanStep
from agi_core.tools.base import Tool, ToolRegistry, ToolResult, ToolContext


class FailingTool(Tool):
    name = "failing-tool"
    description = "Tool that always raises an exception"

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:  # type: ignore[override]
        raise RuntimeError("boom")


class SuccessfulTool(Tool):
    name = "successful-tool"
    description = "Tool that always succeeds"

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:  # type: ignore[override]
        return ToolResult(success=True, output="ok")


def test_executor_handles_tool_exception(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    executor = Executor(registry, working_directory=str(work_dir))

    plan = Plan(
        goal="test failure handling",
        context_summary="",
        steps=[
            PlanStep(
                name="fail-step",
                description="This step should fail",
                tool="failing-tool",
            )
        ],
    )

    results = executor.execute(plan)

    assert len(results) == 1
    result = results[0]
    assert result.success is False
    assert result.output == ""
    assert result.error == "boom"


def test_execute_step_returns_failed_result_on_exception(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    executor = Executor(registry, working_directory=str(work_dir))

    step = PlanStep(
        name="fail-step",
        description="This step should fail",
        tool="failing-tool",
    )

    result = executor._execute_step(step)

    assert result.success is False
    assert result.output == ""
    assert result.error == "boom"


def test_executor_continues_after_failure(tmp_path) -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())
    registry.register(SuccessfulTool())

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    executor = Executor(registry, working_directory=str(work_dir))

    plan = Plan(
        goal="test continuation after failure",
        context_summary="",
        steps=[
            PlanStep(
                name="fail-step",
                description="This step should fail",
                tool="failing-tool",
            ),
            PlanStep(
                name="success-step",
                description="This step should succeed",
                tool="successful-tool",
            ),
        ],
    )

    results = executor.execute(plan)

    assert len(results) == 2
    first, second = results

    assert first.success is False
    assert first.output == ""
    assert first.error == "boom"

    assert second.success is True
    assert second.output == "ok"
    assert second.error is None
