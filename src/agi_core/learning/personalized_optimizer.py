"""Personalized self-optimization heuristics for the agent."""
from __future__ import annotations

import logging
from typing import Dict, Set, Optional

from pathlib import Path

from ..config import LearningConfig
from ..orchestration.task_scheduler import TaskScheduler
from .personalized_feedback import PersonalizedFeedbackCollector
from .jobs import TrainingJobRunner
from .scheduling import ScheduledTrainingTask, schedule_training_if_ready

LOGGER = logging.getLogger(__name__)


class PersonalizedSelfOptimizer:
    """Enhanced optimizer that analyzes user preferences and adapts to working style."""
    
    def __init__(self, config: LearningConfig) -> None:
        self._config = config
        self._cooldown_remaining = 0
        self._active_alerts: Set[str] = set()
        self._last_training_sample_count = 0
        self._training_runner = TrainingJobRunner(config)
        self._user_working_style: Dict[str, any] = {}
    
    def maybe_optimize(
        self,
        scheduler: TaskScheduler,
        feedback: PersonalizedFeedbackCollector,
        telemetry: Dict[str, float],
    ) -> None:
        """Adjust scheduler cadence and enqueue diagnostic work based on user preferences."""
        
        # Update user working style profile
        self._update_user_working_style(feedback.user_preferences)
        
        # Apply standard optimization with personalization
        self._personalized_optimization(scheduler, feedback, telemetry)
    
    def _update_user_working_style(self, user_preferences) -> None:
        """Update internal model of user's working style."""
        self._user_working_style = {
            "preferred_tools": user_preferences.preferred_tools,
            "success_patterns": user_preferences.success_patterns,
            "failure_patterns": user_preferences.failure_patterns,
            "project_preferences": user_preferences.project_preferences,
            "interaction_style": user_preferences.interaction_style,
            "feedback_score": user_preferences.feedback_score,
            "last_updated": user_preferences.last_updated
        }
    
    def _personalized_optimization(
        self,
        scheduler: TaskScheduler,
        feedback: PersonalizedFeedbackCollector,
        telemetry: Dict[str, float],
    ) -> None:
        """Apply optimization with personalized parameters."""
        metrics = feedback.metrics
        if metrics.total_runs < self._config.min_samples_for_optimization:
            LOGGER.debug(
                "Skipping optimization - only %s runs recorded (need %s)",
                metrics.total_runs,
                self._config.min_samples_for_optimization,
            )
            return
        
        if self._cooldown_remaining > 0:
            LOGGER.debug("Optimizer on cooldown for %d iterations", self._cooldown_remaining)
            self._cooldown_remaining -= 1
        else:
            # Use personalized success rate thresholds based on user preferences
            success_floor = self._adjust_success_threshold(
                self._config.success_rate_floor, 
                feedback.user_preferences.feedback_score
            )
            success_ceiling = self._adjust_success_threshold(
                self._config.success_rate_ceiling, 
                feedback.user_preferences.feedback_score
            )
            
            self._tune_scheduler(scheduler, metrics.success_rate, success_floor, success_ceiling)
        
        self._process_telemetry_alerts(scheduler, telemetry)
        self._maybe_enqueue_training(scheduler, feedback)
        self._maybe_adapt_to_user_style(scheduler, feedback)
    
    def _adjust_success_threshold(self, base_threshold: float, user_satisfaction: float) -> float:
        """Adjust success thresholds based on user satisfaction."""
        # If user satisfaction is high, be more demanding; if low, be more lenient
        if user_satisfaction > 0.8:
            return min(1.0, base_threshold * 1.1)  # More demanding
        elif user_satisfaction < 0.6:
            return max(0.0, base_threshold * 0.9)  # More lenient
        return base_threshold
    
    def _tune_scheduler(
        self, 
        scheduler: TaskScheduler, 
        success_rate: float, 
        success_floor: float, 
        success_ceiling: float
    ) -> None:
        """Adjust scheduler with personalized parameters."""
        current_interval = scheduler.autonomous_interval
        target_interval = current_interval
        
        # Adjust based on personalized thresholds
        if success_rate < success_floor:
            target_interval = max(
                self._config.min_autonomous_interval_sec,
                int(current_interval * 0.7) or self._config.min_autonomous_interval_sec,
            )
        elif success_rate > success_ceiling:
            target_interval = min(
                self._config.max_autonomous_interval_sec,
                int(current_interval * 1.3) or current_interval,
            )
        
        # Further adjust based on user working style
        if self._user_working_style.get("interaction_style") == "frequent":
            # User likes frequent interaction, reduce intervals
            target_interval = max(
                self._config.min_autonomous_interval_sec,
                int(target_interval * 0.8)
            )
        elif self._user_working_style.get("interaction_style") == "infrequent":
            # User prefers less interaction, increase intervals
            target_interval = min(
                self._config.max_autonomous_interval_sec,
                int(target_interval * 1.2)
            )
        
        if target_interval != current_interval:
            scheduler.update_autonomous_interval(target_interval)
            self._cooldown_remaining = self._config.optimizer_cooldown
            LOGGER.info(
                "Adjusted autonomous task interval from %s to %s seconds based on success rate %.2f%% and user preferences",
                current_interval,
                target_interval,
                success_rate * 100,
            )
    
    def _process_telemetry_alerts(self, scheduler: TaskScheduler, telemetry: Dict[str, float]) -> None:
        """Process telemetry with user preference awareness."""
        cpu = telemetry.get("cpu_percent", 0.0)
        memory = telemetry.get("memory_mb", 0.0)
        
        # Adjust thresholds based on user preferences
        cpu_threshold = self._config.telemetry_cpu_threshold
        memory_threshold = self._config.telemetry_memory_threshold_mb
        
        # If user prefers performance over caution, adjust thresholds
        if self._user_working_style.get("interaction_style") == "performance":
            cpu_threshold = min(95.0, cpu_threshold * 1.2)
            memory_threshold = min(2048.0, memory_threshold * 1.2)
        
        if cpu > cpu_threshold:
            self._raise_alert(
                scheduler,
                reason="cpu",
                description="Investigate sustained high CPU usage",
                priority=3,
            )
        else:
            self._active_alerts.discard("cpu")
        
        if memory > memory_threshold:
            self._raise_alert(
                scheduler,
                reason="memory",
                description="Review memory footprint and purge caches if necessary",
                priority=3,
            )
        else:
            self._active_alerts.discard("memory")
    
    def _raise_alert(
        self,
        scheduler: TaskScheduler,
        *,
        reason: str,
        description: str,
        priority: int,
    ) -> None:
        """Raise alerts with user preference awareness."""
        if reason in self._active_alerts:
            return
        
        # Adjust alert priority based on user preferences
        if self._user_working_style.get("interaction_style") == "proactive":
            priority = max(1, priority - 1)  # Increase urgency
        elif self._user_working_style.get("interaction_style") == "reactive":
            priority = min(5, priority + 1)  # Decrease urgency
        
        scheduler.add_task(
            description,
            priority=priority,
            metadata={"source": "optimizer", "reason": reason, "personalized": True},
            autonomous=True,
        )
        self._active_alerts.add(reason)
        LOGGER.warning("Queued personalized optimizer task for reason '%s'", reason)
    
    def _maybe_enqueue_training(self, scheduler: TaskScheduler, feedback: PersonalizedFeedbackCollector) -> None:
        """Enqueue training with personalization considerations."""
        dataset_path: Path = self._config.dataset_path
        sample_count = self._training_runner.sample_count(dataset_path)
        threshold = self._config.min_samples_for_training
        
        # Adjust training frequency based on user satisfaction
        if feedback.user_preferences.feedback_score < 0.7:
            # If user is dissatisfied, trigger training more frequently
            threshold = max(10, int(threshold * 0.6))
        
        if sample_count < threshold:
            self._last_training_sample_count = sample_count
            return
        
        if sample_count == self._last_training_sample_count:
            return
        
        decision: ScheduledTrainingTask = schedule_training_if_ready(
            scheduler,
            self._config,
            strategy=self._config.training_strategy,
            dataset_path=dataset_path,
            min_samples=threshold,
        )
        
        if decision.triggered:
            LOGGER.info(
                "Queued personalized fine-tuning job request with %d samples using %s strategy",
                decision.sample_count,
                self._config.training_strategy,
            )
        else:
            LOGGER.debug(
                "Training not enqueued despite threshold met (samples=%d, threshold=%d)",
                decision.sample_count,
                decision.threshold,
            )
        
        self._last_training_sample_count = sample_count
    
    def _maybe_adapt_to_user_style(self, scheduler: TaskScheduler, feedback: PersonalizedFeedbackCollector) -> None:
        """Apply adaptations based on learned user working style."""
        # Adjust tool preferences based on user's preferred tools
        preferred_tool = feedback.get_preferred_tool_for_task("general")
        if preferred_tool:
            # Schedule tasks that utilize the user's preferred tools
            scheduler.add_task(
                f"Utilize preferred tool: {preferred_tool}",
                priority=2,
                metadata={
                    "source": "optimizer", 
                    "reason": "user_preference", 
                    "preferred_tool": preferred_tool,
                    "personalized": True
                },
                autonomous=True,
            )
        
        # Apply workflow pattern recognition
        workflow_pattern = feedback.get_workflow_pattern()
        if workflow_pattern.get("most_common_goal_types"):
            # Identify the most common goal type
            most_common_type = max(
                workflow_pattern["most_common_goal_types"].items(),
                key=lambda x: x[1]
            )[0]
            
            # Schedule tasks related to the user's common patterns
            scheduler.add_task(
                f"Optimize for {most_common_type} workflows",
                priority=2,
                metadata={
                    "source": "optimizer", 
                    "reason": "workflow_pattern", 
                    "goal_type": most_common_type,
                    "personalized": True
                },
                autonomous=True,
            )