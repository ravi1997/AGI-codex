"""Pattern recognition algorithms for identifying recurring tasks and habits."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, Counter
import re
from dataclasses import dataclass

from .workflow_tracker import WorkflowTracker
from .enhanced_episodic import EnhancedEpisodicMemory
from .enhanced_semantic import EnhancedSemanticMemory
from .enhanced_procedural import EnhancedProceduralMemory

LOGGER = logging.getLogger(__name__)


@dataclass
class Pattern:
    """Represents a detected pattern."""
    pattern_id: str
    pattern_type: str  # 'task', 'habit', 'workflow', 'time_based', etc.
    user_id: str
    description: str
    frequency: int
    confidence: float
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]


@dataclass
class TaskPattern:
    """Represents a recurring task pattern."""
    task_name: str
    frequency: int
    avg_interval_days: float
    context: Dict[str, str]
    confidence: float
    schedule_pattern: str  # e.g., "daily", "weekly", "monthly", "irregular"


@dataclass
class HabitPattern:
    """Represents a recurring habit pattern."""
    habit_name: str
    frequency: int
    avg_interval_days: float
    time_of_day: str # e.g., "morning", "afternoon", "evening", "night"
    context: Dict[str, str]
    confidence: float


class PatternRecognizer:
    """Identifies recurring tasks and habits from user activity data."""
    
    def __init__(
        self,
        workflow_tracker: WorkflowTracker,
        episodic_memory: EnhancedEpisodicMemory,
        semantic_memory: EnhancedSemanticMemory,
        procedural_memory: EnhancedProceduralMemory
    ) -> None:
        self._workflow_tracker = workflow_tracker
        self._episodic_memory = episodic_memory
        self._semantic_memory = semantic_memory
        self._procedural_memory = procedural_memory
    
    def detect_recurring_tasks(self, user_id: str, min_frequency: int = 2) -> List[TaskPattern]:
        """Detect recurring tasks for a user."""
        # Get user activities
        activities = self._workflow_tracker.get_user_activities(user_id, days_back=180)  # 6 months
        
        if not activities:
            return []
        
        # Group activities by type and context similarity
        activity_groups = defaultdict(list)
        for activity in activities:
            # Create a signature based on activity type and key context elements
            context_signature = self._create_context_signature(activity.context)
            signature = f"{activity.activity_type}:{context_signature}"
            activity_groups[signature].append(activity)
        
        recurring_tasks = []
        for signature, group in activity_groups.items():
            if len(group) >= min_frequency:
                # Calculate interval statistics
                sorted_activities = sorted(group, key=lambda x: x.timestamp)
                intervals = []
                for i in range(1, len(sorted_activities)):
                    interval = (sorted_activities[i].timestamp - sorted_activities[i-1].timestamp).days
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                
                # Determine schedule pattern
                schedule_pattern = self._determine_schedule_pattern(intervals)
                
                # Calculate confidence based on regularity
                confidence = self._calculate_pattern_confidence(intervals)
                
                # Extract activity type and context
                activity_type, context_str = signature.split(":", 1)
                context = self._parse_context_signature(context_str)
                
                task_pattern = TaskPattern(
                    task_name=activity_type,
                    frequency=len(group),
                    avg_interval_days=avg_interval,
                    context=context,
                    confidence=confidence,
                    schedule_pattern=schedule_pattern
                )
                recurring_tasks.append(task_pattern)
        
        # Sort by confidence and frequency
        recurring_tasks.sort(key=lambda x: (x.confidence, x.frequency), reverse=True)
        return recurring_tasks
    
    def detect_user_habits(self, user_id: str, min_frequency: int = 2) -> List[HabitPattern]:
        """Detect user habits based on timing and activity patterns."""
        activities = self._workflow_tracker.get_user_activities(user_id, days_back=180)  # 6 months
        
        if not activities:
            return []
        
        # Group activities by type
        activity_groups = defaultdict(list)
        for activity in activities:
            activity_groups[activity.activity_type].append(activity)
        
        habits = []
        for activity_type, group in activity_groups.items():
            if len(group) >= min_frequency:
                # Analyze timing patterns
                time_of_day_counts = Counter()
                for activity in group:
                    hour = activity.timestamp.hour
                    if 5 <= hour < 12:
                        time_of_day_counts["morning"] += 1
                    elif 12 <= hour < 17:
                        time_of_day_counts["afternoon"] += 1
                    elif 17 <= hour < 21:
                        time_of_day_counts["evening"] += 1
                    else:
                        time_of_day_counts["night"] += 1
                
                # Get most common time of day
                most_common_time = time_of_day_counts.most_common(1)[0][0] if time_of_day_counts else "irregular"
                
                # Calculate intervals
                sorted_activities = sorted(group, key=lambda x: x.timestamp)
                intervals = []
                for i in range(1, len(sorted_activities)):
                    interval = (sorted_activities[i].timestamp - sorted_activities[i-1].timestamp).days
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals) if intervals else 0
                
                # Calculate confidence
                confidence = self._calculate_pattern_confidence(intervals)
                
                habit = HabitPattern(
                    habit_name=activity_type,
                    frequency=len(group),
                    avg_interval_days=avg_interval,
                    time_of_day=most_common_time,
                    context=group[0].context,  # Use context from first occurrence
                    confidence=confidence
                )
                habits.append(habit)
        
        # Sort by confidence and frequency
        habits.sort(key=lambda x: (x.confidence, x.frequency), reverse=True)
        return habits
    
    def detect_workflow_patterns(self, user_id: str, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """Detect workflow patterns by analyzing sequences of activities."""
        sessions = self._workflow_tracker.get_user_sessions(user_id, days_back=180)  # 6 months
        
        if not sessions:
            return []
        
        # Extract activity sequences from sessions
        activity_sequences = []
        for session in sessions:
            if len(session.activities) > 1:  # Only consider sessions with multiple activities
                sequence = [
                    (activity.activity_type, self._create_context_signature(activity.context))
                    for activity in session.activities
                ]
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
        common_patterns = []
        for pattern, count in pattern_counts.items():
            if count >= min_frequency:
                # Calculate confidence based on frequency and consistency
                confidence = min(1.0, count / 5.0)  # Cap at 1.0, with 5+ occurrences being very confident
                
                # Convert pattern back to readable format
                pattern_activities = [item[0] for item in pattern]  # Just the activity types
                pattern_contexts = [item[1] for item in pattern]  # The context signatures
                
                common_patterns.append({
                    "pattern_id": f"workflow_{hash(str(pattern)) % 10000}",
                    "pattern_activities": pattern_activities,
                    "pattern_contexts": pattern_contexts,
                    "frequency": count,
                    "confidence": confidence
                })
        
        # Sort by frequency and confidence
        common_patterns.sort(key=lambda x: (x["frequency"], x["confidence"]), reverse=True)
        return common_patterns[:20]  # Return top 20 patterns
    
    def detect_time_based_patterns(self, user_id: str) -> Dict[str, Any]:
        """Detect patterns based on time of day, day of week, etc."""
        activities = self._workflow_tracker.get_user_activities(user_id, days_back=365)  # Full year
        
        if not activities:
            return {}
        
        # Analyze by hour of day
        hour_counts = Counter()
        for activity in activities:
            hour_counts[activity.timestamp.hour] += 1
        
        # Analyze by day of week
        day_counts = Counter()
        for activity in activities:
            day_counts[activity.timestamp.weekday()] += 1  # 0=Monday, 6=Sunday
        
        # Analyze by time of day (morning, afternoon, evening, night)
        time_of_day_counts = Counter()
        for activity in activities:
            hour = activity.timestamp.hour
            if 5 <= hour < 12:
                time_of_day_counts["morning"] += 1
            elif 12 <= hour < 17:
                time_of_day_counts["afternoon"] += 1
            elif 17 <= hour < 21:
                time_of_day_counts["evening"] += 1
            else:
                time_of_day_counts["night"] += 1
        
        # Analyze by day of week (for recurring activities)
        weekly_patterns = defaultdict(list)
        for activity in activities:
            day_of_week = activity.timestamp.weekday()
            weekly_patterns[activity.activity_type].append(day_of_week)
        
        # Calculate consistency for each activity type
        activity_consistency = {}
        for activity_type, days in weekly_patterns.items():
            day_counter = Counter(days)
            # Calculate how evenly distributed the activities are across days
            total_activities = len(days)
            if total_activities > 0:
                # Calculate consistency as 1 - (entropy/maximum_entropy)
                entropy = 0
                for count in day_counter.values():
                    prob = count / total_activities
                    entropy -= prob * (prob).log2() if prob > 0 else 0
                max_entropy = (len(day_counter)).log2() if len(day_counter) > 0 else 1
                consistency = 1 - (entropy / max_entropy) if max_entropy > 0 else 0
                activity_consistency[activity_type] = consistency
        
        return {
            "most_active_hour": hour_counts.most_common(1)[0][0] if hour_counts else None,
            "most_active_day": day_counts.most_common(1)[0][0] if day_counts else None,
            "time_of_day_preferences": dict(time_of_day_counts),
            "activity_type_consistency": activity_consistency,
            "hourly_activity_distribution": dict(hour_counts),
            "daily_activity_distribution": dict(day_counts)
        }
    
    def detect_project_based_patterns(self, user_id: str) -> List[Dict[str, Any]]:
        """Detect patterns related to specific projects."""
        # Get user interactions from episodic memory
        interactions = self._episodic_memory.get_user_interactions(user_id, days_back=180)
        
        # Get sessions from workflow tracker
        sessions = self._workflow_tracker.get_user_sessions(user_id, days_back=180)
        
        project_patterns = []
        
        # Group interactions by project context
        project_interactions = defaultdict(list)
        for interaction in interactions:
            if interaction.project_context:
                project_interactions[interaction.project_context].append(interaction)
        
        # Group sessions by project context
        project_sessions = defaultdict(list)
        for session in sessions:
            if session.project_context:
                project_sessions[session.project_context].append(session)
        
        # Analyze each project
        for project_id in set(list(project_interactions.keys()) + list(project_sessions.keys())):
            interactions = project_interactions.get(project_id, [])
            sessions = project_sessions.get(project_id, [])
            
            # Calculate metrics
            total_interactions = len(interactions)
            total_sessions = len(sessions)
            total_activities = sum(len(s.activities) for s in sessions)
            
            if total_interactions + total_sessions > 0:  # Only include if there's activity
                # Determine project type based on activity patterns
                activity_types = Counter()
                for interaction in interactions:
                    activity_types[interaction.interaction_type] += 1
                for session in sessions:
                    for activity in session.activities:
                        activity_types[activity.activity_type] += 1
                
                primary_activity_type = activity_types.most_common(1)[0][0] if activity_types else "unknown"
                
                # Calculate activity timing
                if interactions:
                    first_activity = min(interactions, key=lambda x: x.timestamp).timestamp
                    last_activity = max(interactions, key=lambda x: x.timestamp).timestamp
                    duration_days = (last_activity - first_activity).days
                elif sessions:
                    first_activity = min(sessions, key=lambda x: x.start_time).start_time
                    last_activity = max(sessions, key=lambda x: x.end_time or x.start_time).end_time or max(sessions, key=lambda x: x.start_time).start_time
                    duration_days = (last_activity - first_activity).days
                else:
                    duration_days = 0
                
                project_pattern = {
                    "project_id": project_id,
                    "total_interactions": total_interactions,
                    "total_sessions": total_sessions,
                    "total_activities": total_activities,
                    "primary_activity_type": primary_activity_type,
                    "duration_days": duration_days,
                    "active_days": len(set(i.timestamp.date() for i in interactions)),
                    "most_common_interaction_types": dict(activity_types.most_common(5))
                }
                
                project_patterns.append(project_pattern)
        
        # Sort by total activity
        project_patterns.sort(key=lambda x: x["total_interactions"] + x["total_sessions"], reverse=True)
        return project_patterns
    
    def generate_user_patterns_summary(self, user_id: str) -> Dict[str, Any]:
        """Generate a comprehensive summary of all detected patterns for a user."""
        recurring_tasks = self.detect_recurring_tasks(user_id)
        habits = self.detect_user_habits(user_id)
        workflow_patterns = self.detect_workflow_patterns(user_id)
        time_patterns = self.detect_time_based_patterns(user_id)
        project_patterns = self.detect_project_based_patterns(user_id)
        
        return {
            "recurring_tasks": [
                {
                    "task_name": task.task_name,
                    "frequency": task.frequency,
                    "avg_interval_days": task.avg_interval_days,
                    "confidence": task.confidence,
                    "schedule_pattern": task.schedule_pattern
                }
                for task in recurring_tasks[:10]  # Top 10
            ],
            "habits": [
                {
                    "habit_name": habit.habit_name,
                    "frequency": habit.frequency,
                    "avg_interval_days": habit.avg_interval_days,
                    "time_of_day": habit.time_of_day,
                    "confidence": habit.confidence
                }
                for habit in habits[:10] # Top 10
            ],
            "workflow_patterns": workflow_patterns[:10],  # Top 10
            "time_based_patterns": time_patterns,
            "project_patterns": project_patterns[:10],  # Top 10
            "summary": {
                "total_recurring_tasks": len(recurring_tasks),
                "total_habits": len(habits),
                "total_workflow_patterns": len(workflow_patterns),
                "total_project_patterns": len(project_patterns)
            }
        }
    
    def _create_context_signature(self, context: Dict[str, str]) -> str:
        """Create a signature from context for grouping similar activities."""
        # Only include important context elements for signature
        important_keys = ["project_context", "goal_type", "tool_used", "file_path"]
        signature_parts = []
        
        for key in important_keys:
            if key in context and context[key]:
                signature_parts.append(f"{key}={context[key]}")
        
        return "|".join(sorted(signature_parts))
    
    def _parse_context_signature(self, signature: str) -> Dict[str, str]:
        """Parse a context signature back to a dictionary."""
        context = {}
        if signature:
            for part in signature.split("|"):
                if "=" in part:
                    key, value = part.split("=", 1)
                    context[key] = value
        return context
    
    def _determine_schedule_pattern(self, intervals: List[float]) -> str:
        """Determine the schedule pattern based on intervals."""
        if not intervals:
            return "irregular"
        
        avg_interval = sum(intervals) / len(intervals)
        
        if 0.8 <= avg_interval <= 1.2:
            return "daily"
        elif 6.5 <= avg_interval <= 7.5:
            return "weekly"
        elif 28 <= avg_interval <= 32:
            return "monthly"
        elif 13.5 <= avg_interval <= 14.5:
            return "biweekly"
        else:
            return "irregular"
    
    def _calculate_pattern_confidence(self, intervals: List[float]) -> float:
        """Calculate confidence in a pattern based on interval consistency."""
        if not intervals or len(intervals) < 2:
            return 0.5  # Default confidence for limited data
        
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval == 0:
            return 0.5
        
        # Calculate standard deviation
        variance = sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = variance ** 0.5
        
        # Confidence is inversely related to coefficient of variation
        coeff_of_variation = std_dev / avg_interval if avg_interval != 0 else float('inf')
        
        # Map coefficient of variation to confidence (0-1 scale)
        # Lower variation = higher confidence
        confidence = max(0.0, min(1.0, 1.0 - coeff_of_variation))
        
        # Boost confidence for more frequent patterns
        if len(intervals) >= 5:
            confidence = min(1.0, confidence * 1.2)  # Up to 20% boost
        elif len(intervals) >= 10:
            confidence = min(1.0, confidence * 1.5)  # Up to 50% boost
        
        return confidence