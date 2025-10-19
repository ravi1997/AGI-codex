"""Task scheduling utilities."""
from __future__ import annotations

import heapq
import itertools
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional

from ..config import SchedulerConfig

LOGGER = logging.getLogger(__name__)


@dataclass(order=True)
class ScheduledTask:
    """Internal representation of a scheduled task."""

    priority: int
    created_at: datetime = field(compare=False)
    task_id: int = field(compare=False)
    description: str = field(compare=False)
    metadata: Dict[str, str] = field(default_factory=dict, compare=False)
    autonomous: bool = field(default=False, compare=False)


class TaskScheduler:
    """Priority-based task scheduler."""

    def __init__(self, config: SchedulerConfig) -> None:
        self._config = config
        self._counter = itertools.count()
        self._queue: List[ScheduledTask] = []
        self._last_autonomous_proposal: Optional[datetime] = None

    def add_task(
        self,
        description: str,
        *,
        priority: int = 0,
        metadata: Optional[Dict[str, str]] = None,
        autonomous: bool = False,
    ) -> int:
        """Add a task to the scheduler."""
        task_id = next(self._counter)
        task = ScheduledTask(
            priority=-priority,
            created_at=datetime.utcnow(),
            task_id=task_id,
            description=description,
            metadata=metadata or {},
            autonomous=autonomous,
        )
        heapq.heappush(self._queue, task)
        LOGGER.debug("Task %s queued: %s", task_id, description)
        return task_id

    def pop_next(self) -> Optional[ScheduledTask]:
        """Retrieve the highest-priority task."""
        if not self._queue:
            return None
        task = heapq.heappop(self._queue)
        LOGGER.debug("Task %s dequeued", task.task_id)
        return task

    def should_propose_autonomous(self) -> bool:
        """Determine whether an autonomous task should be generated."""
        if self._last_autonomous_proposal is None:
            return True
        interval = timedelta(seconds=self._config.autonomous_task_interval_sec)
        return datetime.utcnow() - self._last_autonomous_proposal >= interval

    def mark_autonomous_proposal(self) -> None:
        """Update timestamp of last autonomous proposal."""
        self._last_autonomous_proposal = datetime.utcnow()

    def pending_tasks(self) -> Iterable[ScheduledTask]:
        """Return snapshot of pending tasks."""
        return list(self._queue)

    @property
    def autonomous_interval(self) -> int:
        """Return the current autonomous task interval in seconds."""

        return int(self._config.autonomous_task_interval_sec)

    def update_autonomous_interval(self, seconds: int) -> None:
        """Dynamically adjust the autonomous task cadence."""

        seconds = max(1, int(seconds))
        if seconds == self._config.autonomous_task_interval_sec:
            return

        self._config.autonomous_task_interval_sec = seconds
        LOGGER.info("Autonomous task interval updated to %s seconds", seconds)
