#!/usr/bin/env python3
"""
Device Spoofing Manager - v4.5.2 "Odyssey"
Advanced device spoofing capabilities with persistent fingerprints and anti-tracking measures.
"""

import os
import sys
import json
import random
import subprocess
import tempfile
import time
import shutil
import hashlib
import configparser
import re
from pathlib import Path
from datetime import datetime, timedelta

# Import constants from the new constants module
from installer_constants import (
    SCRIPT_VERSION,
    DEFAULT_CONFIG,
    DEFAULT_MANUFACTURERS_PATTERNS,
    DEFAULT_ANDROID_VERSION_RELEASE_MAP,
    DEFAULT_INTERNAL_SDK_MAP,
    DEVICE_PATTERNS_FILE
)

# Rich library support (optional)
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Questionary support (optional)
try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False


class DeviceSpoofingManager:
    """Manages advanced device spoofing capabilities with enhanced validation and patterns."""

    COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF = [
        "ro.product.brand",
        "ro.product.manufacturer",
        "ro.product.model",
        "ro.product.name",
        "ro.product.device",
        "ro.product.board",
        "ro.build.fingerprint",
        "ro.vendor.build.fingerprint",
        "ro.system.build.fingerprint",
        "ro.odm.build.fingerprint",
        "ro.build.id",
        "ro.build.display.id",
        "ro.build.version.incremental",
        "ro.build.version.release",
        "ro.build.version.sdk",
        "ro.serialno",
        "ro.boot.serialno",
        "ro.build.description",
        "ro.build.type",
        "ro.build.tags",
        "ro.build.host",
        "ro.build.user",
        "ro.build.date",
        "ro.build.date.utc",
        "ro.miui.ui.version.name",  # For Xiaomi devices
        "ro.miui.ui.version.code",  # For Xiaomi devices
    ]

    # Additional properties for comprehensive anti-tracking
    ANTI_TRACKING_EXTENDED_PROPS = [
        # Hardware/system identifiers commonly used for tracking
        "ro.hardware",
        "ro.hardware.chipname", 
        "ro.hardware.platform",
        "ro.board.platform",
        "ro.chipname",
        "ro.arch",
        "ro.product.cpu.abi",
        "ro.product.cpu.abilist",
        "ro.product.cpu.abilist32",
        "ro.product.cpu.abilist64",
        # Boot/firmware identifiers
        "ro.bootloader",
        "ro.boot.bootloader",
        "ro.boot.hardware",
        "ro.boot.revision",
        "ro.boot.baseband",
        "ro.baseband",
        # Vendor/OEM specific
        "ro.vendor.product.cpu.abilist",
        "ro.vendor.build.date",
        "ro.vendor.build.id",
        "ro.vendor.build.type",
        "ro.oem.*",  # Wildcard for OEM properties
        # Security/DRM identifiers  
        "ro.hardware.keystore",
        "ro.hardware.gatekeeper",
        "ro.crypto.type",
        "ro.crypto.state",
        # Additional build properties
        "ro.build.flavor",
        "ro.build.product",
        "ro.build.brand",
        "ro.build.device",
        "ro.build.board",
        "ro.build.version.base_os",
        "ro.build.version.security_patch",
        "ro.build.version.min_supported_target_sdk",
        # System service identifiers
        "ro.config.alarm_alert",
        "ro.config.notification_sound", 
        "ro.config.ringtone",
        # Network/connectivity properties
        "ro.telephony.call_ring.multiple",
        "ro.telephony.default_network",
        "ro.telephony.ril.config",
        "wifi.interface",
        "ro.wifi.channels",
        # Display/UI properties
        "ro.sf.lcd_density",
        "ro.config.density_split",
        "ro.config.small_battery",
        # Regional/locale identifiers
        "ro.product.locale.language",
        "ro.product.locale.region", 
        "ro.config.locales",
        # Vendor fingerprints and additional build props
        "ro.vendor.build.fingerprint",
        "ro.system_ext.build.fingerprint",
        "ro.product_services.build.fingerprint",
    ]

    def __init__(self, adb_path="adb", console=None, config=None):
        self.adb_path = adb_path
        self.console = console if console and RICH_AVAILABLE else None
        self.config = config if config else self._create_default_config_for_standalone()

        self.active_spoofed_users = {}
        self.property_backups = {}
        self.user_limit_originals = {}
        self.device_capabilities = {}

        self.patterns_data = self._load_device_patterns_file_or_defaults()
        self.device_manufacturers_patterns = self.patterns_data.get(
            "manufacturers", self._get_default_manufacturers_patterns()
        )
        self.android_version_release_map = self.patterns_data.get(
            "android_versions", self._get_default_android_version_release_map()
        )
        self.internal_sdk_map = self._get_default_internal_sdk_map()

    def _create_default_config_for_standalone(self):
        """Create default configuration for standalone usage."""
        config = configparser.ConfigParser()
        config.add_section("UNIQUENESS")
        config.set("UNIQUENESS", "enable_uniqueness_features", "true")
        config.set("UNIQUENESS", "cleanup_user_profile_after_session", "false")
        config.set("UNIQUENESS", "auto_set_random_android_id", "true")
        config.set("UNIQUENESS", "user_creation_retries", "3")
        config.set("UNIQUENESS", "validate_user_switch", "true")
        config.set("UNIQUENESS", "user_switch_initial_delay_seconds", "3")
        config.set("UNIQUENESS", "validate_user_switch_timeout_seconds", "30")
        config.set("UNIQUENESS", "user_switch_no_validation_delay_seconds", "5")
        config.set("UNIQUENESS", "post_new_user_install_delay_seconds", "10")

        config.add_section("ADVANCED_SPOOFING")
        config.set("ADVANCED_SPOOFING", "enable_magisk_resetprop", "true")
        config.set("ADVANCED_SPOOFING", "backup_original_properties", "true")
        config.set("ADVANCED_SPOOFING", "bypass_user_limits", "false")
        config.set("ADVANCED_SPOOFING", "use_ephemeral_users", "true")
        config.set("ADVANCED_SPOOFING", "spoof_manufacturer", "samsung")
        config.set("ADVANCED_SPOOFING", "spoof_model", "")
        config.set("ADVANCED_SPOOFING", "spoof_android_version", "13")
        config.set("ADVANCED_SPOOFING", "spoof_android_id_magisk", "true")
        config.set("ADVANCED_SPOOFING", "spoof_build_fingerprint", "true")
        config.set("ADVANCED_SPOOFING", "spoof_serial_number", "true")
        config.set("ADVANCED_SPOOFING", "spoof_device_model", "true")
        config.set("ADVANCED_SPOOFING", "spoof_android_version_props", "true")
        config.set("ADVANCED_SPOOFING", "auto_spoof_on_user_creation", "true")
        config.set("ADVANCED_SPOOFING", "restore_properties_after_session", "false")
        config.set("ADVANCED_SPOOFING", "restore_user_limits_after_session", "false")

        config.add_section("SPOOF_VALIDATION")
        config.set("SPOOF_VALIDATION", "min_storage_mb", "500")
        config.set("SPOOF_VALIDATION", "check_multiuser_support", "true")
        config.set("SPOOF_VALIDATION", "validate_root_access", "true")
        config.set("SPOOF_VALIDATION", "require_unlocked_device", "true")
        return config

    def _get_default_manufacturers_patterns(self):
        """Get default manufacturer patterns if constants aren't available."""
        try:
            return DEFAULT_MANUFACTURERS_PATTERNS
        except NameError:
            return {
                "samsung": {
                    "brand": "samsung",
                    "manufacturer": "samsung",
                    "models": [
                        {
                            "product": "dm3qxeea",
                            "device": "dm3q",
                            "model": "SM-S908B",
                            "board": "dm3q",
                            "display_name": "Galaxy S22 Ultra",
                            "hardware": "qcom",
                        }
                    ],
                    "build_id_patterns": {"13": ["TP1A", "TQ1A"], "14": ["UP1A", "UQ1A"]},
                    "serial_pattern": "R{8}",
                    "serial_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
                },
                "google": {
                    "brand": "google",
                    "manufacturer": "Google",
                    "models": [
                        {
                            "product": "husky",
                            "device": "husky",
                            "model": "Pixel 8 Pro",
                            "board": "husky",
                            "display_name": "Pixel 8 Pro",
                            "hardware": "husky",
                        }
                    ],
                    "build_id_patterns": {"13": ["TQ1A"], "14": ["UP1A"]},
                    "serial_pattern": "{16}",
                    "serial_chars": "0123456789ABCDEF",
                }
            }

    def _get_default_android_version_release_map(self):
        """Get default Android version mapping."""
        try:
            return DEFAULT_ANDROID_VERSION_RELEASE_MAP
        except NameError:
            return {
                "13": {"release": "13", "sdk": 33},
                "14": {"release": "14", "sdk": 34},
                "15": {"release": "15", "sdk": 35}
            }

    def _get_default_internal_sdk_map(self):
        """Get default SDK mapping."""
        try:
            return DEFAULT_INTERNAL_SDK_MAP
        except NameError:
            return {33: "13", 34: "14", 35: "15"}

    def _load_device_patterns_file_or_defaults(self):
        """Load device patterns from file or use defaults."""
        try:
            patterns_file = Path(DEVICE_PATTERNS_FILE)
            if patterns_file.exists():
                with open(patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError, NameError) as e:
            self._log_message(f"Could not load device patterns: {e}. Using defaults.", "warning")
        
        # Return default patterns
        return {
            "manufacturers": self._get_default_manufacturers_patterns(),
            "android_versions": self._get_default_android_version_release_map()
        }

    def _run_adb_shell_command(
        self,
        device_id,
        command_list_or_str,
        timeout=30,
        as_root=False,
        target_user_id=None,
    ):
        """Execute ADB shell command with enhanced error handling and user targeting."""
        import shlex
        
        base_cmd = [self.adb_path]
        if device_id:
            base_cmd.extend(["-s", device_id])
        base_cmd.append("shell")

        full_command_str_for_su = ""
        command_list_for_direct_exec = []

        if isinstance(command_list_or_str, str):
            if as_root:
                full_command_str_for_su = command_list_or_str
            else:
                command_list_for_direct_exec = shlex.split(command_list_or_str)
        elif isinstance(command_list_or_str, list):
            command_list_for_direct_exec = command_list_or_str
            if as_root:
                quoted_args = []
                for arg in command_list_or_str:
                    arg_escaped = str(arg).replace("'", "'\\''"
                    )
                    if " " in arg_escaped or any(
                        c in arg_escaped for c in '&|;()<>$`\\"!*?#'
                    ):
                        quoted_args.append(f"'{arg_escaped}'")
                    else:
                        quoted_args.append(arg_escaped)
                full_command_str_for_su = " ".join(quoted_args)
        else:
            self._log_message(
                f"Invalid command type: {type(command_list_or_str)}", "error"
            )
            return subprocess.CompletedProcess(
                args=[], returncode=-3, stdout="", stderr="Invalid command type"
            )

        final_cmd_list = []
        if as_root:
            if not full_command_str_for_su:
                self._log_message("Error: Empty command for root execution.", "error")
                return subprocess.CompletedProcess(
                    args=[], returncode=-4, stdout="", stderr="Empty root command"
                )

            su_prefix = ["su"]
            if target_user_id is not None and str(target_user_id) != "0":
                su_prefix = ["su", str(target_user_id)]
            else:
                su_prefix = ["su", "0"]

            final_cmd_list = base_cmd + su_prefix + ["-c", full_command_str_for_su]
        else:
            final_cmd_list = base_cmd + command_list_for_direct_exec

        try:
            result = subprocess.run(
                final_cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            return result
        except subprocess.TimeoutExpired:
            self._log_message(f"⏰ Command timed out: {' '.join(final_cmd_list)}", "warning")
            return subprocess.CompletedProcess(
                args=final_cmd_list, returncode=-1, stdout="", stderr="Timeout"
            )
        except Exception as e:
            self._log_message(
                f"💥 Exception running command: {e}", "error"
            )
            return subprocess.CompletedProcess(
                args=final_cmd_list, returncode=-2, stdout="", stderr=str(e)
            )

    def _log_message(self, message, level="info", dim_style=False):
        """Log message with cohesive Rich formatting matching installer colors."""
        if not self.console:
            print(f"[{level.upper()}] {message}")
            return
        style_map = {
            "info": "#5f87ff",           # Bright blue
            "success": "#00ff88 bold",   # Bright green bold
            "warning": "#f39c12 bold",   # Orange bold  
            "error": "#e74c3c bold",     # Red bold
            "debug": "#95a5a6",          # Light gray
        }
        style = style_map.get(level, "#ffffff")
        if dim_style:
            style = f"dim {style}"
        self.console.print(message, style=style, markup=True)

    def _generate_random_hex_string(self, length, uppercase=False):
        """Generate random hexadecimal string."""
        hex_chars = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
        return "".join(random.choice(hex_chars) for _ in range(length))

    def _generate_random_string(
        self, length, chars=None, uppercase=False, lowercase=False
    ):
        """Generate random string with specified character set."""
        if chars is None:
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        if uppercase:
            chars = chars.upper()
        elif lowercase:
            chars = chars.lower()
        return "".join(random.choice(chars) for _ in range(length))

    def get_current_property_value(self, device_id, property_name):
        """Get current value of a device property."""
        result = self._run_adb_shell_command(device_id, ["getprop", property_name])
        return result.stdout.strip() if result.returncode == 0 else ""

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

    def backup_property(self, device_id, property_name):
        """Backup current property value before spoofing."""
        if not self._get_config_boolean("ADVANCED_SPOOFING", "backup_original_properties", True):
            return
        if device_id not in self.property_backups:
            self.property_backups[device_id] = {}
        if property_name in self.property_backups[device_id]:
            return

        original_value = self.get_current_property_value(device_id, property_name)
        self.property_backups[device_id][property_name] = original_value

        # Verification read after backup
        current_value_after_read = self.get_current_property_value(
            device_id, property_name
        )
        if current_value_after_read != original_value:
            self._log_message(
                f"  Property '{property_name}' changed during backup read! "
                f"Initial: '{original_value}', After read: '{current_value_after_read}'."
                " This could indicate instability or a very dynamic property.",
                "warning",
            )
        else:
            self._log_message(
                f"  Backed up original '{property_name}': '{original_value}' (Verified)",
                "debug",
                dim_style=True,
            )

    def set_property_with_resetprop(self, device_id, property_name, value):
        """Set property using resetprop with multiple strategies."""
        self.backup_property(device_id, property_name)
        
        # Try multiple resetprop strategies for stubborn properties
        strategies = [
            ["resetprop", property_name, str(value)],
            ["resetprop", "-n", property_name, str(value)],
            ["resetprop", "--force", property_name, str(value)],
        ]
        
        for strategy_idx, command_list in enumerate(strategies):
            strategy_name = ["Standard", "Non-persistent", "Force"][strategy_idx]
            
            result = self._run_adb_shell_command(device_id, command_list, as_root=True)
            if result.returncode == 0:
                time.sleep(0.2)
                newly_set_value = self.get_current_property_value(device_id, property_name)
                if newly_set_value == str(value):
                    self._log_message(
                        f"  ✓ Set {property_name} to: '{value}' (Verified, {strategy_name})", "success"
                    )
                    return True
                else:
                    self._log_message(
                        f"  ⚠️ Set {property_name} to: '{value}' (Command OK with {strategy_name}, but verification failed. Got: '{newly_set_value}')",
                        "warning",
                    )
                    continue
            else:
                self._log_message(
                    f"  ❌ Failed to set {property_name} with {strategy_name}: {result.stderr.strip()}",
                    "warning",
                )
                continue

        # All strategies failed
        self._log_message(
            f"  ❌ All resetprop strategies failed for {property_name}",
            "error",
        )
        return False

    def detect_capabilities(self, device_id):
        """Detect device capabilities for spoofing."""
        caps = {
            "multiuser_support": False,
            "root_access": False,
            "magisk_available": False,
            "ephemeral_user_support": False,
            "android_sdk_version": 0,
        }
        try:
            res_sdk = self._run_adb_shell_command(
                device_id, ["getprop", "ro.build.version.sdk"]
            )
            if res_sdk.returncode == 0 and res_sdk.stdout.strip().isdigit():
                sdk_version = int(res_sdk.stdout.strip())
                caps["android_sdk_version"] = sdk_version
                if sdk_version >= 26:
                    caps["ephemeral_user_support"] = True

            res_max_users = self._run_adb_shell_command(
                device_id, ["pm", "get-max-users"]
            )
            if res_max_users.returncode == 0 and res_max_users.stdout.strip():
                max_users_str = res_max_users.stdout.strip()
                max_users_val = 0
                match = re.search(
                    r"Maximum supported users:\s*(\d+)", max_users_str, re.IGNORECASE
                )
                if match:
                    max_users_val = int(match.group(1))
                elif max_users_str.isdigit():
                    max_users_val = int(max_users_str)

                if max_users_val > 1:
                    caps["multiuser_support"] = True
                elif max_users_val == 1 and caps["android_sdk_version"] >= 21:
                    res_mu_enabled = self._run_adb_shell_command(
                        device_id, ["settings", "get", "global", "multi_user_enabled"]
                    )
                    if (
                        res_mu_enabled.returncode == 0
                        and res_mu_enabled.stdout.strip() == "1"
                    ):
                        caps["multiuser_support"] = True

            # Check for root access
            res_root_id = self._run_adb_shell_command(
                device_id, "id", as_root=True, timeout=5
            )
            if res_root_id.returncode == 0 and "uid=0(root)" in res_root_id.stdout:
                caps["root_access"] = True
                res_resetprop_check = self._run_adb_shell_command(
                    device_id, "which resetprop", as_root=True, timeout=5
                )
                if res_resetprop_check.returncode == 0 and res_resetprop_check.stdout.strip():
                    caps["magisk_available"] = True
                    self._log_message(
                        f"  Found 'resetprop' utility at: {res_resetprop_check.stdout.strip()}.",
                        "debug",
                        dim_style=True
                    )

        except Exception as e:
            self._log_message(
                f"Error detecting capabilities for {device_id}: {e}", "error"
            )
        
        # Cache capabilities
        self.device_capabilities[device_id] = caps
        return caps

    def restore_all_properties(self, device_id):
        """Restore all backed up properties for a device."""
        if device_id not in self.property_backups:
            return True

        all_success = True
        for prop_name, original_value in self.property_backups[device_id].items():
            if original_value:
                success = self.set_property_with_resetprop(device_id, prop_name, original_value)
            else:
                delete_cmd = ["resetprop", "--delete", prop_name]
                result = self._run_adb_shell_command(device_id, delete_cmd, as_root=True)
                success = result.returncode == 0

            if not success:
                all_success = False

        if all_success:
            self.property_backups.pop(device_id, None)

        return all_success

    def apply_random_device_fingerprint_for_new_user(self, device_id):
        """Apply random device fingerprint for newly created user."""
        available_manufacturers = list(self.device_manufacturers_patterns.keys())
        if not available_manufacturers:
            self._log_message("No manufacturer patterns available", "error")
            return False
            
        manufacturer_key = random.choice(available_manufacturers)
        manufacturer_data = self.device_manufacturers_patterns[manufacturer_key]
        
        models = manufacturer_data.get("models", [])
        if not models:
            self._log_message(f"No models available for {manufacturer_key}", "error")
            return False
            
        model_data = random.choice(models)
        model_name = model_data.get("model", "Unknown")
        
        available_versions = list(self.android_version_release_map.keys())
        android_version = random.choice(available_versions) if available_versions else "13"
        
        self._log_message(
            f"  🎲 Random device: {manufacturer_key.title()} {model_name} (Android {android_version})",
            "info",
            dim_style=True
        )
        
        return self.apply_device_spoofing(
            device_id, manufacturer_key, model_name, android_version
        )

    def apply_device_spoofing(
        self,
        device_id,
        target_manufacturer_key,
        target_model_name_config,
        target_android_version_key,
    ):
        """Apply device spoofing with comprehensive property modification."""
        self._log_message(f"🎭 Applying device spoofing to {device_id}...", "info")
        
        # Get capabilities
        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(device_id)
        
        if not caps.get("root_access") or not caps.get("magisk_available"):
            self._log_message(
                "Root access with resetprop required for device spoofing",
                "error"
            )
            return False

        # Find manufacturer and model data
        manufacturer_data = self.device_manufacturers_patterns.get(target_manufacturer_key)
        if not manufacturer_data:
            self._log_message(f"Unknown manufacturer: {target_manufacturer_key}", "error")
            return False

        # Find matching model
        models = manufacturer_data.get("models", [])
        model_data = None
        for model in models:
            if model.get("model") == target_model_name_config or model.get("display_name") == target_model_name_config:
                model_data = model
                break
        
        if not model_data and models:
            model_data = models[0]  # Use first model as fallback
            
        if not model_data:
            self._log_message(f"No model data available for {target_manufacturer_key}", "error")
            return False

        # Generate realistic values
        fingerprint = self.generate_realistic_fingerprint(
            target_manufacturer_key, model_data, target_android_version_key
        )
        serial_number = self.generate_serial_number(target_manufacturer_key)
        
        version_info = self.android_version_release_map.get(target_android_version_key, {})
        release_version = version_info.get("release", target_android_version_key)
        sdk_version = str(version_info.get("sdk", "33"))

        # Apply spoofing properties
        spoof_props = {
            "ro.product.brand": manufacturer_data.get("brand", target_manufacturer_key),
            "ro.product.manufacturer": manufacturer_data.get("manufacturer", target_manufacturer_key.title()),
            "ro.product.model": model_data.get("model", "Unknown"),
            "ro.product.name": model_data.get("product", model_data.get("model", "Unknown")),
            "ro.product.device": model_data.get("device", model_data.get("model", "Unknown")),
            "ro.product.board": model_data.get("board", model_data.get("device", "unknown")),
            "ro.build.fingerprint": fingerprint,
            "ro.build.version.release": release_version,
            "ro.build.version.sdk": sdk_version,
            "ro.serialno": serial_number,
            "ro.boot.serialno": serial_number,
        }

        # Apply properties
        success_count = 0
        total_props = len(spoof_props)
        
        for prop_name, prop_value in spoof_props.items():
            if self.set_property_with_resetprop(device_id, prop_name, prop_value):
                success_count += 1

        success_rate = (success_count / total_props) * 100
        self._log_message(
            f"  ✓ Device spoofing completed: {success_count}/{total_props} properties ({success_rate:.1f}%)",
            "success" if success_rate >= 80 else "warning"
        )
        
        return success_rate >= 50  # Consider success if at least 50% of properties were set

    def generate_realistic_fingerprint(
        self,
        manufacturer_name_cfg,
        model_data,
        android_version_key_cfg,
    ):
        """Generate realistic device fingerprint."""
        version_info = self.android_version_release_map.get(android_version_key_cfg, {})
        release_version = version_info.get("release", android_version_key_cfg)
        
        build_id = self._generate_build_id(manufacturer_name_cfg, android_version_key_cfg)
        incremental = self._generate_incremental(manufacturer_name_cfg, model_data, build_id)
        
        brand = model_data.get("brand", manufacturer_name_cfg.lower())
        product = model_data.get("product", model_data.get("model", "unknown"))
        device = model_data.get("device", product)
        
        fingerprint = f"{brand}/{product}/{device}:{release_version}/{build_id}/{incremental}:user/release-keys"
        
        return fingerprint

    def _generate_build_id(self, manufacturer_config_name, android_version_key):
        """Generate realistic build ID for manufacturer and Android version."""
        patterns = self.device_manufacturers_patterns.get(manufacturer_config_name, {})
        build_patterns = patterns.get("build_id_patterns", {})
        version_patterns = build_patterns.get(android_version_key, [])
        
        if version_patterns:
            base_pattern = random.choice(version_patterns)
        else:
            # Fallback patterns based on Android version
            if android_version_key == "14":
                base_pattern = "UP1A"
            elif android_version_key == "13":
                base_pattern = "TQ1A"
            else:
                base_pattern = "SP1A"
        
        # Generate timestamp-like suffix
        year = random.randint(2022, 2024)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        build_number = random.randint(1, 999)
        
        return f"{base_pattern}.{year:04d}{month:02d}{day:02d}.{build_number:03d}"

    def _generate_incremental(self, manufacturer_config_name, model_data, build_id_str):
        """Generate incremental build number."""
        parts = build_id_str.split('.')
        if len(parts) >= 3:
            base = parts[-1]
        else:
            base = str(random.randint(100, 999))
        
        # Add manufacturer-specific suffix
        suffixes = {
            "samsung": ["N960FXXS", "G973FXXS", "SM-G"],
            "google": ["factory-", "user-"],
            "xiaomi": ["V", "MIUI"],
        }
        
        manufacturer_suffixes = suffixes.get(manufacturer_config_name, [""])
        if manufacturer_suffixes and manufacturer_suffixes[0]:
            suffix = random.choice(manufacturer_suffixes)
            return f"{suffix}{base}"
        
        return base

    def generate_serial_number(self, manufacturer_config_name):
        """Generate realistic serial number for manufacturer."""
        patterns = self.device_manufacturers_patterns.get(manufacturer_config_name, {})
        serial_pattern = patterns.get("serial_pattern", "{8}")
        serial_chars = patterns.get("serial_chars", "0123456789ABCDEF")
        
        # Parse pattern - {N} means N random characters
        pattern_match = re.search(r'\{(\d+)\}', serial_pattern)
        if pattern_match:
            length = int(pattern_match.group(1))
            serial = self._generate_random_string(length, serial_chars, uppercase=True)
            return re.sub(r'\{\d+\}', serial, serial_pattern)
        else:
            # Pattern with specific format like "R{8}"
            result = serial_pattern
            for match in re.finditer(r'\{(\d+)\}', serial_pattern):
                length = int(match.group(1))
                random_part = self._generate_random_string(length, serial_chars, uppercase=True)
                result = result.replace(match.group(0), random_part, 1)
            return result

    def get_install_command_args_for_user(self, user_id_or_str=None):
        """Constructs install command arguments for targeting a specific user."""
        args = []
        if user_id_or_str is not None:
            args.extend(["--user", str(user_id_or_str)])
        return args 