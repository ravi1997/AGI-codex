"""Configuration for security and permission systems."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    
    # Permission system settings
    permission_enabled: bool = Field(
        True, 
        description="Whether the permission system is enabled"
    )
    default_permission_profile: str = Field(
        "default",
        description="Default permission profile to use"
    )
    
    # Consent system settings
    consent_required: bool = Field(
        True,
        description="Whether user consent is required for operations"
    )
    consent_timeout_seconds: int = Field(
        300,  # 5 minutes
        ge=60,
        description="Timeout for consent requests in seconds"
    )
    consent_storage_path: Path = Field(
        Path("storage/consent"),
        description="Path for storing consent requests"
    )
    
    # Policy system settings
    policy_enforcement_enabled: bool = Field(
        True,
        description="Whether security policies are enforced"
    )
    
    # Guardrail system settings
    guardrails_enabled: bool = Field(
        True,
        description="Whether safety guardrails are active"
    )
    guardrail_categories: List[str] = Field(
        default_factory=lambda: ["system_damage", "privacy", "network", "resource"],
        description="Categories of guardrails to enable"
    )
    
    # Credential management settings
    credential_storage_path: Path = Field(
        Path("storage/credentials"),
        description="Path for storing encrypted credentials"
    )
    credential_encryption_enabled: bool = Field(
        True,
        description="Whether credentials are encrypted at rest"
    )
    
    # Audit logging settings
    audit_logging_enabled: bool = Field(
        True,
        description="Whether audit logging is enabled"
    )
    audit_storage_path: Path = Field(
        Path("storage/audit"),
        description="Path for storing audit logs"
    )
    audit_retention_days: int = Field(
        90,
        ge=1,
        description="Number of days to retain audit logs"
    )
    
    # Risk assessment settings
    risk_assessment_enabled: bool = Field(
        True,
        description="Whether risk assessment is performed"
    )
    max_allowed_risk_level: str = Field(
        "medium",
        description="Maximum risk level that allows operation execution (none, low, medium, high, critical)"
    )
    
    # Security-related environment variables
    credential_encryption_key: Optional[str] = Field(
        None,
        description="Encryption key for credentials (if not provided, will be generated)"
    )


def load_security_config() -> SecurityConfig:
    """Load security configuration from environment variables or defaults."""
    # Load from environment variables with defaults
    credential_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    
    return SecurityConfig(
        permission_enabled=os.getenv("SECURITY_PERMISSION_ENABLED", "true").lower() == "true",
        default_permission_profile=os.getenv("SECURITY_DEFAULT_PROFILE", "default"),
        consent_required=os.getenv("SECURITY_CONSENT_REQUIRED", "true").lower() == "true",
        consent_timeout_seconds=int(os.getenv("SECURITY_CONSENT_TIMEOUT", "30")),
        consent_storage_path=Path(os.getenv("SECURITY_CONSENT_STORAGE", "storage/consent")),
        policy_enforcement_enabled=os.getenv("SECURITY_POLICY_ENFORCEMENT", "true").lower() == "true",
        guardrails_enabled=os.getenv("SECURITY_GUARDRAILS_ENABLED", "true").lower() == "true",
        guardrail_categories=os.getenv("SECURITY_GUARDRAIL_CATEGORIES", "system_damage,privacy,network,resource").split(","),
        credential_storage_path=Path(os.getenv("SECURITY_CREDENTIAL_STORAGE", "storage/credentials")),
        credential_encryption_enabled=os.getenv("SECURITY_CREDENTIAL_ENCRYPTION", "true").lower() == "true",
        audit_logging_enabled=os.getenv("SECURITY_AUDIT_LOGGING", "true").lower() == "true",
        audit_storage_path=Path(os.getenv("SECURITY_AUDIT_STORAGE", "storage/audit")),
        audit_retention_days=int(os.getenv("SECURITY_AUDIT_RETENTION", "90")),
        risk_assessment_enabled=os.getenv("SECURITY_RISK_ASSESSMENT", "true").lower() == "true",
        max_allowed_risk_level=os.getenv("SECURITY_MAX_RISK_LEVEL", "medium"),
        credential_encryption_key=credential_key
    )