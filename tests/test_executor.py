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
