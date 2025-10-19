"""Dialogue management for CLI interactions."""
from __future__ import annotations

import logging
from typing import Callable, Optional

LOGGER = logging.getLogger(__name__)


class DialogueManager:
    """Simple dialogue manager for CLI mode."""

    def __init__(self) -> None:
        self._on_user_message: Optional[Callable[[str], None]] = None

    def register_user_message_handler(self, handler: Callable[[str], None]) -> None:
        """Register callback for user messages."""
        self._on_user_message = handler
        LOGGER.debug("User message handler registered")

    def receive_input(self, text: str) -> None:
        """Handle input from a user."""
        LOGGER.info("Received user input: %s", text)
        if self._on_user_message:
            self._on_user_message(text)
        else:
            LOGGER.warning("No handler registered for user messages")

    def send_output(self, text: str) -> None:
        """Emit output to the CLI."""
        LOGGER.info("Agent: %s", text)
        print(text)
