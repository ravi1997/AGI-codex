"""Memory consolidation processes for maintaining long-term user profiles."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
import threading
import time

from ..config import MemoryConsolidationConfig
from .enhanced_episodic import EnhancedEpisodicMemory
from .enhanced_semantic import EnhancedSemanticMemory
from .enhanced_procedural import EnhancedProceduralMemory
from .workflow_tracker import WorkflowTracker
from .pattern_recognizer import PatternRecognizer

LOGGER = logging.getLogger(__name__)




class UserProfile:
    """Represents a consolidated user profile with long-term information."""
    
    def __init__(
        self,
        user_id: str,
        created_at: datetime,
        last_consolidated: datetime,
        preferences: Dict[str, Any] = None,
        habits: Dict[str, Any] = None,
        recurring_tasks: Dict[str, Any] = None,
        project_contexts: Dict[str, Any] = None,
        skills: Dict[str, Any] = None,
        goals: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ):
        self.user_id = user_id
        self.created_at = created_at
        self.last_consolidated = last_consolidated
        self.preferences = preferences or {}
        self.habits = habits or {}
        self.recurring_tasks = recurring_tasks or {}
        self.project_contexts = project_contexts or {}
        self.skills = skills or {}
        self.goals = goals or {}
        self.metadata = metadata or {}


class MemoryConsolidator:
    """Manages memory consolidation processes for long-term user profiles."""
    
    def __init__(
        self,
        config: MemoryConsolidationConfig,
        episodic_memory: EnhancedEpisodicMemory,
        semantic_memory: EnhancedSemanticMemory,
        procedural_memory: EnhancedProceduralMemory,
        workflow_tracker: WorkflowTracker,
        pattern_recognizer: PatternRecognizer
    ):
        self.config = config
        self.episodic_memory = episodic_memory
        self.semantic_memory = semantic_memory
        self.procedural_memory = procedural_memory
        self.workflow_tracker = workflow_tracker
        self.pattern_recognizer = pattern_recognizer
        self._profiles: Dict[str, UserProfile] = {}
        self._storage_path = Path("storage/consolidated_profiles")
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._consolidation_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        self._load_profiles()
    
    def _load_profiles(self) -> None:
        """Load user profiles from storage."""
        profiles_path = self._storage_path / "user_profiles.json"
        if profiles_path.exists():
            with profiles_path.open("r", encoding="utf-8") as handle:
                raw_profiles = json.load(handle)
            
            for item in raw_profiles:
                profile = UserProfile(
                    user_id=item["user_id"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                    last_consolidated=datetime.fromisoformat(item["last_consolidated"]),
                    preferences=item.get("preferences", {}),
                    habits=item.get("habits", {}),
                    recurring_tasks=item.get("recurring_tasks", {}),
                    project_contexts=item.get("project_contexts", {}),
                    skills=item.get("skills", {}),
                    goals=item.get("goals", {}),
                    metadata=item.get("metadata", {})
                )
                self._profiles[profile.user_id] = profile
        
        LOGGER.info(f"Loaded {len(self._profiles)} user profiles from storage")
    
    def _save_profiles(self) -> None:
        """Save user profiles to storage."""
        profiles_path = self._storage_path / "user_profiles.json"
        profiles_serializable = []
        
        for profile in self._profiles.values():
            profile_data = {
                "user_id": profile.user_id,
                "created_at": profile.created_at.isoformat(),
                "last_consolidated": profile.last_consolidated.isoformat(),
                "preferences": profile.preferences,
                "habits": profile.habits,
                "recurring_tasks": profile.recurring_tasks,
                "project_contexts": profile.project_contexts,
                "skills": profile.skills,
                "goals": profile.goals,
                "metadata": profile.metadata
            }
            profiles_serializable.append(profile_data)
        
        with profiles_path.open("w", encoding="utf-8") as handle:
            json.dump(profiles_serializable, handle, indent=2)
        
        LOGGER.debug(f"Saved {len(self._profiles)} user profiles to storage")
    
    def start_consolidation_service(self) -> None:
        """Start the background consolidation service."""
        if self._consolidation_thread is not None and self._consolidation_thread.is_alive():
            LOGGER.warning("Consolidation service is already running")
            return
        
        self._stop_event.clear()
        self._consolidation_thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self._consolidation_thread.start()
        LOGGER.info("Started memory consolidation service")
    
    def stop_consolidation_service(self) -> None:
        """Stop the background consolidation service."""
        self._stop_event.set()
        if self._consolidation_thread:
            self._consolidation_thread.join(timeout=5)  # Wait up to 5 seconds
        LOGGER.info("Stopped memory consolidation service")
    
    def _consolidation_loop(self) -> None:
        """Main loop for periodic consolidation."""
        while not self._stop_event.is_set():
            try:
                # Perform consolidation
                self.consolidate_all_users()
                
                # Wait for the next consolidation cycle
                for _ in range(self.config.consolidation_interval_hours * 60):  # Convert hours to minutes
                    if self._stop_event.is_set():
                        break
                    time.sleep(60)  # Sleep for 1 minute
            except Exception as e:
                LOGGER.error(f"Error in consolidation loop: {e}")
                # Wait a bit before retrying to avoid rapid error cycles
                time.sleep(300)  # 5 minutes
    
    def consolidate_user_profile(self, user_id: str) -> UserProfile:
        """Consolidate memory for a specific user into a long-term profile."""
        with self._lock:
            # Get current time
            now = datetime.utcnow()
            
            # Get user patterns
            patterns = self.pattern_recognizer.generate_user_patterns_summary(user_id)
            
            # Get user preferences from semantic memory
            user_preferences = self.semantic_memory.get_user_preferences(user_id)
            preferences_dict = {}
            for pref in user_preferences:
                if pref.preference_type not in preferences_dict:
                    preferences_dict[pref.preference_type] = []
                preferences_dict[pref.preference_type].append({
                    "value": pref.preference_value,
                    "confidence": pref.confidence
                })
            
            # Get learned knowledge from semantic memory
            learned_knowledge = self.semantic_memory.get_learned_knowledge(user_id)
            skills = {}
            goals = {}
            for knowledge in learned_knowledge:
                if knowledge.knowledge_type == "skill":
                    skills[knowledge.knowledge_content] = knowledge.confidence
                elif knowledge.knowledge_type == "goal":
                    goals[knowledge.knowledge_content] = knowledge.confidence
            
            # Get project info from semantic memory
            project_info = {}
            for proj in self.semantic_memory._project_info.values():
                if user_id in proj.metadata.get("collaborators", []):
                    project_info[proj.project_id] = {
                        "name": proj.project_name,
                        "type": proj.project_type,
                        "last_accessed": proj.last_accessed.isoformat()
                    }
            
            # Create or update profile
            if user_id in self._profiles:
                profile = self._profiles[user_id]
                profile.last_consolidated = now
            else:
                profile = UserProfile(
                    user_id=user_id,
                    created_at=now,
                    last_consolidated=now
                )
                self._profiles[user_id] = profile
            
            # Update profile with consolidated information
            profile.preferences = preferences_dict
            profile.habits = {h["habit_name"]: h for h in patterns["habits"]}
            profile.recurring_tasks = {t["task_name"]: t for t in patterns["recurring_tasks"]}
            profile.project_contexts = project_info
            profile.skills = skills
            profile.goals = goals
            
            # Add metadata
            profile.metadata["last_consolidation_run"] = now.isoformat()
            profile.metadata["consolidation_source"] = "memory_consolidator"
            
            # Save profiles
            self._save_profiles()
            
            LOGGER.info(f"Consolidated profile for user {user_id}")
            return profile
    
    def consolidate_all_users(self) -> Dict[str, UserProfile]:
        """Consolidate memory for all users."""
        # Get all unique user IDs from various sources
        user_ids = set()
        
        # From episodic memory
        for interaction in self.episodic_memory._user_interactions:
            user_ids.add(interaction.user_id)
        
        # From workflow tracker
        for activity in self.workflow_tracker._activity_logs:
            user_ids.add(activity.user_id)
        
        # From semantic memory
        for user_id in self.semantic_memory._user_preferences.keys():
            user_ids.add(user_id)
        
        # Consolidate each user
        consolidated_profiles = {}
        for user_id in user_ids:
            try:
                profile = self.consolidate_user_profile(user_id)
                consolidated_profiles[user_id] = profile
            except Exception as e:
                LOGGER.error(f"Failed to consolidate profile for user {user_id}: {e}")
        
        LOGGER.info(f"Completed consolidation for {len(consolidated_profiles)} users")
        return consolidated_profiles
    
    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get a user's consolidated profile."""
        return self._profiles.get(user_id)
    
    def get_all_user_profiles(self) -> Dict[str, UserProfile]:
        """Get all user profiles."""
        return self._profiles.copy()
    
    def cleanup_old_memories(self) -> int:
        """Clean up old memories that are no longer needed due to consolidation."""
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=self.config.retention_days)
        summary_cutoff_date = now - timedelta(days=self.config.summary_retention_days)
        
        cleaned_count = 0
        
        # Clean up episodic memory interactions
        old_interactions = [
            i for i in self.episodic_memory._user_interactions
            if i.timestamp < cutoff_date
        ]
        
        # Keep interactions that are part of recurring patterns
        patterns = set()
        for pattern_list in self.episodic_memory._workflow_patterns:
            patterns.update(pattern_list.recurring_tasks)
        
        # Only remove interactions that are not part of recurring patterns
        for interaction in old_interactions:
            if interaction.goal_type not in patterns and interaction.project_context not in patterns:
                self.episodic_memory._user_interactions.remove(interaction)
                cleaned_count += 1
        
        # Clean up workflow tracker logs
        old_activities = [
            a for a in self.workflow_tracker._activity_logs
            if a.timestamp < cutoff_date
        ]
        
        # Keep activities that are part of detected patterns
        recurring_tasks = set()
        for profile in self._profiles.values():
            for task_name in profile.recurring_tasks.keys():
                recurring_tasks.add(task_name)
        
        for activity in old_activities:
            if activity.activity_type not in recurring_tasks:
                self.workflow_tracker._activity_logs.remove(activity)
                cleaned_count += 1
        
        # Clean up old sessions
        old_sessions = [
            s for s in self.workflow_tracker._sessions.values()
            if s.start_time < summary_cutoff_date
        ]
        
        for session in old_sessions:
            if session.session_id in self.workflow_tracker._sessions:
                del self.workflow_tracker._sessions[session.session_id]
                if session.user_id in self.workflow_tracker._active_sessions:
                    del self.workflow_tracker._active_sessions[session.user_id]
        
        # Persist changes
        self.episodic_memory._persist()
        self.workflow_tracker._persist()
        
        LOGGER.info(f"Cleaned up {cleaned_count} old memory entries")
        return cleaned_count
    
    def generate_long_term_insights(self, user_id: str) -> Dict[str, Any]:
        """Generate insights from long-term user profile."""
        profile = self.get_user_profile(user_id)
        if not profile:
            return {}
        
        # Generate insights
        insights = {
            "productivity_insights": self._generate_productivity_insights(profile),
            "preference_insights": self._generate_preference_insights(profile),
            "goal_progress": self._generate_goal_progress(profile),
            "skill_development": self._generate_skill_development(profile)
        }
        
        return insights
    
    def _generate_productivity_insights(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate productivity-related insights."""
        insights = {}
        
        # Analyze habits
        if profile.habits:
            most_consistent_habit = max(
                profile.habits.values(), 
                key=lambda h: h.get("confidence", 0)
            )
            insights["most_consistent_habit"] = most_consistent_habit
            
            # Time of day preferences
            time_preferences = defaultdict(int)
            for habit in profile.habits.values():
                time_of_day = habit.get("time_of_day", "unknown")
                time_preferences[time_of_day] += 1
            
            insights["preferred_working_time"] = max(
                time_preferences.items(), 
                key=lambda x: x[1]
            )[0] if time_preferences else "unknown"
        
        # Analyze recurring tasks
        if profile.recurring_tasks:
            most_frequent_task = max(
                profile.recurring_tasks.values(),
                key=lambda t: t.get("frequency", 0)
            )
            insights["most_frequent_task"] = most_frequent_task
            
            # Calculate average task interval
            intervals = [t["avg_interval_days"] for t in profile.recurring_tasks.values() 
                        if t.get("avg_interval_days", 0) > 0]
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                insights["average_task_interval"] = avg_interval
        
        return insights
    
    def _generate_preference_insights(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate preference-related insights."""
        insights = {}
        
        # Identify strong preferences
        strong_preferences = {}
        for pref_type, pref_list in profile.preferences.items():
            strong_prefs = [p for p in pref_list if p.get("confidence", 0) > 0.7]
            if strong_prefs:
                strong_preferences[pref_type] = strong_prefs
        
        insights["strong_preferences"] = strong_preferences
        
        # Identify preference patterns
        if profile.project_contexts:
            insights["project_preferences"] = list(profile.project_contexts.keys())
        
        return insights
    
    def _generate_goal_progress(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate goal progress insights."""
        insights = {}
        
        if profile.goals:
            insights["tracked_goals"] = len(profile.goals)
            avg_goal_confidence = sum(profile.goals.values()) / len(profile.goals) if profile.goals else 0
            insights["average_goal_confidence"] = avg_goal_confidence
        
        return insights
    
    def _generate_skill_development(self, profile: UserProfile) -> Dict[str, Any]:
        """Generate skill development insights."""
        insights = {}
        
        if profile.skills:
            insights["tracked_skills"] = len(profile.skills)
            avg_skill_confidence = sum(profile.skills.values()) / len(profile.skills) if profile.skills else 0
            insights["average_skill_confidence"] = avg_skill_confidence
            insights["top_skills"] = sorted(
                profile.skills.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]  # Top 5 skills
        
        return insights