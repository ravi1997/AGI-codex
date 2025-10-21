"""User context manager for maintaining awareness of current projects and goals."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import threading

from .enhanced_semantic import EnhancedSemanticMemory, ProjectInfo
from .enhanced_episodic import EnhancedEpisodicMemory
from .workflow_tracker import WorkflowTracker
from .consolidation import MemoryConsolidator

LOGGER = logging.getLogger(__name__)


class UserContext:
    """Represents the current context for a user."""
    
    def __init__(
        self,
        user_id: str,
        current_project: str = None,
        current_goal: str = None,
        current_task: str = None,
        active_contexts: List[str] = None,
        context_metadata: Dict[str, Any] = None,
        last_updated: datetime = None
    ):
        self.user_id = user_id
        self.current_project = current_project
        self.current_goal = current_goal
        self.current_task = current_task
        self.active_contexts = active_contexts or []
        self.context_metadata = context_metadata or {}
        self.last_updated = last_updated or datetime.utcnow()
    
    def update_context(
        self,
        project: str = None,
        goal: str = None,
        task: str = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Update the user context."""
        if project is not None:
            self.current_project = project
        if goal is not None:
            self.current_goal = goal
        if task is not None:
            self.current_task = task
        if metadata is not None:
            self.context_metadata.update(metadata)
        
        self.last_updated = datetime.utcnow()


