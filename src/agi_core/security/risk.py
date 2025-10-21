"""Risk assessment system that evaluates operations before execution."""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Levels of risk for operations."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Categories of risk."""
    SYSTEM_INTEGRITY = "system_integrity"
    DATA_PRIVACY = "data_privacy"
    NETWORK_SECURITY = "network_security"
    RESOURCE_UTILIZATION = "resource_utilization"
    AUTHENTICATION = "authentication"
    UNAUTHORIZED_ACCESS = "unauthorized_access"


@dataclass
class RiskFactor:
    """A factor that contributes to the overall risk assessment."""
    category: RiskCategory
    severity: RiskLevel
    weight: float  # 0.0 to 1.0, how much this factor contributes to total risk
    description: str
    mitigation: str


@dataclass
class RiskAssessment:
    """Result of a risk assessment."""
    operation: str
    risk_level: RiskLevel
    score: float  # 0.0 to 1.0
    factors: List[RiskFactor]
    timestamp: float
    recommendations: List[str]
    execution_allowed: bool


class RiskAssessmentEngine(ABC):
    """Abstract base class for risk assessment engines."""
    
    @abstractmethod
    def assess_risk(self, operation: str, context: Dict[str, Any]) -> RiskAssessment:
        """Assess the risk of an operation in the given context."""
        pass


class RuleBasedRiskEngine(RiskAssessmentEngine):
    """Risk assessment engine based on predefined rules."""
    
    def __init__(self) -> None:
        self._risk_rules = self._initialize_risk_rules()
    
    def _initialize_risk_rules(self) -> List[Dict]:
        """Initialize risk assessment rules."""
        return [
            # System integrity risks
            {
                "condition": lambda ctx: any(cmd in ctx.get("command", "") for cmd in ["rm -rf", "format", "dd if=", "mkfs"]),
                "factor": RiskFactor(
                    category=RiskCategory.SYSTEM_INTEGRITY,
                    severity=RiskLevel.CRITICAL,
                    weight=1.0,
                    description="Potentially destructive system command",
                    mitigation="Verify command is intended and has proper safeguards"
                )
            },
            {
                "condition": lambda ctx: ctx.get("path", "").startswith(("/", "/etc", "/bin", "/sbin", "/usr", "/boot")),
                "factor": RiskFactor(
                    category=RiskCategory.SYSTEM_INTEGRITY,
                    severity=RiskLevel.HIGH,
                    weight=0.8,
                    description="Access to system directories",
                    mitigation="Ensure operation is authorized and necessary"
                )
            },
            # Data privacy risks
            {
                "condition": lambda ctx: any(keyword in ctx.get("content", "").lower() for keyword in ["password", "secret", "token", "key", "credential"]),
                "factor": RiskFactor(
                    category=RiskCategory.DATA_PRIVACY,
                    severity=RiskLevel.HIGH,
                    weight=0.7,
                    description="Handling of sensitive data",
                    mitigation="Ensure data is handled securely and not logged"
                )
            },
            {
                "condition": lambda ctx: ctx.get("path", "").endswith((".env", "config", "secrets", "passwords")),
                "factor": RiskFactor(
                    category=RiskCategory.DATA_PRIVACY,
                    severity=RiskLevel.MEDIUM,
                    weight=0.6,
                    description="Access to configuration files",
                    mitigation="Verify access is necessary and authorized"
                )
            },
            # Network security risks
            {
                "condition": lambda ctx: any(tool in ctx.get("tool", "") for tool in ["terminal", "browser"]) and 
                                          any(host in ctx.get("target", "") for host in ["192.168", "10.", "172.", "scan", "nmap"]),
                "factor": RiskFactor(
                    category=RiskCategory.NETWORK_SECURITY,
                    severity=RiskLevel.HIGH,
                    weight=0.8,
                    description="Network scanning or probing activity",
                    mitigation="Ensure network activity is authorized"
                )
            },
            # Resource utilization risks
            {
                "condition": lambda ctx: "infinite" in ctx.get("command", "") or 
                                        any(loop in ctx.get("code", "") for loop in ["while True", "for _ in range(", "while :"]),
                "factor": RiskFactor(
                    category=RiskCategory.RESOURCE_UTILIZATION,
                    severity=RiskLevel.MEDIUM,
                    weight=0.5,
                    description="Potential infinite loop or resource consumption",
                    mitigation="Implement timeouts and resource limits"
                )
            },
            {
                "condition": lambda ctx: any(size in ctx.get("command", "") for size in ["100GB", "1TB", "large_file"]),
                "factor": RiskFactor(
                    category=RiskCategory.RESOURCE_UTILIZATION,
                    severity=RiskLevel.MEDIUM,
                    weight=0.4,
                    description="Large file operations",
                    mitigation="Monitor disk usage and implement quotas"
                )
            }
        ]
    
    def assess_risk(self, operation: str, context: Dict[str, Any]) -> RiskAssessment:
        """Assess the risk of an operation in the given context."""
        factors = []
        total_score = 0.0
        max_possible_score = 0.0
        
        # Apply each rule to the context
        for rule in self._risk_rules:
            if rule["condition"](context):
                factor = rule["factor"]
                factors.append(factor)
                # Calculate weighted contribution to total risk
                severity_values = {
                    RiskLevel.NONE: 0.0,
                    RiskLevel.LOW: 0.2,
                    RiskLevel.MEDIUM: 0.4,
                    RiskLevel.HIGH: 0.7,
                    RiskLevel.CRITICAL: 1.0
                }
                contribution = severity_values[factor.severity] * factor.weight
                total_score += contribution
                max_possible_score += 1.0 * factor.weight
        
        # Calculate overall risk score (0.0 to 1.0)
        if max_possible_score > 0:
            normalized_score = total_score / max_possible_score
        else:
            normalized_score = 0.0
        
        # Determine risk level based on score
        if normalized_score >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif normalized_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif normalized_score >= 0.4:
            risk_level = RiskLevel.MEDIUM
        elif normalized_score >= 0.1:
            risk_level = RiskLevel.LOW
        else:
            risk_level = RiskLevel.NONE
        
        # Determine if execution is allowed based on risk level
        execution_allowed = risk_level in [RiskLevel.NONE, RiskLevel.LOW]
        
        # Generate recommendations based on risk factors
        recommendations = []
        if factors:
            for factor in factors:
                recommendations.append(f"{factor.mitigation} (Risk: {factor.severity.value})")
        
        # Add general recommendations for high-risk operations
        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append("Consider running in a more restricted environment")
            recommendations.append("Obtain additional authorization before proceeding")
        
        return RiskAssessment(
            operation=operation,
            risk_level=risk_level,
            score=normalized_score,
            factors=factors,
            timestamp=time.time(),
            recommendations=recommendations,
            execution_allowed=execution_allowed
        )


