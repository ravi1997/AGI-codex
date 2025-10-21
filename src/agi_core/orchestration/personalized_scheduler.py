"""Personalized task scheduling utilities with pattern-based autonomous tasks."""
from __future__ import annotations

import heapq
import itertools
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Any

from ..config import SchedulerConfig
from .task_scheduler import TaskScheduler, ScheduledTask

LOGGER = logging.getLogger(__name__)


@dataclass(order=True)
class PersonalizedScheduledTask:
    """Enhanced scheduled task with personalization metadata."""
    
    priority: int
    created_at: datetime = field(compare=False)
    task_id: int = field(compare=False)
    description: str = field(compare=False)
    metadata: Dict[str, str] = field(default_factory=dict, compare=False)
    autonomous: bool = field(default=False, compare=False)
    # Personalization-specific fields
    user_preference_match: float = field(default=0.0, compare=False)  # How well it matches user preferences
    project_context: Dict[str, Any] = field(default_factory=dict, compare=False)  # Project-specific context
    execution_pattern: str = field(default="", compare=False)  # Pattern this task follows


class PersonalizedTaskScheduler:
    """Enhanced scheduler that learns from patterns and adapts to user preferences."""
    
    def __init__(self, config: SchedulerConfig) -> None:
        self._config = config
        self._counter = itertools.count()
        self._queue: List[PersonalizedScheduledTask] = []
        self._last_autonomous_proposal: Optional[datetime] = None
        self._learned_patterns: Dict[str, Any] = {}
        self._user_preferences: Dict[str, Any] = {}
        self._project_context: Dict[str, Any] = {}
    
    def set_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Set the user preferences for the scheduler."""
        self._user_preferences = preferences
        LOGGER.debug("Updated user preferences for scheduler")
    
    def set_project_context(self, context: Dict[str, Any]) -> None:
        """Set the project context for the scheduler."""
        self._project_context = context
        LOGGER.debug("Updated project context for scheduler")
    
    def learn_pattern(self, pattern_name: str, pattern_data: Dict[str, Any]) -> None:
        """Learn a new pattern for autonomous task generation."""
        self._learned_patterns[pattern_name] = pattern_data
        LOGGER.info("Learned new pattern: %s", pattern_name)
    
    def add_task(
        self,
        description: str,
        *,
        priority: int = 0,
        metadata: Optional[Dict[str, str]] = None,
        autonomous: bool = False,
        execution_pattern: str = "",
    ) -> int:
        """Add a task to the scheduler with personalization support."""
        task_id = next(self._counter)
        
        # Calculate how well this task matches user preferences
        preference_match = self._calculate_preference_match(description, metadata or {})
        
        task = PersonalizedScheduledTask(
            priority=-priority,
            created_at=datetime.utcnow(),
            task_id=task_id,
            description=description,
            metadata=metadata or {},
            autonomous=autonomous,
            user_preference_match=preference_match,
            project_context=dict(self._project_context),
            execution_pattern=execution_pattern,
        )
        heapq.heappush(self._queue, task)
        LOGGER.debug("Personalized task %s queued: %s (preference match: %.2f)", 
                    task_id, description, preference_match)
        return task_id
    
    def _calculate_preference_match(self, description: str, metadata: Dict[str, str]) -> float:
        """Calculate how well a task matches user preferences."""
        score = 0.0
        
        # Check if the task involves preferred tools
        if 'preferred_tool' in metadata:
            preferred_tool = metadata['preferred_tool']
            if preferred_tool in (self._user_preferences.get('preferred_tools', {}) or {}):
                score += 0.3
        
        # Check if the task matches common goal patterns
        goal_lower = description.lower()
        success_patterns = self._user_preferences.get('success_patterns', [])
        for pattern in success_patterns:
            if pattern.get('goal_pattern') and pattern['goal_pattern'] in goal_lower:
                score += 0.2
                break
        
        # Check if the task is related to current project context
        if self._project_context:
            for key, value in self._project_context.items():
                if str(value).lower() in goal_lower:
                    score += 0.2
                    break
        
        # Normalize score to 0-1 range
        return min(1.0, score)
    
    def pop_next(self) -> Optional[PersonalizedScheduledTask]:
        """Retrieve the highest-priority task, with preference for user-matching tasks."""
        if not self._queue:
            return None
        
        # Sort tasks by priority and user preference match
        # First by priority (higher priority first), then by preference match (higher match first)
        sorted_tasks = sorted(
            self._queue,
            key=lambda x: (-x.priority, -x.user_preference_match)
        )
        
        # Pop the highest priority task
        task = heapq.heappop(self._queue)
        LOGGER.debug("Personalized task %s dequeued", task.task_id)
        return task
    
    def should_propose_autonomous(self) -> bool:
        """Determine whether an autonomous task should be generated based on learned patterns."""
        if self._last_autonomous_proposal is None:
            return True
        
        # Adjust interval based on user interaction patterns
        interval = timedelta(seconds=self._config.autonomous_task_interval_sec)
        
        # If user has been interacting frequently, propose more autonomous tasks
        if self._user_preferences.get('interaction_style') == 'frequent':
            interval = timedelta(seconds=self._config.autonomous_task_interval_sec * 0.7)
        elif self._user_preferences.get('interaction_style') == 'infrequent':
            interval = timedelta(seconds=self._config.autonomous_task_interval_sec * 1.5)
        
        return datetime.utcnow() - self._last_autonomous_proposal >= interval
    
    def mark_autonomous_proposal(self) -> None:
        """Update timestamp of last autonomous proposal."""
        self._last_autonomous_proposal = datetime.utcnow()
    
    def pending_tasks(self) -> Iterable[PersonalizedScheduledTask]:
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
    
    def generate_autonomous_tasks(self) -> List[PersonalizedScheduledTask]:
        """Generate autonomous tasks based on learned patterns and user preferences."""
        tasks = []
        
        # Generate tasks based on learned patterns
        for pattern_name, pattern_data in self._learned_patterns.items():
            if self._should_generate_pattern_task(pattern_name, pattern_data):
                task = self._create_pattern_task(pattern_name, pattern_data)
                if task:
                    tasks.append(task)
        
        # Generate tasks based on project context
        if self._project_context:
            project_tasks = self._generate_project_tasks()
            tasks.extend(project_tasks)
        
        # Generate tasks based on user preferences
        preference_tasks = self._generate_preference_tasks()
        tasks.extend(preference_tasks)
        
        LOGGER.info("Generated %d autonomous tasks based on learned patterns", len(tasks))
        return tasks
    
    def _should_generate_pattern_task(self, pattern_name: str, pattern_data: Dict[str, Any]) -> bool:
        """Determine if a pattern-based task should be generated."""
        # Check if enough time has passed since last generation
        last_generated = pattern_data.get('last_generated')
        if last_generated:
            interval = pattern_data.get('generation_interval', 3600)  # Default to 1 hour
            if (datetime.utcnow() - datetime.fromisoformat(last_generated)).total_seconds() < interval:
                return False
        
        return True
    
    def _create_pattern_task(self, pattern_name: str, pattern_data: Dict[str, Any]) -> Optional[PersonalizedScheduledTask]:
        """Create a task based on a learned pattern."""
        description = pattern_data.get('description', f'Execute pattern: {pattern_name}')
        priority = pattern_data.get('priority', 1)
        metadata = pattern_data.get('metadata', {})
        
        task_id = next(self._counter)
        task = PersonalizedScheduledTask(
            priority=-priority,
            created_at=datetime.utcnow(),
            task_id=task_id,
            description=description,
            metadata=metadata,
            autonomous=True,
            user_preference_match=0.8,  # Pattern-based tasks are generally good matches
            project_context=dict(self._project_context),
            execution_pattern=pattern_name,
        )
        
        # Update last generation time
        pattern_data['last_generated'] = datetime.utcnow().isoformat()
        
        return task
    
    def _generate_project_tasks(self) -> List[PersonalizedScheduledTask]:
        """Generate tasks based on project context."""
        tasks = []
        
        # Check for common project maintenance tasks
        if 'project_type' in self._project_context:
            project_type = self._project_context['project_type']
            
            if project_type in ['python', 'javascript', 'typescript']:
                # Add common development tasks
                tasks.append(self._create_project_task(
                    f"Update {project_type} dependencies",
                    priority=2,
                    metadata={'category': 'maintenance', 'project_type': project_type}
                ))
                
                tasks.append(self._create_project_task(
                    f"Run {project_type} tests",
                    priority=3,
                    metadata={'category': 'testing', 'project_type': project_type}
                ))
        
        # Check for project-specific tasks
        if 'last_activity' in self._project_context:
            # If there was recent activity, suggest follow-up tasks
            last_activity = datetime.fromisoformat(self._project_context['last_activity'])
            if (datetime.utcnow() - last_activity).total_seconds() < 3600:  # Last hour
                tasks.append(self._create_project_task(
                    "Continue recent work",
                    priority=2,
                    metadata={'category': 'followup', 'context': 'recent_activity'}
                ))
        
        return tasks
    
    def _generate_preference_tasks(self) -> List[PersonalizedScheduledTask]:
        """Generate tasks based on user preferences."""
        tasks = []
        
        # Generate tasks for preferred tools
        preferred_tools = self._user_preferences.get('preferred_tools', {})
        for tool_name, usage_count in preferred_tools.items():
            if usage_count > 2:  # Only if used multiple times
                tasks.append(self._create_project_task(
                    f"Utilize preferred tool: {tool_name}",
                    priority=2,
                    metadata={'category': 'tool_usage', 'preferred_tool': tool_name}
                ))
        
        # Generate tasks based on success patterns
        success_patterns = self._user_preferences.get('success_patterns', [])
        if success_patterns:
            # Find the most recent successful pattern
            latest_pattern = success_patterns[-1] if success_patterns else None
            if latest_pattern:
                goal_pattern = latest_pattern.get('goal_pattern', 'general')
                tasks.append(self._create_project_task(
                    f"Continue {goal_pattern} work pattern",
                    priority=2,
                    metadata={'category': 'pattern_continuation', 'pattern': goal_pattern}
                ))
        
        return tasks
    
    def _create_project_task(self, description: str, priority: int, metadata: Dict[str, str]) -> PersonalizedScheduledTask:
        """Helper to create a project task."""
        task_id = next(self._counter)
        return PersonalizedScheduledTask(
            priority=-priority,
            created_at=datetime.utcnow(),
            task_id=task_id,
            description=description,
            metadata=metadata,
            autonomous=True,
            user_preference_match=0.7,  # Project-specific tasks are generally good matches
            project_context=dict(self._project_context),
            execution_pattern="project_context",
        )
    
    def get_adaptation_summary(self) -> Dict[str, Any]:
        """Get a summary of how the scheduler has adapted to user preferences."""
        return {
            'learned_patterns_count': len(self._learned_patterns),
            'user_preferences_keys': list(self._user_preferences.keys()),
            'project_context_keys': list(self._project_context.keys()),
            'pending_tasks_count': len(self._queue),
            'autonomous_interval': self._config.autonomous_task_interval_sec
        }