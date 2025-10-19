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

    NETWORK_COMMANDS = {
        "curl",
        "wget",
        "ssh",
        "scp",
        "sftp",
        "ftp",
        "telnet",
        "nc",
        "netcat",
        "ping",
        "dig",
        "nslookup",
    }

    def __init__(
        self,
        sandbox_root: Path,
        *,
        allow_network: bool = False,
        network_allowlist: Sequence[str] | None = None,
        allowed_binaries: Sequence[str] | None = None,
    ) -> None:
        self._sandbox_root = sandbox_root.resolve()
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        self._allow_network = allow_network
        self._network_allowlist = {
            Path(binary).name for binary in (network_allowlist or [])
        }
        self._allowed_binaries = {Path(binary).name for binary in (allowed_binaries or [])}

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:
        command = " ".join(args)
        LOGGER.info("Executing command: %s", command)
        working_dir = Path(context.working_directory).resolve()
        if not str(working_dir).startswith(str(self._sandbox_root)):
            return ToolResult(success=False, output="", error="Working directory outside sandbox")

        if not command:
            return ToolResult(success=False, output="", error="No command provided")

        parts = shlex.split(command)
        base_command = Path(parts[0]).name

        if self._allowed_binaries and base_command not in self._allowed_binaries:
            return ToolResult(success=False, output="", error="Command not allowed")

        if not self._allow_network and base_command in self.NETWORK_COMMANDS:
            return ToolResult(
                success=False,
                output="",
                error="Networking commands are disabled by configuration",
            )

        if (
            self._allow_network
            and self._network_allowlist
            and base_command in self.NETWORK_COMMANDS
            and base_command not in self._network_allowlist
        ):
            return ToolResult(
                success=False,
                output="",
                error="Networking command not allowed by allowlist",
            )

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
