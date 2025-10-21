"""
Transparent Reporting and Action Logging System for AGI Codex
Provides comprehensive logging and reporting of all AGI actions with transparency
"""
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
import csv
from dataclasses import dataclass, field
import os


class ActionType(Enum):
    """Types of actions that can be performed by the AGI"""
    TOOL_EXECUTION = "tool_execution"
    MEMORY_OPERATION = "memory_operation"
    LEARNING_EVENT = "learning_event"
    TASK_EXECUTION = "task_execution"
    SYSTEM_OPERATION = "system_operation"
    WEB_ACCESS = "web_access"
    FILE_OPERATION = "file_operation"
    TERMINAL_COMMAND = "terminal_command"
    API_CALL = "api_call"
    PLANNING = "planning"
    REASONING = "reasoning"


class LogLevel(Enum):
    """Log levels for reporting"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ActionLogEntry:
    """Represents a single action log entry"""
    timestamp: datetime
    action_type: ActionType
    action_id: str
    description: str
    details: Dict[str, Any]
    agent_id: str
    status: str  # 'started', 'completed', 'failed', 'cancelled'
    duration_ms: Optional[float] = None
    user_consent: Optional[bool] = None
    risk_level: Optional[str] = None  # 'low', 'medium', 'high', 'critical'
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TransparentReportingSystem:
    """
    System for transparent reporting and action logging
    """
    def __init__(self, log_dir: Path, max_log_size_mb: int = 100):
        self.log_dir = log_dir
        self.max_log_size_mb = max_log_size_mb
        self.logger = logging.getLogger(__name__)
        
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize log files
        self.action_log_path = self.log_dir / "actions.log"
        self.summary_log_path = self.log_dir / "summary.log"
        
        # Initialize action counter
        self.action_counter = 0
        
        # Initialize the log files
        self._init_log_files()
        
        # For async logging
        self.log_queue = asyncio.Queue()
        self._logging_task = None

    def _init_log_files(self):
        """Initialize log files if they don't exist"""
        for log_path in [self.action_log_path, self.summary_log_path]:
            if not log_path.exists():
                log_path.touch()

    def log_action(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any],
        agent_id: str,
        status: str = "completed",
        duration_ms: Optional[float] = None,
        user_consent: Optional[bool] = None,
        risk_level: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Log an action with full transparency
        """
        self.action_counter += 1
        action_id = f"action_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.action_counter:04d}"
        
        log_entry = ActionLogEntry(
            timestamp=datetime.now(),
            action_type=action_type,
            action_id=action_id,
            description=description,
            details=details,
            agent_id=agent_id,
            status=status,
            duration_ms=duration_ms,
            user_consent=user_consent,
            risk_level=risk_level,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        # Write to action log
        self._write_action_log(log_entry)
        
        # Write summary to summary log
        self._write_summary_log(log_entry)
        
        # Log to standard logger as well
        self.logger.info(f"Action {action_id}: {description} - Status: {status}")
        
        return action_id

    def _write_action_log(self, entry: ActionLogEntry):
        """Write action log entry to the action log file"""
        try:
            with open(self.action_log_path, 'a', encoding='utf-8') as f:
                log_dict = asdict(entry)
                # Convert datetime to ISO format string
                log_dict['timestamp'] = entry.timestamp.isoformat()
                f.write(json.dumps(log_dict) + '\n')
        except Exception as e:
            self.logger.error(f"Error writing action log: {e}")

    def _write_summary_log(self, entry: ActionLogEntry):
        """Write a summary of the action to the summary log file"""
        try:
            summary = {
                'timestamp': entry.timestamp.isoformat(),
                'action_id': entry.action_id,
                'action_type': entry.action_type.value,
                'description': entry.description,
                'status': entry.status,
                'risk_level': entry.risk_level,
                'agent_id': entry.agent_id
            }
            
            with open(self.summary_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(summary) + '\n')
        except Exception as e:
            self.logger.error(f"Error writing summary log: {e}")

    def get_action_history(
        self,
        limit: int = 100,
        action_types: List[ActionType] = None,
        status_filter: str = None,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> List[ActionLogEntry]:
        """
        Retrieve action history with various filters
        """
        try:
            entries = []
            with open(self.action_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # Convert timestamp back to datetime
                            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                            entry = ActionLogEntry(**data)
                            
                            # Apply filters
                            if action_types and entry.action_type not in action_types:
                                continue
                            if status_filter and entry.status != status_filter:
                                continue
                            if date_from and entry.timestamp < date_from:
                                continue
                            if date_to and entry.timestamp > date_to:
                                continue
                                
                            entries.append(entry)
                        except Exception as e:
                            self.logger.error(f"Error parsing log entry: {e}")
            
            # Return most recent entries first, limited by the specified limit
            return sorted(entries, key=lambda x: x.timestamp, reverse=True)[:limit]
        except Exception as e:
            self.logger.error(f"Error retrieving action history: {e}")
            return []

    def generate_report(
        self,
        report_type: str = "daily",
        date_from: datetime = None,
        date_to: datetime = None
    ) -> Dict[str, Any]:
        """
        Generate various types of reports
        """
        if report_type == "daily":
            if not date_from:
                date_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if not date_to:
                date_to = datetime.now()
        elif report_type == "weekly":
            if not date_from:
                date_from = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            if not date_to:
                date_to = datetime.now()
        elif report_type == "monthly":
            if not date_from:
                date_from = (datetime.now() - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
            if not date_to:
                date_to = datetime.now()
        
        # Count actions by type
        action_counts = {}
        risk_counts = {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        total_actions = 0
        
        with open(self.action_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line)
                        entry_timestamp = datetime.fromisoformat(data['timestamp'])
                        
                        if date_from <= entry_timestamp <= date_to:
                            action_type = data['action_type']
                            action_counts[action_type] = action_counts.get(action_type, 0) + 1
                            
                            risk_level = data.get('risk_level')
                            if risk_level in risk_counts:
                                risk_counts[risk_level] += 1
                            
                            total_actions += 1
                    except Exception:
                        continue  # Skip malformed entries
        
        return {
            "report_type": report_type,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "total_actions": total_actions,
            "action_counts": action_counts,
            "risk_distribution": risk_counts,
            "generated_at": datetime.now().isoformat()
        }

    def export_logs(self, export_format: str = "json", output_path: Path = None) -> Path:
        """
        Export logs in various formats
        """
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agi_logs_{timestamp}.{export_format}"
            output_path = self.log_dir / filename
        
        if export_format == "json":
            # Just copy the action log as is
            import shutil
            shutil.copy2(self.action_log_path, output_path)
        elif export_format == "csv":
            # Convert JSON log to CSV
            with open(self.action_log_path, 'r', encoding='utf-8') as input_file, \
                 open(output_path, 'w', newline='', encoding='utf-8') as output_file:
                
                fieldnames = [
                    'timestamp', 'action_type', 'action_id', 'description', 
                    'status', 'duration_ms', 'user_consent', 'risk_level', 
                    'agent_id', 'details'
                ]
                
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                
                for line in input_file:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            # Convert nested details to string
                            data['details'] = json.dumps(data.get('details', {}))
                            # Convert timestamp to string if it's a datetime object
                            if isinstance(data['timestamp'], datetime):
                                data['timestamp'] = data['timestamp'].isoformat()
                            writer.writerow(data)
                        except Exception:
                            continue  # Skip malformed entries
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        return output_path

    def get_transparency_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for transparency dashboard
        """
        # Get recent actions
        recent_actions = self.get_action_history(limit=10)
        
        # Get summary statistics
        total_actions = len(self.get_action_history(limit=10000))
        recent_24h = self.get_action_history(
            date_from=datetime.now() - timedelta(hours=24)
        )
        
        # Count by action type
        type_counts = {}
        for action in recent_24h:
            action_type = action.action_type.value
            type_counts[action_type] = type_counts.get(action_type, 0) + 1
        
        # Count by risk level
        risk_counts = {}
        for action in recent_24h:
            risk_level = action.risk_level or "unknown"
            risk_counts[risk_level] = risk_counts.get(risk_level, 0) + 1
        
        return {
            "total_actions": total_actions,
            "recent_actions": [
                {
                    "action_id": action.action_id,
                    "description": action.description,
                    "action_type": action.action_type.value,
                    "timestamp": action.timestamp.isoformat(),
                    "status": action.status,
                    "risk_level": action.risk_level
                }
                for action in recent_actions
            ],
            "last_24h_counts": {
                "total": len(recent_24h),
                "by_type": type_counts,
                "by_risk": risk_counts
            },
            "last_updated": datetime.now().isoformat()
        }

    def cleanup_logs(self, retention_days: int = 30):
        """
        Clean up old logs based on retention policy
        """
        try:
            import tempfile
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            # Create temporary files for filtered logs
            temp_action_log = self.log_dir / "temp_action.log"
            temp_summary_log = self.log_dir / "temp_summary.log"
            
            # Filter action log
            with open(self.action_log_path, 'r', encoding='utf-8') as input_file, \
                 open(temp_action_log, 'w', encoding='utf-8') as output_file:
                for line in input_file:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            timestamp = datetime.fromisoformat(data['timestamp'])
                            if timestamp >= cutoff_date:
                                output_file.write(line)
                        except Exception:
                            continue  # Skip malformed entries
            
            # Filter summary log
            with open(self.summary_log_path, 'r', encoding='utf-8') as input_file, \
                 open(temp_summary_log, 'w', encoding='utf-8') as output_file:
                for line in input_file:
                    if line.strip():
                        try:
                            data = json.loads(line)
                            timestamp = datetime.fromisoformat(data['timestamp'])
                            if timestamp >= cutoff_date:
                                output_file.write(line)
                        except Exception:
                            continue  # Skip malformed entries
            
            # Replace original files with filtered ones
            temp_action_log.replace(self.action_log_path)
            temp_summary_log.replace(self.summary_log_path)
            
            self.logger.info(f"Log cleanup completed. Retained logs from {cutoff_date.date()} onwards")
        except Exception as e:
            self.logger.error(f"Error during log cleanup: {e}")


