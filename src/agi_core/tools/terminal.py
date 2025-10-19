"""Terminal execution tool."""
from __future__ import annotations

import logging
import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from .base import Tool, ToolContext, ToolResult

LOGGER = logging.getLogger(__name__)


class TerminalTool(Tool):
    """Executes shell commands within a sandbox."""

    name = "terminal.run"
    description = "Execute shell commands inside the configured sandbox directory."

    def __init__(self, sandbox_root: Path, allowed_binaries: Sequence[str] | None = None) -> None:
        self._sandbox_root = sandbox_root.resolve()
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        self._allowed_binaries = set(allowed_binaries or [])

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:
        command = " ".join(args)
        LOGGER.info("Executing command: %s", command)
        working_dir = Path(context.working_directory).resolve()
        if not str(working_dir).startswith(str(self._sandbox_root)):
            return ToolResult(success=False, output="", error="Working directory outside sandbox")

        if not command:
            return ToolResult(success=False, output="", error="No command provided")

        parts = shlex.split(command)
        if self._allowed_binaries and parts[0] not in self._allowed_binaries:
            return ToolResult(success=False, output="", error="Command not allowed")

        try:
            process = subprocess.run(
                parts,
                cwd=str(working_dir),
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            LOGGER.exception("Failed to execute command")
            return ToolResult(success=False, output="", error=str(exc))

        success = process.returncode == 0
        output = process.stdout.strip()
        error_output = process.stderr.strip() or None
        if success:
            LOGGER.debug("Command succeeded: %s", output)
        else:
            LOGGER.warning("Command failed (%s): %s", process.returncode, error_output)
        return ToolResult(success=success, output=output, error=error_output)
