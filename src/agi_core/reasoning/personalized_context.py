"""Personalized context building with project and goal awareness."""
from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Sequence, Any, Optional

from ..memory.orchestrator import MemoryOrchestrator
from ..tools.base import ToolRegistry
from .context import PlanningContext

LOGGER = logging.getLogger(__name__)


@dataclass
class PersonalizedPlanningContext:
    """Enhanced context information with personalization data."""
    
    goal: str
    memory_snippets: List[str]
    memory_metadata: List[Dict[str, str]]
    telemetry: Dict[str, float]
    available_tools: Dict[str, str]
    query_embedding: Sequence[float]
    # Personalization-specific fields
    user_preferences: Dict[str, Any]
    project_context: Dict[str, Any]
    goal_history: List[str]
    working_style_profile: Dict[str, Any]


class PersonalizedContextBuilder:
    """Enhanced context builder that maintains awareness of user's projects and goals."""
    
    def __init__(self, memory: MemoryOrchestrator, embedding_dim: int = 64) -> None:
        self._memory = memory
        self._embedding_dim = embedding_dim
        self._user_preferences: Dict[str, Any] = {}
        self._project_context: Dict[str, Any] = {}
        self._goal_history: List[str] = []
        self._working_style_profile: Dict[str, Any] = {}
    
    def set_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Set the user preferences for context building."""
        self._user_preferences = preferences
        LOGGER.debug("Updated user preferences for context building")
    
    def set_project_context(self, context: Dict[str, Any]) -> None:
        """Set the project context for context building."""
        self._project_context = context
        LOGGER.debug("Updated project context for context building")
    
    def set_working_style_profile(self, profile: Dict[str, Any]) -> None:
        """Set the working style profile for context building."""
        self._working_style_profile = profile
        LOGGER.debug("Updated working style profile for context building")
    
    def add_goal_to_history(self, goal: str) -> None:
        """Add a goal to the history for context awareness."""
        self._goal_history.append(goal)
        # Keep only the last 20 goals to prevent unbounded growth
        if len(self._goal_history) > 20:
            self._goal_history = self._goal_history[-20:]
    
    def embed(self, text: str) -> List[float]:
        """Generate a deterministic embedding using hashed token features."""
        
        tokens = [token for token in text.lower().split() if token]
        vector = [0.0] * self._embedding_dim
        if not tokens:
            return vector
        
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index in range(self._embedding_dim):
                byte = digest[index % len(digest)]
                vector[index] += 1.0 if byte % 2 == 0 else -1.0
        
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
    
    def build(
        self,
        goal: str,
        telemetry: Dict[str, float],
        tools: ToolRegistry,
        *,
        limit: int = 5,
    ) -> PersonalizedPlanningContext:
        """Compose the personalized planning context for a given goal."""
        
        embedding = self.embed(goal)
        
        # Enhance memory retrieval with project context
        enhanced_embedding = self._enhance_embedding_with_context(embedding)
        memories = self._memory.retrieve_relevant(enhanced_embedding, limit=limit)
        
        memory_snippets = [record.content for record in memories]
        memory_metadata = [dict(record.metadata) for record in memories]
        
        available_tools = {name: tool.description for name, tool in tools.list_tools().items()}
        
        # Add goal to history
        self.add_goal_to_history(goal)
        
        LOGGER.debug(
            "Personalized planning context built with %d memories and %d tools", 
            len(memory_snippets), 
            len(available_tools)
        )
        
        return PersonalizedPlanningContext(
            goal=goal,
            memory_snippets=memory_snippets,
            memory_metadata=memory_metadata,
            telemetry=telemetry,
            available_tools=available_tools,
            query_embedding=embedding,
            user_preferences=self._user_preferences,
            project_context=self._project_context,
            goal_history=self._goal_history,
            working_style_profile=self._working_style_profile,
        )
    
    def _enhance_embedding_with_context(self, base_embedding: Sequence[float]) -> List[float]:
        """Enhance the base embedding with project and user context."""
        # Create an embedding for project context
        project_context_str = " ".join([
            f"{key}:{str(value)[:50]}"  # Limit value length to prevent huge embeddings
            for key, value in self._project_context.items()
        ])
        
        # Create an embedding for user preferences
        user_pref_str = " ".join([
            f"{key}:{str(value)[:50]}" 
            for key, value in self._user_preferences.items()
        ])
        
        # Create embeddings for these contexts
        project_embedding = self.embed(project_context_str)
        user_embedding = self.embed(user_pref_str)
        
        # Combine embeddings: base + project + user preference
        combined = [
            (base_embedding[i] + project_embedding[i] + user_embedding[i]) / 3
            for i in range(len(base_embedding))
        ]
        
        # Normalize the combined embedding
        norm = math.sqrt(sum(value * value for value in combined))
        if norm == 0:
            return combined
        return [value / norm for value in combined]
    
    def update_project_context(self, new_context: Dict[str, Any]) -> None:
        """Update project context with new information."""
        for key, value in new_context.items():
            self._project_context[key] = value
        LOGGER.debug("Updated project context with %d new items", len(new_context))
    
    def get_project_context_summary(self) -> str:
        """Get a text summary of the current project context."""
        if not self._project_context:
            return "No project context available"
        
        lines = ["# Project Context Summary"]
        for key, value in self._project_context.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def get_user_preference_summary(self) -> str:
        """Get a text summary of user preferences."""
        if not self._user_preferences:
            return "No user preferences available"
        
        lines = ["# User Preference Summary"]
        for key, value in self._user_preferences.items():
            if key == 'preferred_tools':
                lines.append("- Preferred tools:")
                for tool, count in value.items():
                    lines.append(f"  - {tool}: {count} uses")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def get_working_style_summary(self) -> str:
        """Get a text summary of working style profile."""
        if not self._working_style_profile:
            return "No working style profile available"
        
        lines = ["# Working Style Profile"]
        for key, value in self._working_style_profile.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
    
    def get_context_awareness_level(self) -> float:
        """Get a measure of how context-aware the system is."""
        # Calculate awareness level based on available context
        total_context_items = (
            len(self._project_context) + 
            len(self._user_preferences) + 
            len(self._working_style_profile) + 
            len(self._goal_history)
        )
        
        # Normalize to 0-1 range (arbitrary max of 50 context items)
        return min(1.0, total_context_items / 50.0)
    
    def get_project_goals_summary(self) -> str:
        """Get a summary of recent goals for the current project."""
        if not self._goal_history:
            return "No goals recorded for this project"
        
        lines = ["# Recent Project Goals"]
        for i, goal in enumerate(self._goal_history[-5:], 1):  # Show last 5 goals
            lines.append(f"{i}. {goal}")
        return "\n".join(lines)