class ReportingManager:
    """
    Manager for the reporting system
    """
    def __init__(self, config):
        self.config = config
        self.reporting_system = TransparentReportingSystem(
            log_dir=config.logging.log_dir / "reporting",
            max_log_size_mb=getattr(config.learning, 'max_log_size_mb', 100)
        )
        self.logger = logging.getLogger(__name__)

    def log_action(
        self,
        action_type: ActionType,
        description: str,
        details: Dict[str, Any],
        agent_id: str = "agi_agent",
        status: str = "completed",
        duration_ms: Optional[float] = None,
        user_consent: Optional[bool] = None,
        risk_level: Optional[str] = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Log an action through the reporting system
        """
        return self.reporting_system.log_action(
            action_type=action_type,
            description=description,
            details=details,
            agent_id=agent_id,
            status=status,
            duration_ms=duration_ms,
            user_consent=user_consent,
            risk_level=risk_level,
            tags=tags,
            metadata=metadata
        )

    def get_transparency_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for the transparency dashboard
        """
        return self.reporting_system.get_transparency_dashboard_data()

    def generate_report(self, report_type: str = "daily") -> Dict[str, Any]:
        """
        Generate a report
        """
        return self.reporting_system.generate_report(report_type=report_type)

    def export_logs(self, export_format: str = "json") -> Path:
        """
        Export logs
        """
        return self.reporting_system.export_logs(export_format=export_format)

    def cleanup_logs(self, retention_days: int = 30):
        """
        Clean up old logs
        """
        self.reporting_system.cleanup_logs(retention_days=retention_days)