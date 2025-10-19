"""File read/write tool."""
from __future__ import annotations

import logging
from pathlib import Path

from .base import Tool, ToolContext, ToolResult

LOGGER = logging.getLogger(__name__)


class FileIOTool(Tool):
    """Tool for interacting with files inside the sandbox."""

    name = "file.io"
    description = "Read or write files in the sandboxed workspace."

    def __init__(self, sandbox_root: Path) -> None:
        self._sandbox_root = sandbox_root.resolve()
        self._sandbox_root.mkdir(parents=True, exist_ok=True)

    def run(self, context: ToolContext, *args: str, **kwargs: str) -> ToolResult:
        action = kwargs.get("action") or (args[0] if args else None)
        if action not in {"read", "write"}:
            return ToolResult(success=False, output="", error="Unsupported action")

        target = kwargs.get("path") or (args[1] if len(args) > 1 else None)
        if not target:
            return ToolResult(success=False, output="", error="Missing path")

        path = (Path(context.working_directory) / target).resolve()
        if not str(path).startswith(str(self._sandbox_root)):
            return ToolResult(success=False, output="", error="Path outside sandbox")

        if action == "read":
            if not path.exists():
                return ToolResult(success=False, output="", error="File not found")
            content = path.read_text(encoding="utf-8")
            LOGGER.debug("Read file %s", path)
            return ToolResult(success=True, output=content)

        # write
        data = kwargs.get("data") or (args[2] if len(args) > 2 else None)
        if data is None:
            return ToolResult(success=False, output="", error="Missing data for write")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(data), encoding="utf-8")
        LOGGER.debug("Wrote file %s", path)
        return ToolResult(success=True, output=f"Wrote {len(str(data))} characters")