class RiskAssessmentManager:
    """Manages risk assessment for operations."""
    
    def __init__(self, assessment_engine: RiskAssessmentEngine) -> None:
        self._engine = assessment_engine
        self._logger = logging.getLogger(__name__ + ".risk")
    
    def assess_operation(self, operation: str, context: Dict[str, Any]) -> RiskAssessment:
        """Assess the risk of an operation in the given context."""
        assessment = self._engine.assess_risk(operation, context)
        self._logger.info(
            f"Risk assessment for '{operation}': {assessment.risk_level.value} "
            f"(score: {assessment.score:.2f}, allowed: {assessment.execution_allowed})"
        )
        return assessment
    
    def is_operation_allowed(self, operation: str, context: Dict[str, Any]) -> bool:
        """Check if an operation is allowed based on risk assessment."""
        assessment = self.assess_operation(operation, context)
        return assessment.execution_allowed
    
    def get_risk_score(self, operation: str, context: Dict[str, Any]) -> Tuple[RiskLevel, float]:
        """Get the risk level and score for an operation."""
        assessment = self.assess_operation(operation, context)
        return assessment.risk_level, assessment.score
    
    def get_recommendations(self, operation: str, context: Dict[str, Any]) -> List[str]:
        """Get recommendations for safely executing an operation."""
        assessment = self.assess_operation(operation, context)
        return assessment.recommendations
    
    def register_custom_risk_rule(self, condition, risk_factor: RiskFactor) -> None:
        """Register a custom risk rule with the engine (if supported)."""
        # This would be implemented differently based on the specific engine type
        # For the rule-based engine, we'd need to add the rule to its internal list
        if isinstance(self._engine, RuleBasedRiskEngine):
            self._engine._risk_rules.append({
                "condition": condition,
                "factor": risk_factor
            })