"""Personalized feedback collection utilities with user preference learning."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Sequence, Optional

from ..config import LearningConfig
from ..reasoning.planner import Plan
from ..tools.base import ToolResult

LOGGER = logging.getLogger(__name__)


@dataclass
class UserPreferenceProfile:
    """Captures and maintains user preferences and working style."""
    
    preferred_tools: Dict[str, int]  # tool name -> usage count
    success_patterns: List[Dict[str, Any]]  # successful execution patterns
    failure_patterns: List[Dict[str, Any]]  # failure patterns to avoid
    time_preferences: Dict[str, float]  # preferred execution times/durations
    project_preferences: Dict[str, Any]  # project-specific preferences
    interaction_style: str  # how user likes to interact
    feedback_score: float  # overall satisfaction score
    last_updated: datetime


class PersonalizedFeedbackCollector:
    """Enhanced feedback collection with user preference learning capabilities."""
    
    def __init__(self, config: LearningConfig) -> None:
        self._path = config.feedback_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._max_history = config.max_feedback_history
        self._history: List[Dict[str, Any]] = []
        self._user_preferences = UserPreferenceProfile(
            preferred_tools={},
            success_patterns=[],
            failure_patterns=[],
            time_preferences={},
            project_preferences={},
            interaction_style="default",
            feedback_score=0.0,
            last_updated=datetime.utcnow()
        )
        self._load()
    
    def _load(self) -> None:
        if not self._path.exists():
            LOGGER.debug("No existing feedback file at %s", self._path)
            return
        
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            LOGGER.warning("Failed to load feedback history (%s); starting fresh", exc)
            return
        
        self._history = list(payload.get("history", []))[-self._max_history :]
        preferences_data = payload.get("user_preferences", {})
        if preferences_data:
            self._load_preferences(preferences_data)
        
        LOGGER.info("Loaded %d feedback entries and user preferences", len(self._history))
    
    def _load_preferences(self, data: Dict[str, Any]) -> None:
        """Load user preference profile from data."""
        self._user_preferences.preferred_tools = data.get("preferred_tools", {})
        self._user_preferences.success_patterns = data.get("success_patterns", [])
        self._user_preferences.failure_patterns = data.get("failure_patterns", [])
        self._user_preferences.time_preferences = data.get("time_preferences", {})
        self._user_preferences.project_preferences = data.get("project_preferences", {})
        self._user_preferences.interaction_style = data.get("interaction_style", "default")
        self._user_preferences.feedback_score = data.get("feedback_score", 0.0)
        last_updated_str = data.get("last_updated")
        if last_updated_str:
            self._user_preferences.last_updated = datetime.fromisoformat(last_updated_str)
    
    def _persist(self) -> None:
        payload = {
            "history": self._history[-self._max_history :],
            "user_preferences": {
                "preferred_tools": self._user_preferences.preferred_tools,
                "success_patterns": self._user_preferences.success_patterns,
                "failure_patterns": self._user_preferences.failure_patterns,
                "time_preferences": self._user_preferences.time_preferences,
                "project_preferences": self._user_preferences.project_preferences,
                "interaction_style": self._user_preferences.interaction_style,
                "feedback_score": self._user_preferences.feedback_score,
                "last_updated": self._user_preferences.last_updated.isoformat(),
            }
        }
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        LOGGER.debug("Persisted feedback history and preferences (%d entries)", len(self._history))
    
    @property
    def user_preferences(self) -> UserPreferenceProfile:
        return self._user_preferences
    
    def record_run(
        self,
        *,
        task_id: str,
        goal: str,
        success: bool,
        plan: Plan,
        results: Sequence[ToolResult],
        telemetry: Dict[str, float],
        user_feedback: Optional[str] = None,
        user_satisfaction: Optional[float] = None,
        project_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record the outcome of a completed run with enhanced user preference tracking."""
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": task_id,
            "goal": goal,
            "success": success,
            "context_summary": plan.context_summary,
            "telemetry": telemetry,
            "user_feedback": user_feedback,
            "user_satisfaction": user_satisfaction,
            "project_context": project_context,
            "steps": [
                {
                    "name": step.name,
                    "tool": step.tool,
                    "description": step.description,
                    "args": list(step.args),
                    "kwargs": dict(step.kwargs),
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
                for step, result in zip(plan.steps, results)
            ],
        }
        
        self._history.append(entry)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]
        
        # Update user preferences based on this run
        self._update_preferences(entry, user_feedback, user_satisfaction, project_context)
        
        self._persist()
        LOGGER.debug(
            "Recorded run for task %s (success=%s). Updated preferences.",
            task_id,
            success,
        )
        return entry
    
    def _update_preferences(
        self,
        entry: Dict[str, Any],
        user_feedback: Optional[str],
        user_satisfaction: Optional[float],
        project_context: Optional[Dict[str, Any]]
    ) -> None:
        """Update user preferences based on the execution result."""
        
        # Update preferred tools based on successful usage
        for step in entry["steps"]:
            if step["tool"] and step["success"]:
                tool_name = step["tool"]
                self._user_preferences.preferred_tools[tool_name] = \
                    self._user_preferences.preferred_tools.get(tool_name, 0) + 1
        
        # Update success/failure patterns
        if entry["success"]:
            self._user_preferences.success_patterns.append({
                "goal_pattern": self._extract_goal_pattern(entry["goal"]),
                "tool_sequence": [step["tool"] for step in entry["steps"] if step["tool"]],
                "context": entry["context_summary"],
                "timestamp": entry["timestamp"]
            })
        else:
            self._user_preferences.failure_patterns.append({
                "goal_pattern": self._extract_goal_pattern(entry["goal"]),
                "tool_sequence": [step["tool"] for step in entry["steps"] if step["tool"]],
                "context": entry["context_summary"],
                "timestamp": entry["timestamp"]
            })
        
        # Update project preferences
        if project_context:
            for key, value in project_context.items():
                self._user_preferences.project_preferences[key] = value
        
        # Update satisfaction score if provided
        if user_satisfaction is not None:
            self._user_preferences.feedback_score = user_satisfaction
        
        # Update last updated timestamp
        self._user_preferences.last_updated = datetime.utcnow()
    
    def _extract_goal_pattern(self, goal: str) -> str:
        """Extract a pattern from the goal for categorization."""
        goal_lower = goal.lower()
        if any(keyword in goal_lower for keyword in ["file", "directory", "create", "read", "write"]):
            return "file_operations"
        elif any(keyword in goal_lower for keyword in ["code", "program", "function", "debug"]):
            return "code_operations"
        elif any(keyword in goal_lower for keyword in ["web", "browser", "url", "page"]):
            return "web_operations"
        elif any(keyword in goal_lower for keyword in ["system", "process", "memory", "cpu"]):
            return "system_operations"
        else:
            return "general"
    
    def get_preferred_tool_for_task(self, task_type: str) -> Optional[str]:
        """Get the most preferred tool for a specific task type."""
        if not self._user_preferences.preferred_tools:
            return None
        
        # Sort tools by usage count
        sorted_tools = sorted(
            self._user_preferences.preferred_tools.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_tools[0][0] if sorted_tools else None
    
    def recent_failures(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the most recent failed runs."""
        failures = [entry for entry in reversed(self._history) if not entry.get("success", False)]
        return failures[:limit]
    
    def get_workflow_pattern(self) -> Dict[str, Any]:
        """Extract common workflow patterns from user's successful runs."""
        if not self._user_preferences.success_patterns:
            return {}
        
        # Analyze patterns in successful runs
        patterns = {
            "most_common_goal_types": {},
            "preferred_tool_sequences": [],
            "average_completion_time": 0.0,
            "peak_performance_times": []
        }
        
        # Count goal patterns
        for pattern in self._user_preferences.success_patterns:
            goal_type = pattern.get("goal_pattern", "general")
            patterns["most_common_goal_types"][goal_type] = \
                patterns["most_common_goal_types"].get(goal_type, 0) + 1
        
        # Get most common tool sequences
        if self._user_preferences.success_patterns:
            most_common_sequence = max(
                [p["tool_sequence"] for p in self._user_preferences.success_patterns if p["tool_sequence"]],
                key=lambda seq: len([p for p in self._user_preferences.success_patterns if p["tool_sequence"] == seq]),
                default=[]
            )
            patterns["preferred_tool_sequences"] = [most_common_sequence] if most_common_sequence else []
        
        return patterns