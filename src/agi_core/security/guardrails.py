"""Safety guardrail system to prevent harmful operations."""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Pattern
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class HarmType(Enum):
    """Types of potential harm to guard against."""
    SYSTEM_DAMAGE = "system_damage"
    PRIVACY_BREACH = "privacy_breach"
    NETWORK_ATTACK = "network_attack"
    RESOURCE_ABUSE = "resource_abuse"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_CORRUPTION = "data_corruption"


@dataclass
class GuardrailRule:
    """A rule that defines a potential threat and how to handle it."""
    id: str
    harm_type: HarmType
    pattern: str | Pattern
    description: str
    severity: int  # 1-10 scale, 10 being highest severity
    action: str = "block"  # "block", "warn", "log"
    enabled: bool = True


class GuardrailEngine(ABC):
    """Abstract base class for guardrail engines."""
    
    @abstractmethod
    def check(self, content: str, context: Optional[Dict] = None) -> List[GuardrailRule]:
        """Check content against guardrails and return any violations."""
        pass


class PatternGuardrailEngine(GuardrailEngine):
    """Guardrail engine that uses regex patterns to detect threats."""
    
    def __init__(self, rules: List[GuardrailRule]):
        self._rules = [rule for rule in rules if rule.enabled]
        # Compile regex patterns for performance
        for rule in self._rules:
            if isinstance(rule.pattern, str):
                rule.pattern = re.compile(rule.pattern, re.IGNORECASE)
    
    def check(self, content: str, context: Optional[Dict] = None) -> List[GuardrailRule]:
        """Check content against all enabled rules."""
        violations = []
        
        for rule in self._rules:
            if isinstance(rule.pattern, Pattern):
                if rule.pattern.search(content):
                    violations.append(rule)
                    LOGGER.warning(f"Guardrail triggered: {rule.id} - {rule.description}")
        
        return violations


