"""Audit logging for all actions taken by the autonomous system."""
from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    TOOL_EXECUTION = "tool_execution"
    PERMISSION_CHECK = "permission_check"
    CONSENT_REQUEST = "consent_request"
    SECURITY_VIOLATION = "security_violation"
    CREDENTIAL_ACCESS = "credential_access"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    SYSTEM_ACCESS = "system_access"
    USER_ACTION = "user_action"
    AUTONOMOUS_TASK = "autonomous_task"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    id: str
    timestamp: float
    event_type: AuditEventType
    actor: str  # User ID or system component
    action: str  # Description of the action taken
    resource: str  # Resource affected by the action
    metadata: Dict[str, Any] # Additional context-specific data
    success: bool = True
    details: Optional[str] = None


class AuditLogStore(ABC):
    """Abstract base class for audit log storage."""
    
    @abstractmethod
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event."""
        pass
    
    @abstractmethod
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Retrieve audit events with optional filtering."""
        pass
    
    @abstractmethod
    def search_events(self, query: str) -> List[AuditEvent]:
        """Search audit events by query string."""
        pass


class InMemoryAuditLogStore(AuditLogStore):
    """In-memory implementation of audit log store."""
    
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event to memory."""
        self._events.append(event)
        return True
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Retrieve audit events with optional filtering."""
        events = self._events[:]
        
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        
        if actor:
            events = [event for event in events if event.actor == actor]
        
        if start_time:
            events = [event for event in events if event.timestamp >= start_time]
        
        if end_time:
            events = [event for event in events if event.timestamp <= end_time]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            events = events[:limit]
        
        return events
    
    def search_events(self, query: str) -> List[AuditEvent]:
        """Search audit events by query string."""
        query_lower = query.lower()
        matching_events = []
        
        for event in self._events:
            # Search in action, resource, details, and metadata
            search_text = (
                event.action.lower() + " " +
                event.resource.lower() + " " +
                (event.details.lower() if event.details else "") + " " +
                " ".join(str(v).lower() for v in event.metadata.values() if isinstance(v, (str, int, float)))
            )
            
            if query_lower in search_text:
                matching_events.append(event)
        
        # Sort by timestamp (newest first)
        matching_events.sort(key=lambda e: e.timestamp, reverse=True)
        return matching_events


class FileBasedAuditLogStore(AuditLogStore):
    """File-based implementation of audit log store."""
    
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._log_file = self._storage_path / "audit.log"
        self._events: List[AuditEvent] = []
        self._load_events()
    
    def _load_events(self) -> None:
        """Load audit events from file."""
        if self._log_file.exists():
            try:
                with self._log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                event_data = json.loads(line)
                                event = AuditEvent(
                                    id=event_data['id'],
                                    timestamp=event_data['timestamp'],
                                    event_type=AuditEventType(event_data['event_type']),
                                    actor=event_data['actor'],
                                    action=event_data['action'],
                                    resource=event_data['resource'],
                                    metadata=event_data['metadata'],
                                    success=event_data.get('success', True),
                                    details=event_data.get('details')
                                )
                                self._events.append(event)
                            except (json.JSONDecodeError, KeyError, ValueError) as e:
                                LOGGER.warning(f"Failed to parse audit log entry: {e}")
            except Exception as e:
                LOGGER.error(f"Failed to load audit log from file: {e}")
    
    def _append_event(self, event: AuditEvent) -> None:
        """Append a single event to the log file."""
        try:
            with self._log_file.open("a", encoding="utf-8") as f:
                event_data = {
                    'id': event.id,
                    'timestamp': event.timestamp,
                    'event_type': event.event_type.value,
                    'actor': event.actor,
                    'action': event.action,
                    'resource': event.resource,
                    'metadata': event.metadata,
                    'success': event.success,
                    'details': event.details
                }
                f.write(json.dumps(event_data) + "\n")
        except Exception as e:
            LOGGER.error(f"Failed to write audit log entry: {e}")
    
    def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event to file."""
        try:
            # Add to in-memory list
            self._events.append(event)
            
            # Append to file
            self._append_event(event)
            
            # Keep only recent events to prevent unbounded growth
            # In a real implementation, you might want to implement log rotation
            if len(self._events) > 10000:  # Keep last 10k events
                self._events = self._events[-5000:]  # Keep last 5k in memory
            
            return True
        except Exception as e:
            LOGGER.error(f"Failed to log audit event: {e}")
            return False
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Retrieve audit events with optional filtering."""
        # Reload from file to ensure latest data
        self._load_events()
        
        events = self._events[:]
        
        if event_type:
            events = [event for event in events if event.event_type == event_type]
        
        if actor:
            events = [event for event in events if event.actor == actor]
        
        if start_time:
            events = [event for event in events if event.timestamp >= start_time]
        
        if end_time:
            events = [event for event in events if event.timestamp <= end_time]
        
        # Sort by timestamp (newest first)
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        if limit:
            events = events[:limit]
        
        return events
    
    def search_events(self, query: str) -> List[AuditEvent]:
        """Search audit events by query string."""
        # Reload from file to ensure latest data
        self._load_events()
        
        query_lower = query.lower()
        matching_events = []
        
        for event in self._events:
            # Search in action, resource, details, and metadata
            search_text = (
                event.action.lower() + " " +
                event.resource.lower() + " " +
                (event.details.lower() if event.details else "") + " " +
                " ".join(str(v).lower() for v in event.metadata.values() if isinstance(v, (str, int, float)))
            )
            
            if query_lower in search_text:
                matching_events.append(event)
        
        # Sort by timestamp (newest first)
        matching_events.sort(key=lambda e: e.timestamp, reverse=True)
        return matching_events


