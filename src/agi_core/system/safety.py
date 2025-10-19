"""Safety guardrail utilities."""
from __future__ import annotations

import logging
from typing import List

LOGGER = logging.getLogger(__name__)


class SafetyGuard:
    """Enforces simple permission checks for plans."""

    def __init__(self, restricted_keywords: List[str] | None = None) -> None:
        self._restricted_keywords = set(restricted_keywords or ["rm -rf", "shutdown"])

    def approve_goal(self, goal: str) -> bool:
        lowered = goal.lower()
        for keyword in self._restricted_keywords:
            if keyword in lowered:
                LOGGER.warning("Goal rejected due to restricted keyword: %s", keyword)
                return False
        return True
