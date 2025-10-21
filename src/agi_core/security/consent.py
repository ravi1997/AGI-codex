"""User consent mechanisms for autonomous operations."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class ConsentType(Enum):
    """Types of consent that can be requested."""
    AUTONOMOUS_EXECUTION = "autonomous_execution"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    APPLICATION_ACCESS = "application_access"
    SYSTEM_MONITORING = "system_monitoring"
    CREDENTIAL_ACCESS = "credential_access"
    TERMINAL_ACCESS = "terminal_access"
    BROWSER_ACCESS = "browser_access"


class ConsentDecision(Enum):
    """Possible consent decisions."""
    GRANTED = "granted"
    DENIED = "denied"
    TIMEOUT = "timeout"
    PENDING = "pending"


@dataclass
class ConsentRequest:
    """Represents a request for user consent."""
    id: str
    type: ConsentType
    description: str
    timestamp: float
    expiry_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    decision: ConsentDecision = ConsentDecision.PENDING
    decision_timestamp: Optional[float] = None
    decision_reason: Optional[str] = None


class ConsentStore(ABC):
    """Abstract base class for consent storage."""
    
    @abstractmethod
    def store_request(self, request: ConsentRequest) -> None:
        """Store a consent request."""
        pass
    
    @abstractmethod
    def get_request(self, request_id: str) -> Optional[ConsentRequest]:
        """Get a consent request by ID."""
        pass
    
    @abstractmethod
    def update_request(self, request: ConsentRequest) -> None:
        """Update an existing consent request."""
        pass
    
    @abstractmethod
    def get_pending_requests(self) -> List[ConsentRequest]:
        """Get all pending consent requests."""
        pass
    
    @abstractmethod
    def cleanup_expired_requests(self) -> None:
        """Remove expired consent requests."""
        pass


class InMemoryConsentStore(ConsentStore):
    """In-memory implementation of consent store."""
    
    def __init__(self) -> None:
        self._requests: Dict[str, ConsentRequest] = {}
    
    def store_request(self, request: ConsentRequest) -> None:
        """Store a consent request."""
        self._requests[request.id] = request
    
    def get_request(self, request_id: str) -> Optional[ConsentRequest]:
        """Get a consent request by ID."""
        return self._requests.get(request_id)
    
    def update_request(self, request: ConsentRequest) -> None:
        """Update an existing consent request."""
        if request.id in self._requests:
            self._requests[request.id] = request
    
    def get_pending_requests(self) -> List[ConsentRequest]:
        """Get all pending consent requests."""
        return [
            req for req in self._requests.values()
            if req.decision == ConsentDecision.PENDING
            and (req.expiry_time is None or time.time() < req.expiry_time)
        ]
    
    def cleanup_expired_requests(self) -> None:
        """Remove expired consent requests."""
        current_time = time.time()
        expired_ids = [
            req_id for req_id, req in self._requests.items()
            if req.expiry_time is not None and current_time >= req.expiry_time
        ]
        for req_id in expired_ids:
            del self._requests[req_id]


class FileBasedConsentStore(ConsentStore):
    """File-based implementation of consent store."""
    
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._requests: Dict[str, ConsentRequest] = {}
        self._load_requests()
    
    def _load_requests(self) -> None:
        """Load consent requests from storage."""
        # For now, implement basic functionality
        pass
    
    def store_request(self, request: ConsentRequest) -> None:
        """Store a consent request to file."""
        self._requests[request.id] = request
        # In a real implementation, this would serialize to file
    
    def get_request(self, request_id: str) -> Optional[ConsentRequest]:
        """Get a consent request by ID from file."""
        return self._requests.get(request_id)
    
    def update_request(self, request: ConsentRequest) -> None:
        """Update an existing consent request in file."""
        if request.id in self._requests:
            self._requests[request.id] = request
            # In a real implementation, this would update the file
    
    def get_pending_requests(self) -> List[ConsentRequest]:
        """Get all pending consent requests from file."""
        return [
            req for req in self._requests.values()
            if req.decision == ConsentDecision.PENDING
            and (req.expiry_time is None or time.time() < req.expiry_time)
        ]
    
    def cleanup_expired_requests(self) -> None:
        """Remove expired consent requests from file."""
        current_time = time.time()
        expired_ids = [
            req_id for req_id, req in self._requests.items()
            if req.expiry_time is not None and current_time >= req.expiry_time
        ]
        for req_id in expired_ids:
            del self._requests[req_id]
            # In a real implementation, this would remove the file entry


class ConsentManager:
    """Manages user consent for autonomous operations."""
    
    def __init__(self, consent_store: ConsentStore) -> None:
        self._consent_store = consent_store
        self._default_timeout = 300  # 5 minutes
    
    def request_consent(
        self,
        consent_type: ConsentType,
        description: str,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Request user consent for an operation."""
        request_id = f"consent_{int(time.time() * 1000)}_{hash(description) % 10000}"
        expiry_time = time.time() + (timeout or self._default_timeout)
        
        request = ConsentRequest(
            id=request_id,
            type=consent_type,
            description=description,
            timestamp=time.time(),
            expiry_time=expiry_time,
            metadata=metadata
        )
        
        self._consent_store.store_request(request)
        LOGGER.info(f"Consent requested: {request_id} for {consent_type.value} - {description}")
        
        return request_id
    
    def check_consent(self, request_id: str) -> ConsentDecision:
        """Check the status of a consent request."""
        request = self._consent_store.get_request(request_id)
        if not request:
            LOGGER.warning(f"Consent request not found: {request_id}")
            return ConsentDecision.DENIED
        
        # Check if request has expired
        if request.expiry_time and time.time() > request.expiry_time:
            request.decision = ConsentDecision.TIMEOUT
            self._consent_store.update_request(request)
            return ConsentDecision.TIMEOUT
        
        return request.decision
    
    def grant_consent(self, request_id: str, reason: Optional[str] = None) -> bool:
        """Grant consent for a request."""
        request = self._consent_store.get_request(request_id)
        if not request or request.decision != ConsentDecision.PENDING:
            return False
        
        request.decision = ConsentDecision.GRANTED
        request.decision_timestamp = time.time()
        request.decision_reason = reason
        self._consent_store.update_request(request)
        
        LOGGER.info(f"Consent granted: {request_id}")
        return True
    
    def deny_consent(self, request_id: str, reason: Optional[str] = None) -> bool:
        """Deny consent for a request."""
        request = self._consent_store.get_request(request_id)
        if not request or request.decision != ConsentDecision.PENDING:
            return False
        
        request.decision = ConsentDecision.DENIED
        request.decision_timestamp = time.time()
        request.decision_reason = reason
        self._consent_store.update_request(request)
        
        LOGGER.info(f"Consent denied: {request_id}")
        return True
    
    def is_consent_required(self, consent_type: ConsentType) -> bool:
        """Check if consent is required for a specific type of operation."""
        # In a real implementation, this would check against user preferences
        # For now, return True for all types to enforce consent
        return True
    
    def get_pending_requests(self) -> List[ConsentRequest]:
        """Get all pending consent requests."""
        return self._consent_store.get_pending_requests()
    
    def cleanup_expired_requests(self) -> None:
        """Clean up expired consent requests."""
        self._consent_store.cleanup_expired_requests()
    
    def has_active_consent(
        self,
        consent_type: ConsentType,
        description: Optional[str] = None,
        max_age: int = 3600  # 1 hour
    ) -> bool:
        """Check if there's recent consent for a similar operation."""
        # In a real implementation, this would check for previously granted consents
        # that match the type and description within the max_age window
        return False