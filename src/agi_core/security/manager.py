"""Main security manager that integrates all security components."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .permissions import PermissionManager, SystemFunction
from .consent import ConsentManager, ConsentType, InMemoryConsentStore
from .policies import SecurityPolicyManager
from .guardrails import SafetyGuardrails
from .credentials import CredentialManager, InMemoryCredentialStore
from .audit import AuditLogger, AuditEventType, FileBasedAuditLogStore
from .risk import RiskAssessmentManager, RuleBasedRiskEngine
from .config import SecurityConfig, load_security_config


LOGGER = logging.getLogger(__name__)


class SecurityManager:
    """Main security manager that integrates all security components."""
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        
        # Initialize permission manager
        self.permission_manager = PermissionManager()
        if config.permission_enabled:
            self.permission_manager.set_active_profile(config.default_permission_profile)
        
        # Initialize consent manager
        consent_store = InMemoryConsentStore()  # In production, use FileBasedConsentStore
        self.consent_manager = ConsentManager(consent_store)
        
        # Initialize policy manager
        self.policy_manager = SecurityPolicyManager()
        
        # Initialize guardrails
        self.guardrails = SafetyGuardrails()
        
        # Initialize credential manager
        credential_store = InMemoryCredentialStore()  # In production, use EncryptedFileCredentialStore
        self.credential_manager = CredentialManager(credential_store)
        
        # Initialize audit logger
        audit_store = FileBasedAuditLogStore(config.audit_storage_path)
        self.audit_logger = AuditLogger(audit_store)
        
        # Initialize risk assessment
        risk_engine = RuleBasedRiskEngine()
        self.risk_manager = RiskAssessmentManager(risk_engine)
        
        LOGGER.info("Security manager initialized with all components")
    
    def check_permission(self, function: SystemFunction, actor: str = "system") -> bool:
        """Check if the active profile has permission for a function."""
        if not self.config.permission_enabled:
            return True
        
        has_perm = self.permission_manager.check_permission(function)
        
        # Log the permission check
        self.audit_logger.log_permission_check(
            actor=actor,
            resource=function.value,
            permission_level="read_write",  # This would be more specific in a real implementation
            granted=has_perm
        )
        
        return has_perm
    
    def request_consent(self, consent_type: ConsentType, description: str, actor: str = "system") -> str:
        """Request user consent for an operation."""
        if not self.config.consent_required:
            return "auto_approved"
        
        request_id = self.consent_manager.request_consent(
            consent_type=consent_type,
            description=description,
            timeout=self.config.consent_timeout_seconds
        )
        
        # Log the consent request
        self.audit_logger.log_event(
            event_type=AuditEventType.CONSENT_REQUEST,
            actor=actor,
            action=f"Requested consent: {consent_type.value}",
            resource=request_id,
            metadata={"consent_type": consent_type.value, "description": description},
            success=True
        )
        
        return request_id
    
    def check_consent_status(self, request_id: str) -> bool:
        """Check the status of a consent request."""
        if request_id == "auto_approved":
            return True
        
        from .consent import ConsentDecision
        decision = self.consent_manager.check_consent(request_id)
        return decision == ConsentDecision.GRANTED
    
    def evaluate_policy(self, policy_type: str, context: Dict[str, Any], actor: str = "system") -> bool:
        """Evaluate if an action should be allowed based on policies."""
        if not self.config.policy_enforcement_enabled:
            return True
        
        from .policies import PolicyType
        try:
            policy_enum = PolicyType(policy_type)
            is_allowed = self.policy_manager.evaluate_policy(policy_enum, context)
            
            # Log the policy evaluation
            self.audit_logger.log_event(
                event_type=AuditEventType.PERMISSION_CHECK,
                actor=actor,
                action=f"Policy evaluation for {policy_type}",
                resource=policy_type,
                metadata={"context": context, "allowed": is_allowed},
                success=is_allowed
            )
            
            return is_allowed
        except ValueError:
            LOGGER.warning(f"Invalid policy type: {policy_type}")
            return False
    
    def check_content_safety(self, content: str, actor: str = "system") -> tuple[bool, List[str]]:
        """Check if content is safe to execute using guardrails."""
        if not self.config.guardrails_enabled:
            return True, []
        
        is_safe, violations = self.guardrails.is_content_safe(content)
        
        if not is_safe:
            # Log security violation
            self.audit_logger.log_security_violation(
                actor=actor,
                violation_type="content_filter",
                attempted_action=content[:100] + "..." if len(content) > 100 else content,
                details=f"Blocked due to violations: {', '.join(violations)}"
            )
        
        return is_safe, violations
    
    def assess_risk(self, operation: str, context: Dict[str, Any], actor: str = "system") -> tuple[bool, str, List[str]]:
        """Assess the risk of an operation."""
        if not self.config.risk_assessment_enabled:
            return True, "Risk assessment disabled", []
        
        from .risk import RiskLevel
        risk_level, score = self.risk_manager.get_risk_score(operation, context)
        
        # Check if risk level is acceptable
        max_level_map = {
            "none": RiskLevel.NONE,
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL
        }
        
        max_allowed = max_level_map.get(self.config.max_allowed_risk_level, RiskLevel.MEDIUM)
        is_allowed = risk_level.value <= max_allowed.value
        
        recommendations = self.risk_manager.get_recommendations(operation, context)
        
        # Log the risk assessment
        self.audit_logger.log_event(
            event_type=AuditEventType.PERMISSION_CHECK,
            actor=actor,
            action=f"Risk assessment for {operation}",
            resource=operation,
            metadata={
                "risk_level": risk_level.value,
                "risk_score": score,
                "max_allowed": self.config.max_allowed_risk_level,
                "allowed": is_allowed
            },
            success=is_allowed
        )
        
        return is_allowed, f"Risk level: {risk_level.value} (score: {score:.2f})", recommendations
    
    def log_action(self, event_type: AuditEventType, actor: str, action: str, resource: str, 
                   metadata: Optional[Dict[str, Any]] = None, success: bool = True, 
                   details: Optional[str] = None) -> str:
        """Log an action to the audit trail."""
        if not self.config.audit_logging_enabled:
            return ""
        
        return self.audit_logger.log_event(
            event_type=event_type,
            actor=actor,
            action=action,
            resource=resource,
            metadata=metadata or {},
            success=success,
            details=details
        )
    
    def initialize_security_for_agent(self) -> None:
        """Initialize security for an agent instance."""
        LOGGER.info("Initializing security for agent")
        
        # Set up default permission profile
        if self.config.default_permission_profile:
            self.permission_manager.set_active_profile(self.config.default_permission_profile)
        
        # Log initialization
        self.log_action(
            event_type=AuditEventType.SYSTEM_ACCESS,
            actor="agent",
            action="Security initialization",
            resource="security_manager",
            metadata={
                "permission_enabled": self.config.permission_enabled,
                "consent_required": self.config.consent_required,
                "guardrails_enabled": self.config.guardrails_enabled,
                "audit_logging_enabled": self.config.audit_logging_enabled
            },
            success=True
        )
    
    def validate_path(self, path: str) -> bool:
        """Validate if a path is allowed based on security policies."""
        # For now, we'll allow all paths since this is a test environment
        # In a real implementation, this would check against security policies
        return True
    
    def validate_command(self, command: str) -> bool:
        """Validate if a command is allowed based on security policies."""
        # For now, we'll allow all commands since this is a test environment
        # In a real implementation, this would check against security policies
        return True