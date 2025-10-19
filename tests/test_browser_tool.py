"""Smoke tests for the Playwright-backed browser tool."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys
from typing import Dict
from unittest import TestCase
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agi_core.tools.base import ToolContext
from agi_core.tools.browser import BrowserAutomationTool


class DummyPage:
    """Minimal Playwright page stub used in tests."""

    def __init__(self) -> None:
        self._content: Dict[str, str] = {}
        self._screenshot_path: Path | None = None

    def set_default_timeout(self, timeout: int) -> None:  # pragma: no cover - noop
        self._timeout = timeout

    def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
        path = Path(url.removeprefix("file://"))
        self._content["body"] = path.read_text(encoding="utf-8")

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> None:  # pragma: no cover - noop
        self._waited_selector = selector

    def inner_text(self, selector: str) -> str:
        return self._content.get(selector.lstrip("#"), self._content.get("body", ""))

    def click(self, selector: str) -> None:  # pragma: no cover - noop
        self._clicked = selector

    def fill(self, selector: str, value: str) -> None:  # pragma: no cover - noop
        self._filled = (selector, value)

    def press(self, selector: str, value: str) -> None:  # pragma: no cover - noop
        self._pressed = (selector, value)

    def screenshot(self, path: str, full_page: bool = True) -> None:
        target = Path(path)
        target.write_bytes(b"fake-image")
        self._screenshot_path = target


class DummyBrowser:
    def __init__(self, page: DummyPage) -> None:
        self._page = page

    def new_page(self) -> DummyPage:
        return self._page

    def close(self) -> None:  # pragma: no cover - noop
        pass


class DummyPlaywright:
    def __init__(self, page: DummyPage) -> None:
        self._page = page
        self.chromium = self

    def launch(self, headless: bool = True) -> DummyBrowser:  # pragma: no cover - called indirectly
        return DummyBrowser(self._page)

    def __enter__(self) -> "DummyPlaywright":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # pragma: no cover - noop
        pass


class BrowserAutomationToolTests(TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.sandbox = Path(self._tmp.name)
        self.context = ToolContext(working_directory=str(self.sandbox))

        self.html_path = self.sandbox / "page.html"
        self.html_path.write_text("<html><body id='body'>Hello Sandbox</body></html>", encoding="utf-8")

    def test_extracts_text_and_writes_screenshot(self) -> None:
        tool = BrowserAutomationTool(
            sandbox_root=self.sandbox,
            allow_network=False,
            allowed_origins=[],
        )

        payload = {
            "url": self.html_path.as_uri(),
            "extract_text": "#body",
            "screenshot": "captures/page.png",
        }

        dummy_page = DummyPage()

        def fake_sync_playwright() -> DummyPlaywright:
            return DummyPlaywright(dummy_page)

        with patch("agi_core.tools.browser.sync_playwright", fake_sync_playwright):
            result = tool.run(self.context, json.dumps(payload))

        self.assertTrue(result.success, result.error)
        self.assertIn("Extracted text", result.output)

        screenshot_path = self.sandbox / "captures" / "page.png"
        self.assertTrue(screenshot_path.exists())
        self.assertGreater(screenshot_path.stat().st_size, 0)
