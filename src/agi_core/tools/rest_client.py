"""REST client tool for interacting with HTTP APIs."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional
from urllib.parse import urlparse

try:  # pragma: no cover - runtime dependency check
    import requests
except ImportError:  # pragma: no cover
    requests = None  # type: ignore[assignment]


class _RequestException(Exception):
    pass


RequestException = (
    requests.RequestException if requests is not None else _RequestException
)

from .base import Tool, ToolContext, ToolResult

LOGGER = logging.getLogger(__name__)


class RestClientTool(Tool):
    """Perform HTTP requests with sandbox-aware restrictions."""

    name = "rest_client"
    description = (
        "Send HTTP and GraphQL requests with JSON payloads, query parameters,"
        " and optional sandboxed persistence of responses."
    )

    def __init__(
        self,
        *,
        allow_network: bool,
        allowed_hosts: Iterable[str],
        default_headers: Optional[Dict[str, str]] = None,
        auth_token: Optional[str] = None,
        default_timeout: float = 10.0,
        sandbox_root: Path,
    ) -> None:
        self._allow_network = allow_network
        self._allowed_hosts = {host.lower() for host in allowed_hosts}
        self._default_headers = dict(default_headers or {})
        self._auth_token = auth_token
        self._timeout = default_timeout
        self._sandbox_root = Path(sandbox_root).resolve()

    # ------------------------------------------------------------------
    def run(self, context: ToolContext, *args: str, **_: str) -> ToolResult:
        if requests is None:
            return ToolResult(
                False,
                "",
                "The requests package is not installed; install it to enable REST access.",
            )

        if not self._allow_network:
            return ToolResult(False, "", "Network access is disabled for REST client")

        if not args:
            return ToolResult(False, "", "REST client expects a JSON instruction")

        try:
            payload = json.loads(args[0])
        except json.JSONDecodeError as exc:
            return ToolResult(False, "", f"Invalid REST instruction JSON: {exc}")

        url = payload.get("url")
        if not url:
            return ToolResult(False, "", "Missing required 'url' field")

        graphql_payload = payload.get("graphql")
        method = str(payload.get("method", "POST" if graphql_payload else "GET")).upper()
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"}:
            return ToolResult(False, "", f"Unsupported HTTP method: {method}")

        try:
            self._validate_url(url)
        except ValueError as exc:
            return ToolResult(False, "", str(exc))

        headers = {**self._default_headers, **payload.get("headers", {})}
        if graphql_payload:
            headers.setdefault("Content-Type", "application/json")

        if self._auth_token and not any(key.lower() == "authorization" for key in headers):
            headers.setdefault("Authorization", self._auth_token)

        request_kwargs = {
            "params": payload.get("params"),
            "json": payload.get("json"),
            "data": payload.get("data"),
            "timeout": payload.get("timeout", self._timeout),
        }

        if graphql_payload:
            query = graphql_payload.get("query")
            if not query:
                return ToolResult(False, "", "GraphQL payload requires a 'query' field")
            request_kwargs["json"] = {
                "query": query,
                "variables": graphql_payload.get("variables"),
                "operationName": graphql_payload.get("operation_name"),
            }
            request_kwargs["data"] = None
            method = "POST"

        save_path = payload.get("save_to")
        if save_path:
            try:
                destination = self._resolve_path(Path(save_path))
            except ValueError as exc:
                return ToolResult(False, "", str(exc))
        else:
            destination = None

        try:
            response = requests.request(method, url, headers=headers, **request_kwargs)
        except RequestException as exc:
            return ToolResult(False, "", f"Request failed: {exc}")

        content_preview = response.text[:4000]

        if destination is not None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(response.text, encoding=response.encoding or "utf-8")

        output = {
            "status_code": response.status_code,
            "reason": response.reason,
            "headers": dict(response.headers),
            "body_preview": content_preview,
            "saved_to": str(destination.relative_to(self._sandbox_root)) if destination else None,
            "graphql": bool(graphql_payload),
        }

        return ToolResult(True, json.dumps(output, indent=2))

    # ------------------------------------------------------------------
    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("REST client only supports http/https URLs")

        host = (parsed.hostname or "").lower()
        if host not in self._allowed_hosts:
            raise ValueError(f"Host '{host}' is not permitted for REST client usage")

    # ------------------------------------------------------------------
    def _resolve_path(self, candidate: Path) -> Path:
        resolved = (self._sandbox_root / candidate).resolve()
        if not resolved.is_relative_to(self._sandbox_root):
            raise ValueError("Response save path must remain within sandbox")
        return resolved
