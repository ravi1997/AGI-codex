"""Enhanced semantic memory for storing user preferences, project information, and learned knowledge."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Optional
from collections import defaultdict

from .base import MemoryRecord, MemoryStore

LOGGER = logging.getLogger(__name__)


class UserPreference:
    """Represents a user preference or learned behavior."""
    
    def __init__(
        self,
        user_id: str,
        preference_type: str,
        preference_value: str,
        confidence: float = 1.0,
        last_updated: datetime = None,
        metadata: Dict[str, str] = None
    ):
        self.user_id = user_id
        self.preference_type = preference_type
        self.preference_value = preference_value
        self.confidence = confidence
        self.last_updated = last_updated or datetime.utcnow()
        self.metadata = metadata or {}


class ProjectInfo:
    """Represents project-specific information and context."""
    
    def __init__(
        self,
        project_id: str,
        project_name: str,
        project_description: str = None,
        project_type: str = None,
        created_at: datetime = None,
        last_accessed: datetime = None,
        metadata: Dict[str, str] = None
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.project_description = project_description
        self.project_type = project_type
        self.created_at = created_at or datetime.utcnow()
        self.last_accessed = last_accessed or datetime.utcnow()
        self.metadata = metadata or {}


class LearnedKnowledge:
    """Represents knowledge learned about a user."""
    
    def __init__(
        self,
        user_id: str,
        knowledge_type: str,
        knowledge_content: str,
        confidence: float = 1.0,
        source: str = None,
        learned_at: datetime = None,
        metadata: Dict[str, str] = None
    ):
        self.user_id = user_id
        self.knowledge_type = knowledge_type
        self.knowledge_content = knowledge_content
        self.confidence = confidence
        self.source = source
        self.learned_at = learned_at or datetime.utcnow()
        self.metadata = metadata or {}


class EnhancedSemanticMemory(MemoryStore):
    """Enhanced semantic memory with user preference and project information storage."""
    
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._records: List[MemoryRecord] = []
        self._user_preferences: Dict[str, List[UserPreference]] = defaultdict(list)
        self._project_info: Dict[str, ProjectInfo] = {}
        self._learned_knowledge: Dict[str, List[LearnedKnowledge]] = defaultdict(list)
        self._load()
    
    def _load(self) -> None:
        if not self._path.exists():
            LOGGER.debug("Semantic memory database missing at %s", self._path)
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
        
        # Load user preferences
        if "user_preferences" in raw_data:
            for item in raw_data["user_preferences"]:
                pref = UserPreference(
                    user_id=item["user_id"],
                    preference_type=item["preference_type"],
                    preference_value=item["preference_value"],
                    confidence=item["confidence"],
                    last_updated=datetime.fromisoformat(item["last_updated"]),
                    metadata=item.get("metadata", {})
                )
                self._user_preferences[pref.user_id].append(pref)
        
        # Load project info
        if "project_info" in raw_data:
            for item in raw_data["project_info"]:
                proj = ProjectInfo(
                    project_id=item["project_id"],
                    project_name=item["project_name"],
                    project_description=item.get("project_description"),
                    project_type=item.get("project_type"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    last_accessed=datetime.fromisoformat(item["last_accessed"]),
                    metadata=item.get("metadata", {})
                )
                self._project_info[proj.project_id] = proj
        
        # Load learned knowledge
        if "learned_knowledge" in raw_data:
            for item in raw_data["learned_knowledge"]:
                knowledge = LearnedKnowledge(
                    user_id=item["user_id"],
                    knowledge_type=item["knowledge_type"],
                    knowledge_content=item["knowledge_content"],
                    confidence=item["confidence"],
                    source=item.get("source"),
                    learned_at=datetime.fromisoformat(item["learned_at"]),
                    metadata=item.get("metadata", {})
                )
                self._learned_knowledge[knowledge.user_id].append(knowledge)
        
        LOGGER.info("Loaded %d semantic memories, %d user preferences, %d projects, and %d learned knowledge items", 
                   len(self._records), 
                   sum(len(prefs) for prefs in self._user_preferences.values()),
                   len(self._project_info),
                   sum(len(knowledge) for knowledge in self._learned_knowledge.values()))
    
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
            "user_preferences": [
                {
                    "user_id": pref.user_id,
                    "preference_type": pref.preference_type,
                    "preference_value": pref.preference_value,
                    "confidence": pref.confidence,
                    "last_updated": pref.last_updated.isoformat(),
                    "metadata": pref.metadata
                }
                for prefs in self._user_preferences.values() for pref in prefs
            ],
            "project_info": [
                {
                    "project_id": proj.project_id,
                    "project_name": proj.project_name,
                    "project_description": proj.project_description,
                    "project_type": proj.project_type,
                    "created_at": proj.created_at.isoformat(),
                    "last_accessed": proj.last_accessed.isoformat(),
                    "metadata": proj.metadata
                }
                for proj in self._project_info.values()
            ],
            "learned_knowledge": [
                {
                    "user_id": knowledge.user_id,
                    "knowledge_type": knowledge.knowledge_type,
                    "knowledge_content": knowledge.knowledge_content,
                    "confidence": knowledge.confidence,
                    "source": knowledge.source,
                    "learned_at": knowledge.learned_at.isoformat(),
                    "metadata": knowledge.metadata
                }
                for knowledge_list in self._learned_knowledge.values() for knowledge in knowledge_list
            ]
        }
        
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(serializable, handle, indent=2)
        LOGGER.debug("Persisted %d semantic memories, %d user preferences, %d projects, and %d learned knowledge items", 
                    len(self._records), 
                    sum(len(prefs) for prefs in self._user_preferences.values()),
                    len(self._project_info),
                    sum(len(knowledge) for knowledge in self._learned_knowledge.values()))
    
    def add(self, record: MemoryRecord) -> None:
        self._records.append(record)
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
    
    def add_user_preference(self, preference: UserPreference) -> None:
        """Add or update a user preference."""
        # Check if preference already exists and update if so
        existing_pref = None
        for pref in self._user_preferences[preference.user_id]:
            if (pref.preference_type == preference.preference_type and 
                pref.preference_value == preference.preference_value):
                existing_pref = pref
                break
        
        if existing_pref:
            # Update existing preference
            existing_pref.confidence = preference.confidence
            existing_pref.last_updated = preference.last_updated
            existing_pref.metadata = preference.metadata
        else:
            # Add new preference
            self._user_preferences[preference.user_id].append(preference)
        
        self._persist()
        LOGGER.info(f"Added/updated user preference for {preference.user_id}: {preference.preference_type}={preference.preference_value}")
    
    def get_user_preferences(self, user_id: str) -> List[UserPreference]:
        """Get all preferences for a specific user."""
        return self._user_preferences.get(user_id, [])
    
    def get_user_preference_by_type(self, user_id: str, preference_type: str) -> List[UserPreference]:
        """Get preferences of a specific type for a user."""
        user_prefs = self._user_preferences.get(user_id, [])
        return [pref for pref in user_prefs if pref.preference_type == preference_type]
    
    def add_project_info(self, project: ProjectInfo) -> None:
        """Add or update project information."""
        # Update last accessed time
        project.last_accessed = datetime.utcnow()
        self._project_info[project.project_id] = project
        self._persist()
        LOGGER.info(f"Added/updated project info: {project.project_name}")
    
    def get_project_info(self, project_id: str) -> ProjectInfo:
        """Get information about a specific project."""
        return self._project_info.get(project_id)
    
    def get_all_projects(self) -> List[ProjectInfo]:
        """Get all project information."""
        return list(self._project_info.values())
    
    def add_learned_knowledge(self, knowledge: LearnedKnowledge) -> None:
        """Add or update learned knowledge about a user."""
        # Check if knowledge already exists and update if so
        existing_knowledge = None
        for k in self._learned_knowledge[knowledge.user_id]:
            if (k.knowledge_type == knowledge.knowledge_type and 
                k.knowledge_content == knowledge.knowledge_content):
                existing_knowledge = k
                break
        
        if existing_knowledge:
            # Update existing knowledge
            existing_knowledge.confidence = knowledge.confidence
            existing_knowledge.learned_at = knowledge.learned_at
            existing_knowledge.metadata = knowledge.metadata
        else:
            # Add new knowledge
            self._learned_knowledge[knowledge.user_id].append(knowledge)
        
        self._persist()
        LOGGER.info(f"Added/updated learned knowledge for {knowledge.user_id}: {knowledge.knowledge_type}")
    
    def get_learned_knowledge(self, user_id: str) -> List[LearnedKnowledge]:
        """Get all learned knowledge for a specific user."""
        return self._learned_knowledge.get(user_id, [])
    
    def get_learned_knowledge_by_type(self, user_id: str, knowledge_type: str) -> List[LearnedKnowledge]:
        """Get learned knowledge of a specific type for a user."""
        user_knowledge = self._learned_knowledge.get(user_id, [])
        return [k for k in user_knowledge if k.knowledge_type == knowledge_type]
    
    def get_user_profile_summary(self, user_id: str) -> Dict[str, any]:
        """Get a comprehensive summary of a user's profile."""
        preferences = self.get_user_preferences(user_id)
        knowledge = self.get_learned_knowledge(user_id)
        
        # Group preferences by type
        pref_by_type = defaultdict(list)
        for pref in preferences:
            pref_by_type[pref.preference_type].append({
                "value": pref.preference_value,
                "confidence": pref.confidence,
                "last_updated": pref.last_updated.isoformat()
            })
        
        # Group knowledge by type
        knowledge_by_type = defaultdict(list)
        for k in knowledge:
            knowledge_by_type[k.knowledge_type].append({
                "content": k.knowledge_content,
                "confidence": k.confidence,
                "learned_at": k.learned_at.isoformat()
            })
        
        # Get related projects
        related_projects = []
        for proj in self._project_info.values():
            if user_id in proj.metadata.get("collaborators", []):
                related_projects.append({
                    "project_id": proj.project_id,
                    "project_name": proj.project_name,
                    "project_type": proj.project_type
                })
        
        return {
            "user_id": user_id,
            "preference_summary": dict(pref_by_type),
            "knowledge_summary": dict(knowledge_by_type),
            "related_projects": related_projects,
            "total_preferences": len(preferences),
            "total_knowledge_items": len(knowledge)
        }
    
    def update_project_access(self, project_id: str) -> None:
        """Update the last accessed time for a project."""
        if project_id in self._project_info:
            self._project_info[project_id].last_accessed = datetime.utcnow()
            self._persist()