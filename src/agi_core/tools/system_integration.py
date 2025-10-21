"""
System Integration Tools for AGI Codex
Provides integration with installed applications, system resources, and common services
"""
import os
import subprocess
import sys
import platform
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import shutil
import psutil
import requests
from datetime import datetime

from .base import BaseTool, ToolError
from ..security.manager import SecurityManager
from ..security.permissions import SystemFunction


class ApplicationDiscoveryTool(BaseTool):
    """
    Tool for discovering and integrating with installed applications
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="application_discovery", description="Discover and interact with installed applications")
        self.security_manager = security_manager

    def _run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Run application discovery actions
        """
        if not self.security_manager.check_permission(SystemFunction.APPLICATIONS, "READ"):
            raise ToolError("Permission denied: APPLICATIONS required for application discovery")
        
        if action == "list_installed_apps":
            return self._list_installed_applications()
        elif action == "check_app_installed":
            app_name = kwargs.get("app_name")
            if not app_name:
                raise ToolError("app_name is required for check_app_installed action")
            return {"installed": self._check_application_installed(app_name)}
        elif action == "get_app_info":
            app_name = kwargs.get("app_name")
            if not app_name:
                raise ToolError("app_name is required for get_app_info action")
            return self._get_application_info(app_name)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _list_installed_applications(self) -> Dict[str, Any]:
        """List all installed applications"""
        apps = []
        
        # On Linux, check common application directories
        if platform.system() == "Linux":
            app_dirs = ["/usr/bin", "/usr/local/bin", "/snap/bin"]
            for app_dir in app_dirs:
                if os.path.exists(app_dir):
                    for app in os.listdir(app_dir):
                        app_path = os.path.join(app_dir, app)
                        if os.access(app_path, os.X_OK) and os.path.isfile(app_path):
                            apps.append(app)
        
        # On macOS, check common application locations
        elif platform.system() == "Darwin":
            app_dirs = ["/Applications", "/Applications/Utilities"]
            for app_dir in app_dirs:
                if os.path.exists(app_dir):
                    for app in os.listdir(app_dir):
                        if app.endswith('.app'):
                            apps.append(app)
        
        # On Windows, check common application locations
        elif platform.system() == "Windows":
            # This is a simplified check; in practice, you'd want to check the registry
            program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
            if os.path.exists(program_files):
                for app in os.listdir(program_files):
                    apps.append(app)
        
        return {"applications": list(set(apps))}  # Remove duplicates

    def _check_application_installed(self, app_name: str) -> bool:
        """Check if a specific application is installed"""
        if platform.system() == "Windows":
            # On Windows, check if the executable exists in common paths
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), app_name),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), app_name),
                "C:\\Windows\\System32"
            ]
            
            for path in common_paths:
                if os.path.exists(path):
                    # Check for .exe files
                    exe_path = os.path.join(path, f"{app_name}.exe")
                    if os.path.exists(exe_path):
                        return True
                    
                    # Also check subdirectories
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if file.lower() == f"{app_name}.exe":
                                return True
        else:
            # On Unix-like systems, use 'which' command
            try:
                result = subprocess.run(["which", app_name], capture_output=True, text=True)
                return result.returncode == 0
            except Exception:
                return False
        
        return False

    def _get_application_info(self, app_name: str) -> Dict[str, Any]:
        """Get detailed information about an installed application"""
        installed = self._check_application_installed(app_name)
        if not installed:
            return {"app_name": app_name, "installed": False}
        
        info = {"app_name": app_name, "installed": True, "details": {}}
        
        if platform.system() != "Windows":
            try:
                # Get version information using common commands
                result = subprocess.run([app_name, "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info["details"]["version"] = result.stdout.strip()
                
                # Get help information
                result = subprocess.run([app_name, "--help"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    info["details"]["help"] = result.stdout[:500]  # First 500 chars
            except Exception:
                pass  # Silently ignore if these commands fail
        
        return info


class FileSystemIntegrationTool(BaseTool):
    """
    Tool for file system integration and common operations
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="file_system_integration", description="Perform file system operations")
        self.security_manager = security_manager

    def _run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Run file system integration actions
        """
        if not self.security_manager.check_permission(SystemFunction.FILE_SYSTEM, "READ"):
            raise ToolError("Permission denied: FILE_SYSTEM required for file system operations")
        
        if action == "list_directory":
            path = kwargs.get("path", ".")
            return self._list_directory(path)
        elif action == "file_info":
            file_path = kwargs.get("file_path")
            if not file_path:
                raise ToolError("file_path is required for file_info action")
            return self._get_file_info(file_path)
        elif action == "search_files":
            pattern = kwargs.get("pattern")
            directory = kwargs.get("directory", ".")
            if not pattern:
                raise ToolError("pattern is required for search_files action")
            return self._search_files(pattern, directory)
        elif action == "file_operations":
            operation = kwargs.get("operation")
            file_path = kwargs.get("file_path")
            if not operation or not file_path:
                raise ToolError("operation and file_path are required for file_operations action")
            return self._perform_file_operation(operation, file_path, **kwargs)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _list_directory(self, path: str) -> Dict[str, Any]:
        """List contents of a directory"""
        try:
            path_obj = Path(path).resolve()
            
            # Security check: ensure path is within allowed directories
            if not self.security_manager.validate_path(str(path_obj)):
                raise ToolError(f"Access denied: {path} is not in allowed directories")
            
            if not path_obj.exists():
                raise ToolError(f"Directory does not exist: {path}")
            
            if not path_obj.is_dir():
                raise ToolError(f"Path is not a directory: {path}")
            
            contents = {
                "path": str(path_obj),
                "directories": [],
                "files": []
            }
            
            for item in path_obj.iterdir():
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                
                if item.is_dir():
                    contents["directories"].append(item_info)
                else:
                    contents["files"].append(item_info)
            
            return contents
        except Exception as e:
            raise ToolError(f"Error listing directory: {str(e)}")

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get detailed information about a file"""
        try:
            path_obj = Path(file_path).resolve()
            
            # Security check: ensure path is within allowed directories
            if not self.security_manager.validate_path(str(path_obj)):
                raise ToolError(f"Access denied: {file_path} is not in allowed directories")
            
            if not path_obj.exists():
                raise ToolError(f"File does not exist: {file_path}")
            
            stat = path_obj.stat()
            info = {
                "path": str(path_obj),
                "name": path_obj.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "permissions": oct(stat.st_mode)[-3:],
                "is_file": path_obj.is_file(),
                "is_directory": path_obj.is_dir(),
                "extension": path_obj.suffix if path_obj.is_file() else None
            }
            
            # If it's a text file, try to read the first few lines
            if path_obj.is_file() and path_obj.suffix.lower() in ['.txt', '.py', '.js', '.html', '.css', '.json', '.yaml', '.md']:
                try:
                    with open(path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                        info["preview"] = f.read(200)  # First 200 characters
                except Exception:
                    pass  # Ignore if we can't read the file
            
            return info
        except Exception as e:
            raise ToolError(f"Error getting file info: {str(e)}")

    def _search_files(self, pattern: str, directory: str = ".") -> Dict[str, Any]:
        """Search for files matching a pattern"""
        try:
            dir_obj = Path(directory).resolve()
            
            # Security check: ensure path is within allowed directories
            if not self.security_manager.validate_path(str(dir_obj)):
                raise ToolError(f"Access denied: {directory} is not in allowed directories")
            
            if not dir_obj.exists() or not dir_obj.is_dir():
                raise ToolError(f"Directory does not exist or is not a directory: {directory}")
            
            matches = []
            for file_path in dir_obj.rglob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    matches.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
            
            return {"pattern": pattern, "directory": str(dir_obj), "matches": matches}
        except Exception as e:
            raise ToolError(f"Error searching files: {str(e)}")

    def _perform_file_operation(self, operation: str, file_path: str, **kwargs) -> Dict[str, Any]:
        """Perform file operations like copy, move, delete"""
        try:
            path_obj = Path(file_path).resolve()
            
            # Security check: ensure path is within allowed directories
            if not self.security_manager.validate_path(str(path_obj)):
                raise ToolError(f"Access denied: {file_path} is not in allowed directories")
            
            if operation == "copy":
                destination = kwargs.get("destination")
                if not destination:
                    raise ToolError("destination is required for copy operation")
                
                dest_obj = Path(destination).resolve()
                if not self.security_manager.validate_path(str(dest_obj)):
                    raise ToolError(f"Access denied: {destination} is not in allowed directories")
                
                shutil.copy2(str(path_obj), str(dest_obj))
                return {"status": "success", "operation": "copy", "source": str(path_obj), "destination": str(dest_obj)}
            
            elif operation == "move":
                destination = kwargs.get("destination")
                if not destination:
                    raise ToolError("destination is required for move operation")
                
                dest_obj = Path(destination).resolve()
                if not self.security_manager.validate_path(str(dest_obj)):
                    raise ToolError(f"Access denied: {destination} is not in allowed directories")
                
                shutil.move(str(path_obj), str(dest_obj))
                return {"status": "success", "operation": "move", "source": str(path_obj), "destination": str(dest_obj)}
            
            elif operation == "delete":
                if not self.security_manager.check_permission("FILE_ACCESS", "WRITE"):
                    raise ToolError("Permission denied: FILE_ACCESS with WRITE required for delete operation")
                
                if path_obj.is_file():
                    path_obj.unlink()
                elif path_obj.is_dir():
                    shutil.rmtree(path_obj)
                else:
                    raise ToolError(f"Path does not exist: {file_path}")
                
                return {"status": "success", "operation": "delete", "path": str(path_obj)}
            
            else:
                raise ToolError(f"Unsupported operation: {operation}")
        
        except Exception as e:
            raise ToolError(f"Error performing file operation: {str(e)}")


class TerminalIntegrationTool(BaseTool):
    """
    Tool for terminal command integration with security validation
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="terminal_integration", description="Execute terminal commands with security validation")
        self.security_manager = security_manager

    def _run(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Run terminal commands with security validation
        """
        if not self.security_manager.check_permission(SystemFunction.TERMINAL, "EXECUTE"):
            raise ToolError("Permission denied: TERMINAL required for command execution")
        
        # Validate command against security policies
        if not self.security_manager.validate_command(command):
            raise ToolError(f"Command blocked by security policy: {command}")
        
        # Check risk level of the command
        risk_level = self.security_manager.assess_command_risk(command)
        if risk_level == "HIGH":
            consent = self.security_manager.request_user_consent(f"Execute high-risk command: {command}")
            if not consent:
                raise ToolError("User consent denied for high-risk command")
        
        timeout = kwargs.get("timeout", 30)
        
        try:
            # Execute the command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_time": timeout
            }
        except subprocess.TimeoutExpired:
            raise ToolError(f"Command timed out after {timeout} seconds: {command}")
        except Exception as e:
            raise ToolError(f"Error executing command: {str(e)}")


class SystemResourceMonitor(BaseTool):
    """
    Tool for system resource monitoring and management
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="system_monitor", description="Monitor and manage system resources")
        self.security_manager = security_manager

    def _run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Run system monitoring actions
        """
        if not self.security_manager.check_permission(SystemFunction.SYSTEM_MONITOR, "READ"):
            raise ToolError("Permission denied: SYSTEM_MONITOR required for system monitoring")
        
        if action == "get_system_info":
            return self._get_system_info()
        elif action == "get_cpu_usage":
            return self._get_cpu_usage()
        elif action == "get_memory_usage":
            return self._get_memory_usage()
        elif action == "get_disk_usage":
            return self._get_disk_usage()
        elif action == "get_running_processes":
            return self._get_running_processes()
        elif action == "get_network_info":
            return self._get_network_info()
        else:
            raise ToolError(f"Unknown action: {action}")

    def _get_system_info(self) -> Dict[str, Any]:
        """Get overall system information"""
        return {
            "platform": platform.platform(),
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

    def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage information"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "cpu_count": psutil.cpu_count(),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "load_average": os.getloadavg() if platform.system() != "Windows" else None
        }

    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage information"""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "virtual_memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            },
            "swap_memory": {
                "total": swap.total,
                "used": swap.used,
                "free": swap.free,
                "percent": swap.percent
            }
        }

    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage information"""
        disk_info = {}
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": (usage.used / usage.total) * 100
                }
            except PermissionError:
                # This can happen on some systems where we don't have permission to access certain partitions
                continue
        
        return disk_info

    def _get_running_processes(self) -> Dict[str, Any]:
        """Get information about running processes"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Handle cases where process disappears or we don't have access
                continue
        
        return {"processes": processes, "count": len(processes)}

    def _get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        net_io = psutil.net_io_counters()
        net_addrs = psutil.net_if_addrs()
        net_stats = psutil.net_if_stats()
        
        return {
            "net_io": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            },
            "network_interfaces": {
                name: [addr._asdict() for addr in addrs] 
                for name, addrs in net_addrs.items()
            },
            "interface_stats": {
                name: {
                    "is_up": stats.isup,
                    "duplex": str(stats.duplex),
                    "speed": stats.speed,
                    "mtu": stats.mtu
                } 
                for name, stats in net_stats.items()
            }
        }


class WebIntegrationTool(BaseTool):
    """
    Tool for web browser automation and integration
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="web_integration", description="Web browser automation and integration")
        self.security_manager = security_manager

    def _run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Run web integration actions
        """
        if not self.security_manager.check_permission(SystemFunction.BROWSER, "BROWSER"):
            raise ToolError("Permission denied: BROWSER required for web operations")
        
        if action == "open_url":
            url = kwargs.get("url")
            if not url:
                raise ToolError("url is required for open_url action")
            return self._open_url(url)
        elif action == "get_page_content":
            url = kwargs.get("url")
            if not url:
                raise ToolError("url is required for get_page_content action")
            return self._get_page_content(url)
        elif action == "screenshot_page":
            url = kwargs.get("url")
            if not url:
                raise ToolError("url is required for screenshot_page action")
            return self._screenshot_page(url)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _open_url(self, url: str) -> Dict[str, Any]:
        """Open a URL in the default web browser"""
        import webbrowser
        
        # Validate URL against security policies
        if not self.security_manager.validate_url(url):
            raise ToolError(f"URL blocked by security policy: {url}")
        
        try:
            webbrowser.open(url)
            return {"status": "success", "action": "open_url", "url": url}
        except Exception as e:
            raise ToolError(f"Error opening URL: {str(e)}")

    def _get_page_content(self, url: str) -> Dict[str, Any]:
        """Get content from a web page"""
        # Validate URL against security policies
        if not self.security_manager.validate_url(url):
            raise ToolError(f"URL blocked by security policy: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get('content-type'),
                "content_length": len(response.content),
                "title": self._extract_title(response.text),
                "text_content": self._extract_text_content(response.text)[:1000]  # First 1000 chars
            }
        except Exception as e:
            raise ToolError(f"Error getting page content: {str(e)}")

    def _screenshot_page(self, url: str) -> Dict[str, Any]:
        """Take a screenshot of a web page (placeholder implementation)"""
        # This would require additional dependencies like selenium or playwright
        # For now, we'll return an error indicating it's not implemented
        raise ToolError("Screenshot functionality requires additional setup and is not currently available")

    def _extract_title(self, html_content: str) -> str:
        """Extract title from HTML content"""
        import re
        title_match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return title_match.group(1) if title_match else "No title found"

    def _extract_text_content(self, html_content: str) -> str:
        """Extract text content from HTML"""
        from html import unescape
        import re
        
        # Remove script and style elements
        clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', clean_html)
        # Unescape HTML entities
        text = unescape(text)
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text


class APIIntegrationTool(BaseTool):
    """
    Tool for API integration with common services
    """
    def __init__(self, security_manager: SecurityManager):
        super().__init__(name="api_integration", description="API integration with common services")
        self.security_manager = security_manager

    def _run(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Run API integration actions
        """
        if not self.security_manager.check_permission(SystemFunction.NETWORK, "NETWORK"):
            raise ToolError("Permission denied: NETWORK required for API operations")
        
        if action == "email_service":
            return self._email_service_action(**kwargs)
        elif action == "calendar_service":
            return self._calendar_service_action(**kwargs)
        elif action == "cloud_storage":
            return self._cloud_storage_action(**kwargs)
        elif action == "generic_api":
            return self._generic_api_action(**kwargs)
        else:
            raise ToolError(f"Unknown action: {action}")

    def _email_service_action(self, **kwargs) -> Dict[str, Any]:
        """Handle email service actions"""
        service = kwargs.get("service", "generic")
        operation = kwargs.get("operation")
        
        # This would integrate with specific email services (Gmail, Outlook, etc.)
        # For now, we'll return a placeholder
        return {
            "service": service,
            "operation": operation,
            "status": "not_implemented",
            "message": "Email service integration requires specific API setup"
        }

    def _calendar_service_action(self, **kwargs) -> Dict[str, Any]:
        """Handle calendar service actions"""
        service = kwargs.get("service", "generic")
        operation = kwargs.get("operation")
        
        # This would integrate with specific calendar services (Google Calendar, Outlook, etc.)
        # For now, we'll return a placeholder
        return {
            "service": service,
            "operation": operation,
            "status": "not_implemented",
            "message": "Calendar service integration requires specific API setup"
        }

    def _cloud_storage_action(self, **kwargs) -> Dict[str, Any]:
        """Handle cloud storage actions"""
        service = kwargs.get("service", "generic")
        operation = kwargs.get("operation")
        
        # This would integrate with specific cloud storage services (Google Drive, Dropbox, etc.)
        # For now, we'll return a placeholder
        return {
            "service": service,
            "operation": operation,
            "status": "not_implemented",
            "message": "Cloud storage integration requires specific API setup"
        }

    def _generic_api_action(self, **kwargs) -> Dict[str, Any]:
        """Handle generic API actions"""
        url = kwargs.get("url")
        method = kwargs.get("method", "GET")
        headers = kwargs.get("headers", {})
        data = kwargs.get("data", {})
        
        # Validate URL against security policies
        if not self.security_manager.validate_url(url):
            raise ToolError(f"URL blocked by security policy: {url}")
        
        try:
            response = requests.request(method, url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            return {
                "url": url,
                "method": method,
                "status_code": response.status_code,
                "response": response.json() if response.content else None
            }
        except Exception as e:
            raise ToolError(f"Error making API request: {str(e)}")


class PluginManager:
    """
    Plugin architecture for easy addition of new tool integrations
    """
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.plugins = {}
        self.plugin_dir = Path("plugins")
        self.plugin_dir.mkdir(exist_ok=True)

    def register_plugin(self, name: str, plugin_class):
        """Register a new plugin"""
        if not self.security_manager.check_permission(SystemFunction.APPLICATIONS, "REGISTER"):
            raise ToolError("Permission denied: APPLICATIONS required to register plugins")
        
        self.plugins[name] = plugin_class

    def load_plugin(self, plugin_name: str, plugin_path: str):
        """Load a plugin from a file path"""
        if not self.security_manager.check_permission(SystemFunction.APPLICATIONS, "LOAD"):
            raise ToolError("Permission denied: APPLICATIONS required to load plugins")
        
        # Validate path for security
        path_obj = Path(plugin_path).resolve()
        if not self.security_manager.validate_path(str(path_obj)):
            raise ToolError(f"Access denied: {plugin_path} is not in allowed directories")
        
        # Import and register the plugin
        import importlib.util
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Assuming the plugin class is named after the plugin with "Plugin" suffix
        plugin_class = getattr(module, f"{plugin_name.capitalize()}Plugin", None)
        if plugin_class:
            self.register_plugin(plugin_name, plugin_class)
            return {"status": "success", "plugin": plugin_name, "path": plugin_path}
        else:
            raise ToolError(f"Plugin class not found in {plugin_path}")

    def get_available_plugins(self) -> List[str]:
        """Get list of available plugins"""
        return list(self.plugins.keys())

    def execute_plugin(self, plugin_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Execute a plugin action"""
        if plugin_name not in self.plugins:
            raise ToolError(f"Plugin not found: {plugin_name}")
        
        plugin_instance = self.plugins[plugin_name](self.security_manager)
        return plugin_instance._run(action, **kwargs)