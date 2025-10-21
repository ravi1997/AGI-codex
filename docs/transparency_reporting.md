# Transparent Reporting and Action Logging System for AGI Codex

This document provides an overview of the transparent reporting and action logging capabilities of the AGI Codex project, ensuring full visibility into all AGI actions and decisions.

## Overview

The Transparent Reporting and Action Logging System provides comprehensive logging and reporting of all AGI actions with full transparency. This system ensures users can understand, review, and audit all activities performed by the AGI system.

## Components

### 1. TransparentReportingSystem

The core system that handles all logging and reporting functionality.

**Features:**
- Comprehensive action logging with full context
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Action categorization by type
- Risk level assessment for each action
- User consent tracking
- Flexible filtering and querying capabilities

### 2. ReportingManager

The manager that orchestrates the reporting system and provides high-level interfaces.

**Features:**
- Simplified logging interface
- Report generation capabilities
- Transparency dashboard data
- Log export functionality
- Log cleanup and retention management

### 3. ActionLogEntry

Data structure representing a single logged action with all relevant details.

**Fields:**
- `timestamp`: When the action occurred
- `action_type`: Type of action (tool execution, memory operation, etc.)
- `action_id`: Unique identifier for the action
- `description`: Human-readable description of the action
- `details`: Additional technical details about the action
- `agent_id`: Identifier of the agent performing the action
- `status`: Current status (started, completed, failed, cancelled)
- `duration_ms`: How long the action took to complete
- `user_consent`: Whether user consent was obtained
- `risk_level`: Risk level assessment (low, medium, high, critical)
- `tags`: Additional tags for categorization
- `metadata`: Additional metadata

## Action Types

The system categorizes actions into the following types:

- `TOOL_EXECUTION`: Execution of any tool (terminal, browser, file I/O, etc.)
- `MEMORY_OPERATION`: Operations on memory systems (episodic, semantic, procedural)
- `LEARNING_EVENT`: Learning-related activities
- `TASK_EXECUTION`: Execution of autonomous or user-requested tasks
- `SYSTEM_OPERATION`: System-level operations
- `WEB_ACCESS`: Web browsing and content retrieval
- `FILE_OPERATION`: File system operations
- `TERMINAL_COMMAND`: Terminal command execution
- `API_CALL`: API calls to external services
- `PLANNING`: Planning and decision-making processes
- `REASONING`: Reasoning and inference activities

## Log Files

The system maintains two main log files:

### Actions Log (`actions.log`)
- Contains complete details of all actions
- Each line is a JSON object representing a single action
- Used for detailed analysis and auditing

### Summary Log (`summary.log`)
- Contains high-level summaries of actions
- Each line is a JSON object with key action information
- Used for quick overview and dashboard display

## Configuration

The reporting system is configured through the main configuration file. Key configuration options include:

### Logging Settings
- `log_dir`: Directory where logs are stored
- `max_log_size_mb`: Maximum size of log files before rotation

### Reporting Settings
- `retention_days`: How long to retain logs
- `report_types`: Types of reports to generate
- `dashboard_enabled`: Whether to enable the transparency dashboard

## Usage Examples

### Logging an Action
```python
from src.agi_core.system.reporting import ReportingManager, ActionType

reporting_manager = ReportingManager(config)

# Log a tool execution action
action_id = reporting_manager.log_action(
    action_type=ActionType.TOOL_EXECUTION,
    description="Executed terminal command: ls -la",
    details={
        "command": "ls -la",
        "result": "Command executed successfully",
        "exit_code": 0
    },
    agent_id="agi_agent_001",
    status="completed",
    duration_ms=150.5,
    user_consent=True,
    risk_level="low",
    tags=["terminal", "file_system"],
    metadata={"context": "user_request"}
)
```

### Retrieving Action History
```python
# Get recent actions
recent_actions = reporting_manager.get_action_history(limit=10)

# Get actions of specific type
tool_actions = reporting_manager.get_action_history(
    action_types=[ActionType.TOOL_EXECUTION],
    limit=50
)

# Get actions within a date range
from datetime import datetime, timedelta
date_from = datetime.now() - timedelta(days=1)
recent_actions = reporting_manager.get_action_history(
    date_from=date_from
)
```

### Generating Reports
```python
# Generate a daily report
daily_report = reporting_manager.generate_report(report_type="daily")

# Generate a weekly report
weekly_report = reporting_manager.generate_report(report_type="weekly")

# Generate a monthly report
monthly_report = reporting_manager.generate_report(report_type="monthly")
```

### Getting Transparency Dashboard Data
```python
# Get data for transparency dashboard
dashboard_data = reporting_manager.get_transparency_dashboard_data()
print(f"Total actions: {dashboard_data['total_actions']}")
print(f"Recent actions: {len(dashboard_data['recent_actions'])}")
print(f"Last 24h counts: {dashboard_data['last_24h_counts']}")
```

### Exporting Logs
```python
# Export logs in JSON format
json_export_path = reporting_manager.export_logs(export_format="json")

# Export logs in CSV format
csv_export_path = reporting_manager.export_logs(export_format="csv")
```

### Cleaning Up Old Logs
```python
# Clean up logs older than 30 days
reporting_manager.cleanup_logs(retention_days=30)
```

## Transparency Dashboard

The system provides a transparency dashboard with the following information:

### Overview Section
- Total number of actions performed
- Actions in the last 24 hours
- Distribution by action type
- Distribution by risk level

### Recent Actions Section
- List of most recent actions with key details
- Action type, description, timestamp, and status
- Risk level and user consent status

### Trend Analysis Section
- Action volume over time
- Risk level trends
- Most common action types

## Privacy and Security

The reporting system implements several privacy and security measures:

1. **Minimal Data Collection**: Only necessary information is logged
2. **Data Encryption**: Sensitive data can be encrypted before logging
3. **Access Controls**: Log access is restricted to authorized users
4. **Anonymization**: Personal information can be anonymized when possible
5. **Retention Policies**: Automatic cleanup of old logs based on retention settings

## Best Practices

1. **Regular Review**: Regularly review logs to understand AGI behavior
2. **Risk Assessment**: Pay special attention to high-risk actions
3. **User Consent**: Ensure proper user consent for sensitive operations
4. **Audit Trail**: Maintain the audit trail for accountability
5. **Dashboard Monitoring**: Use the transparency dashboard for ongoing monitoring

## Troubleshooting

### Log File Issues
- Check that the log directory has proper write permissions
- Verify that there's sufficient disk space for logs
- Monitor log file sizes to prevent excessive growth

### Performance Issues
- Adjust log retention settings to balance detail with performance
- Consider reducing log verbosity if performance is impacted
- Monitor the impact of logging on AGI performance

### Dashboard Issues
- Verify that the dashboard data is being updated regularly
- Check that all required data sources are accessible
- Review the dashboard refresh interval settings

## Extending the System

The reporting system can be extended by:
1. Adding new action types for specific AGI activities
2. Implementing custom log analysis tools
3. Adding integration with external monitoring systems
4. Enhancing the dashboard with additional visualizations
5. Adding automated alerting for specific action types or risk levels