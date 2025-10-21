"""Workflow tracking system for monitoring and logging user activities."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import defaultdict, Counter
import threading
import time

from .base import MemoryRecord
from .enhanced_episodic import UserInteractionRecord
from .enhanced_semantic import EnhancedSemanticMemory
from .enhanced_procedural import EnhancedProceduralMemory

LOGGER = logging.getLogger(__name__)


class ActivityLog:
    """Represents a single activity log entry."""
    
    def __init__(
        self,
        activity_id: str,
        user_id: str,
        activity_type: str,
        description: str,
        timestamp: datetime,
        duration: float = None,  # Duration in seconds
        success: bool = True,
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.activity_id = activity_id
        self.user_id = user_id
        self.activity_type = activity_type
        self.description = description
        self.timestamp = timestamp
        self.duration = duration
        self.success = success
        self.context = context or {}
        self.metadata = metadata or {}


class ActivitySession:
    """Represents a session of related activities."""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        start_time: datetime,
        end_time: datetime = None,
        goal: str = None,
        project_context: str = None,
        activities: List[ActivityLog] = None,
        metadata: Dict[str, Any] = None
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = start_time
        self.end_time = end_time
        self.goal = goal
        self.project_context = project_context
        self.activities = activities or []
        self.metadata = metadata or {}
    
    def add_activity(self, activity: ActivityLog) -> None:
        """Add an activity to the session."""
        self.activities.append(activity)
    
    def complete_session(self) -> None:
        """Mark the session as complete."""
        if not self.end_time:
            self.end_time = datetime.utcnow()


class WorkflowTracker:
    """Tracks user activities and workflow patterns."""
    
    def __init__(
        self,
        storage_path: Path,
        semantic_memory: EnhancedSemanticMemory,
        procedural_memory: EnhancedProceduralMemory
    ) -> None:
        self._storage_path = storage_path
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._semantic_memory = semantic_memory
        self._procedural_memory = procedural_memory
        self._activity_logs: List[ActivityLog] = []
        self._sessions: Dict[str, ActivitySession] = {}
        self._active_sessions: Dict[str, ActivitySession] = {}  # user_id -> session
        self._lock = threading.Lock()
        self._load()
    
    def _load(self) -> None:
        """Load activity logs and sessions from storage."""
        # Load activity logs
        logs_path = self._storage_path / "activity_logs.json"
        if logs_path.exists():
            with logs_path.open("r", encoding="utf-8") as handle:
                raw_logs = json.load(handle)
            
            for item in raw_logs:
                log = ActivityLog(
                    activity_id=item["activity_id"],
                    user_id=item["user_id"],
                    activity_type=item["activity_type"],
                    description=item["description"],
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    duration=item.get("duration"),
                    success=item.get("success", True),
                    context=item.get("context", {}),
                    metadata=item.get("metadata", {})
                )
                self._activity_logs.append(log)
        
        # Load sessions
        sessions_path = self._storage_path / "sessions.json"
        if sessions_path.exists():
            with sessions_path.open("r", encoding="utf-8") as handle:
                raw_sessions = json.load(handle)
            
            for item in raw_sessions:
                activities = []
                for activity_data in item.get("activities", []):
                    activity = ActivityLog(
                        activity_id=activity_data["activity_id"],
                        user_id=activity_data["user_id"],
                        activity_type=activity_data["activity_type"],
                        description=activity_data["description"],
                        timestamp=datetime.fromisoformat(activity_data["timestamp"]),
                        duration=activity_data.get("duration"),
                        success=activity_data.get("success", True),
                        context=activity_data.get("context", {}),
                        metadata=activity_data.get("metadata", {})
                    )
                    activities.append(activity)
                
                session = ActivitySession(
                    session_id=item["session_id"],
                    user_id=item["user_id"],
                    start_time=datetime.fromisoformat(item["start_time"]),
                    end_time=datetime.fromisoformat(item["end_time"]) if item.get("end_time") else None,
                    goal=item.get("goal"),
                    project_context=item.get("project_context"),
                    activities=activities,
                    metadata=item.get("metadata", {})
                )
                self._sessions[session.session_id] = session
                
                # Add to active sessions if not completed
                if not session.end_time:
                    self._active_sessions[session.user_id] = session
        
        LOGGER.info("Loaded %d activity logs and %d sessions", 
                   len(self._activity_logs), len(self._sessions))
    
    def _persist(self) -> None:
        """Persist activity logs and sessions to storage."""
        # Save activity logs
        logs_path = self._storage_path / "activity_logs.json"
        logs_serializable = [
            {
                "activity_id": log.activity_id,
                "user_id": log.user_id,
                "activity_type": log.activity_type,
                "description": log.description,
                "timestamp": log.timestamp.isoformat(),
                "duration": log.duration,
                "success": log.success,
                "context": log.context,
                "metadata": log.metadata
            }
            for log in self._activity_logs
        ]
        
        with logs_path.open("w", encoding="utf-8") as handle:
            json.dump(logs_serializable, handle, indent=2)
        
        # Save sessions
        sessions_path = self._storage_path / "sessions.json"
        sessions_serializable = []
        
        for session in self._sessions.values():
            session_data = {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "goal": session.goal,
                "project_context": session.project_context,
                "activities": [
                    {
                        "activity_id": activity.activity_id,
                        "user_id": activity.user_id,
                        "activity_type": activity.activity_type,
                        "description": activity.description,
                        "timestamp": activity.timestamp.isoformat(),
                        "duration": activity.duration,
                        "success": activity.success,
                        "context": activity.context,
                        "metadata": activity.metadata
                    }
                    for activity in session.activities
                ],
                "metadata": session.metadata
            }
            sessions_serializable.append(session_data)
        
        with sessions_path.open("w", encoding="utf-8") as handle:
            json.dump(sessions_serializable, handle, indent=2)
        
        LOGGER.debug("Persisted %d activity logs and %d sessions", 
                    len(self._activity_logs), len(self._sessions))
    
    def start_session(self, user_id: str, goal: str = None, project_context: str = None) -> ActivitySession:
        """Start a new activity session for a user."""
        session_id = f"session_{user_id}_{int(datetime.utcnow().timestamp())}"
        session = ActivitySession(
            session_id=session_id,
            user_id=user_id,
            start_time=datetime.utcnow(),
            goal=goal,
            project_context=project_context
        )
        
        with self._lock:
            self._sessions[session_id] = session
            self._active_sessions[user_id] = session
            self._persist()
        
        LOGGER.info(f"Started session {session_id} for user {user_id}")
        return session
    
    def end_session(self, user_id: str) -> Optional[ActivitySession]:
        """End the active session for a user."""
        with self._lock:
            if user_id in self._active_sessions:
                session = self._active_sessions[user_id]
                session.complete_session()
                
                # Remove from active sessions
                del self._active_sessions[user_id]
                
                self._persist()
                LOGGER.info(f"Ended session {session.session_id} for user {user_id}")
                return session
            else:
                LOGGER.warning(f"No active session found for user {user_id}")
                return None
    
    def log_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        duration: float = None,
        success: bool = True,
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> ActivityLog:
        """Log a user activity."""
        activity_id = f"activity_{user_id}_{int(datetime.utcnow().timestamp())}_{hash(description) % 10000}"
        activity = ActivityLog(
            activity_id=activity_id,
            user_id=user_id,
            activity_type=activity_type,
            description=description,
            timestamp=datetime.utcnow(),
            duration=duration,
            success=success,
            context=context or {},
            metadata=metadata or {}
        )
        
        with self._lock:
            self._activity_logs.append(activity)
            
            # Add to active session if one exists
            if user_id in self._active_sessions:
                self._active_sessions[user_id].add_activity(activity)
            
            self._persist()
        
        # Also store in episodic memory as a user interaction
        interaction = UserInteractionRecord(
            user_id=user_id,
            interaction_type=activity_type,
            content=description,
            timestamp=activity.timestamp,
            metadata=activity.metadata,
            project_context=activity.context.get("project_context"),
            goal_type=activity.context.get("goal_type")
        )
        self._semantic_memory.add_user_preference(
            self._semantic_memory.UserPreference(
                user_id=user_id,
                preference_type="activity_type",
                preference_value=activity_type,
                confidence=0.8  # Medium confidence for activity type
            )
        )
        
        LOGGER.debug(f"Logged activity {activity_id} for user {user_id}: {activity_type}")
        return activity
    
    def get_user_activities(self, user_id: str, days_back: int = 30) -> List[ActivityLog]:
        """Get activities for a specific user within a time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        return [
            activity for activity in self._activity_logs
            if activity.user_id == user_id and activity.timestamp >= cutoff_date
        ]
    
    def get_session_activities(self, session_id: str) -> List[ActivityLog]:
        """Get activities for a specific session."""
        if session_id in self._sessions:
            return self._sessions[session_id].activities
        return []
    
    def get_active_session(self, user_id: str) -> Optional[ActivitySession]:
        """Get the active session for a user, if any."""
        return self._active_sessions.get(user_id)
    
    def get_user_sessions(self, user_id: str, days_back: int = 30) -> List[ActivitySession]:
        """Get sessions for a specific user within a time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        return [
            session for session in self._sessions.values()
            if session.user_id == user_id and session.start_time >= cutoff_date
        ]
    
    def get_activity_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's activities."""
        activities = self.get_user_activities(user_id, days_back=365)  # Full year
        
        if not activities:
            return {}
        
        # Count activity types
        activity_types = Counter([a.activity_type for a in activities])
        
        # Calculate success rates by type
        type_success = defaultdict(list)
        for a in activities:
            type_success[a.activity_type].append(a.success)
        
        success_rates = {}
        for activity_type, results in type_success.items():
            success_rates[activity_type] = sum(results) / len(results)
        
        # Calculate duration statistics
        durations = [a.duration for a in activities if a.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Time-based analysis
        if activities:
            earliest = min(activities, key=lambda x: x.timestamp).timestamp
            latest = max(activities, key=lambda x: x.timestamp).timestamp
            total_days = (latest - earliest).days + 1 if latest != earliest else 1
        else:
            total_days = 1
        
        # Get context statistics
        contexts = Counter()
        for a in activities:
            for key, value in a.context.items():
                contexts[f"{key}:{value}"] += 1
        
        return {
            "total_activities": len(activities),
            "activity_types": dict(activity_types),
            "success_rates_by_type": success_rates,
            "average_duration": avg_duration,
            "total_duration": sum(durations) if durations else 0,
            "active_days": total_days,
            "average_daily_activities": len(activities) / total_days,
            "most_common_contexts": dict(contexts.most_common(10)),
            "first_activity": earliest.isoformat() if activities else None,
            "last_activity": latest.isoformat() if activities else None
        }
    
    def get_user_session_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about a user's sessions."""
        sessions = self.get_user_sessions(user_id, days_back=365)  # Full year
        
        if not sessions:
            return {}
        
        # Calculate session statistics
        total_sessions = len(sessions)
        total_activities = sum(len(s.activities) for s in sessions)
        avg_activities_per_session = total_activities / total_sessions if total_sessions > 0 else 0
        
        # Calculate session duration
        session_durations = []
        for session in sessions:
            if session.end_time:
                duration = (session.end_time - session.start_time).total_seconds()
                session_durations.append(duration)
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        
        # Count goals
        goals = Counter([s.goal for s in sessions if s.goal])
        
        # Count project contexts
        project_contexts = Counter([s.project_context for s in sessions if s.project_context])
        
        return {
            "total_sessions": total_sessions,
            "total_activities_in_sessions": total_activities,
            "average_activities_per_session": avg_activities_per_session,
            "average_session_duration": avg_session_duration,
            "most_common_goals": dict(goals.most_common(10)),
            "most_common_project_contexts": dict(project_contexts.most_common(10))
        }
    
    def detect_recurring_activities(self, user_id: str, min_frequency: int = 3) -> List[Dict[str, Any]]:
        """Detect recurring activities for a user."""
        activities = self.get_user_activities(user_id, days_back=90)  # Look at last 3 months
        
        # Group activities by type and context
        activity_groups = defaultdict(list)
        for activity in activities:
            key = (activity.activity_type, str(sorted(activity.context.items())))
            activity_groups[key].append(activity)
        
        recurring_activities = []
        for (activity_type, context), group in activity_groups.items():
            if len(group) >= min_frequency:
                # Calculate frequency pattern
                timestamps = sorted([a.timestamp for a in group])
                intervals = []
                for i in range(1, len(timestamps)):
                    intervals.append((timestamps[i] - timestamps[i-1]).days)
                
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                
                recurring_activities.append({
                    "activity_type": activity_type,
                    "context": eval(context),  # Convert back to dict
                    "frequency": len(group),
                    "average_interval_days": avg_interval,
                    "first_occurrence": timestamps[0].isoformat(),
                    "last_occurrence": timestamps[-1].isoformat()
                })
        
        return recurring_activities
    
    def detect_workflow_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Detect workflow patterns based on sequences of activities."""
        sessions = self.get_user_sessions(user_id, days_back=90)  # Look at last 3 months
        
        # Analyze activity sequences within sessions
        activity_sequences = []
        for session in sessions:
            if len(session.activities) > 1:  # Only consider sessions with multiple activities
                sequence = [activity.activity_type for activity in session.activities]
                activity_sequences.append(sequence)
        
        # Find common subsequences
        pattern_counts = Counter()
        for sequence in activity_sequences:
            # Generate all possible sub-sequences of length 2 or more
            for i in range(len(sequence)):
                for j in range(i + 2, len(sequence) + 1):  # Minimum length of 2
                    subsequence = tuple(sequence[i:j])
                    pattern_counts[subsequence] += 1
        
        # Filter for patterns that occur multiple times
        common_patterns = [
            {"pattern": list(pattern), "frequency": count}
            for pattern, count in pattern_counts.items()
            if count >= 2  # At least 2 occurrences
        ]
        
        # Sort by frequency
        common_patterns.sort(key=lambda x: x["frequency"], reverse=True)
        
        return common_patterns[:10]  # Return top 10 patterns