class SafetyGuardrails:
    """Main safety guardrail system."""
    
    def __init__(self):
        self._engines: Dict[str, GuardrailEngine] = {}
        self._initialize_default_guardrails()
    
    def _initialize_default_guardrails(self) -> None:
        """Initialize default guardrails for common threats."""
        # System damage guardrails
        system_damage_rules = [
            GuardrailRule(
                id="gd_rm_rf",
                harm_type=HarmType.SYSTEM_DAMAGE,
                pattern=r"rm\s+-rf\s+/",
                description="Recursive delete of root directory",
                severity=10,
                action="block"
            ),
            GuardrailRule(
                id="gd_format_disk",
                harm_type=HarmType.SYSTEM_DAMAGE,
                pattern=r"(format|dd|mkfs)\s+.*(/dev/|hd|sd)",
                description="Disk formatting or raw write operations",
                severity=10,
                action="block"
            ),
            GuardrailRule(
                id="gd_chmod_system",
                harm_type=HarmType.SYSTEM_DAMAGE,
                pattern=r"chmod\s+777\s+/(etc|bin|sbin|usr|boot|sys|proc)",
                description="Dangerous permission changes to system directories",
                severity=9,
                action="block"
            ),
            GuardrailRule(
                id="gd_overwrite_system",
                harm_type=HarmType.SYSTEM_DAMAGE,
                pattern=r"(>|>>)\s+/(etc|bin|sbin|usr|boot)/",
                description="Overwriting system files",
                severity=9,
                action="block"
            )
        ]
        
        # Privacy breach guardrails
        privacy_rules = [
            GuardrailRule(
                id="pb_password_exposure",
                harm_type=HarmType.PRIVACY_BREACH,
                pattern=r"(password|secret|token|key|credential).*['\"].*['\"]",
                description="Potential exposure of sensitive credentials",
                severity=8,
                action="warn"
            ),
            GuardrailRule(
                id="pb_config_access",
                harm_type=HarmType.PRIVACY_BREACH,
                pattern=r"(cat|grep|find)\s+.*(\.env|config\.|passwords\.|secrets\.)",
                description="Accessing configuration or secrets files",
                severity=7,
                action="warn"
            ),
            GuardrailRule(
                id="pb_ssh_key_access",
                harm_type=HarmType.PRIVACY_BREACH,
                pattern=r"cat\s+~/.ssh/.*\.pub|cat\s+~/.ssh/id_.*",
                description="Accessing SSH keys",
                severity=8,
                action="warn"
            )
        ]
        
        # Network attack guardrails
        network_rules = [
            GuardrailRule(
                id="na_port_scan",
                harm_type=HarmType.NETWORK_ATTACK,
                pattern=r"nmap|nc\s+.*\s+\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
                description="Network scanning or port probing",
                severity=8,
                action="warn"
            ),
            GuardrailRule(
                id="na_ddos_attempt",
                harm_type=HarmType.NETWORK_ATTACK,
                pattern=r"ab\s+|siege\s+|hydra\s+|medusa\s+",
                description="Potential DDoS or brute force tools",
                severity=9,
                action="block"
            ),
            GuardrailRule(
                id="na_packet_manipulation",
                harm_type=HarmType.NETWORK_ATTACK,
                pattern=r"tcpdump|wireshark|ettercap|arpspoof|dsniff",
                description="Network packet manipulation tools",
                severity=8,
                action="block"
            )
        ]
        
        # Resource abuse guardrails
        resource_rules = [
            GuardrailRule(
                id="ra_infinite_loop",
                harm_type=HarmType.RESOURCE_ABUSE,
                pattern=r"while\s+:\s*|for\s+.*\s+in\s+.*:\s*.*\s*while\s+True:",
                description="Potential infinite loops",
                severity=7,
                action="warn"
            ),
            GuardrailRule(
                id="ra_fork_bomb",
                harm_type=HarmType.RESOURCE_ABUSE,
                pattern=r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
                description="Fork bomb attempt",
                severity=10,
                action="block"
            ),
            GuardrailRule(
                id="ra_large_file_creation",
                harm_type=HarmType.RESOURCE_ABUSE,
                pattern=r"dd\s+if=/dev/zero|truncate\s+.*\s+\d+[MGTP]",
                description="Large file creation that could fill disk",
                severity=7,
                action="warn"
            )
        ]
        
        # Create engines for each category
        self._engines["system_damage"] = PatternGuardrailEngine(system_damage_rules)
        self._engines["privacy"] = PatternGuardrailEngine(privacy_rules)
        self._engines["network"] = PatternGuardrailEngine(network_rules)
        self._engines["resource"] = PatternGuardrailEngine(resource_rules)
    
    def check_content(self, content: str, context: Optional[Dict] = None) -> Dict[str, List[GuardrailRule]]:
        """Check content against all guardrail engines."""
        results = {}
        for category, engine in self._engines.items():
            violations = engine.check(content, context)
            if violations:
                results[category] = violations
        return results
    
    def is_content_safe(self, content: str, context: Optional[Dict] = None) -> tuple[bool, List[str]]:
        """Check if content is safe to execute. Returns (is_safe, [violated_rule_ids])."""
        all_violations = self.check_content(content, context)
        blocked_violations = []
        
        for category, violations in all_violations.items():
            for violation in violations:
                if violation.action == "block":
                    blocked_violations.append(violation.id)
        
        is_safe = len(blocked_violations) == 0
        return is_safe, blocked_violations
    
    def add_guardrail_engine(self, name: str, engine: GuardrailEngine) -> None:
        """Add a custom guardrail engine."""
        self._engines[name] = engine
    
    def get_all_violations(self, content: str, context: Optional[Dict] = None) -> List[GuardrailRule]:
        """Get all violations across all engines, regardless of action."""
        all_violations = []
        for engine in self._engines.values():
            all_violations.extend(engine.check(content, context))
        return all_violations
    
    def evaluate_command(self, command: str) -> tuple[bool, str, List[str]]:
        """Evaluate a command against guardrails and return (is_safe, recommendation, violations)."""
        is_safe, violations = self.is_content_safe(command)
        
        if not is_safe:
            return False, f"Command blocked due to security violations: {', '.join(violations)}", violations
        
        # Check for warnings too
        all_violations = self.get_all_violations(command)
        warning_violations = [v.id for v in all_violations if v.action == "warn"]
        
        if warning_violations:
            return True, f"Command allowed but with warnings: {', '.join(warning_violations)}", warning_violations
        
        return True, "Command is safe to execute", []