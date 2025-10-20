"""Browser automation tool powered by Playwright or Selenium."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urlparse

from .base import Tool, ToolContext, ToolResult

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - import is validated in runtime checks
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover - exercised when dependency missing
    sync_playwright = None  # type: ignore[assignment]
    PlaywrightError = RuntimeError  # type: ignore[assignment]
    PlaywrightTimeoutError = RuntimeError  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency for Selenium backend
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException as SeleniumTimeoutError
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError:  # pragma: no cover - handled gracefully when missing
    webdriver = None  # type: ignore[assignment]
    SeleniumTimeoutError = RuntimeError  # type: ignore[assignment]
    WebDriverException = RuntimeError  # type: ignore[assignment]
    By = None  # type: ignore[assignment]
    EC = None  # type: ignore[assignment]
    WebDriverWait = None  # type: ignore[assignment]


@dataclass
class BrowserAction:
    """Representation of a minimal browser action."""

    type: str
    selector: Optional[str] = None
    value: Optional[str] = None


class BrowserAutomationTool(Tool):
    """Execute simple headless browser workflows via Playwright or Selenium."""

    name = "browser_automation"
    description = (
        "Automate a browser session using Playwright or Selenium to navigate"
        " sandboxed content, perform limited interactions, capture"
        " screenshots, and extract text."
    )

    def __init__(
        self,
        *,
        sandbox_root: Path,
        allow_network: bool,
        allowed_origins: Iterable[str],
        headless: bool = True,
        default_timeout_ms: int = 10_000,
        backend: str = "playwright",
    ) -> None:
        self._sandbox_root = Path(sandbox_root).resolve()
        self._allow_network = allow_network
        self._allowed_origins: List[str] = list(allowed_origins)
        self._headless = headless
        self._timeout_ms = default_timeout_ms
        self._backend = backend.lower()

    # ------------------------------------------------------------------
    def run(self, context: ToolContext, *args: str, **_: str) -> ToolResult:
        if not args:
            return ToolResult(False, "", "Browser instructions must be supplied as JSON")

        try:
            payload = json.loads(args[0])
        except json.JSONDecodeError as exc:
            return ToolResult(False, "", f"Invalid browser instruction JSON: {exc}")

        url = payload.get("url")
        if not url:
            return ToolResult(False, "", "Missing required 'url' field")

        try:
            normalized_url = self._validate_url(url)
        except ValueError as exc:
            return ToolResult(False, "", str(exc))

        wait_for = payload.get("wait_for_selector")
        extract_selector = payload.get("extract_text")
        screenshot_path = payload.get("screenshot")
        try:
            actions = [BrowserAction(**item) for item in payload.get("actions", [])]
        except TypeError as exc:
            return ToolResult(False, "", f"Invalid browser action payload: {exc}")

        screenshot_target: Optional[Path] = None
        if screenshot_path:
            screenshot_target = self._resolve_path(Path(screenshot_path))

        LOGGER.info("Running browser automation (%s) against %s", self._backend, normalized_url)

        if self._backend == "playwright":
            return self._run_playwright(
                normalized_url,
                wait_for,
                extract_selector,
                screenshot_target,
                actions,
            )
        if self._backend == "selenium":
            return self._run_selenium(
                normalized_url,
                wait_for,
                extract_selector,
                screenshot_target,
                actions,
            )

        return ToolResult(False, "", f"Unknown browser backend: {self._backend}")

    # ------------------------------------------------------------------
    def _run_playwright(
        self,
        url: str,
        wait_for: Optional[str],
        extract_selector: Optional[str],
        screenshot_target: Optional[Path],
        actions: List[BrowserAction],
    ) -> ToolResult:
        if sync_playwright is None:
            return ToolResult(
                success=False,
                output="",
                error=(
                    "playwright is not installed. Install the dependency and its"
                    " browsers to use the browser_automation tool."
                ),
            )

        extracted_text: Optional[str] = None

        try:
            with sync_playwright() as playwright:  # type: ignore[operator]
                browser = playwright.chromium.launch(headless=self._headless)
                page = browser.new_page()
                page.set_default_timeout(self._timeout_ms)
                page.goto(url, wait_until="load", timeout=self._timeout_ms)

                if wait_for:
                    page.wait_for_selector(wait_for, timeout=self._timeout_ms)

                for action in actions:
                    self._execute_action(page, action)

                if extract_selector:
                    extracted_text = page.inner_text(extract_selector).strip()

                if screenshot_target is not None:
                    screenshot_target.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot_target), full_page=True)

                browser.close()
        except PlaywrightTimeoutError as exc:
            return ToolResult(False, "", f"Playwright timeout: {exc}")
        except PlaywrightError as exc:
            return ToolResult(False, "", f"Playwright error: {exc}")

        fragments = [f"Navigated to {url}"]
        if extracted_text is not None:
            fragments.append(f"Extracted text: {extracted_text}")
        if screenshot_target is not None:
            fragments.append(
                f"Screenshot stored at {screenshot_target.relative_to(self._sandbox_root)}"
            )

        return ToolResult(True, "\n".join(fragments))

    # ------------------------------------------------------------------
    def _run_selenium(
        self,
        url: str,
        wait_for: Optional[str],
        extract_selector: Optional[str],
        screenshot_target: Optional[Path],
        actions: List[BrowserAction],
    ) -> ToolResult:
        if webdriver is None or By is None or WebDriverWait is None or EC is None:
            return ToolResult(
                False,
                "",
                "selenium is not installed. Install selenium and a compatible driver"
                " to use the browser_automation tool with the selenium backend.",
            )

        extracted_text: Optional[str] = None
        timeout_sec = max(self._timeout_ms / 1000.0, 0.1)

        options = None
        if hasattr(webdriver, "ChromeOptions"):
            options = webdriver.ChromeOptions()
            if self._headless:
                options.add_argument("--headless=new")
        kwargs = {"options": options} if options is not None else {}

        try:
            browser = webdriver.Chrome(**kwargs)  # type: ignore[call-arg]
        except WebDriverException as exc:
            return ToolResult(False, "", f"Failed to start Selenium driver: {exc}")

        try:
            if hasattr(browser, "set_page_load_timeout"):
                browser.set_page_load_timeout(timeout_sec)
            browser.get(url)

            if wait_for:
                WebDriverWait(browser, timeout_sec).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
                )

            for action in actions:
                self._execute_selenium_action(browser, action)

            if extract_selector:
                element = browser.find_element(By.CSS_SELECTOR, extract_selector)
                extracted_text = element.text.strip()

            if screenshot_target is not None:
                screenshot_target.parent.mkdir(parents=True, exist_ok=True)
                browser.save_screenshot(str(screenshot_target))
        except SeleniumTimeoutError as exc:
            return ToolResult(False, "", f"Selenium timeout: {exc}")
        except WebDriverException as exc:
            return ToolResult(False, "", f"Selenium error: {exc}")
        finally:
            browser.quit()

        fragments = [f"Navigated to {url}"]
        if extracted_text is not None:
            fragments.append(f"Extracted text: {extracted_text}")
        if screenshot_target is not None:
            fragments.append(
                f"Screenshot stored at {screenshot_target.relative_to(self._sandbox_root)}"
            )

        return ToolResult(True, "\n".join(fragments))

    # ------------------------------------------------------------------
    def _validate_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        if parsed.scheme == "file":
            candidate = Path(parsed.path or parsed.netloc).resolve()
            if not candidate.is_file():
                raise ValueError(f"Sandbox file not found: {candidate}")
            if not candidate.is_relative_to(self._sandbox_root):
                raise ValueError("Browser navigation outside sandbox is not permitted")
            return candidate.as_uri()

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme for browser automation: {parsed.scheme}")

        if not self._allow_network:
            raise ValueError("Network browsing is disabled by configuration")

        if self._allowed_origins:
            if not any(raw_url.startswith(prefix) for prefix in self._allowed_origins):
                raise ValueError("URL is not permitted by the allowed_origins list")

        return raw_url

    # ------------------------------------------------------------------
    def _resolve_path(self, candidate: Path) -> Path:
        resolved = (self._sandbox_root / candidate).resolve()
        if not resolved.is_relative_to(self._sandbox_root):
            raise ValueError("Screenshot path must remain within sandbox")
        return resolved

    # ------------------------------------------------------------------
    @staticmethod
    def _execute_action(page, action: BrowserAction) -> None:  # pragma: no cover - thin wrapper
        """Execute a constrained action against a Playwright page."""

        if action.type == "click" and action.selector:
            page.click(action.selector)
        elif action.type == "fill" and action.selector is not None:
            page.fill(action.selector, action.value or "")
        elif action.type == "press" and action.selector and action.value:
            page.press(action.selector, action.value)
        else:
            LOGGER.warning("Skipping unsupported browser action: %s", action)

    # ------------------------------------------------------------------
    @staticmethod
    def _execute_selenium_action(browser, action: BrowserAction) -> None:  # pragma: no cover - thin wrapper
        if By is None:
            return

        if action.selector is None:
            LOGGER.warning("Skipping Selenium action missing selector: %s", action)
            return

        try:
            element = browser.find_element(By.CSS_SELECTOR, action.selector)
        except WebDriverException as exc:  # pragma: no cover - runtime failure path
            LOGGER.warning("Selenium action failed (%s): %s", action.type, exc)
            return

        if action.type == "click":
            element.click()
        elif action.type == "fill":
            element.clear()
            element.send_keys(action.value or "")
        elif action.type == "press" and action.value:
            element.send_keys(action.value)
        else:
            LOGGER.warning("Skipping unsupported Selenium action: %s", action)
