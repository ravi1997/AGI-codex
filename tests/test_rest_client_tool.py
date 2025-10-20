"""Smoke tests for the REST client tool."""
from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import sys
import types
import urllib.error
import urllib.parse
import urllib.request
from unittest import TestCase

fake_requests = types.ModuleType("requests")


class _FakeResponse:
    def __init__(self, status: int, reason: str, headers: dict[str, str], text: str) -> None:
        self.status_code = status
        self.reason = reason
        self.headers = headers
        self.text = text
        self.encoding = "utf-8"


class _FakeRequestException(Exception):
    pass


def _request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    json: dict | None = None,
    data: str | bytes | None = None,
    timeout: float | None = None,
):
    headers = headers or {}
    if params:
        parsed = list(urllib.parse.urlparse(url))
        query = dict(urllib.parse.parse_qsl(parsed[4], keep_blank_values=True))
        query.update({str(k): str(v) for k, v in params.items()})
        parsed[4] = urllib.parse.urlencode(query)
        url = urllib.parse.urlunparse(parsed)

    payload = data
    if json is not None:
        payload = json_module.dumps(json).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}
    elif isinstance(data, str):
        payload = data.encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            text = resp.read().decode(charset)
            return _FakeResponse(resp.status, resp.reason, dict(resp.headers), text)
    except urllib.error.URLError as exc:  # pragma: no cover - network failure path
        raise _FakeRequestException(str(exc)) from exc


fake_requests.RequestException = _FakeRequestException
json_module = json
fake_requests.request = _request

sys.modules.setdefault("requests", fake_requests)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agi_core.tools.base import ToolContext
from agi_core.tools.rest_client import RestClientTool
import agi_core.tools.rest_client as rest_client_module

rest_client_module.requests = fake_requests  # type: ignore[attr-defined]
rest_client_module.RequestException = fake_requests.RequestException  # type: ignore[attr-defined]


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # type: ignore[override]
        payload = json.dumps({"message": "hello", "path": self.path}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):  # type: ignore[override]
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            data = {}
        message = (
            data.get("variables", {}).get("message")
            if isinstance(data.get("variables"), dict)
            else None
        )
        payload = json.dumps({"data": {"echo": message}}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):  # pragma: no cover - silence server logs
        return


def _start_server() -> tuple[HTTPServer, threading.Thread]:
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class RestClientToolTests(TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sandbox = Path(self._tmp.name)
        self.context = ToolContext(working_directory=str(self.sandbox))

    def test_get_request_and_save_response(self) -> None:
        server, thread = _start_server()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.addCleanup(lambda: thread.join(timeout=1))

        host, port = server.server_address
        url = f"http://{host}:{port}/status?source=test"

        tool = RestClientTool(
            allow_network=True,
            allowed_hosts=["127.0.0.1", "localhost"],
            default_headers={"User-Agent": "agi-core-tests"},
            sandbox_root=self.sandbox,
        )

        payload = {
            "method": "GET",
            "url": url,
            "save_to": "responses/status.json",
        }

        result = tool.run(self.context, json.dumps(payload))

        self.assertTrue(result.success, result.error)
        summary = json.loads(result.output)
        self.assertEqual(summary["status_code"], 200)
        self.assertIn("status", summary["body_preview"])
        self.assertEqual(summary["saved_to"], "responses/status.json")

        saved_file = self.sandbox / "responses" / "status.json"
        self.assertTrue(saved_file.exists())
        saved_payload = json.loads(saved_file.read_text(encoding="utf-8"))
        self.assertEqual(saved_payload["message"], "hello")

    def test_graphql_request(self) -> None:
        server, thread = _start_server()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        self.addCleanup(lambda: thread.join(timeout=1))

        host, port = server.server_address
        url = f"http://{host}:{port}/graphql"

        tool = RestClientTool(
            allow_network=True,
            allowed_hosts=["127.0.0.1", "localhost"],
            sandbox_root=self.sandbox,
        )

        payload = {
            "url": url,
            "graphql": {
                "query": "query Echo($message: String!) { echo(message: $message) }",
                "variables": {"message": "world"},
            },
        }

        result = tool.run(self.context, json.dumps(payload))

        self.assertTrue(result.success, result.error)
        summary = json.loads(result.output)
        self.assertTrue(summary["graphql"])
        self.assertEqual(summary["status_code"], 200)
        self.assertIn("world", summary["body_preview"])
