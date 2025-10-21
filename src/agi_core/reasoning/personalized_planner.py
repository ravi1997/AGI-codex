"""Personalized planning agent implementation."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any

from .personalized_context import PersonalizedPlanningContext
from .planner import Plan, PlanStep

LOGGER = logging.getLogger(__name__)


@dataclass
class PersonalizedPlan:
    """Enhanced plan with personalization data."""
    
    goal: str
    context_summary: str
    steps: List[PlanStep]
    # Personalization-specific fields
    user_preference_alignment: float
    project_context_relevance: float
    working_style_fit: float
    plan_confidence: float


class PersonalizedPlanner:
    """Enhanced planner that incorporates user preferences, project context, and working style."""
    
    def build_plan(self, context: PersonalizedPlanningContext) -> PersonalizedPlan:
        LOGGER.info("Personalized planning for goal: %s", context.goal)
        
        context_summary = self._summarize_context(context)
        
        # Generate steps based on personalization
        steps: List[PlanStep] = self._generate_personalized_steps(context)
        
        # Calculate personalization metrics
        preference_alignment = self._calculate_preference_alignment(context, steps)
        project_relevance = self._calculate_project_relevance(context, steps)
        working_style_fit = self._calculate_working_style_fit(context, steps)
        plan_confidence = self._calculate_plan_confidence(context, steps)
        
        LOGGER.debug(
            "Generated personalized plan with %d steps (alignment: %.2f, relevance: %.2f, style_fit: %.2f)", 
            len(steps), 
            preference_alignment, 
            project_relevance, 
            working_style_fit
        )
        
        return PersonalizedPlan(
            goal=context.goal,
            context_summary=context_summary,
            steps=steps,
            user_preference_alignment=preference_alignment,
            project_context_relevance=project_relevance,
            working_style_fit=working_style_fit,
            plan_confidence=plan_confidence
        )
    
    def _generate_personalized_steps(self, context: PersonalizedPlanningContext) -> List[PlanStep]:
        """Generate plan steps based on personalization data."""
        steps: List[PlanStep] = []
        
        # Add telemetry capture if system.monitor is available and user prefers monitoring
        if "system.monitor" in context.available_tools:
            # Check if user prefers monitoring based on working style
            if context.working_style_profile.get('monitoring_preference', 'default') in ['high', 'default']:
                steps.append(
                    PlanStep(
                        name="capture-telemetry",
                        description="Capture a fresh telemetry snapshot to ensure up-to-date metrics",
                        tool="system.monitor",
                    )
                )
        
        # Add memory reflection based on user preferences
        if context.memory_snippets:
            steps.append(
                PlanStep(
                    name="reflect-on-memories",
                    description="Reflect on similar past tasks and incorporate lessons learned",
                    tool=None,
                )
            )
        
        # Add context persistence based on user preferences
        if "file.io" in context.available_tools:
            # Only add if user likes documentation or persistence
            interaction_style = context.user_preferences.get('interaction_style', 'default')
            if interaction_style in ['detailed', 'documented', 'default']:
                steps.append(
                    PlanStep(
                        name="persist-context",
                        description="Persist the planning context for traceability",
                        tool="file.io",
                        kwargs={
                            "action": "write",
                            "path": "reports/context_snapshot.md",
                            "data": context_summary,
                        },
                    )
                )
        
        # Generate execution steps based on user preferences
        execution_steps = self._generate_execution_steps(context)
        steps.extend(execution_steps)
        
        # Add follow-up steps based on project context
        follow_up_steps = self._generate_follow_up_steps(context)
        steps.extend(follow_up_steps)
        
        return steps
    
    def _generate_execution_steps(self, context: PersonalizedPlanningContext) -> List[PlanStep]:
        """Generate execution steps based on user preferences and project context."""
        steps = []
        
        # Determine the preferred tool for this goal type
        preferred_tool = self._get_preferred_tool_for_goal(context)
        
        if preferred_tool and preferred_tool in context.available_tools:
            # Use the user's preferred tool
            command = self._derive_command(context.goal, preferred_tool)
            steps.append(
                PlanStep(
                    name="execute-with-preferred-tool",
                    description=f"Execute using user's preferred tool: {preferred_tool}",
                    tool=preferred_tool,
                    args=[command],
                )
            )
        else:
            # Fallback to standard tool selection
            if "terminal.run" in context.available_tools:
                command = self._derive_command(context.goal)
                steps.append(
                    PlanStep(
                        name="execute-goal",
                        description=f"Execute command to satisfy goal: {context.goal}",
                        tool="terminal.run",
                        args=[command],
                    )
                )
        
        return steps
    
    def _get_preferred_tool_for_goal(self, context: PersonalizedPlanningContext) -> str | None:
        """Get the user's preferred tool for this type of goal."""
        goal_lower = context.goal.lower()
        
        # Check if there's a specific tool preference for this goal type
        preferred_tools = context.user_preferences.get('preferred_tools', {})
        if not preferred_tools:
            return None
        
        # Look for tools commonly used with similar goals
        for tool_name, _ in sorted(preferred_tools.items(), key=lambda x: x[1], reverse=True):
            # If the goal contains keywords related to the tool
            if self._tool_matches_goal(tool_name, goal_lower):
                return tool_name
        
        return None
    
    def _tool_matches_goal(self, tool_name: str, goal: str) -> bool:
        """Check if a tool matches the goal based on keywords."""
        tool_keywords = {
            'terminal.run': ['command', 'run', 'execute', 'shell', 'bash', 'script'],
            'file.io': ['file', 'read', 'write', 'create', 'edit', 'save', 'document'],
            'browser': ['web', 'browse', 'search', 'url', 'page', 'website'],
            'rest.client': ['api', 'request', 'http', 'service', 'endpoint'],
            'system.monitor': ['monitor', 'status', 'metrics', 'telemetry', 'performance']
        }
        
        keywords = tool_keywords.get(tool_name, [])
        return any(keyword in goal for keyword in keywords)
    
    def _derive_command(self, goal: str, preferred_tool: str | None = None) -> str:
        """Derive command with personalization considerations."""
        lowered = goal.strip().lower()
        if not lowered:
            return "echo 'No goal provided'"
        
        # Use preferred tool if specified
        if preferred_tool:
            if preferred_tool == 'terminal.run':
                known_prefixes = ("ls", "cat", "python", "bash", "sh", "pip", "git")
                if goal.strip().startswith(known_prefixes):
                    return goal.strip()
                
                if any(keyword in lowered for keyword in ["list", "show files", "display directory"]):
                    return "ls -la"
                
                if any(keyword in lowered for keyword in ["status", "metrics", "telemetry"]):
                    return "echo 'Telemetry captured separately'"
                
                return f"echo \"Goal: {goal}\""
            elif preferred_tool == 'file.io':
                # For file operations, create appropriate command
                if any(keyword in lowered for keyword in ["create", "write", "save"]):
                    return f"echo '{goal}' > output.txt"
                elif any(keyword in lowered for keyword in ["read", "show", "display"]):
                    return "cat *.txt"
        
        # Default behavior
        known_prefixes = ("ls", "cat", "python", "bash", "sh", "pip", "git")
        if goal.strip().startswith(known_prefixes):
            return goal.strip()
        
        if any(keyword in lowered for keyword in ["list", "show files", "display directory"]):
            return "ls -la"
        
        if any(keyword in lowered for keyword in ["status", "metrics", "telemetry"]):
            return "echo 'Telemetry captured separately'"
        
        return f"echo \"Goal: {goal}\""
    
    def _generate_follow_up_steps(self, context: PersonalizedPlanningContext) -> List[PlanStep]:
        """Generate follow-up steps based on project context."""
        steps = []
        
        # Check if there are project-specific follow-up actions
        project_type = context.project_context.get('project_type')
        if project_type:
            if project_type in ['python', 'javascript', 'typescript'] and "terminal.run" in context.available_tools:
                # Add common development follow-up steps
                if context.project_context.get('needs_testing', False):
                    steps.append(
                        PlanStep(
                            name="run-tests",
                            description="Run tests for the project",
                            tool="terminal.run",
                            args=[f"python -m pytest" if project_type == 'python' else f"npm test"],
                        )
                    )
                
                if context.project_context.get('needs_building', False):
                    steps.append(
                        PlanStep(
                            name="build-project",
                            description="Build the project",
                            tool="terminal.run",
                            args=[f"python setup.py build" if project_type == 'python' else f"npm run build"],
                        )
                    )
        
        return steps
    
    def _calculate_preference_alignment(self, context: PersonalizedPlanningContext, steps: List[PlanStep]) -> float:
        """Calculate how well the plan aligns with user preferences."""
        if not context.user_preferences:
            return 0.5  # Default alignment
        
        # Count steps that align with user preferences
        aligned_steps = 0
        total_steps = len(steps)
        
        for step in steps:
            if step.tool:
                preferred_tools = context.user_preferences.get('preferred_tools', {})
                if step.tool in preferred_tools:
                    aligned_steps += 1
        
        return aligned_steps / total_steps if total_steps > 0 else 0.0
    
    def _calculate_project_relevance(self, context: PersonalizedPlanningContext, steps: List[PlanStep]) -> float:
        """Calculate how relevant the plan is to the current project."""
        if not context.project_context:
            return 0.5  # Default relevance
        
        # Check if steps relate to project context
        relevant_steps = 0
        total_steps = len(steps)
        
        project_keywords = []
        for key, value in context.project_context.items():
            project_keywords.append(str(key).lower())
            project_keywords.append(str(value).lower())
        
        for step in steps:
            step_text = f"{step.name} {step.description} {' '.join(step.args)} {' '.join(step.kwargs.values())}".lower()
            if any(keyword in step_text for keyword in project_keywords):
                relevant_steps += 1
        
        return relevant_steps / total_steps if total_steps > 0 else 0.0
    
    def _calculate_working_style_fit(self, context: PersonalizedPlanningContext, steps: List[PlanStep]) -> float:
        """Calculate how well the plan fits the user's working style."""
        if not context.working_style_profile:
            return 0.5  # Default fit
        
        # This is a simplified calculation - in a real implementation, this would be more complex
        style_preference = context.working_style_profile.get('interaction_style', 'default')
        
        if style_preference == 'detailed':
            # User prefers detailed steps
            return min(1.0, len(steps) / 5)  # More steps = better for detailed style
        elif style_preference == 'minimal':
            # User prefers minimal steps
            return max(0.0, 1.0 - (len(steps) / 10))  # Fewer steps = better for minimal style
        else:
            # Default style - moderate number of steps
            if 2 <= len(steps) <= 5:
                return 1.0
            else:
                return 0.7  # Moderate fit
    
    def _calculate_plan_confidence(self, context: PersonalizedPlanningContext, steps: List[PlanStep]) -> float:
        """Calculate confidence in the plan based on context."""
        # Start with base confidence
        confidence = 0.5
        
        # Increase confidence if we have relevant memories
        if context.memory_snippets:
            confidence += 0.2
        
        # Increase confidence if we have project context
        if context.project_context:
            confidence += 0.15
        
        # Increase confidence if we have user preferences
        if context.user_preferences:
            confidence += 0.15
        
        return min(1.0, confidence)
    
    def _summarize_context(self, context: PersonalizedPlanningContext) -> str:
        """Create a summary of the personalized context."""
        lines = [
            "# Personalized Planning Context", 
            "", 
            f"## Goal\n{context.goal}"
        ]
        
        if context.telemetry:
            lines.append("\n## Telemetry")
            for key, value in context.telemetry.items():
                lines.append(f"- {key}: {value}")
        
        if context.memory_snippets:
            lines.append("\n## Relevant Memories")
            for snippet, metadata in zip(context.memory_snippets, context.memory_metadata):
                label = metadata.get("label") if metadata else None
                if label:
                    lines.append(f"- {label}")
                    continue
                first_line = snippet.splitlines()[0] if snippet else ""
                lines.append(f"- {first_line}")
        
        if context.available_tools:
            lines.append("\n## Available Tools")
            for name, description in context.available_tools.items():
                lines.append(f"- {name}: {description}")
        
        # Add personalization-specific sections
        if context.user_preferences:
            lines.append("\n## User Preferences")
            for key, value in context.user_preferences.items():
                if key == 'preferred_tools':
                    lines.append("- Preferred tools:")
                    for tool, count in value.items():
                        lines.append(f"  - {tool}: {count} uses")
                else:
                    lines.append(f"- {key}: {value}")
        
        if context.project_context:
            lines.append("\n## Project Context")
            for key, value in context.project_context.items():
                lines.append(f"- {key}: {value}")
        
        if context.working_style_profile:
            lines.append("\n## Working Style Profile")
            for key, value in context.working_style_profile.items():
                lines.append(f"- {key}: {value}")
        
        if context.goal_history:
            lines.append("\n## Recent Goals")
            for goal in context.goal_history[-3:]:  # Show last 3 goals
                lines.append(f"- {goal}")
        
        return "\n".join(lines)