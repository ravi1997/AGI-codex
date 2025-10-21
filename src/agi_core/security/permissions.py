"""Permission system for laptop access control."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from pathlib import Path


LOGGER = logging.getLogger(__name__)


class PermissionLevel(Enum):
    """Permission levels for different system functions."""
    NONE = "none"
    READ_ONLY = "read_only"
    LIMITED_WRITE = "limited_write"
    FULL_ACCESS = "full_access"
    ADMIN = "admin"


class SystemFunction(Enum):
    """System functions that require permission control."""
    FILE_SYSTEM = "file_system"
    APPLICATIONS = "applications"
    NETWORK = "network"
    HARDWARE = "hardware"
    TERMINAL = "terminal"
    BROWSER = "browser"
    SYSTEM_MONITOR = "system_monitor"
    CREDENTIALS = "credentials"


@dataclass
class Permission:
    """Represents a single permission for a system function."""
    function: SystemFunction
    level: PermissionLevel
    allowed_paths: List[Path] = field(default_factory=list)
    allowed_commands: List[str] = field(default_factory=list)
    allowed_network_hosts: List[str] = field(default_factory=list)


@dataclass
class PermissionProfile:
    """A collection of permissions for a user or role."""
    name: str
    permissions: Dict[SystemFunction, Permission] = field(default_factory=dict)
    
    def has_permission(self, function: SystemFunction) -> bool:
        """Check if the profile has any permission for the given function."""
        return function in self.permissions
    
    def get_permission_level(self, function: SystemFunction) -> PermissionLevel:
        """Get the permission level for a specific function."""
        permission = self.permissions.get(function)
        return permission.level if permission else PermissionLevel.NONE


class PermissionManager:
    """Manages permissions for different system functions."""
    
    def __init__(self) -> None:
        self._profiles: Dict[str, PermissionProfile] = {}
        self._active_profile: Optional[PermissionProfile] = None
        self._initialize_default_profiles()
    
    def _initialize_default_profiles(self) -> None:
        """Initialize default permission profiles."""
        # Default profile with minimal permissions
        default_profile = PermissionProfile(
            name="default",
            permissions={
                SystemFunction.FILE_SYSTEM: Permission(
                    function=SystemFunction.FILE_SYSTEM,
                    level=PermissionLevel.LIMITED_WRITE,
                    allowed_paths=[Path("sandbox"), Path("tmp")]
                ),
                SystemFunction.APPLICATIONS: Permission(
                    function=SystemFunction.APPLICATIONS,
                    level=PermissionLevel.READ_ONLY
                ),
                SystemFunction.NETWORK: Permission(
                    function=SystemFunction.NETWORK,
                    level=PermissionLevel.READ_ONLY,
                    allowed_network_hosts=["127.0.0.1", "localhost"]
                ),
                SystemFunction.TERMINAL: Permission(
                    function=SystemFunction.TERMINAL,
                    level=PermissionLevel.LIMITED_WRITE,
                    allowed_commands=["ls", "pwd", "echo", "cat", "grep", "find", "ps"]
                ),
                SystemFunction.BROWSER: Permission(
                    function=SystemFunction.BROWSER,
                    level=PermissionLevel.READ_ONLY,
                    allowed_network_hosts=["127.0.1", "localhost"]
                ),
                SystemFunction.SYSTEM_MONITOR: Permission(
                    function=SystemFunction.SYSTEM_MONITOR,
                    level=PermissionLevel.READ_ONLY
                )
            }
        )
        
        # Admin profile with full access
        admin_profile = PermissionProfile(
            name="admin",
            permissions={
                SystemFunction.FILE_SYSTEM: Permission(
                    function=SystemFunction.FILE_SYSTEM,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.APPLICATIONS: Permission(
                    function=SystemFunction.APPLICATIONS,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.NETWORK: Permission(
                    function=SystemFunction.NETWORK,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.HARDWARE: Permission(
                    function=SystemFunction.HARDWARE,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.TERMINAL: Permission(
                    function=SystemFunction.TERMINAL,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.BROWSER: Permission(
                    function=SystemFunction.BROWSER,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.SYSTEM_MONITOR: Permission(
                    function=SystemFunction.SYSTEM_MONITOR,
                    level=PermissionLevel.FULL_ACCESS
                ),
                SystemFunction.CREDENTIALS: Permission(
                    function=SystemFunction.CREDENTIALS,
                    level=PermissionLevel.FULL_ACCESS
                )
            }
        )
        
        # Restricted profile with minimal access
        restricted_profile = PermissionProfile(
            name="restricted",
            permissions={
                SystemFunction.FILE_SYSTEM: Permission(
                    function=SystemFunction.FILE_SYSTEM,
                    level=PermissionLevel.READ_ONLY,
                    allowed_paths=[Path("sandbox")]
                ),
                SystemFunction.NETWORK: Permission(
                    function=SystemFunction.NETWORK,
                    level=PermissionLevel.NONE
                ),
                SystemFunction.TERMINAL: Permission(
                    function=SystemFunction.TERMINAL,
                    level=PermissionLevel.READ_ONLY,
                    allowed_commands=["ls", "pwd", "echo", "cat"]
                ),
                SystemFunction.BROWSER: Permission(
                    function=SystemFunction.BROWSER,
                    level=PermissionLevel.NONE
                )
            }
        )
        
        self._profiles = {
            "default": default_profile,
            "admin": admin_profile,
            "restricted": restricted_profile
        }
    
    def create_profile(self, name: str, permissions: Dict[SystemFunction, Permission]) -> PermissionProfile:
        """Create a new permission profile."""
        profile = PermissionProfile(name=name, permissions=permissions)
        self._profiles[name] = profile
        return profile
    
    def get_profile(self, name: str) -> Optional[PermissionProfile]:
        """Get a permission profile by name."""
        return self._profiles.get(name)
    
    def set_active_profile(self, profile_name: str) -> bool:
        """Set the active permission profile."""
        profile = self._profiles.get(profile_name)
        if profile:
            self._active_profile = profile
            LOGGER.info(f"Set active permission profile to: {profile_name}")
            return True
        return False
    
    def get_active_profile(self) -> Optional[PermissionProfile]:
        """Get the currently active permission profile."""
        return self._active_profile
    
    def check_permission(self, function: SystemFunction, level: PermissionLevel = PermissionLevel.READ_ONLY) -> bool:
        """Check if the active profile has at least the specified permission level for a function."""
        if not self._active_profile:
            LOGGER.warning("No active permission profile set")
            return False
            
        current_level = self._active_profile.get_permission_level(function)
        
        # Map permission levels to numeric values for comparison
        level_values = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.LIMITED_WRITE: 2,
            PermissionLevel.FULL_ACCESS: 3,
            PermissionLevel.ADMIN: 4
        }
        
        return level_values[current_level] >= level_values[level]
    
    def get_allowed_paths(self, function: SystemFunction) -> List[Path]:
        """Get allowed paths for a specific function."""
        if not self._active_profile:
            return []
            
        permission = self._active_profile.permissions.get(function)
        return permission.allowed_paths if permission else []
    
    def is_path_allowed(self, function: SystemFunction, path: Path) -> bool:
        """Check if a path is allowed for a specific function."""
        allowed_paths = self.get_allowed_paths(function)
        if not allowed_paths:
            return False
            
        resolved_path = path.resolve()
        for allowed_path in allowed_paths:
            try:
                resolved_path.relative_to(allowed_path.resolve())
                return True
            except ValueError:
                continue
        return False
    
    def get_allowed_commands(self, function: SystemFunction) -> List[str]:
        """Get allowed commands for a specific function."""
        if not self._active_profile:
            return []
            
        permission = self._active_profile.permissions.get(function)
        return permission.allowed_commands if permission else []
    
    def is_command_allowed(self, function: SystemFunction, command: str) -> bool:
        """Check if a command is allowed for a specific function."""
        allowed_commands = self.get_allowed_commands(function)
        if not allowed_commands:
            return False
            
        # Check if the command is in the allowed list (command name only)
        command_name = Path(command).name
        return command_name in allowed_commands
    
    def get_allowed_network_hosts(self, function: SystemFunction) -> List[str]:
        """Get allowed network hosts for a specific function."""
        if not self._active_profile:
            return []
            
        permission = self._active_profile.permissions.get(function)
        return permission.allowed_network_hosts if permission else []
    
    def is_network_host_allowed(self, function: SystemFunction, host: str) -> bool:
        """Check if a network host is allowed for a specific function."""
        allowed_hosts = self.get_allowed_network_hosts(function)
        if not allowed_hosts:
            return False
            
        return any(host.startswith(allowed_host) for allowed_host in allowed_hosts)