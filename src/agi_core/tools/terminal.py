"""Terminal execution tool."""
from __future__ import annotations

import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .base import BaseTool, ToolContext, ToolResult, ToolError

LOGGER = logging.getLogger(__name__)


DEFAULT_NETWORK_BINARIES = {
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


@dataclass(frozen=True)
class TerminalNetworkPolicy:
    """Captures networking rules for ``TerminalTool`` invocations."""

    allow_network: bool
    allowlist: frozenset[str]
    denylist: frozenset[str]

    @staticmethod
    def _normalize(values: Sequence[str]) -> frozenset[str]:
        return frozenset(Path(value).name for value in values)

    @classmethod
    def offline(
        cls, denylist: Sequence[str] | None = None
    ) -> "TerminalNetworkPolicy":
        """Create a policy that blocks obvious networking binaries."""

        commands = denylist or DEFAULT_NETWORK_BINARIES
        return cls(False, frozenset(), cls._normalize(commands))

    @classmethod
    def online(
        cls, allowlist: Sequence[str] | None = None
    ) -> "TerminalNetworkPolicy":
        """Create a policy that optionally restricts networking binaries."""

        return cls(True, cls._normalize(allowlist or []), frozenset())


class TerminalTool(BaseTool):
    """Executes shell commands within a sandbox."""

    def __init__(
        self,
        sandbox_root: Path,
        *,
        network_policy: TerminalNetworkPolicy | None = None,
        allow_network: bool = False,
        network_allowlist: Sequence[str] | None = None,
        allowed_binaries: Sequence[str] | None = None,
    ) -> None:
        super().__init__("terminal.run", "Execute shell commands inside the configured sandbox directory.")
        self._sandbox_root = sandbox_root.resolve()
        self._sandbox_root.mkdir(parents=True, exist_ok=True)
        if network_policy is None:
            network_policy = (
                TerminalNetworkPolicy.online(network_allowlist)
                if allow_network
                else TerminalNetworkPolicy.offline()
            )
        self._network_policy = network_policy
        self._allowed_binaries = {
            Path(binary).name for binary in (allowed_binaries or [])
        }
        self.NETWORK_COMMANDS = DEFAULT_NETWORK_BINARIES

    def _run(self, *args: str, **kwargs: str) -> str:
        command = " ".join(args)
        if 'working_dir' in kwargs:
            working_dir = Path(kwargs['working_dir']).resolve()
        else:
            # Default to current directory or sandbox root
            working_dir = self._sandbox_root
            
        LOGGER.info("Executing command: %s", command)
        
        if not str(working_dir).startswith(str(self._sandbox_root)):
            raise ToolError("Working directory outside sandbox")

        if not command:
            raise ToolError("No command provided")

        parts = shlex.split(command)
        base_command = Path(parts[0]).name

        if self._allowed_binaries and base_command not in self._allowed_binaries:
            raise ToolError("Command not allowed")

        policy = self._network_policy
        if not policy.allow_network and base_command in (
            policy.denylist or self.NETWORK_COMMANDS
        ):
            raise ToolError("Networking commands are disabled by configuration")

        if (
            policy.allow_network
            and policy.allowlist
            and base_command in self.NETWORK_COMMANDS
            and base_command not in policy.allowlist
        ):
            raise ToolError("Networking command not allowed by allowlist")

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
            raise ToolError(str(exc))

        success = process.returncode == 0
        output = process.stdout.strip()
        error_output = process.stderr.strip() or None
        if success:
            LOGGER.debug("Command succeeded: %s", output)
            return output
        else:
            LOGGER.warning("Command failed (%s): %s", process.returncode, error_output)
            raise ToolError(f"Command failed with return code {process.returncode}: {error_output}")
