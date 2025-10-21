"""File read/write tool."""
from __future__ import annotations

import logging
from pathlib import Path

from .base import BaseTool, ToolContext, ToolResult, ToolError

LOGGER = logging.getLogger(__name__)


class FileIOTool(BaseTool):
    """Tool for interacting with files inside the sandbox."""

    def __init__(self, sandbox_root: Path) -> None:
        super().__init__("file.io", "Read or write files in the sandboxed workspace.")
        self._sandbox_root = sandbox_root.resolve()
        self._sandbox_root.mkdir(parents=True, exist_ok=True)

    def _run(self, *args: str, **kwargs: str) -> str:
        action = kwargs.get("action") or (args[0] if args else None)
        if action not in {"read", "write"}:
            raise ToolError("Unsupported action")

        target = kwargs.get("path") or (args[1] if len(args) > 1 else None)
        if not target:
            raise ToolError("Missing path")

        path = Path(target).resolve()
        if not str(path).startswith(str(self._sandbox_root)):
            raise ToolError("Path outside sandbox")

        if action == "read":
            if not path.exists():
                raise ToolError("File not found")
            content = path.read_text(encoding="utf-8")
            LOGGER.debug("Read file %s", path)
            return content

        # write
        data = kwargs.get("data") or (args[2] if len(args) > 2 else None)
        if data is None:
            raise ToolError("Missing data for write")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(data), encoding="utf-8")
        LOGGER.debug("Wrote file %s", path)
        return f"Wrote {len(str(data))} characters"
