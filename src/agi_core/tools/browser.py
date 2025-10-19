"""Browser automation tool powered by Playwright."""
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


@dataclass
class BrowserAction:
    """Representation of a minimal browser action."""

    type: str
    selector: Optional[str] = None
    value: Optional[str] = None


class BrowserAutomationTool(Tool):
    """Execute simple headless browser workflows via Playwright."""

    name = "browser_automation"
    description = (
        "Launch a headless Chromium instance to open sandboxed pages, perform"
        " limited interactions, capture screenshots, and extract text."
    )

    def __init__(
        self,
        *,
        sandbox_root: Path,
        allow_network: bool,
        allowed_origins: Iterable[str],
        headless: bool = True,
        default_timeout_ms: int = 10_000,
    ) -> None:
        self._sandbox_root = Path(sandbox_root).resolve()
        self._allow_network = allow_network
        self._allowed_origins: List[str] = list(allowed_origins)
        self._headless = headless
        self._timeout_ms = default_timeout_ms

    # ------------------------------------------------------------------
    def run(self, context: ToolContext, *args: str, **_: str) -> ToolResult:
        if sync_playwright is None:
            return ToolResult(
                success=False,
                output="",
                error=(
                    "playwright is not installed. Install the dependency and its"
                    " browsers to use the browser_automation tool."
                ),
            )

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

        extracted_text: Optional[str] = None

        LOGGER.info("Running browser automation against %s", normalized_url)

        try:
            with sync_playwright() as playwright:  # type: ignore[operator]
                browser = playwright.chromium.launch(headless=self._headless)
                page = browser.new_page()
                page.set_default_timeout(self._timeout_ms)
                page.goto(normalized_url, wait_until="load", timeout=self._timeout_ms)

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

        fragments = [f"Navigated to {normalized_url}"]
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
