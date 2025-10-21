#!/usr/bin/env python3
"""
Interactive APK Installer Core - v4.5.2 "Odyssey"  
Core installation logic and interactive workflows for the APK Installer suite.
"""

import os
import sys
import json
import re
import shutil
import subprocess
import tempfile
import configparser
import zipfile
import time
from pathlib import Path

# Import constants and device spoofing
from installer_constants import (
    SCRIPT_VERSION,
    DEFAULT_CONFIG, 
    ASCII_BANNER,
    SPOOFING_OPTIONS_MAP
)
from device_spoofing import DeviceSpoofingManager

# Rich library support (optional)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Questionary for interactive prompts (optional)
try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

# pyaxmlparser for APK parsing (optional)
try:
    from pyaxmlparser import AXMLP
    AXMLPARSER_AVAILABLE = True
except ImportError:
    AXMLPARSER_AVAILABLE = False

class InteractiveAPKInstaller:
    """Main interactive APK installer with enhanced user experience and spoofing integration."""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.config = {}
        self.adb_path = "adb"  # Default ADB path
        self.apk_directory = "apks"  # Default APK directory
        self.spoofing_manager = None
        self.temp_dir = None
        self.temp_files_to_cleanup = []
        self.device_capabilities = {}  # Store device capabilities
        
        # Define cohesive styling theme
        self.app_style = self._create_app_style()
        
        # Initialize configuration and spoofing manager
        self.load_config()
        self._apply_fallback_configs_and_init_manager()

    def _create_app_style(self):
        """Create cohesive styling theme for the entire application."""
        if not QUESTIONARY_AVAILABLE:
            return None
            
        return questionary.Style([
            # Main interface elements
            ('question', '#5f87ff bold'),           # Bright blue for questions
            ('answer', '#ffffff bold'),             # White for answers
            ('instruction', '#95a5a6'),             # Light gray for instructions
            ('text', '#ffffff'),                    # White for general text
            
            # Selection and highlighting
            ('selected', '#00ff88 bold'),           # Bright green for selected items
            ('highlighted', '#00ff88'),             # Light green for highlighted items
            ('pointer', '#00ff88 bold'),            # Green pointer/cursor
            
            # Checkboxes and interactive elements
            ('checkbox-selected', '#00ff88'),       # Green checkboxes
            ('checkbox-checked', '#00ff88 bold'),   # Bold green for checked items
            ('checkbox', '#ffffff'),                # White unchecked boxes
            
            # Status and feedback
            ('disabled', '#7f8c8d'),               # Gray for disabled items
            ('separator', '#34495e'),               # Dark gray for separators
            ('skipped', '#f39c12'),                # Orange for skipped items
            ('answered', '#00ff88'),               # Green for answered items
            
            # Confirmation dialogs
            ('confirmation', '#5f87ff bold'),       # Blue for confirmations
            ('error', '#e74c3c bold'),             # Red for errors
            ('warning', '#f39c12 bold'),           # Orange for warnings
            ('success', '#00ff88 bold'),           # Green for success
            
            # Background highlights
            ('highlighted-bg', 'bg:#2c3e50 #00ff88 bold'),  # Dark bg with green text
            ('selected-bg', 'bg:#34495e #00ff88 bold'),     # Slightly lighter bg
        ])

    def _log_message(self, message, level="info", dim_style=False):
        """Centralized logging with Rich formatting using cohesive app colors."""
        if self.console and RICH_AVAILABLE:
            style_map = {
                "info": "#5f87ff",           # Bright blue
                "success": "#00ff88 bold",   # Bright green bold
                "warning": "#f39c12 bold",   # Orange bold  
                "error": "#e74c3c bold",     # Red bold
                "debug": "#95a5a6",          # Light gray
                "bold blue": "#5f87ff bold", # Blue bold
                "bold cyan": "#17a2b8 bold", # Cyan bold
                "cyan": "#17a2b8",           # Cyan
                "green": "#00ff88",          # Green
                "blue": "#5f87ff",           # Blue
                "red": "#e74c3c",            # Red
                "yellow": "#f39c12"          # Orange/yellow
            }
            style = style_map.get(level, "#ffffff")
            if dim_style:
                style = f"dim {style}"
            self.console.print(message, style=style)
        else:
            print(f"[{level.upper()}] {message}")

    def ensure_temp_directory(self):
        """Ensure temporary directory exists for extractions."""
        if not self.temp_dir:
            self.temp_dir = tempfile.mkdtemp(prefix="apk_installer_")
            self._log_message(f"Created temp directory: {self.temp_dir}", "debug", dim_style=True)
        return self.temp_dir

    def cleanup_temp_files(self):
        """Clean up temporary files and directories."""
        cleanup_count = 0
        
        # Clean individual temp files
        for temp_file in self.temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    cleanup_count += 1
            except Exception as e:
                self._log_message(f"Warning: Could not clean up {temp_file}: {e}", "warning", dim_style=True)
        
        # Clean temp directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                cleanup_count += 1
                self._log_message(f"Cleaned up temp directory: {self.temp_dir}", "debug", dim_style=True)
            except Exception as e:
                self._log_message(f"Warning: Could not clean up temp directory: {e}", "warning", dim_style=True)
        
        if cleanup_count > 0:
            self._log_message(f"Cleaned up {cleanup_count} temporary items", "debug", dim_style=True)

    def get_package_name_from_apk(self, apk_path_str):
        """Extract package name from APK using multiple methods."""
        
        # Method 1: Try pyaxmlparser (most reliable)
        if AXMLPARSER_AVAILABLE:
            try:
                axmlp = AXMLP(apk_path_str)
                package_name = axmlp.get_package()
                if package_name:
                    return package_name
            except Exception as e:
                self._log_message(f"pyaxmlparser failed for {apk_path_str}: {e}", "debug", dim_style=True)
        
        # Method 2: Try aapt if available
        try:
            result = subprocess.run(
                ["aapt", "dump", "badging", apk_path_str],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith("package:"):
                        # Extract package name from: package: name='com.example.app' versionCode='123'
                        parts = line.split("'")
                        if len(parts) >= 2:
                            return parts[1]
        except FileNotFoundError:
            # AAPT tool not found - this is common and expected in many environments
            pass
        except (subprocess.TimeoutExpired, Exception) as e:
            self._log_message(f"Package detection issue: {e}", "debug", dim_style=True)
        
        # Method 3: Try adb if device is available (fallback)
        try:
            # This requires a connected device, so it's a last resort
            temp_path = f"/data/local/tmp/temp_package_check.apk"
            devices = self.get_connected_devices()
            
            if devices:
                device_id = devices[0]['id']
                
                # Push APK temporarily
                subprocess.run(
                    ["adb", "-s", device_id, "push", apk_path_str, temp_path],
                    capture_output=True,
                    timeout=30
                )
                
                # Get package info
                result = subprocess.run(
                    ["adb", "-s", device_id, "shell", "pm", "dump", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Clean up
                subprocess.run(
                    ["adb", "-s", device_id, "shell", "rm", temp_path],
                    capture_output=True
                )
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if "Package name=" in line:
                            return line.split("=")[1].strip()
                            
        except Exception as e:
            self._log_message(f"adb method failed: {e}", "debug", dim_style=True)
        
        # If all methods fail, return unknown
        return "unknown_package"

    def print_banner(self):
        """Display the application banner."""
        if self.console and RICH_AVAILABLE:
            banner_panel = Panel(
                ASCII_BANNER,
                style="bold blue",
                border_style="blue"
            )
            self.console.print(banner_panel)
            self.console.print()
        else:
            print(ASCII_BANNER)
            print()

    def validate_configuration(self):
        """Validate configuration settings."""
        validation_errors = []
        
        # Validate required sections exist
        required_sections = ["UNIQUENESS", "ADVANCED_SPOOFING", "FILE_DISCOVERY", "INSTALLATION", "LOGGING"]
        for section in required_sections:
            if section not in self.config:
                validation_errors.append(f"Missing configuration section: {section}")
        
        # Validate numeric values
        numeric_configs = [
            ("UNIQUENESS", "user_creation_retries"),
            ("FILE_DISCOVERY", "max_file_size_mb"),
            ("INSTALLATION", "installation_timeout_seconds"),
        ]
        
        for section, key in numeric_configs:
            if section in self.config and key in self.config[section]:
                try:
                    int(self.config[section][key])
                except ValueError:
                    validation_errors.append(f"Invalid numeric value for {section}.{key}")
        
        if validation_errors:
            self._log_message("Configuration validation errors found:", "warning")
            for error in validation_errors:
                self._log_message(f"  - {error}", "warning")
            return False
        
        return True

    def load_config(self):
        """Load configuration from file or create defaults."""
        config_file = "apk_installer_config.ini"
        
        if os.path.exists(config_file):
            try:
                config_parser = configparser.ConfigParser()
                config_parser.read(config_file, encoding='utf-8')
                
                # Convert to regular dict
                self.config = {}
                for section_name in config_parser.sections():
                    self.config[section_name] = dict(config_parser[section_name])
                
                # Validate configuration
                if self.validate_configuration():
                    self._log_message(f"Configuration loaded from {config_file}", "debug", dim_style=True)
                else:
                    self._log_message("Configuration validation failed, using defaults", "warning")
                    self.config = DEFAULT_CONFIG.copy()
                    
            except Exception as e:
                self._log_message(f"Error loading config: {e}, using defaults", "warning")
                self.config = DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.config = DEFAULT_CONFIG.copy()
            self.create_default_config(config_file)
        
        # Extract key configuration values
        self.adb_path = self.config.get("PATHS", {}).get("adb_path", "adb")
        self.apk_directory = self.config.get("PATHS", {}).get("apk_directory", "apks")

    def create_default_config(self, config_file_str):
        """Create default configuration file."""
        try:
            config_parser = configparser.ConfigParser()
            
            # Convert dict config to ConfigParser format
            for section_name, section_data in DEFAULT_CONFIG.items():
                config_parser.add_section(section_name)
                for key, value in section_data.items():
                    config_parser.set(section_name, key, str(value))
            
            # Write to file
            with open(config_file_str, 'w', encoding='utf-8') as f:
                config_parser.write(f)
                
            self._log_message(f"Created default configuration: {config_file_str}", "info")
            return True
            
        except Exception as e:
            self._log_message(f"Error creating default config: {e}", "error")
            return False

    def _apply_fallback_configs_and_init_manager(self):
        """Initialize spoofing manager with fallback configuration."""
        try:
            if not self.config:
                self.config = DEFAULT_CONFIG.copy()
            
            # Initialize spoofing manager with correct adb_path
            self.spoofing_manager = DeviceSpoofingManager(
                adb_path=self.adb_path,
                console=self.console,
                config=self.config
            )
            
            self._log_message("Spoofing manager initialized successfully", "debug", dim_style=True)
            
        except Exception as e:
            self._log_message(f"Error initializing spoofing manager: {e}", "error")
            # Create minimal spoofing manager for basic functionality
            self.spoofing_manager = DeviceSpoofingManager(adb_path=self.adb_path)

    def verify_adb(self):
        """Verify ADB is available and functional."""
        try:
            result = subprocess.run(
                ["adb", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version_info = result.stdout.strip().split('\n')[0]
                self._log_message(f"ADB verified: {version_info}", "debug", dim_style=True)
                return True
            else:
                self._log_message("ADB command failed", "error")
                return False
                
        except FileNotFoundError:
            self._log_message("ADB not found in PATH", "error")
            return False
        except subprocess.TimeoutExpired:
            self._log_message("ADB verification timed out", "error")
            return False
        except Exception as e:
            self._log_message(f"ADB verification error: {e}", "error")
            return False

    def get_connected_devices(self):
        """Get list of connected Android devices with detailed capability scanning."""
        self._log_message("\n📱 Device Detection & Capability Scan", "bold blue")
        if self.console: self.console.rule(style="#5f87ff")
        
        try:
            result = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self._log_message(f"✗ Failed to get device list: {result.stderr.strip()}", "error")
                return []
            
            devices_found = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip() and ('device' in line or 'offline' in line or 'unauthorized' in line):
                    parts = re.split(r'\s+', line.strip())
                    device_id = parts[0]
                    status = parts[1] if len(parts) > 1 else ""
                    
                    if status == "device":
                        # Extract model hint from device info
                        model_hint = next((p.split(":")[1] for p in parts if p.startswith("model:")), "")
                        
                        # Get basic device info (more robust, no advanced capabilities)
                        device_info = self.get_basic_device_info_str(device_id, model_hint)
                        
                        # Always add device to list first (don't let capability scanning block detection)
                        devices_found.append({
                            'id': device_id,
                            'info': device_info
                        })
                        
                        # Perform simplified capability scanning (optional, non-blocking)
                        try:
                            if device_id not in self.device_capabilities:
                                self._log_message(f"🔬 Scanning capabilities for {device_id} ({device_info})...", "debug", dim_style=True)
                                # Use a more basic capability detection that avoids config issues
                                capabilities = self._detect_basic_capabilities(device_id)
                                self.device_capabilities[device_id] = capabilities
                        except Exception as e:
                            # Don't let capability scanning failures block device detection
                            self._log_message(f"⚠️ Capability scanning failed for {device_id}: {e}", "debug", dim_style=True)
                            # Provide minimal capabilities
                            self.device_capabilities[device_id] = {
                                "multiuser_support": False,
                                "root_access": False,
                                "magisk_available": False,
                                "ephemeral_user_support": False,
                                "android_sdk_version": 0,
                            }

            if not devices_found:
                self._log_message("✗ No devices/emulators found or authorized.", "warning")
                self._log_message("💡 Make sure USB debugging is enabled and device is authorized.", "info")
            else:
                self._log_message(f"✓ Found {len(devices_found)} connected device(s)", "success")
            
            return devices_found
            
        except Exception as e:
            self._log_message(f"✗ Device detection error: {e}", "error")
            return []

    def get_device_info_str(self, device_id, model_hint=""):
        """Get detailed device information string with enhanced property detection."""
        try:
            def get_prop_fast(prop_name):
                result = self.spoofing_manager._run_adb_shell_command(device_id, ["getprop", prop_name], timeout=3)
                return result.stdout.strip() if result.returncode == 0 else None
            
            model = get_prop_fast("ro.product.model") or model_hint or "Unknown Model"
            android_version = get_prop_fast("ro.build.version.release") or "Unknown"
            build_id = get_prop_fast("ro.build.id") or "Unknown"
            manufacturer = get_prop_fast("ro.product.manufacturer") or ""
            
            # Enhanced device info with manufacturer if available
            if manufacturer and manufacturer.lower() != "unknown":
                return f"{manufacturer} {model} (Android {android_version}, Build: {build_id})"
            else:
                return f"{model} (Android {android_version}, Build: {build_id})"
                
        except Exception:
            return f"{model_hint or 'Unknown Device'} (Info unavailable)"

    def get_basic_device_info_str(self, device_id, model_hint=""):
        """Get basic device information with minimal ADB calls and robust error handling."""
        try:
            # Try to get basic model info with short timeout
            try:
                result = subprocess.run(
                    [self.adb_path, "-s", device_id, "shell", "getprop", "ro.product.model"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                model = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else model_hint
            except:
                model = model_hint
            
            # Fallback to model hint or device ID
            if not model or model.lower() == "unknown":
                model = model_hint or f"Device {device_id}"
            
            # Try to get Android version with short timeout
            try:
                result = subprocess.run(
                    [self.adb_path, "-s", device_id, "shell", "getprop", "ro.build.version.release"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                android_version = result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else "Unknown"
            except:
                android_version = "Unknown"
            
            return f"{model} (Android {android_version})"
            
        except Exception:
            # Ultimate fallback
            return f"{model_hint or device_id} (Connected)"

    def _detect_basic_capabilities(self, device_id):
        """Detect basic device capabilities without config dependencies."""
        caps = {
            "multiuser_support": False,
            "root_access": False,
            "magisk_available": False,
            "ephemeral_user_support": False,
            "android_sdk_version": 0,
        }
        
        try:
            # Get Android SDK version
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "getprop", "ro.build.version.sdk"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                sdk_version = int(result.stdout.strip())
                caps["android_sdk_version"] = sdk_version
                if sdk_version >= 26:
                    caps["ephemeral_user_support"] = True
            
            # Check for root access
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "su", "-c", "id"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and "uid=0(root)" in result.stdout:
                caps["root_access"] = True
                
                # Check for resetprop (Magisk)
                result = subprocess.run(
                    [self.adb_path, "-s", device_id, "shell", "su", "-c", "which resetprop"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0 and result.stdout.strip():
                    caps["magisk_available"] = True
            
            # Check multi-user support
            result = subprocess.run(
                [self.adb_path, "-s", device_id, "shell", "pm", "get-max-users"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                try:
                    max_users = int(result.stdout.strip().split()[-1])
                    if max_users > 1:
                        caps["multiuser_support"] = True
                except:
                    pass
        
        except Exception:
            pass  # Return default caps
        
        return caps

    def display_capability_summary(self, device_id, capabilities):
        """Display comprehensive device capability summary with professional formatting."""
        if not self.console or not capabilities:
            return

        # Check which features are enabled in config
        user_profile_enabled = self._get_config_boolean("UNIQUENESS", "enable_uniqueness_features", False)
        magisk_enabled = self._get_config_boolean("ADVANCED_SPOOFING", "enable_magisk_resetprop", False)
        
        if not (user_profile_enabled or magisk_enabled):
            return

        capability_items = []
        
        # Multi-user support assessment
        if user_profile_enabled:
            if capabilities.get("multiuser_support"):
                capability_items.append("[green]✓ Multi-user Support[/]")
                max_users = capabilities.get("max_users", "Unknown")
                capability_items.append(f"[dim cyan]  └─ Max Users: {max_users}[/]")
                
                if self._get_config_boolean("ADVANCED_SPOOFING", "use_ephemeral_users", True):
                    if capabilities.get("ephemeral_user_support"):
                        capability_items.append("[green]✓ Ephemeral User Support[/]")
                    else:
                        capability_items.append("[orange3]~ Ephemeral Users Not Available[/]")
            else:
                capability_items.append("[red]✗ No Multi-user Support[/]")
        
        # Root access assessment
        needs_root = magisk_enabled or (user_profile_enabled and self._get_config_boolean("UNIQUENESS", "auto_set_random_android_id", True))
        if needs_root:
            if capabilities.get("root_access"):
                capability_items.append("[green]✓ Root Access Available[/]")
                
                # Magisk-specific checks
                if magisk_enabled:
                    if capabilities.get("magisk_available"):
                        capability_items.append("[green]✓ Magisk Detected[/]")
                        magisk_version = capabilities.get("magisk_version", "Unknown")
                        capability_items.append(f"[dim cyan]  └─ Version: {magisk_version}[/]")
                    else:
                        capability_items.append("[orange3]~ Magisk Not Detected[/]")
                        capability_items.append("[dim yellow]  └─ Property spoofing may be limited[/]")
            else:
                capability_items.append("[red]✗ No Root Access[/]")
                if magisk_enabled:
                    capability_items.append("[dim red]  └─ Magisk spoofing unavailable[/]")

        # Storage space check
        storage_mb = capabilities.get("available_storage_mb")
        if storage_mb is not None:
            min_required = int(self._get_config_value("SPOOF_VALIDATION", "min_storage_mb", "500"))
            if storage_mb >= min_required:
                capability_items.append(f"[green]✓ Storage: {storage_mb}MB available[/]")
            else:
                capability_items.append(f"[orange3]⚠ Storage: {storage_mb}MB (minimum: {min_required}MB)[/]")

        # Display the capability summary
        if capability_items:
            self._log_message(f"🔍 Device Capabilities for [bold]{device_id}[/bold]:", "info")
            for item in capability_items:
                self.console.print(Text.from_markup(f"  {item}"))
            if self.console: 
                self.console.rule(style="dim cyan")

    def find_apk_files(self):
        """Find APK, XAPK, APKM, and ZIP files with detailed discovery reporting."""
        self._log_message("\n📦 APK/XAPK/APKM/ZIP File Discovery", "bold blue")
        if self.console: self.console.rule(style="blue")
        
        apk_dir = Path(self.apk_directory)
        
        if not apk_dir.exists():
            try:
                apk_dir.mkdir(parents=True, exist_ok=True)
                self._log_message(f"✓ Created APK directory: [italic]{apk_dir.resolve()}[/italic]", "success")
            except Exception as e:
                self._log_message(f"✗ Failed to create APK directory: {e}", "error")
                return []
        
        self._log_message(f"🔍 Scanning directory: [italic]{apk_dir.resolve()}[/italic]", "info")
        
        file_types = self._get_config_value("FILE_DISCOVERY", "allowed_extensions", "apk,xapk,apkm,zip").split(",")
        search_subdirs = self._get_config_boolean("FILE_DISCOVERY", "search_subdirectories", True)
        max_size_mb = int(self._get_config_value("FILE_DISCOVERY", "max_file_size_mb", "2048"))
        
        found_files = []
        file_type_counts = {"APK": 0, "XAPK": 0, "APKM": 0, "ZIP": 0}
        total_size_mb = 0
        
        # Enhanced file discovery with validation
        extensions = [f"*.{ft.strip().lower()}" for ft in file_types]
        
        for ext in extensions:
            search_pattern = f"**/{ext}" if search_subdirs else ext
            
            for file_path in apk_dir.glob(search_pattern):
                if file_path.is_file():
                    try:
                        file_type = file_path.suffix.upper().replace('.', '')
                        if file_type not in file_type_counts:
                            file_type_counts[file_type] = 0
                        
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        
                        # Skip files that are too large
                        if file_size_mb > max_size_mb:
                            self._log_message(f"⚠️ Skipping large file: {file_path.name} ({file_size_mb:.1f}MB > {max_size_mb}MB)", "warning")
                            continue
                        
                        # Skip empty files
                        if file_size_mb < 0.01:
                            self._log_message(f"⚠️ Skipping empty file: {file_path.name}", "warning") 
                            continue
                        
                        found_files.append({
                            'name': file_path.name,
                            'path': str(file_path.resolve()),
                            'size_mb': round(file_size_mb, 1),
                            'type': file_type,
                            'modified': file_path.stat().st_mtime
                        })
                        
                        file_type_counts[file_type] += 1
                        total_size_mb += file_size_mb
                        
                    except OSError as e:
                        self._log_message(f"⚠️ Error reading file {file_path.name}: {e}", "debug", dim_style=True)
        
        # Display discovery results
        if not found_files:
            self._log_message(f"✗ No compatible files found in [italic]{apk_dir.resolve()}[/italic]", "warning")
            self._log_message("💡 Supported formats: APK, XAPK, APKM, ZIP", "info")
        else:
            self._log_message(f"✓ Found {len(found_files)} compatible file(s) ([cyan]{total_size_mb:.1f}MB total[/cyan])", "success")
            
            # Show breakdown by file type
            type_summary = []
            for ftype, count in file_type_counts.items():
                if count > 0:
                    type_summary.append(f"{count} {ftype}")
            
            if type_summary and self.console:
                self.console.print(f"  📋 Breakdown: {', '.join(type_summary)}", style="dim cyan")
        
        # Sort by type, then by modification time (newest first), then by name
        found_files.sort(key=lambda x: (x['type'], -x['modified'], x['name'].lower()))
        return found_files

    def run(self):
        """Main application entry point."""
        try:
            self.print_banner()
            
            # Verify ADB
            if not self.verify_adb():
                self._log_message("Please ensure ADB is installed and in your PATH", "error")
                return False
            
            # Show main menu
            return self._show_main_menu()
            
        except KeyboardInterrupt:
            self._log_message("\nOperation cancelled by user", "warning")
            return False
        except Exception as e:
            self._log_message(f"Unexpected error: {e}", "error")
            return False
        finally:
            self.cleanup_temp_files()

    def _show_main_menu(self):
        """Display main menu and handle user selection."""
        while True:
            if self.console and RICH_AVAILABLE:
                self.console.print("\n" + "="*60, style="blue")
                self.console.print("  APK INSTALLER MAIN MENU", style="bold blue")
                self.console.print("="*60, style="blue")
            else:
                print("\n" + "="*60)
                print("  APK INSTALLER MAIN MENU")
                print("="*60)
            
            menu_options = [
                "🚀 Install APKs/XAPKs (Full Workflow)",
                "⚡ Simple Install APK(s)",
                "🎭 Spoofing Configuration", 
                "📱 Phone Management Tools",
                "⚙️  Configuration Settings",
                "❌ Exit"
            ]
            
            if QUESTIONARY_AVAILABLE:
                try:
                    choice = questionary.select(
                        "🎯 Please select an option:",
                        choices=menu_options,
                        style=self.app_style
                    ).ask()
                    
                    if not choice:  # User cancelled
                        return False
                        
                except KeyboardInterrupt:
                    return False
            else:
                # Fallback menu
                print("\nPlease select an option:")
                for i, option in enumerate(menu_options, 1):
                    print(f"{i}. {option}")
                
                try:
                    choice_num = int(input("\nEnter your choice (1-6): "))
                    if 1 <= choice_num <= len(menu_options):
                        choice = menu_options[choice_num - 1]
                    else:
                        self._log_message("Invalid choice", "error")
                        continue
                except (ValueError, KeyboardInterrupt):
                    return False
            
            # Handle menu selection
            if "Install APKs/XAPKs (Full Workflow)" in choice:
                if not self._run_installation_workflow():
                    continue
            elif "Simple Install APK(s)" in choice:
                if not self._run_simple_install_workflow():
                    continue
            elif "Spoofing Configuration" in choice:
                self._show_spoofing_configuration_menu()
            elif "Phone Management" in choice:
                self._show_phone_management_tools_menu()
            elif "Configuration Settings" in choice:
                self._display_configuration_menu()
            elif "Exit" in choice:
                self._log_message("Thank you for using APK Installer!", "info")
                return True

    def _run_installation_workflow(self):
        """Run the main APK installation workflow."""
        try:
            # Get connected devices
            devices = self.get_connected_devices()
            if not devices:
                self._log_message("No Android devices detected. Please connect a device and try again.", "error")
                return False
            
            # Select devices
            selected_devices = self.select_devices(devices)
            if not selected_devices:
                self._log_message("No devices selected", "warning")
                return False
            
            # Find APK files
            apk_files = self.find_apk_files()
            if not apk_files:
                self._log_message("No APK/XAPK/APKM files found in current directory", "error")
                return False
            
            # Select files
            selected_files = self.select_apks(apk_files)
            if not selected_files:
                self._log_message("No files selected", "warning")
                return False
            
            # Confirm and install
            if self.confirm_installation(selected_devices, selected_files):
                return self.install_selected_apks(selected_devices, selected_files)
            
            return False
            
        except Exception as e:
            self._log_message(f"Installation workflow error: {e}", "error")
            return False

    def _run_simple_install_workflow(self):
        """Run the simple APK installation workflow with force install and overwrite."""
        try:
            # Get connected devices
            devices = self.get_connected_devices()
            if not devices:
                self._log_message("No Android devices detected. Please connect a device and try again.", "error")
                return False
            
            # Select devices (multi-select)
            selected_devices = self.select_devices(devices)
            if not selected_devices:
                self._log_message("No devices selected", "warning")
                return False
            
            # Find APK files
            apk_files = self.find_apk_files()
            if not apk_files:
                self._log_message("No APK/XAPK/APKM files found in current directory", "error")
                return False
            
            # Select files (multi-select)
            selected_files = self.select_apks(apk_files)
            if not selected_files:
                self._log_message("No files selected", "warning")
                return False
            
            # Force install without confirmation - with beautiful styling
            if self.console and RICH_AVAILABLE:
                self.console.rule("[#5f87ff]Simple Install Mode[/#5f87ff]", style="#5f87ff")
                self.console.print("⚡ Force installing with overwrite capabilities...", style="#f39c12 bold")
                self.console.print("🔥 Bypassing confirmations for streamlined installation", style="#95a5a6")
            else:
                self._log_message("📦 Simple Install Mode: Force installing with overwrite...", "info")
            return self.simple_install_apks(selected_devices, selected_files)
            
        except Exception as e:
            self._log_message(f"Simple installation workflow error: {e}", "error")
            return False

    def _get_config_boolean(self, section, key, fallback=True):
        """Safely get boolean config value from either dict or ConfigParser."""
        try:
            if hasattr(self.config, 'getboolean'):
                # ConfigParser object
                return self.config.getboolean(section, key, fallback=fallback)
            else:
                # Dict object
                value = self.config.get(section, {}).get(key, str(fallback))
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes', 'on')
        except:
            return fallback

    def _get_config_value(self, section, key, fallback=""):
        """Safely get config value from either dict or ConfigParser."""
        try:
            if hasattr(self.config, 'get'):
                # ConfigParser object
                if hasattr(self.config, 'getboolean'):
                    return self.config.get(section, key, fallback=fallback)
                else:
                    # Dict object - no fallback keyword support
                    return self.config.get(section, {}).get(key, fallback)
            else:
                return fallback
        except:
            return fallback

    def select_devices(self, devices_list_param):
        """Simple interactive device selection with basic information."""
        if not devices_list_param:
            return []
        
        def formatter(dev_item):
            # Simple, clean device display
            device_id = dev_item['id']
            device_info = dev_item['info']
            
            # Add simple status indicators
            status_parts = []
            
            if device_id in self.device_capabilities:
                caps = self.device_capabilities[device_id]
                
                # Root status
                if caps.get("root_access", False):
                    status_parts.append("🔓 Rooted")
                else:
                    status_parts.append("🔒 Not Rooted")
                
                # Connection type (simplified)
                if "usb" in device_id.lower() or len(device_id) > 15:
                    status_parts.append("🔌 USB")
                else:
                    status_parts.append("📶 WiFi")
            
            status_str = " | ".join(status_parts) if status_parts else ""
            return f"{device_id} - {device_info}" + (f" ({status_str})" if status_str else "")
        
        if len(devices_list_param) == 1:
            self._log_message(f"✓ Auto-selected single device: {formatter(devices_list_param[0])}", "success")
            return devices_list_param
        
        return self._prompt_interactive_selection(
            devices_list_param,
            "device",
            formatter
        )

    def select_apks(self, apk_files_list_param):
        """Enhanced interactive APK file selection with detailed formatting."""
        if not apk_files_list_param:
            return []
        
        def formatter(f_info):
            # Color-coded file type display
            file_type = f_info['type']
            type_colors = {
                "APK": "cyan",
                "XAPK": "magenta", 
                "APKM": "bright_magenta",
                "ZIP": "yellow"
            }
            
            color = type_colors.get(file_type, "white")
            size_mb = f_info.get('size_mb', f_info.get('size', 0))  # Handle both key names
            
            # Use simple formatting since questionary doesn't support Rich markup
            return f"[{file_type}] {f_info['name']} ({size_mb:.1f} MB)"
        
        # Display additional information about bundled files
        if self.console:
            bundled_count = sum(1 for f in apk_files_list_param if f['type'] in ['XAPK', 'APKM', 'ZIP'])
            if bundled_count > 0:
                self.console.print("💡 Note: XAPK, APKM, and ZIP files will be processed for base APKs, split APKs, and OBB files.", style="dim")
        
        if len(apk_files_list_param) == 1:
            self._log_message(f"✓ Auto-selected single file: {formatter(apk_files_list_param[0])}", "success")
            return apk_files_list_param
        
        return self._prompt_interactive_selection(
            apk_files_list_param,
            "file",
            formatter
        )

    def _prompt_interactive_selection(self, items_list, item_type_name, item_formatter_func):
        """Enhanced interactive selection with rich UI and detailed prompts."""
        if not items_list:
            return []
        
        plural_name = f"{item_type_name}s"
        self._log_message(f"\n🎯 {item_type_name.title()} Selection", "bold blue")
        if self.console: self.console.rule(style="blue")

        if not QUESTIONARY_AVAILABLE:
            self._log_message(f"Cannot prompt for {item_type_name}: 'questionary' is not installed.", "error")
            self._log_message("Selecting all items by default...", "warning")
            return items_list

        # Display available items first for clarity
        self._log_message(f"Available {plural_name.lower()}:", "info")
        for item in items_list:
            if self.console:
                self.console.print(f"  • {item_formatter_func(item)}", style="bright_cyan")
            else:
                print(f"  • {item_formatter_func(item)}")

        try:
            choices = [
                questionary.Choice(
                    title=item_formatter_func(item),
                    value=item
                )
                for item in items_list
            ]
            
            # Enhanced selection loop with helpful instructions
            while True:
                if self.console:
                    self.console.print("\n💡 Controls: [#00ff88 bold]SPACEBAR[/#00ff88 bold] select/deselect • [#00ff88 bold]A[/#00ff88 bold] select all • [#00ff88 bold]I[/#00ff88 bold] invert • [#00ff88 bold]ENTER[/#00ff88 bold] confirm", style="#95a5a6")
                
                selected = questionary.checkbox(
                    f"📋 Select {plural_name.lower()}:",
                    choices=choices,
                    style=self.app_style
                ).ask()
                
                if selected is None:  # User cancelled
                    raise KeyboardInterrupt
                
                if selected:
                    self._log_message(f"✓ Selected {len(selected)} {plural_name.lower()}:", "success")
                    for item in selected:
                        if self.console:
                            self.console.print(f"  • {item_formatter_func(item)}", style="bright_green")
                        else:
                            print(f"  • {item_formatter_func(item)}")
                    return selected
                else:
                    self._log_message(f"⚠️ No {plural_name.lower()} selected! Use [bold]SPACEBAR[/bold] to select items, then [bold]ENTER[/bold].", "warning")
                    if not questionary.confirm(f"❓ Continue with no {plural_name.lower()} selected?", default=False, style=self.app_style).ask():
                        continue
                    else:
                        self._log_message(f"No {plural_name.lower()} selected.", "warning")
                        return []
            
        except KeyboardInterrupt:
            self._log_message(f"\n{item_type_name.title()} selection cancelled by user.", "warning")
            return []
        except Exception as e:
            self._log_message(f"Error in {item_type_name} selection: {e}", "error")
            return []

    def _prompt_single_selection(self, items_list, item_type_name, item_formatter_func):
        """Fallback single selection when questionary is not available."""
        print(f"\nAvailable {item_type_name}s:")
        for i, item in enumerate(items_list, 1):
            print(f"{i}. {item_formatter_func(item)}")
        
        try:
            choice = input(f"\nSelect {item_type_name} (1-{len(items_list)}, or 'all' for all): ").strip()
            
            if choice.lower() == 'all':
                return items_list
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(items_list):
                return [items_list[choice_num - 1]]
            else:
                self._log_message("Invalid selection", "error")
                return []
                
        except (ValueError, KeyboardInterrupt):
            return []

    def confirm_installation(self, selected_devices_list, selected_files_list):
        """Confirm installation details with user."""
        if self.console and RICH_AVAILABLE:
            self.console.print("\n" + "="*50, style="green")
            self.console.print("  INSTALLATION SUMMARY", style="bold green")
            self.console.print("="*50, style="green")
            
            # Devices table
            devices_table = Table(title="Selected Devices", show_header=True)
            devices_table.add_column("Device ID", style="cyan")
            devices_table.add_column("Device Info", style="white")
            
            for device in selected_devices_list:
                devices_table.add_row(device['id'], device['info'])
            
            self.console.print(devices_table)
            self.console.print()
            
            # Files table
            files_table = Table(title="Selected Files", show_header=True)
            files_table.add_column("File Name", style="yellow")
            files_table.add_column("Size", style="white")
            files_table.add_column("Type", style="magenta")
            
            for file_info in selected_files_list:
                files_table.add_row(
                    file_info['name'],
                    f"{file_info['size_mb']} MB",
                    file_info['type']
                )
            
            self.console.print(files_table)
        else:
            print("\n" + "="*50)
            print("  INSTALLATION SUMMARY")
            print("="*50)
            
            print(f"\nDevices ({len(selected_devices_list)}):")
            for device in selected_devices_list:
                print(f"  - {device['id']} - {device['info']}")
            
            print(f"\nFiles ({len(selected_files_list)}):")
            for file_info in selected_files_list:
                print(f"  - {file_info['name']} ({file_info['size_mb']} MB, {file_info['type']})")
        
        total_operations = len(selected_devices_list) * len(selected_files_list)
        
        if QUESTIONARY_AVAILABLE:
            try:
                confirm = questionary.confirm(
                    f"🚀 Proceed with {total_operations} installation operations?",
                    default=True,
                    style=self.app_style
                ).ask()
                
                return confirm if confirm is not None else False
            except KeyboardInterrupt:
                return False
        else:
            try:
                choice = input(f"\nProceed with {total_operations} installation operations? (y/N): ").strip().lower()
                return choice in ['y', 'yes']
            except KeyboardInterrupt:
                return False

    def install_selected_apks(self, selected_devices_list, selected_files_info_list):
        """Install selected APKs on selected devices."""
        total_ops = len(selected_devices_list) * len(selected_files_info_list)
        successful_ops = 0
        
        if self.console and RICH_AVAILABLE:
            self.console.print(f"\n🚀 Starting installation of {len(selected_files_info_list)} files on {len(selected_devices_list)} devices...", style="#5f87ff bold")
        else:
            print(f"\nStarting installation of {len(selected_files_info_list)} files on {len(selected_devices_list)} devices...")
        
        for device_dict in selected_devices_list:
            device_successes = 0
            device_failures = 0
            
            if self.console and RICH_AVAILABLE:
                self.console.print(f"\n📱 Installing on {device_dict['id']} - {device_dict['info']}", style="#17a2b8 bold")
            else:
                print(f"\nInstalling on {device_dict['id']} - {device_dict['info']}")
            
            for file_info_dict in selected_files_info_list:
                try:
                    success = self.install_apk_or_xapk(device_dict, file_info_dict)
                    if success:
                        successful_ops += 1
                        device_successes += 1
                    else:
                        device_failures += 1
                        
                except Exception as e:
                    self._log_message(f"Installation error: {e}", "error")
                    device_failures += 1
            
            # Show device summary
            self.show_device_installation_summary(device_dict['id'], device_successes, device_failures)
        
        # Show overall summary
        self.show_summary(successful_ops, total_ops)
        
        return successful_ops > 0

    def simple_install_apks(self, selected_devices_list, selected_files_info_list):
        """Simple force installation of APKs with overwrite capability."""
        total_ops = len(selected_devices_list) * len(selected_files_info_list)
        successful_ops = 0
        
        if self.console and RICH_AVAILABLE:
            self.console.print(f"\n⚡ Force installing {len(selected_files_info_list)} files on {len(selected_devices_list)} devices with overwrite...", style="#f39c12 bold")
            self.console.print("🔥 Streamlined installation - no confirmations needed!", style="#95a5a6")
        else:
            print(f"\nForce installing {len(selected_files_info_list)} files on {len(selected_devices_list)} devices with overwrite...")
        
        for device_dict in selected_devices_list:
            device_successes = 0
            device_failures = 0
            
            if self.console and RICH_AVAILABLE:
                self.console.print(f"\n📱 Force installing on {device_dict['id']} - {device_dict['info']}", style="#17a2b8 bold")
            else:
                print(f"\nForce installing on {device_dict['id']} - {device_dict['info']}")
            
            for file_info_dict in selected_files_info_list:
                try:
                    # Force install with overwrite - always replace existing packages
                    if self.simple_force_install_apk(device_dict, file_info_dict):
                        successful_ops += 1
                        device_successes += 1
                        if self.console and RICH_AVAILABLE:
                            self.console.print(f"  ✅ {file_info_dict['name']}", style="green")
                        else:
                            print(f"  ✅ {file_info_dict['name']}")
                    else:
                        device_failures += 1
                        if self.console and RICH_AVAILABLE:
                            self.console.print(f"  ❌ {file_info_dict['name']}", style="red")
                        else:
                            print(f"  ❌ {file_info_dict['name']}")
                            
                except Exception as e:
                    device_failures += 1
                    self._log_message(f"Installation error for {file_info_dict['name']}: {e}", "error")
            
            # Show device summary
            self.show_device_installation_summary(device_dict['id'], device_successes, device_failures)
        
        # Show overall summary
        self.show_summary(successful_ops, total_ops)
        
        return successful_ops > 0

    def simple_force_install_apk(self, device_dict, file_info_dict):
        """Force install APK with overwrite, bypassing all conflicts."""
        try:
            file_path = file_info_dict['path'] 
            file_type = file_info_dict.get('type', 'APK')
            device_id = device_dict['id']
            
            # Get package name first for uninstallation if needed
            package_name = self.get_package_name_from_apk(str(file_path))
            
            # First try to uninstall existing package (ignore failures)
            if package_name and package_name != "unknown_package":
                try:
                    uninstall_cmd = [self.adb_path, "-s", device_id, "uninstall", package_name]
                    subprocess.run(uninstall_cmd, capture_output=True, timeout=30)
                    # We don't care if uninstall fails - continue with install
                except:
                    pass  # Ignore uninstall failures
            
            # Force install with all aggressive flags
            if file_type == 'APK':
                install_cmd = [
                    self.adb_path, "-s", device_id, "install", 
                    "-r",  # Replace existing application
                    "-t",  # Allow test packages
                    "-d",  # Allow version downgrade
                    "-g",  # Grant all runtime permissions
                    str(file_path)
                ]
                
                # Add bypass flag only for newer Android versions that support it
                try:
                    # Check Android API level to determine if bypass flag is supported
                    check_result = subprocess.run(
                        [self.adb_path, "-s", device_id, "shell", "getprop", "ro.build.version.sdk"],
                        capture_output=True, text=True, timeout=10
                    )
                    if check_result.returncode == 0:
                        sdk_level = int(check_result.stdout.strip())
                        if sdk_level >= 30:  # Android 11+ supports this flag
                            install_cmd.insert(-1, "--bypass-low-target-sdk-block")
                except:
                    pass  # If we can't determine SDK level, proceed without the flag
            else:
                # For XAPK/APKM bundles, extract and install
                return self._simple_install_bundle_file(device_dict, file_info_dict)
            
            # Execute installation
            result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self._log_message(f"  ✅ {file_info_dict['name']} force installed successfully", "success")
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                
                # Provide helpful error messages for common issues
                if "Unknown option --bypass-low-target-sdk-block" in error_msg:
                    self._log_message(f"  ⚠️ {file_info_dict['name']} - Retrying without compatibility flags...", "warning")
                    # Retry without the problematic flag
                    basic_install_cmd = [
                        self.adb_path, "-s", device_id, "install", 
                        "-r", "-t", "-d", "-g",
                        str(file_path)
                    ]
                    retry_result = subprocess.run(basic_install_cmd, capture_output=True, text=True, timeout=300)
                    if retry_result.returncode == 0:
                        self._log_message(f"  ✅ {file_info_dict['name']} installed successfully (compatibility mode)", "success")
                        return True
                    else:
                        error_msg = retry_result.stderr.strip() or retry_result.stdout.strip()
                elif "INSTALL_FAILED_MISSING_SPLIT" in error_msg:
                    self._log_message(f"  ❌ {file_info_dict['name']} - Split APK missing additional files", "error")
                    self._log_message("  💡 Try using the XAPK or bundle version instead", "warning")
                    return False
                elif "INSTALL_FAILED_ALREADY_EXISTS" in error_msg:
                    self._log_message(f"  ❌ {file_info_dict['name']} - Signature conflict with existing app", "error")
                    return False
                elif "INSTALL_FAILED_INSUFFICIENT_STORAGE" in error_msg:
                    self._log_message(f"  ❌ {file_info_dict['name']} - Not enough storage space", "error")
                    return False
                
                # Generic error message for other failures
                self._log_message(f"  ❌ {file_info_dict['name']} - {error_msg}", "error")
                return False
                
        except Exception as e:
            self._log_message(f"Force install error: {e}", "error")
            return False

    def _simple_install_bundle_file(self, device_dict, file_info_dict):
        """Simple installation for bundle files (XAPK/APKM)."""
        try:
            # Extract bundle to temp directory
            bundle_path = file_info_dict['path']
            temp_extract_dir = self.ensure_temp_directory()
            extract_dir = os.path.join(temp_extract_dir, f"bundle_{int(time.time())}")
            
            # Extract archive
            with zipfile.ZipFile(bundle_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Find APK files in extracted content
            apk_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.endswith('.apk'):
                        apk_files.append(os.path.join(root, file))
            
            if not apk_files:
                self._log_message(f"No APK files found in bundle {file_info_dict['name']}", "error")
                return False
            
            # Force install each APK
            device_id = device_dict['id']
            all_success = True
            
            for apk_file in apk_files:
                try:
                    install_cmd = [
                        self.adb_path, "-s", device_id, "install", 
                        "-r", "-t", "-d", "-g",  # All force flags
                        apk_file
                    ]
                    
                    result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode != 0:
                        all_success = False
                        self._log_message(f"APK install failed: {os.path.basename(apk_file)}", "debug", dim_style=True)
                        
                except Exception as e:
                    all_success = False
                    self._log_message(f"APK install error: {e}", "debug", dim_style=True)
            
            # Cleanup temp directory
            try:
                shutil.rmtree(extract_dir)
            except:
                pass
                
            return all_success
            
        except Exception as e:
            self._log_message(f"Bundle install error: {e}", "error")
            return False

    def install_apk_or_xapk(self, device_dict, file_info_dict, target_user_id_str=None):
        """Install APK or bundle file on device."""
        file_type = file_info_dict.get('type', 'APK')
        
        if file_type == 'APK':
            return self._install_single_apk_file(device_dict, file_info_dict, target_user_id_str)
        else:
            return self._install_bundle_file(device_dict, file_info_dict, target_user_id_str)

    def _install_single_apk_file(self, device_dict, apk_file_data, target_user_id_str=None):
        """Install a single APK file."""
        device_id = device_dict['id']
        apk_path = apk_file_data['path']
        apk_name = apk_file_data['name']
        
        self._log_message(f"  📦 Installing {apk_name}...", "info")
        
        try:
            # Get package name
            package_name = self.get_package_name_from_apk(apk_path)
            
            # Install APK
            install_cmd = ["adb", "-s", device_id, "install"]
            
            # Add user parameter if specified
            if target_user_id_str:
                install_cmd.extend(["--user", target_user_id_str])
            
            # Add installation options from config
            if self.config.get("INSTALLATION", {}).get("allow_downgrade", "false") == "true":
                install_cmd.append("-d")
            
            if self.config.get("INSTALLATION", {}).get("replace_existing", "false") == "true":
                install_cmd.append("-r")
            
            if self.config.get("INSTALLATION", {}).get("grant_runtime_permissions", "true") == "true":
                install_cmd.append("-g")
            
            install_cmd.append(apk_path)
            
            # Execute installation
            timeout = int(self.config.get("INSTALLATION", {}).get("installation_timeout_seconds", "300"))
            result = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0 and "Success" in result.stdout:
                self._log_message(f"  ✅ {apk_name} installed successfully", "success")
                return True
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                self._log_message(f"  ❌ {apk_name} installation failed: {error_msg}", "error")
                return False
                
        except subprocess.TimeoutExpired:
            self._log_message(f"  ⏰ {apk_name} installation timed out", "error")
            return False
        except Exception as e:
            self._log_message(f"  ❌ {apk_name} installation error: {e}", "error")
            return False

    def _install_bundle_file(self, device_dict, bundle_file_data, target_user_id_str=None):
        """Install XAPK/APKM/ZIP bundle file."""
        device_id = device_dict['id']
        bundle_path = bundle_file_data['path']
        bundle_name = bundle_file_data['name']
        
        self._log_message(f"  📦 Extracting and installing {bundle_name}...", "info")
        
        try:
            # Extract bundle
            extract_dir = self.extract_xapk(bundle_path)
            if not extract_dir:
                return False
            
            # Find APKs in extraction
            apk_files = []
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file.lower().endswith('.apk'):
                        apk_files.append(os.path.join(root, file))
            
            if not apk_files:
                self._log_message(f"  ❌ No APK files found in {bundle_name}", "error")
                return False
            
            # Install APK files
            success_count = 0
            for apk_path in apk_files:
                apk_name = os.path.basename(apk_path)
                apk_data = {
                    'name': apk_name,
                    'path': apk_path,
                    'type': 'APK'
                }
                
                if self._install_single_apk_file(device_dict, apk_data, target_user_id_str):
                    success_count += 1
            
            if success_count > 0:
                self._log_message(f"  ✅ {bundle_name} installed successfully ({success_count}/{len(apk_files)} APKs)", "success")
                return True
            else:
                self._log_message(f"  ❌ {bundle_name} installation failed", "error")
                return False
                
        except Exception as e:
            self._log_message(f"  ❌ {bundle_name} installation error: {e}", "error")
            return False

    def extract_xapk(self, xapk_path_str):
        """Extract XAPK/APKM/ZIP file to temporary directory."""
        try:
            extract_dir = os.path.join(self.ensure_temp_directory(), f"extracted_{int(time.time())}")
            
            with zipfile.ZipFile(xapk_path_str, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            self._log_message(f"Extracted to: {extract_dir}", "debug", dim_style=True)
            return extract_dir
            
        except Exception as e:
            self._log_message(f"Extraction failed: {e}", "error")
            return None

    def show_device_installation_summary(self, device_id_str, successes_on_device_count, failures_on_device_count):
        """Show installation summary for a specific device."""
        total_on_device = successes_on_device_count + failures_on_device_count
        
        if total_on_device == 0:
            return
        
        success_rate = (successes_on_device_count / total_on_device) * 100
        
        if self.console and RICH_AVAILABLE:
            if success_rate == 100:
                style = "#00ff88 bold"
                icon = "✅"
            elif success_rate >= 50:
                style = "#f39c12 bold"  
                icon = "⚠️"
            else:
                style = "#e74c3c bold"
                icon = "❌"
            
            self.console.print(
                f"  {icon} Device {device_id_str}: {successes_on_device_count}/{total_on_device} successful ({success_rate:.0f}%)",
                style=style
            )
        else:
            print(f"  Device {device_id_str}: {successes_on_device_count}/{total_on_device} successful ({success_rate:.0f}%)")

    def show_summary(self, successful_ops_count, total_ops_count):
        """Show overall installation summary."""
        if total_ops_count == 0:
            return
        
        success_rate = (successful_ops_count / total_ops_count) * 100
        
        if self.console and RICH_AVAILABLE:
            # Beautiful rule separator with cohesive colors
            if success_rate == 100:
                rule_color, text_style = "#00ff88", "#00ff88 bold"
                message = "🎉 ALL INSTALLATIONS COMPLETED SUCCESSFULLY!"
                emoji = "🌟"
            elif success_rate >= 75:
                rule_color, text_style = "#00ff88", "#00ff88 bold" 
                message = "✅ MOST INSTALLATIONS COMPLETED SUCCESSFULLY"
                emoji = "✅"
            elif success_rate >= 25:
                rule_color, text_style = "#f39c12", "#f39c12 bold"
                message = "⚠️ SOME INSTALLATIONS COMPLETED"
                emoji = "⚠️"
            else:
                rule_color, text_style = "#e74c3c", "#e74c3c bold"
                message = "❌ MOST INSTALLATIONS FAILED"
                emoji = "💥"
            
            self.console.rule(f"[{rule_color}]Installation Complete[/{rule_color}]", style=rule_color)
            self.console.print(f"\n{message}", style=text_style)
            self.console.print(f"{emoji} Summary: {successful_ops_count}/{total_ops_count} successful ({success_rate:.1f}%)", style="#ffffff bold")
            
            # Additional context-aware info
            if successful_ops_count < total_ops_count:
                failed_count = total_ops_count - successful_ops_count
                self.console.print(f"📊 {successful_ops_count} succeeded • {failed_count} failed", style="#95a5a6")
                self.console.print("💡 Check device connections and permissions for failed installations", style="#95a5a6 dim")
            else:
                self.console.print("🎯 Perfect installation - all APKs installed successfully!", style="#00ff88")
                
            self.console.rule(style=rule_color)
        else:
            print("\n" + "="*60)
            print(f"📊 Installation Summary: {successful_ops_count}/{total_ops_count} successful ({success_rate:.1f}%)")
            print("="*60)

    def _show_spoofing_configuration_menu(self):
        """Show spoofing configuration submenu."""
        if self.console and RICH_AVAILABLE:
            self.console.rule("[#f39c12]🎭 Spoofing Configuration[/#f39c12]", style="#f39c12")
            self.console.print("🚧 Advanced spoofing features coming soon!", style="#f39c12 bold")
            self.console.print("📱 Device fingerprint spoofing, Android ID modification, and more...", style="#95a5a6")
        else:
            self._log_message("🎭 Spoofing configuration menu - Advanced features coming soon!", "warning")

    def _show_phone_management_tools_menu(self):
        """Show phone management tools submenu."""
        if self.console and RICH_AVAILABLE:
            self.console.rule("[#17a2b8]📱 Phone Management Tools[/#17a2b8]", style="#17a2b8") 
            self.console.print("🛠️ Device management features under development!", style="#17a2b8 bold")
            self.console.print("🔧 User profiles, permissions, cleanup tools, and diagnostics...", style="#95a5a6")
        else:
            self._log_message("📱 Phone management tools - Advanced features coming soon!", "warning")

    def _display_configuration_menu(self):
        """Show configuration settings menu."""
        if self.console and RICH_AVAILABLE:
            self.console.rule("[#5f87ff]⚙️ Configuration Settings[/#5f87ff]", style="#5f87ff")
            self.console.print("⚙️ Settings management interface in development!", style="#5f87ff bold") 
            self.console.print("🎛️ Installation options, device preferences, and advanced configs...", style="#95a5a6")
        else:
            self._log_message("⚙️ Configuration settings - Interface coming soon!", "warning") 