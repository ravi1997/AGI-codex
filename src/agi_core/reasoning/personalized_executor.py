"""Personalized execution agent with enhanced safety checks."""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from ..tools.base import ToolContext, ToolRegistry, ToolResult
from .personalized_planner import PersonalizedPlan, PlanStep
from ..system.safety import SafetyGuard

LOGGER = logging.getLogger(__name__)


class PersonalizedExecutor:
    """Enhanced executor that incorporates user preferences and safety checks for autonomous operations."""
    
    def __init__(self, tools: ToolRegistry, working_directory: str) -> None:
        self._tools = tools
        self._context = ToolContext(working_directory=working_directory)
        self._safety_guard = SafetyGuard()
        self._user_preferences: Dict[str, Any] = {}
        self._working_style_profile: Dict[str, Any] = {}
        self._execution_history: List[Dict[str, Any]] = []
    
    def set_user_preferences(self, preferences: Dict[str, Any]) -> None:
        """Set user preferences for execution."""
        self._user_preferences = preferences
        LOGGER.debug("Updated user preferences for executor")
    
    def set_working_style_profile(self, profile: Dict[str, Any]) -> None:
        """Set working style profile for execution."""
        self._working_style_profile = profile
        LOGGER.debug("Updated working style profile for executor")
    
    def execute(self, plan: PersonalizedPlan) -> List[ToolResult]:
        """Execute personalized plan steps with safety checks."""
        results: List[ToolResult] = []
        
        for step in plan.steps:
            # Perform safety checks before execution
            if not self._is_step_safe(step):
                LOGGER.warning("Step failed safety check: %s", step.name)
                results.append(ToolResult(
                    success=False, 
                    output="", 
                    error=f"Step {step.name} failed safety validation"
                ))
                continue
            
            # Apply personalization to the execution
            result = self._execute_step_personalized(step, plan)
            results.append(result)
            
            # Record execution in history
            self._record_execution(step, result, plan)
        
        return results
    
    def _is_step_safe(self, step: PlanStep) -> bool:
        """Perform safety checks on a step before execution."""
        # Check if the goal is safe
        if hasattr(step, 'description') and not self._safety_guard.approve_goal(step.description or ""):
            return False
        
        # Additional safety checks based on user preferences
        interaction_style = self._working_style_profile.get('interaction_style', 'default')
        
        # If user prefers safe operations, apply stricter checks
        if interaction_style == 'conservative':
            # Check for potentially dangerous commands
            if step.tool == 'terminal.run' and step.args:
                command = ' '.join(step.args)
                dangerous_patterns = ['rm -rf', 'format', 'delete', 'destroy']
                if any(pattern in command.lower() for pattern in dangerous_patterns):
                    LOGGER.warning("Potentially dangerous command blocked for conservative user: %s", command)
                    return False
        
        return True
    
    def _execute_step_personalized(self, step: PlanStep, plan: PersonalizedPlan) -> ToolResult:
        """Execute a step with personalization considerations."""
        if step.tool is None:
            LOGGER.info("Internal step '%s': %s", step.name, step.description)
            return ToolResult(success=True, output=step.description)
        
        try:
            tool = self._tools.get(step.tool)
        except KeyError as exc:
            LOGGER.error("Unknown tool: %s", step.tool)
            return ToolResult(success=False, output="", error=str(exc))
        
        LOGGER.info("Executing step '%s' with tool %s", step.name, step.tool)
        
        # Apply personalization to tool execution
        personalized_args, personalized_kwargs = self._personalize_tool_execution(
            step, tool, plan
        )
        
        try:
            result = tool.run(self._context, *personalized_args, **personalized_kwargs)
        except Exception as exc:  # noqa: BLE001 - broad exception to capture tool failures
            LOGGER.exception(
                "Tool '%s' failed while executing step '%s'", step.tool, step.name
            )
            return ToolResult(success=False, output="", error=str(exc))
        
        return result
    
    def _personalize_tool_execution(self, step: PlanStep, tool, plan: PersonalizedPlan):
        """Apply personalization to tool execution parameters."""
        args = list(step.args)
        kwargs = dict(step.kwargs)
        
        # Adjust tool execution based on user preferences
        preferred_tools = self._user_preferences.get('preferred_tools', {})
        
        if step.tool in preferred_tools:
            # User prefers this tool, potentially adjust parameters for better experience
            if step.tool == 'terminal.run':
                # For terminal commands, user might prefer more verbose output
                if self._working_style_profile.get('verbosity_preference') == 'high':
                    if args and not any(flag in args[0] for flag in ['-v', '--verbose']):
                        # Add verbose flag to commands that support it
                        command = args[0]
                        if command.startswith('git '):
                            args[0] = command.replace('git ', 'git -v ', 1)
                        elif command.startswith('pip '):
                            args[0] = command.replace('pip ', 'pip -v ', 1)
        
        # Adjust based on working style
        working_style = self._working_style_profile.get('working_style', 'default')
        if working_style == 'careful':
            # Add extra safety or confirmation steps
            if step.tool == 'file.io' and kwargs.get('action') == 'write':
                # For careful users, ensure overwrite protection
                if 'confirm' not in kwargs:
                    kwargs['confirm'] = True
        
        return args, kwargs
    
    def _record_execution(self, step: PlanStep, result: ToolResult, plan: PersonalizedPlan) -> None:
        """Record execution details for learning."""
        execution_record = {
            'step_name': step.name,
            'tool_used': step.tool,
            'description': step.description,
            'args': list(step.args),
            'kwargs': dict(step.kwargs),
            'success': result.success,
            'output': result.output,
            'error': result.error,
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'plan_confidence': plan.plan_confidence,
            'preference_alignment': plan.user_preference_alignment,
        }
        self._execution_history.append(execution_record)
        
        # Keep only the last 50 executions to prevent unbounded growth
        if len(self._execution_history) > 50:
            self._execution_history = self._execution_history[-50:]
    
    def get_execution_insights(self) -> Dict[str, Any]:
        """Get insights from execution history."""
        if not self._execution_history:
            return {'message': 'No execution history available'}
        
        # Calculate success rates by tool
        tool_success_rates = {}
        for record in self._execution_history:
            tool = record['tool_used']
            if tool not in tool_success_rates:
                tool_success_rates[tool] = {'success': 0, 'total': 0}
            tool_success_rates[tool]['total'] += 1
            if record['success']:
                tool_success_rates[tool]['success'] += 1
        
        for tool in tool_success_rates:
            total = tool_success_rates[tool]['total']
            success = tool_success_rates[tool]['success']
            tool_success_rates[tool]['rate'] = success / total if total > 0 else 0
        
        return {
            'total_executions': len(self._execution_history),
            'overall_success_rate': sum(1 for r in self._execution_history if r['success']) / len(self._execution_history),
            'tool_success_rates': tool_success_rates,
            'recent_execution_count': len(self._execution_history)
        }
    
    def should_execute_autonomous_task(self, step: PlanStep, plan: PersonalizedPlan) -> bool:
        """Determine if an autonomous task should be executed based on safety and preferences."""
        # Check if the task is safe
        if not self._is_step_safe(step):
            return False
        
        # Check user's comfort with autonomous operations
        autonomous_comfort = self._user_preferences.get('autonomous_comfort_level', 'medium')
        
        if autonomous_comfort == 'low':
            # For users uncomfortable with autonomous operations, only execute simple tasks
            if step.tool and step.tool not in ['file.io', 'system.monitor']:
                return False
        elif autonomous_comfort == 'high':
            # For users comfortable with autonomous operations, be more permissive
            pass # Allow most operations
        else:  # medium
            # For medium comfort, apply standard safety checks
            pass
        
        # Check if the task aligns with user preferences
        if plan.user_preference_alignment < 0.3:
            # If the plan doesn't align well with preferences, be more cautious
            LOGGER.info("Plan has low preference alignment (%.2f), being cautious about autonomous execution", 
                       plan.user_preference_alignment)
            return False
        
        return True
    
    def execute_autonomous_step(self, step: PlanStep, plan: PersonalizedPlan) -> ToolResult:
        """Execute an autonomous step with enhanced safety checks."""
        if not self.should_execute_autonomous_task(step, plan):
            return ToolResult(
                success=False, 
                output="", 
                error="Autonomous task rejected due to safety or preference concerns"
            )
        
        LOGGER.info("Executing autonomous step: %s", step.name)
        return self._execute_step_personalized(step, plan)