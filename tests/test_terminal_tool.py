"""Tests for the TerminalTool networking policy controls."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import subprocess

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from agi_core.tools.base import ToolContext
from agi_core.tools.terminal import TerminalTool


class DummyCompletedProcess(SimpleNamespace):
    """Helper to mimic subprocess.CompletedProcess for testing."""

    returncode: int
    stdout: str
    stderr: str


@pytest.fixture()
def tool_context(tmp_path: Path) -> ToolContext:
    return ToolContext(working_directory=str(tmp_path))


def test_terminal_blocks_network_when_disabled(tmp_path: Path, tool_context: ToolContext) -> None:
    tool = TerminalTool(sandbox_root=tmp_path, allow_network=False)

    result = tool.run(tool_context, "curl http://example.com")

    assert not result.success
    assert result.error is not None
    assert "disabled" in result.error.lower()


def test_terminal_blocks_network_path_when_disabled(
    tmp_path: Path, tool_context: ToolContext
) -> None:
    tool = TerminalTool(sandbox_root=tmp_path, allow_network=False)

    result = tool.run(tool_context, "/usr/bin/curl --version")

    assert not result.success
    assert result.error is not None
    assert "disabled" in result.error.lower()


def test_terminal_allows_non_network_commands_when_disabled(
    tmp_path: Path, tool_context: ToolContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = TerminalTool(sandbox_root=tmp_path, allow_network=False)

    captured: dict[str, list[str]] = {}

    def fake_run(args, cwd, check, capture_output, text):  # type: ignore[no-untyped-def]
        captured["args"] = args
        return DummyCompletedProcess(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tool.run(tool_context, "ls")

    assert result.success
    assert captured["args"][0] == "ls"


def test_terminal_allows_network_when_enabled(
    tmp_path: Path, tool_context: ToolContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = TerminalTool(sandbox_root=tmp_path, allow_network=True)

    captured: dict[str, list[str]] = {}

    def fake_run(args, cwd, check, capture_output, text):  # type: ignore[no-untyped-def]
        captured["args"] = args
        return DummyCompletedProcess(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tool.run(tool_context, "curl --version")

    assert result.success
    assert captured["args"][0] == "curl"


def test_terminal_blocks_command_not_in_allowlist(tmp_path: Path, tool_context: ToolContext) -> None:
    tool = TerminalTool(
        sandbox_root=tmp_path,
        allow_network=True,
        network_allowlist=["curl"],
    )

    result = tool.run(tool_context, "wget http://example.com")

    assert not result.success
    assert result.error is not None
    assert "allowlist" in result.error.lower()


def test_terminal_allows_command_in_allowlist(
    tmp_path: Path, tool_context: ToolContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = TerminalTool(
        sandbox_root=tmp_path,
        allow_network=True,
        network_allowlist=["curl"],
    )

    captured: dict[str, list[str]] = {}

    def fake_run(args, cwd, check, capture_output, text):  # type: ignore[no-untyped-def]
        captured["args"] = args
        return DummyCompletedProcess(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = tool.run(tool_context, "curl http://example.com")

    assert result.success
    assert captured["args"][0] == "curl"


def test_allowlist_still_blocks_when_network_disabled(tmp_path: Path, tool_context: ToolContext) -> None:
    tool = TerminalTool(
        sandbox_root=tmp_path,
        allow_network=False,
        network_allowlist=["curl"],
    )

    result = tool.run(tool_context, "curl http://example.com")

    assert not result.success
    assert result.error is not None
    assert "disabled" in result.error.lower()
