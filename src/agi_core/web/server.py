from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from aiohttp import web, WSMsgType

from ..config import AgentConfig
from ..orchestration.agent_kernel import AgentKernel

LOGGER = logging.getLogger(__name__)


class WebChatServer:
    def __init__(self, config: AgentConfig, static_dir: Path) -> None:
        self._config = config
        self._static_dir = static_dir
        self._agent = AgentKernel(config)
        self._app = web.Application()
        self._app.add_routes([
            web.get('/ws', self._ws_handler),
            web.get('/health', self._health),
        ])
        self._app.add_routes([web.static('/', str(static_dir), show_index=True)])

    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def _ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Simple dialogue: receive user message, queue task, process once, return latest summary
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    text: str = data.get("message", "").strip()
                except Exception:
                    text = msg.data.strip()

                if not text:
                    await ws.send_json({"type": "error", "error": "empty_message"})
                    continue

                # Send to dialogue manager to queue task
                self._agent.dialogue.receive_input(text)

                # Run a single iteration
                self._agent.run_once()

                # Return last summary if available
                summary: Optional[str] = None
                if self._agent.state.last_task is not None:
                    # _summarize_execution is called internally; DialogueManager sent output
                    # For the web client, send a compact payload
                    summary = (
                        f"Task {self._agent.state.last_task.task_id}: "
                        f"{self._agent.state.last_task.description}"
                    )
                await ws.send_json({
                    "type": "ack",
                    "message": text,
                    "summary": summary,
                })

            elif msg.type == WSMsgType.ERROR:
                LOGGER.error("WebSocket error: %s", ws.exception())

        return ws

    def run(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        web.run_app(self._app, host=host, port=port)


def run_web(config: AgentConfig, static_dir: Path, host: str = "127.0.0.1", port: int = 8080) -> None:
    server = WebChatServer(config, static_dir)
    server.run(host=host, port=port)
