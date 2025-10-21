"""Security policies for tool usage."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class PolicyType(Enum):
    """Types of security policies."""
    TERMINAL = "terminal"
    BROWSER = "browser"
    FILE_IO = "file_io"
    SYSTEM_MONITOR = "system_monitor"
    NETWORK = "network"
    APPLICATION = "application"


@dataclass
class PolicyRule:
    """A single rule within a security policy."""
    name: str
    description: str
    condition: str  # A condition expression
    action: str     # "allow", "deny", "warn", "log"
    priority: int = 100


class PolicyEngine(ABC):
    """Abstract base class for policy engines."""
    
    @abstractmethod
    def evaluate(self, policy_type: PolicyType, context: Dict) -> bool:
        """Evaluate if an action should be allowed based on policies."""
        pass


class ToolPolicy:
    """Security policy for a specific tool."""
    
    def __init__(self, policy_type: PolicyType, rules: List[PolicyRule]):
        self.policy_type = policy_type
        self.rules = sorted(rules, key=lambda r: r.priority)  # Lower priority number = higher priority
    
    def evaluate(self, context: Dict) -> str:
        """Evaluate the policy against the given context."""
        for rule in self.rules:
            if self._evaluate_condition(rule.condition, context):
                LOGGER.debug(f"Policy rule '{rule.name}' matched with action '{rule.action}'")
                return rule.action
        return "deny" # Default action if no rules match
    
    def _evaluate_condition(self, condition: str, context: Dict) -> bool:
        """Evaluate a condition against the context."""
        # This is a simplified condition evaluator
        # In a real implementation, this would be more sophisticated
        try:
            # Basic condition evaluation - this is a placeholder for a more robust system
            if condition == "always":
                return True
            elif condition == "never":
                return False
            elif condition.startswith("path_in("):
                # Extract path from condition like "path_in('/sandbox', '/tmp')"
                import re
                path_match = re.search(r"path_in\((.*)\)", condition)
                if path_match:
                    paths_str = path_match.group(1).strip('\'"')
                    allowed_paths = [p.strip().strip('\'"') for p in paths_str.split(',')]
                    target_path = context.get('path', '')
                    return any(str(target_path).startswith(path) for path in allowed_paths)
            elif condition.startswith("command_in("):
                # Extract commands from condition like "command_in('ls', 'pwd', 'echo')"
                import re
                cmd_match = re.search(r"command_in\((.*)\)", condition)
                if cmd_match:
                    cmds_str = cmd_match.group(1).strip('\'"')
                    allowed_commands = [c.strip().strip('\'"') for c in cmds_str.split(',')]
                    target_cmd = context.get('command', '')
                    return target_cmd in allowed_commands
            elif condition.startswith("host_in("):
                # Extract hosts from condition like "host_in('localhost', '127.0.0.1')"
                import re
                host_match = re.search(r"host_in\((.*)\)", condition)
                if host_match:
                    hosts_str = host_match.group(1).strip('\'"')
                    allowed_hosts = [h.strip().strip('\'"') for h in hosts_str.split(',')]
                    target_host = context.get('host', '')
                    return target_host in allowed_hosts
        except Exception as e:
            LOGGER.error(f"Error evaluating condition '{condition}': {e}")
            return False
        return False


class SecurityPolicyManager:
    """Manages security policies for different tools."""
    
    def __init__(self):
        self._policies: Dict[PolicyType, ToolPolicy] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self) -> None:
        """Initialize default security policies for tools."""
        # Terminal policy
        terminal_rules = [
            PolicyRule(
                name="allow_safe_commands",
                description="Allow safe terminal commands",
                condition="command_in('ls', 'pwd', 'echo', 'cat', 'grep', 'find', 'ps', 'whoami', 'date', 'time')",
                action="allow",
                priority=10
            ),
            PolicyRule(
                name="deny_network_commands",
                description="Deny network-related commands by default",
                condition="command_in('curl', 'wget', 'ssh', 'scp', 'ftp', 'telnet', 'ping', 'nc', 'netcat')",
                action="deny",
                priority=5
            ),
            PolicyRule(
                name="allow_sandbox_path",
                description="Allow operations in sandbox directory",
                condition="path_in('sandbox', '/tmp')",
                action="allow",
                priority=20
            ),
            PolicyRule(
                name="deny_system_paths",
                description="Deny operations in sensitive system paths",
                condition="path_in('/etc', '/root', '/proc', '/sys', '/dev')",
                action="deny",
                priority=5
            )
        ]
        self._policies[PolicyType.TERMINAL] = ToolPolicy(PolicyType.TERMINAL, terminal_rules)
        
        # Browser policy
        browser_rules = [
            PolicyRule(
                name="allow_local_hosts",
                description="Allow browsing local hosts",
                condition="host_in('localhost', '127.0.0.1', '0.0.0.0')",
                action="allow",
                priority=10
            ),
            PolicyRule(
                name="deny_external_hosts",
                description="Deny browsing external hosts by default",
                condition="always",
                action="deny",
                priority=5
            )
        ]
        self._policies[PolicyType.BROWSER] = ToolPolicy(PolicyType.BROWSER, browser_rules)
        
        # File I/O policy
        file_io_rules = [
            PolicyRule(
                name="allow_sandbox_access",
                description="Allow file operations in sandbox",
                condition="path_in('sandbox', '/tmp')",
                action="allow",
                priority=10
            ),
            PolicyRule(
                name="deny_config_access",
                description="Deny access to config files",
                condition="path_in('config', '.env', '/etc')",
                action="deny",
                priority=5
            )
        ]
        self._policies[PolicyType.FILE_IO] = ToolPolicy(PolicyType.FILE_IO, file_io_rules)
        
        # System monitor policy
        system_monitor_rules = [
            PolicyRule(
                name="allow_monitoring",
                description="Allow system monitoring",
                condition="always",
                action="allow",
                priority=10
            )
        ]
        self._policies[PolicyType.SYSTEM_MONITOR] = ToolPolicy(PolicyType.SYSTEM_MONITOR, system_monitor_rules)
    
    def get_policy(self, policy_type: PolicyType) -> Optional[ToolPolicy]:
        """Get a policy for a specific tool type."""
        return self._policies.get(policy_type)
    
    def add_policy(self, policy: ToolPolicy) -> None:
        """Add a new policy."""
        self._policies[policy.policy_type] = policy
    
    def evaluate_policy(self, policy_type: PolicyType, context: Dict) -> bool:
        """Evaluate if an action should be allowed based on the policy."""
        policy = self._policies.get(policy_type)
        if not policy:
            LOGGER.warning(f"No policy found for type: {policy_type}")
            return False
        
        result = policy.evaluate(context)
        LOGGER.debug(f"Policy evaluation for {policy_type.value}: {result}")
        return result == "allow"
    
    def update_policy_rules(self, policy_type: PolicyType, rules: List[PolicyRule]) -> bool:
        """Update the rules for a specific policy."""
        if policy_type in self._policies:
            self._policies[policy_type] = ToolPolicy(policy_type, rules)
            return True
        return False