class ProjectContext:
    """Represents context information for a specific project."""
    
    def __init__(
        self,
        project_id: str,
        project_name: str,
        goals: List[str] = None,
        active_tasks: List[str] = None,
        participants: List[str] = None,
        context_data: Dict[str, Any] = None,
        last_accessed: datetime = None
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.goals = goals or []
        self.active_tasks = active_tasks or []
        self.participants = participants or []
        self.context_data = context_data or {}
        self.last_accessed = last_accessed or datetime.utcnow()
    
    def add_goal(self, goal: str) -> None:
        """Add a goal to the project."""
        if goal not in self.goals:
            self.goals.append(goal)
            self.last_accessed = datetime.utcnow()
    
    def remove_goal(self, goal: str) -> None:
        """Remove a goal from the project."""
        if goal in self.goals:
            self.goals.remove(goal)
            self.last_accessed = datetime.utcnow()
    
    def add_task(self, task: str) -> None:
        """Add a task to the project."""
        if task not in self.active_tasks:
            self.active_tasks.append(task)
            self.last_accessed = datetime.utcnow()
    
    def remove_task(self, task: str) -> None:
        """Remove a task from the project."""
        if task in self.active_tasks:
            self.active_tasks.remove(task)
            self.last_accessed = datetime.utcnow()


class UserContextManager:
    """Manages user context including current projects and goals."""
    
    def __init__(
        self,
        storage_path: Path,
        semantic_memory: EnhancedSemanticMemory,
        episodic_memory: EnhancedEpisodicMemory,
        workflow_tracker: WorkflowTracker,
        memory_consolidator: MemoryConsolidator
    ):
        self._storage_path = storage_path
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._semantic_memory = semantic_memory
        self._episodic_memory = episodic_memory
        self._workflow_tracker = workflow_tracker
        self._memory_consolidator = memory_consolidator
        
        self._user_contexts: Dict[str, UserContext] = {}
        self._project_contexts: Dict[str, ProjectContext] = {}
        self._lock = threading.Lock()
        
        self._load_contexts()
    
    def _load_contexts(self) -> None:
        """Load user and project contexts from storage."""
        # Load user contexts
        user_contexts_path = self._storage_path / "user_contexts.json"
        if user_contexts_path.exists():
            with user_contexts_path.open("r", encoding="utf-8") as handle:
                raw_contexts = json.load(handle)
            
            for item in raw_contexts:
                context = UserContext(
                    user_id=item["user_id"],
                    current_project=item.get("current_project"),
                    current_goal=item.get("current_goal"),
                    current_task=item.get("current_task"),
                    active_contexts=item.get("active_contexts", []),
                    context_metadata=item.get("context_metadata", {}),
                    last_updated=datetime.fromisoformat(item["last_updated"])
                )
                self._user_contexts[context.user_id] = context
        
        # Load project contexts
        project_contexts_path = self._storage_path / "project_contexts.json"
        if project_contexts_path.exists():
            with project_contexts_path.open("r", encoding="utf-8") as handle:
                raw_contexts = json.load(handle)
            
            for item in raw_contexts:
                project_context = ProjectContext(
                    project_id=item["project_id"],
                    project_name=item["project_name"],
                    goals=item.get("goals", []),
                    active_tasks=item.get("active_tasks", []),
                    participants=item.get("participants", []),
                    context_data=item.get("context_data", {}),
                    last_accessed=datetime.fromisoformat(item["last_accessed"])
                )
                self._project_contexts[project_context.project_id] = project_context
        
        LOGGER.info(f"Loaded {len(self._user_contexts)} user contexts and {len(self._project_contexts)} project contexts")
    
    def _save_contexts(self) -> None:
        """Save user and project contexts to storage."""
        # Save user contexts
        user_contexts_path = self._storage_path / "user_contexts.json"
        user_contexts_serializable = [
            {
                "user_id": context.user_id,
                "current_project": context.current_project,
                "current_goal": context.current_goal,
                "current_task": context.current_task,
                "active_contexts": context.active_contexts,
                "context_metadata": context.context_metadata,
                "last_updated": context.last_updated.isoformat()
            }
            for context in self._user_contexts.values()
        ]
        
        with user_contexts_path.open("w", encoding="utf-8") as handle:
            json.dump(user_contexts_serializable, handle, indent=2)
        
        # Save project contexts
        project_contexts_path = self._storage_path / "project_contexts.json"
        project_contexts_serializable = [
            {
                "project_id": context.project_id,
                "project_name": context.project_name,
                "goals": context.goals,
                "active_tasks": context.active_tasks,
                "participants": context.participants,
                "context_data": context.context_data,
                "last_accessed": context.last_accessed.isoformat()
            }
            for context in self._project_contexts.values()
        ]
        
        with project_contexts_path.open("w", encoding="utf-8") as handle:
            json.dump(project_contexts_serializable, handle, indent=2)
        
        LOGGER.debug(f"Saved {len(self._user_contexts)} user contexts and {len(self._project_contexts)} project contexts")
    
    def set_user_context(
        self,
        user_id: str,
        project: str = None,
        goal: str = None,
        task: str = None,
        metadata: Dict[str, Any] = None
    ) -> UserContext:
        """Set the context for a user."""
        with self._lock:
            if user_id in self._user_contexts:
                context = self._user_contexts[user_id]
                context.update_context(project=project, goal=goal, task=task, metadata=metadata)
            else:
                context = UserContext(
                    user_id=user_id,
                    current_project=project,
                    current_goal=goal,
                    current_task=task,
                    context_metadata=metadata or {}
                )
                self._user_contexts[user_id] = context
            
            # Update project context if project is specified
            if project:
                self._update_project_context(user_id, project)
            
            self._save_contexts()
            LOGGER.info(f"Updated context for user {user_id}: project={project}, goal={goal}, task={task}")
            return context
    
    def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """Get the current context for a user."""
        return self._user_contexts.get(user_id)
    
    def get_current_project(self, user_id: str) -> Optional[str]:
        """Get the current project for a user."""
        context = self.get_user_context(user_id)
        return context.current_project if context else None
    
    def get_current_goal(self, user_id: str) -> Optional[str]:
        """Get the current goal for a user."""
        context = self.get_user_context(user_id)
        return context.current_goal if context else None
    
    def get_current_task(self, user_id: str) -> Optional[str]:
        """Get the current task for a user."""
        context = self.get_user_context(user_id)
        return context.current_task if context else None
    
    def _update_project_context(self, user_id: str, project_id: str) -> None:
        """Update project context when user starts working on a project."""
        # Ensure project exists in semantic memory
        project_info = self._semantic_memory.get_project_info(project_id)
        if not project_info:
            # Create a basic project info if it doesn't exist
            project_info = ProjectInfo(
                project_id=project_id,
                project_name=project_id,  # Use ID as name if not specified
                metadata={"created_by_context_manager": True}
            )
            self._semantic_memory.add_project_info(project_info)
        
        # Update or create project context
        if project_id not in self._project_contexts:
            self._project_contexts[project_id] = ProjectContext(
                project_id=project_id,
                project_name=project_info.project_name
            )
        
        project_context = self._project_contexts[project_id]
        project_context.last_accessed = datetime.utcnow()
        
        # Add user to participants if not already there
        if user_id not in project_context.participants:
            project_context.participants.append(user_id)
        
        # If user has a goal, add it to project goals
        user_context = self._user_contexts.get(user_id)
        if user_context and user_context.current_goal and user_context.current_goal not in project_context.goals:
            project_context.goals.append(user_context.current_goal)
    
    def get_project_context(self, project_id: str) -> Optional[ProjectContext]:
        """Get context information for a project."""
        return self._project_contexts.get(project_id)
    
    def get_project_participants(self, project_id: str) -> List[str]:
        """Get all users participating in a project."""
        project_context = self.get_project_context(project_id)
        return project_context.participants if project_context else []
    
    def get_user_projects(self, user_id: str) -> List[str]:
        """Get all projects a user is involved in."""
        projects = []
        for project_id, project_context in self._project_contexts.items():
            if user_id in project_context.participants:
                projects.append(project_id)
        return projects
    
    def add_project_goal(self, project_id: str, goal: str) -> None:
        """Add a goal to a project."""
        with self._lock:
            if project_id in self._project_contexts:
                self._project_contexts[project_id].add_goal(goal)
            else:
                # Create project context if it doesn't exist
                self._project_contexts[project_id] = ProjectContext(
                    project_id=project_id,
                    project_name=project_id,
                    goals=[goal]
                )
            
            self._save_contexts()
            LOGGER.info(f"Added goal '{goal}' to project '{project_id}'")
    
    def remove_project_goal(self, project_id: str, goal: str) -> None:
        """Remove a goal from a project."""
        with self._lock:
            if project_id in self._project_contexts:
                self._project_contexts[project_id].remove_goal(goal)
                self._save_contexts()
                LOGGER.info(f"Removed goal '{goal}' from project '{project_id}'")
    
    def add_project_task(self, project_id: str, task: str) -> None:
        """Add a task to a project."""
        with self._lock:
            if project_id in self._project_contexts:
                self._project_contexts[project_id].add_task(task)
            else:
                # Create project context if it doesn't exist
                self._project_contexts[project_id] = ProjectContext(
                    project_id=project_id,
                    project_name=project_id,
                    active_tasks=[task]
                )
            
            self._save_contexts()
            LOGGER.info(f"Added task '{task}' to project '{project_id}'")
    
    def remove_project_task(self, project_id: str, task: str) -> None:
        """Remove a task from a project."""
        with self._lock:
            if project_id in self._project_contexts:
                self._project_contexts[project_id].remove_task(task)
                self._save_contexts()
                LOGGER.info(f"Removed task '{task}' from project '{project_id}'")
    
    def get_relevant_context(self, user_id: str, query: str = None) -> Dict[str, Any]:
        """Get context relevant to the user's current situation."""
        user_context = self.get_user_context(user_id)
        if not user_context:
            return {}
        
        context = {
            "user_id": user_id,
            "current_context": {
                "project": user_context.current_project,
                "goal": user_context.current_goal,
                "task": user_context.current_task
            }
        }
        
        # Add project-specific context if available
        if user_context.current_project:
            project_context = self.get_project_context(user_context.current_project)
            if project_context:
                context["project_context"] = {
                    "project_name": project_context.project_name,
                    "project_goals": project_context.goals,
                    "active_tasks": project_context.active_tasks,
                    "participants": project_context.participants,
                    "context_data": project_context.context_data
                }
        
        # Add user profile insights if available
        profile = self._memory_consolidator.get_user_profile(user_id)
        if profile:
            context["user_profile"] = {
                "preferences": profile.preferences,
                "habits": profile.habits,
                "recurring_tasks": profile.recurring_tasks,
                "skills": profile.skills
            }
        
        # Add recent activity context
        recent_activities = self._workflow_tracker.get_user_activities(user_id, days_back=7)
        context["recent_activities"] = [
            {
                "activity_type": a.activity_type,
                "description": a.description,
                "timestamp": a.timestamp.isoformat(),
                "context": a.context
            }
            for a in recent_activities[-10:]  # Last 10 activities
        ]
        
        # Add detected patterns if available
        patterns = self._memory_consolidator.generate_long_term_insights(user_id)
        if patterns:
            context["detected_patterns"] = patterns
        
        return context
    
    def clear_user_context(self, user_id: str) -> None:
        """Clear the context for a user."""
        with self._lock:
            if user_id in self._user_contexts:
                del self._user_contexts[user_id]
                self._save_contexts()
                LOGGER.info(f"Cleared context for user {user_id}")
    
    def get_all_user_contexts(self) -> Dict[str, UserContext]:
        """Get all user contexts."""
        return self._user_contexts.copy()
    
    def get_all_project_contexts(self) -> Dict[str, ProjectContext]:
        """Get all project contexts."""
        return self._project_contexts.copy()
    
    def update_context_from_interaction(self, user_id: str, interaction_type: str, content: str, metadata: Dict[str, str]) -> None:
        """Update context based on a user interaction."""
        with self._lock:
            # Determine if this interaction suggests a change in context
            project_context = metadata.get("project_context")
            goal_type = metadata.get("goal_type")
            
            # Update user context if project or goal information is available
            needs_update = False
            if project_context:
                needs_update = True
            if goal_type:
                needs_update = True
            
            if needs_update:
                current_context = self.get_user_context(user_id)
                if current_context:
                    # Only update if different from current context
                    if project_context and project_context != current_context.current_project:
                        self.set_user_context(user_id, project=project_context)
                    if goal_type and goal_type != current_context.current_goal:
                        self.set_user_context(user_id, goal=goal_type)
                else:
                    # Set initial context
                    self.set_user_context(user_id, project=project_context, goal=goal_type)
    
    def get_context_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of the user's current context."""
        user_context = self.get_user_context(user_id)
        if not user_context:
            return {"message": "No context available for user"}
        
        summary = {
            "user_id": user_id,
            "current_project": user_context.current_project,
            "current_goal": user_context.current_goal,
            "current_task": user_context.current_task,
            "last_updated": user_context.last_updated.isoformat(),
            "active_contexts": user_context.active_contexts
        }
        
        # Add project information if available
        if user_context.current_project:
            project_info = self._semantic_memory.get_project_info(user_context.current_project)
            if project_info:
                summary["project_details"] = {
                    "name": project_info.project_name,
                    "description": project_info.project_description,
                    "type": project_info.project_type,
                    "created_at": project_info.created_at.isoformat(),
                    "last_accessed": project_info.last_accessed.isoformat()
                }
        
        # Add recent activity stats
        activity_stats = self._workflow_tracker.get_activity_statistics(user_id)
        if activity_stats:
            summary["activity_stats"] = {
                "total_activities": activity_stats.get("total_activities", 0),
                "active_days": activity_stats.get("active_days", 0),
                "most_common_contexts": activity_stats.get("most_common_contexts", {})
            }
        
        # Add pattern information
        patterns = self._memory_consolidator.generate_long_term_insights(user_id)
        if patterns:
            summary["patterns"] = {
                "productivity_insights": patterns.get("productivity_insights", {}),
                "preference_insights": patterns.get("preference_insights", {}),
                "recurring_tasks": list(self._memory_consolidator.get_user_profile(user_id).recurring_tasks.keys()) if self._memory_consolidator.get_user_profile(user_id) else []
            }
        
        return summary