class AuditLogger:
    """Main audit logging system."""
    
    def __init__(self, audit_store: AuditLogStore) -> None:
        self._audit_store = audit_store
        self._logger = logging.getLogger(__name__ + ".audit")
    
    def log_event(
        self,
        event_type: AuditEventType,
        actor: str,
        action: str,
        resource: str,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        details: Optional[str] = None
    ) -> str:
        """Log an audit event."""
        import time
        event_id = f"audit_{int(time.time() * 1000)}_{hash(action) % 1000}"
        
        event = AuditEvent(
            id=event_id,
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            metadata=metadata or {},
            success=success,
            details=details
        )
        
        success = self._audit_store.log_event(event)
        if success:
            self._logger.info(f"Audit event logged: {event_id} - {event_type.value} by {actor}")
            return event_id
        else:
            self._logger.error(f"Failed to log audit event: {event_type.value} by {actor}")
            return ""
    
    def log_tool_execution(
        self,
        actor: str,
        tool_name: str,
        parameters: Dict[str, Any],
        success: bool,
        result: Optional[str] = None
    ) -> str:
        """Log a tool execution event."""
        return self.log_event(
            event_type=AuditEventType.TOOL_EXECUTION,
            actor=actor,
            action=f"Executed tool: {tool_name}",
            resource=tool_name,
            metadata={"parameters": parameters, "result_length": len(result) if result else 0},
            success=success,
            details=result
        )
    
    def log_permission_check(
        self,
        actor: str,
        resource: str,
        permission_level: str,
        granted: bool,
        reason: Optional[str] = None
    ) -> str:
        """Log a permission check event."""
        return self.log_event(
            event_type=AuditEventType.PERMISSION_CHECK,
            actor=actor,
            action=f"Checked permission: {permission_level} for {resource}",
            resource=resource,
            metadata={"permission_level": permission_level, "granted": granted},
            success=granted,
            details=reason
        )
    
    def log_security_violation(
        self,
        actor: str,
        violation_type: str,
        attempted_action: str,
        details: Optional[str] = None
    ) -> str:
        """Log a security violation event."""
        return self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            actor=actor,
            action=f"Security violation: {violation_type}",
            resource=attempted_action,
            metadata={"violation_type": violation_type},
            success=False,
            details=details
        )
    
    def log_credential_access(
        self,
        actor: str,
        credential_id: str,
        service: str,
        success: bool
    ) -> str:
        """Log a credential access event."""
        return self.log_event(
            event_type=AuditEventType.CREDENTIAL_ACCESS,
            actor=actor,
            action=f"Accessed credential for: {service}",
            resource=credential_id,
            metadata={"service": service},
            success=success
        )
    
    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """Retrieve audit events with optional filtering."""
        return self._audit_store.get_events(
            event_type=event_type,
            actor=actor,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def search_events(self, query: str) -> List[AuditEvent]:
        """Search audit events by query string."""
        return self._audit_store.search_events(query)
    
    def get_recent_events(self, hours: int = 24, limit: int = 100) -> List[AuditEvent]:
        """Get recent audit events."""
        import time
        start_time = time.time() - (hours * 3600)
        return self.get_events(start_time=start_time, limit=limit)
    
    def get_security_violations(self, hours: int = 24) -> List[AuditEvent]:
        """Get recent security violations."""
        import time
        start_time = time.time() - (hours * 3600)
        return self.get_events(
            event_type=AuditEventType.SECURITY_VIOLATION,
            start_time=start_time
        )