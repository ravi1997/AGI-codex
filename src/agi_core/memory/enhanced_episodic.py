"""Enhanced episodic memory for tracking user interactions and workflow patterns."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Optional
from collections import defaultdict, Counter

from .base import MemoryRecord, MemoryStore

LOGGER = logging.getLogger(__name__)


class UserInteractionRecord:
    """Represents a user interaction with metadata for workflow tracking."""
    
    def __init__(
        self, 
        user_id: str, 
        interaction_type: str, 
        content: str, 
        timestamp: datetime,
        metadata: Dict[str, str] = None,
        project_context: str = None,
        goal_type: str = None
    ):
        self.user_id = user_id
        self.interaction_type = interaction_type
        self.content = content
        self.timestamp = timestamp
        self.metadata = metadata or {}
        self.project_context = project_context
        self.goal_type = goal_type


class WorkflowPattern:
    """Represents a detected workflow pattern."""
    
    def __init__(
        self, 
        pattern_id: str, 
        user_id: str, 
        pattern_type: str, 
        frequency: int,
        last_occurred: datetime,
        recurring_tasks: List[str],
        context: Dict[str, str] = None
    ):
        self.pattern_id = pattern_id
        self.user_id = user_id
        self.pattern_type = pattern_type
        self.frequency = frequency
        self.last_occurred = last_occurred
        self.recurring_tasks = recurring_tasks
        self.context = context or {}


class EnhancedEpisodicMemory(MemoryStore):
    """Enhanced episodic memory with user workflow tracking capabilities."""
    
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[MemoryRecord] = []
        self._user_interactions: List[UserInteractionRecord] = []
        self._workflow_patterns: List[WorkflowPattern] = []
        self._load()
    
    def _load(self) -> None:
        if not self._path.exists():
            LOGGER.debug("No episodic memory file found at %s", self._path)
            return
        
        with self._path.open("r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
        
        # Load regular memory records
        if "records" in raw_data:
            for item in raw_data["records"]:
                created_at = (
                    datetime.fromisoformat(item["created_at"]) if "created_at" in item else datetime.utcnow()
                )
                record = MemoryRecord(
                    content=item["content"],
                    embedding=item["embedding"],
                    metadata=item.get("metadata", {}),
                    created_at=created_at,
                )
                self._records.append(record)
        
        # Load user interactions
        if "user_interactions" in raw_data:
            for item in raw_data["user_interactions"]:
                timestamp = datetime.fromisoformat(item["timestamp"])
                interaction = UserInteractionRecord(
                    user_id=item["user_id"],
                    interaction_type=item["interaction_type"],
                    content=item["content"],
                    timestamp=timestamp,
                    metadata=item.get("metadata", {}),
                    project_context=item.get("project_context"),
                    goal_type=item.get("goal_type")
                )
                self._user_interactions.append(interaction)
        
        # Load workflow patterns
        if "workflow_patterns" in raw_data:
            for item in raw_data["workflow_patterns"]:
                last_occurred = datetime.fromisoformat(item["last_occurred"])
                pattern = WorkflowPattern(
                    pattern_id=item["pattern_id"],
                    user_id=item["user_id"],
                    pattern_type=item["pattern_type"],
                    frequency=item["frequency"],
                    last_occurred=last_occurred,
                    recurring_tasks=item["recurring_tasks"],
                    context=item.get("context", {})
                )
                self._workflow_patterns.append(pattern)
        
        LOGGER.info("Loaded %d episodic memories, %d user interactions, and %d workflow patterns", 
                   len(self._records), len(self._user_interactions), len(self._workflow_patterns))
    
    def _persist(self) -> None:
        serializable = {
            "records": [
                {
                    "content": record.content,
                    "embedding": list(record.embedding),
                    "metadata": record.metadata,
                    "created_at": record.created_at.isoformat(),
                }
                for record in self._records
            ],
            "user_interactions": [
                {
                    "user_id": interaction.user_id,
                    "interaction_type": interaction.interaction_type,
                    "content": interaction.content,
                    "timestamp": interaction.timestamp.isoformat(),
                    "metadata": interaction.metadata,
                    "project_context": interaction.project_context,
                    "goal_type": interaction.goal_type
                }
                for interaction in self._user_interactions
            ],
            "workflow_patterns": [
                {
                    "pattern_id": pattern.pattern_id,
                    "user_id": pattern.user_id,
                    "pattern_type": pattern.pattern_type,
                    "frequency": pattern.frequency,
                    "last_occurred": pattern.last_occurred.isoformat(),
                    "recurring_tasks": pattern.recurring_tasks,
                    "context": pattern.context
                }
                for pattern in self._workflow_patterns
            ]
        }
        
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, indent=2)
        LOGGER.debug("Persisted %d episodic memories, %d user interactions, and %d workflow patterns", 
                    len(self._records), len(self._user_interactions), len(self._workflow_patterns))
    
    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)
        self._persist()
    
    def add_user_interaction(self, interaction: UserInteractionRecord) -> None:
        """Add a user interaction record for workflow tracking."""
        self._user_interactions.append(interaction)
        self._detect_workflow_patterns(interaction)
        self._persist()
    
    def query(self, query_embedding: Sequence[float], limit: int = 5) -> List[MemoryRecord]:
        ranked = sorted(
            self._records,
            key=lambda record: record.similarity(query_embedding),
            reverse=True,
        )
        return ranked[:limit]
    
    def all_records(self) -> Iterable[MemoryRecord]:
        return list(self._records)
    
    def get_user_interactions(self, user_id: str, days_back: int = 30) -> List[UserInteractionRecord]:
        """Get user interactions for a specific user within a time period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        return [
            interaction for interaction in self._user_interactions
            if interaction.user_id == user_id and interaction.timestamp >= cutoff_date
        ]
    
    def get_user_interaction_stats(self, user_id: str) -> Dict[str, any]:
        """Get statistics about a user's interactions."""
        interactions = self.get_user_interactions(user_id, days_back=365)  # Full year
        
        if not interactions:
            return {}
        
        # Count interaction types
        interaction_types = Counter([i.interaction_type for i in interactions])
        
        # Count goal types
        goal_types = Counter([i.goal_type for i in interactions if i.goal_type])
        
        # Count project contexts
        project_contexts = Counter([i.project_context for i in interactions if i.project_context])
        
        # Time-based analysis
        earliest = min(interactions, key=lambda x: x.timestamp).timestamp
        latest = max(interactions, key=lambda x: x.timestamp).timestamp
        total_days = (latest - earliest).days + 1 if latest != earliest else 1
        
        return {
            "total_interactions": len(interactions),
            "interaction_types": dict(interaction_types),
            "goal_types": dict(goal_types),
            "project_contexts": dict(project_contexts),
            "active_days": total_days,
            "average_daily_interactions": len(interactions) / total_days,
            "first_interaction": earliest.isoformat(),
            "last_interaction": latest.isoformat()
        }
    
    def _detect_workflow_patterns(self, new_interaction: UserInteractionRecord) -> None:
        """Detect and update workflow patterns based on user interactions."""
        # Group interactions by user
        user_interactions = [i for i in self._user_interactions if i.user_id == new_interaction.user_id]
        
        # Look for recurring patterns in goal types
        goal_type_interactions = [i for i in user_interactions if i.goal_type]
        goal_type_counts = Counter([i.goal_type for i in goal_type_interactions])
        
        # Look for recurring patterns in project contexts
        project_context_interactions = [i for i in user_interactions if i.project_context]
        project_context_counts = Counter([i.project_context for i in project_context_interactions])
        
        # Update or create workflow patterns for frequently occurring goal types
        for goal_type, count in goal_type_counts.items():
            if count >= 3:  # Consider it a pattern if it occurs 3+ times
                pattern_id = f"goal_{new_interaction.user_id}_{goal_type}"
                existing_pattern = next((p for p in self._workflow_patterns if p.pattern_id == pattern_id), None)
                
                if existing_pattern:
                    # Update existing pattern
                    existing_pattern.frequency = count
                    existing_pattern.last_occurred = new_interaction.timestamp
                else:
                    # Create new pattern
                    pattern = WorkflowPattern(
                        pattern_id=pattern_id,
                        user_id=new_interaction.user_id,
                        pattern_type="goal_type",
                        frequency=count,
                        last_occurred=new_interaction.timestamp,
                        recurring_tasks=[goal_type],
                        context={"goal_type": goal_type}
                    )
                    self._workflow_patterns.append(pattern)
        
        # Update or create workflow patterns for frequently occurring project contexts
        for project_context, count in project_context_counts.items():
            if count >= 3:  # Consider it a pattern if it occurs 3+ times
                pattern_id = f"project_{new_interaction.user_id}_{project_context}"
                existing_pattern = next((p for p in self._workflow_patterns if p.pattern_id == pattern_id), None)
                
                if existing_pattern:
                    # Update existing pattern
                    existing_pattern.frequency = count
                    existing_pattern.last_occurred = new_interaction.timestamp
                else:
                    # Create new pattern
                    pattern = WorkflowPattern(
                        pattern_id=pattern_id,
                        user_id=new_interaction.user_id,
                        pattern_type="project_context",
                        frequency=count,
                        last_occurred=new_interaction.timestamp,
                        recurring_tasks=[project_context],
                        context={"project_context": project_context}
                    )
                    self._workflow_patterns.append(pattern)
    
    def get_workflow_patterns(self, user_id: str) -> List[WorkflowPattern]:
        """Get workflow patterns for a specific user."""
        return [p for p in self._workflow_patterns if p.user_id == user_id]
    
    def get_recurring_tasks(self, user_id: str) -> List[Dict[str, any]]:
        """Get recurring tasks for a user based on workflow patterns."""
        patterns = self.get_workflow_patterns(user_id)
        recurring_tasks = []
        
        for pattern in patterns:
            if pattern.frequency >= 3:  # Only consider tasks that appear 3+ times
                recurring_tasks.append({
                    "pattern_id": pattern.pattern_id,
                    "pattern_type": pattern.pattern_type,
                    "frequency": pattern.frequency,
                    "tasks": pattern.recurring_tasks,
                    "context": pattern.context
                })
        
        return recurring_tasks