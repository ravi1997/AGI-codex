"""Smoke tests for the Playwright-backed browser tool."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
import sys
from typing import Dict
import types
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

    def test_selenium_backend_extracts_text(self) -> None:
        tool = BrowserAutomationTool(
            sandbox_root=self.sandbox,
            allow_network=False,
            allowed_origins=[],
            backend="selenium",
        )

        payload = {
            "url": self.html_path.as_uri(),
            "extract_text": "#body",
            "screenshot": "captures/selenium.png",
        }

        html_path = self.html_path

        class FakeChromeOptions:
            def __init__(self) -> None:
                self.arguments: list[str] = []

            def add_argument(self, argument: str) -> None:  # pragma: no cover - trivial setter
                self.arguments.append(argument)

        class FakeElement:
            def __init__(self, text: str) -> None:
                self.text = text

            def click(self) -> None:  # pragma: no cover - noop
                pass

            def clear(self) -> None:  # pragma: no cover - noop
                pass

            def send_keys(self, value: str) -> None:  # pragma: no cover - noop
                self.text = value

        class FakeBrowser:
            def __init__(self) -> None:
                self._last_url: str | None = None

            def set_page_load_timeout(self, timeout: float) -> None:  # pragma: no cover - noop
                self._timeout = timeout

            def get(self, url: str) -> None:
                self._last_url = url

            def find_element(self, by: str, selector: str) -> FakeElement:
                content = html_path.read_text(encoding="utf-8")
                return FakeElement("Hello Selenium" if "Hello" in content else selector)

            def save_screenshot(self, path: str) -> None:
                Path(path).write_bytes(b"selenium-image")

            def quit(self) -> None:  # pragma: no cover - noop
                pass

        fake_webdriver = types.SimpleNamespace(
            Chrome=lambda **_: FakeBrowser(),
            ChromeOptions=FakeChromeOptions,
        )

        fake_by = types.SimpleNamespace(CSS_SELECTOR="css")

        class FakeWebDriverWait:
            def __init__(self, *_args, **_kwargs) -> None:
                pass

            def until(self, method):  # pragma: no cover - unused in this test
                return method(FakeBrowser())

        fake_ec = types.SimpleNamespace(
            presence_of_element_located=lambda *_args, **_kwargs: (lambda driver: driver)
        )

        with patch.multiple(
            "agi_core.tools.browser",
            webdriver=fake_webdriver,
            By=fake_by,
            WebDriverWait=FakeWebDriverWait,
            EC=fake_ec,
            SeleniumTimeoutError=RuntimeError,
            WebDriverException=RuntimeError,
        ):
            result = tool.run(self.context, json.dumps(payload))

        self.assertTrue(result.success, result.error)
        self.assertIn("Extracted text", result.output)

        screenshot_path = self.sandbox / "captures" / "selenium.png"
        self.assertTrue(screenshot_path.exists())
        self.assertGreater(screenshot_path.stat().st_size, 0)
