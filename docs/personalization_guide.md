# AGI Codex Personalization System

This document describes the personalized learning and adaptation system implemented in the AGI Codex framework.

## Overview

The AGI Codex personalization system is designed to learn from user interactions and adapt the AI agent's behavior to match individual user preferences, working styles, and project contexts. The system consists of several interconnected components that work together to provide a personalized experience.

## Components

### 1. Learning Pipeline
- Tracks user interactions and workflow patterns
- Captures execution outcomes for future learning
- Maintains datasets for fine-tuning the AI model
- Implements batch flushing for efficient storage

### 2. Feedback Collection System
- Records user satisfaction and preferences
- Tracks successful and failed execution patterns
- Maintains user preference profiles
- Identifies common goal patterns and preferred tools

### 3. Optimization Mechanisms
- Adapts to user's working style through continuous learning
- Adjusts scheduler intervals based on success rates and user satisfaction
- Processes telemetry alerts with user preference awareness
- Triggers training when user satisfaction is low

### 4. Scheduler with Pattern Recognition
- Performs autonomous tasks based on learned patterns
- Generates tasks tailored to user preferences
- Learns from project context to suggest relevant actions
- Adjusts task priorities based on user preference alignment

### 5. Context Building System
- Maintains awareness of user's projects and goals
- Builds comprehensive context with personalization data
- Enhances embeddings with project and user context
- Tracks goal history for context awareness

### 6. Personalized Planner
- Generates action plans based on user preferences
- Incorporates project context into planning
- Aligns plan steps with working style profile
- Calculates confidence metrics for personalization

### 7. Executor with Safety Checks
- Executes plans with enhanced safety for autonomous operations
- Applies personalization to tool execution parameters
- Maintains execution history for learning
- Validates autonomous tasks against safety and preference criteria

## Configuration

The personalization system is configured through `config/personalized_learning.yaml` which includes settings for:

- Memory storage paths for personalized data
- Learning thresholds and parameters
- Scheduler intervals adapted to user preferences
- Safety settings for autonomous operations
- Personalization-specific flags and parameters

### Key Configuration Parameters

- `interaction_tracking_enabled`: Enable tracking of user interactions
- `workflow_pattern_tracking`: Enable tracking of workflow patterns
- `user_preference_learning`: Enable learning from user preferences
- `adaptation_mechanisms_enabled`: Enable adaptation mechanisms
- `context_awareness_enabled`: Enable context awareness
- `personalized_planning_enabled`: Enable personalized planning
- `safety_enhanced_execution`: Enable safety for autonomous operations

## Usage

The personalization system operates automatically as users interact with the AGI Codex system. As the agent performs tasks, it learns from:

1. **Success/Failure Patterns**: Understanding what approaches work best for the user
2. **Tool Preferences**: Learning which tools the user prefers for specific tasks
3. **Working Style**: Adapting to the user's interaction patterns and preferences
4. **Project Context**: Maintaining awareness of current projects and goals
5. **Feedback**: Incorporating explicit user feedback when provided

## Safety Considerations

The system includes multiple safety mechanisms:

- Conservative execution for users with low autonomous comfort
- Safety validation for all autonomous operations
- Preference alignment checks before executing plans
- Configurable safety levels based on user comfort

## Data Storage

Personalization data is stored in the following locations:

- Feedback and preferences: `storage/analytics/personalized_feedback.json`
- Learning datasets: `storage/learning/personalized_dataset.jsonl`
- Memory: `storage/episodic/personalized_memory.json` and `storage/semantic/personalized_knowledge.json`
- Models: `storage/learning/personalized_models/`

## Integration Points

The personalization system integrates with existing AGI Codex components through:

- Enhanced configuration loading
- Personalized context building
- Specialized planner and executor implementations
- Extended feedback and optimization systems

## Extending Personalization

To extend the personalization system:

1. Add new preference categories to `PersonalizedFeedbackCollector`
2. Enhance the context builder with additional awareness capabilities
3. Modify the planner to consider new personalization factors
4. Update the executor with additional safety checks or personalization logic