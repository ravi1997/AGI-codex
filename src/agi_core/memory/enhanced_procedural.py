"""Enhanced procedural memory for storing learned workflows, automation patterns, and best practices."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

LOGGER = logging.getLogger(__name__)


class WorkflowStep:
    """Represents a single step in a workflow."""
    
    def __init__(
        self,
        step_id: str,
        action: str,
        parameters: Dict[str, Any] = None,
        description: str = None,
        estimated_duration: int = None,  # in seconds
        dependencies: List[str] = None,  # List of step IDs this step depends on
        success_rate: float = 1.0 # Track success rate of this step
    ):
        self.step_id = step_id
        self.action = action
        self.parameters = parameters or {}
        self.description = description
        self.estimated_duration = estimated_duration
        self.dependencies = dependencies or []
        self.success_rate = success_rate


class Workflow:
    """Represents a complete workflow with metadata."""
    
    def __init__(
        self,
        name: str,
        description: str = None,
        steps: List[WorkflowStep] = None,
        tags: List[str] = None,
        created_at: datetime = None,
        last_modified: datetime = None,
        author: str = None,
        success_rate: float = 1.0,  # Overall workflow success rate
        usage_count: int = 0,  # How many times this workflow has been used
        metadata: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.steps = steps or []
        self.tags = tags or []
        self.created_at = created_at or datetime.utcnow()
        self.last_modified = last_modified or datetime.utcnow()
        self.author = author
        self.success_rate = success_rate
        self.usage_count = usage_count
        self.metadata = metadata or {}


class BestPractice:
    """Represents a best practice or optimization rule."""
    
    def __init__(
        self,
        practice_id: str,
        title: str,
        description: str,
        context: str,  # When this practice applies
        recommendation: str,  # What to do
        confidence: float = 1.0,
        learned_from: str = None,  # Source of the practice
        created_at: datetime = None,
        metadata: Dict[str, Any] = None
    ):
        self.practice_id = practice_id
        self.title = title
        self.description = description
        self.context = context
        self.recommendation = recommendation
        self.confidence = confidence
        self.learned_from = learned_from
        self.created_at = created_at or datetime.utcnow()
        self.metadata = metadata or {}


class EnhancedProceduralMemory:
    """Enhanced procedural memory with workflow and best practice storage."""
    
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)
        self._workflows: Dict[str, Workflow] = {}
        self._best_practices: Dict[str, BestPractice] = {}
        self._load()
    
    def _load(self) -> None:
        # Load workflows
        workflows_path = self._path / "workflows.json"
        if workflows_path.exists():
            with workflows_path.open("r", encoding="utf-8") as handle:
                raw_workflows = json.load(handle)
            
            for item in raw_workflows:
                steps = []
                for step_data in item.get("steps", []):
                    step = WorkflowStep(
                        step_id=step_data["step_id"],
                        action=step_data["action"],
                        parameters=step_data.get("parameters", {}),
                        description=step_data.get("description"),
                        estimated_duration=step_data.get("estimated_duration"),
                        dependencies=step_data.get("dependencies", []),
                        success_rate=step_data.get("success_rate", 1.0)
                    )
                    steps.append(step)
                
                workflow = Workflow(
                    name=item["name"],
                    description=item.get("description"),
                    steps=steps,
                    tags=item.get("tags", []),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    last_modified=datetime.fromisoformat(item["last_modified"]),
                    author=item.get("author"),
                    success_rate=item.get("success_rate", 1.0),
                    usage_count=item.get("usage_count", 0),
                    metadata=item.get("metadata", {})
                )
                self._workflows[workflow.name] = workflow
        
        # Load best practices
        practices_path = self._path / "best_practices.json"
        if practices_path.exists():
            with practices_path.open("r", encoding="utf-8") as handle:
                raw_practices = json.load(handle)
            
            for item in raw_practices:
                practice = BestPractice(
                    practice_id=item["practice_id"],
                    title=item["title"],
                    description=item["description"],
                    context=item["context"],
                    recommendation=item["recommendation"],
                    confidence=item.get("confidence", 1.0),
                    learned_from=item.get("learned_from"),
                    created_at=datetime.fromisoformat(item["created_at"]),
                    metadata=item.get("metadata", {})
                )
                self._best_practices[practice.practice_id] = practice
        
        LOGGER.info("Loaded %d workflows and %d best practices", 
                   len(self._workflows), len(self._best_practices))
    
    def _persist(self) -> None:
        # Save workflows
        workflows_path = self._path / "workflows.json"
        workflows_serializable = []
        
        for workflow in self._workflows.values():
            workflow_data = {
                "name": workflow.name,
                "description": workflow.description,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "action": step.action,
                        "parameters": step.parameters,
                        "description": step.description,
                        "estimated_duration": step.estimated_duration,
                        "dependencies": step.dependencies,
                        "success_rate": step.success_rate
                    }
                    for step in workflow.steps
                ],
                "tags": workflow.tags,
                "created_at": workflow.created_at.isoformat(),
                "last_modified": workflow.last_modified.isoformat(),
                "author": workflow.author,
                "success_rate": workflow.success_rate,
                "usage_count": workflow.usage_count,
                "metadata": workflow.metadata
            }
            workflows_serializable.append(workflow_data)
        
        with workflows_path.open("w", encoding="utf-8") as handle:
            json.dump(workflows_serializable, handle, indent=2)
        
        # Save best practices
        practices_path = self._path / "best_practices.json"
        practices_serializable = []
        
        for practice in self._best_practices.values():
            practice_data = {
                "practice_id": practice.practice_id,
                "title": practice.title,
                "description": practice.description,
                "context": practice.context,
                "recommendation": practice.recommendation,
                "confidence": practice.confidence,
                "learned_from": practice.learned_from,
                "created_at": practice.created_at.isoformat(),
                "metadata": practice.metadata
            }
            practices_serializable.append(practice_data)
        
        with practices_path.open("w", encoding="utf-8") as handle:
            json.dump(practices_serializable, handle, indent=2)
        
        LOGGER.debug("Persisted %d workflows and %d best practices", 
                    len(self._workflows), len(self._best_practices))
    
    def save_workflow(self, workflow: Workflow) -> None:
        """Save a workflow to storage."""
        # Update last modified time
        workflow.last_modified = datetime.utcnow()
        self._workflows[workflow.name] = workflow
        self._persist()
        LOGGER.info("Saved workflow: %s", workflow.name)
    
    def load_workflow(self, name: str) -> Workflow:
        """Load a workflow by name."""
        if name in self._workflows:
            # Update access stats
            self._workflows[name].usage_count += 1
            self._workflows[name].last_modified = datetime.utcnow()
            self._persist()
            return self._workflows[name]
        else:
            raise FileNotFoundError(f"Workflow not found: {name}")
    
    def delete_workflow(self, name: str) -> None:
        """Delete a workflow by name."""
        if name in self._workflows:
            del self._workflows[name]
            self._persist()
            LOGGER.info("Deleted workflow: %s", name)
    
    def list_workflows(self) -> List[str]:
        """List all available workflow names."""
        return list(self._workflows.keys())
    
    def get_workflows_by_tag(self, tag: str) -> List[Workflow]:
        """Get workflows that have a specific tag."""
        return [workflow for workflow in self._workflows.values() if tag in workflow.tags]
    
    def get_workflows_by_author(self, author: str) -> List[Workflow]:
        """Get workflows by a specific author."""
        return [workflow for workflow in self._workflows.values() if workflow.author == author]
    
    def add_best_practice(self, practice: BestPractice) -> None:
        """Add a best practice to storage."""
        self._best_practices[practice.practice_id] = practice
        self._persist()
        LOGGER.info("Added best practice: %s", practice.title)
    
    def get_best_practice(self, practice_id: str) -> BestPractice:
        """Get a best practice by ID."""
        return self._best_practices.get(practice_id)
    
    def get_best_practices_by_context(self, context: str) -> List[BestPractice]:
        """Get best practices that apply to a specific context."""
        return [practice for practice in self._best_practices.values() 
                if context.lower() in practice.context.lower()]
    
    def get_best_practices_by_tag(self, tag: str) -> List[BestPractice]:
        """Get best practices by a specific tag from metadata."""
        return [practice for practice in self._best_practices.values() 
                if tag in practice.metadata.get("tags", [])]
    
    def list_best_practices(self) -> List[str]:
        """List all best practice IDs."""
        return list(self._best_practices.keys())
    
    def update_workflow_success_rate(self, name: str, success: bool) -> None:
        """Update the success rate of a workflow based on execution result."""
        if name in self._workflows:
            workflow = self._workflows[name]
            total_executions = workflow.usage_count
            if success:
                # Adjust success rate upward
                workflow.success_rate = (workflow.success_rate * (total_executions - 1) + 1.0) / total_executions
            else:
                # Adjust success rate downward
                workflow.success_rate = (workflow.success_rate * (total_executions - 1) + 0.0) / total_executions
            
            self._persist()
            LOGGER.debug("Updated success rate for workflow %s to %.2f", name, workflow.success_rate)
    
    def get_top_workflows_by_success_rate(self, limit: int = 10) -> List[Workflow]:
        """Get top workflows sorted by success rate."""
        sorted_workflows = sorted(
            self._workflows.values(),
            key=lambda w: w.success_rate,
            reverse=True
        )
        return sorted_workflows[:limit]
    
    def get_top_workflows_by_usage(self, limit: int = 10) -> List[Workflow]:
        """Get top workflows sorted by usage count."""
        sorted_workflows = sorted(
            self._workflows.values(),
            key=lambda w: w.usage_count,
            reverse=True
        )
        return sorted_workflows[:limit]
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about stored workflows."""
        if not self._workflows:
            return {}
        
        total_workflows = len(self._workflows)
        total_steps = sum(len(w.steps) for w in self._workflows.values())
        avg_steps = total_steps / total_workflows if total_workflows > 0 else 0
        avg_success_rate = sum(w.success_rate for w in self._workflows.values()) / total_workflows if total_workflows > 0 else 0
        total_usage = sum(w.usage_count for w in self._workflows.values())
        avg_usage = total_usage / total_workflows if total_workflows > 0 else 0
        
        # Get most common tags
        all_tags = [tag for workflow in self._workflows.values() for tag in workflow.tags]
        tag_counts = defaultdict(int)
        for tag in all_tags:
            tag_counts[tag] += 1
        
        return {
            "total_workflows": total_workflows,
            "total_steps": total_steps,
            "average_steps_per_workflow": avg_steps,
            "average_success_rate": avg_success_rate,
            "total_usage": total_usage,
            "average_usage_per_workflow": avg_usage,
            "most_common_tags": dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def get_best_practices_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about stored best practices."""
        if not self._best_practices:
            return {}
        
        total_practices = len(self._best_practices)
        avg_confidence = sum(p.confidence for p in self._best_practices.values()) / total_practices if total_practices > 0 else 0
        
        # Get practices by confidence level
        high_confidence = len([p for p in self._best_practices.values() if p.confidence >= 0.8])
        medium_confidence = len([p for p in self._best_practices.values() if 0.5 <= p.confidence < 0.8])
        low_confidence = len([p for p in self._best_practices.values() if p.confidence < 0.5])
        
        return {
            "total_best_practices": total_practices,
            "average_confidence": avg_confidence,
            "high_confidence_practices": high_confidence,
            "medium_confidence_practices": medium_confidence,
            "low_confidence_practices": low_confidence
        }