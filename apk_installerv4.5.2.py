#!/usr/bin/env python3
"""
Professional APK Installation Tool - v4.2.0 "Odyssey"
- Merged Features: Combines the best of v3.5.0 and v4.0.0.
- New Feature: Automatic dependency installer for rich, pyaxmlparser, questionary.
- New Feature: Interactive multi-selection menu for APKs/devices via `questionary`.
- New Feature: Prompt for custom user profile names, with a timestamped default.
- New Feature: "User Profile Management" menu to list and remove existing profiles on a device.
- Restored: Full interactive spoofing configuration menu from v3.5.0.
- Restored: "Phone Management Tools" menu with clipboard setter.
- Restored: Robust installation logic with detailed error parsing and uninstall-on-conflict prompts.
- Fix: Corrected interactive selection logic to re-prompt on empty selection, improving user experience.
- Fix: Attempt to enable clipboard for new user profiles to improve integration with tools like scrcpy.
- General code polish, updated versioning, and refined logging.
"""

import configparser
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

# --- Dependency Checks & Auto-Installation ---
try:
    from rich import box
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from pyaxmlparser import APK as AXMLParserAPK

    PYAXMLPARSER_AVAILABLE = True
except ImportError:
    PYAXMLPARSER_AVAILABLE = False

try:
    import questionary
    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False


DEVICE_PATTERNS_FILE = "device_patterns.json"
SCRIPT_VERSION = "v4.2.0"


# --- BEGIN DeviceSpoofingManager (From v3.5.0 - Mature & Complete) ---
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

    # Additional properties for comprehensive anti-tracking (used with auto-spoof on user profile creation)
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
        # This is primarily for when DeviceSpoofingManager is used standalone,
        # the main script has its own default config generation.
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
                    },
                    {
                        "product": "gts7xlwifi",
                        "device": "gts7xlwifi",
                        "model": "SM-T970",
                        "board": "kona",
                        "display_name": "Galaxy Tab S7+ Wi-Fi",
                        "hardware": "qcom",
                    },
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
                    },
                    {
                        "product": "oriole",
                        "device": "oriole",
                        "model": "Pixel 6",
                        "board": "slider",
                        "display_name": "Pixel 6",
                        "hardware": "gs101",
                    },
                ],
                "build_id_patterns": {
                    "13": ["TQ3A", "TP1A"],
                    "14": ["UD1A", "UP1A"],
                    "15": ["AP1A", "AP2A"],
                },
                "serial_pattern": "{12}",
                "serial_chars": "0123456789ABCDEF",
            },
            "xiaomi": {
                "brand": "Xiaomi",
                "manufacturer": "Xiaomi",
                "models": [
                    {
                        "product": "veux",
                        "device": "veux",
                        "model": "2201116SG",
                        "board": "veux",
                        "display_name": "Redmi Note 11 Pro+ 5G",
                        "hardware": "mt6877",
                    },
                    {
                        "product": "lisa",
                        "device": "lisa",
                        "model": "2109119DG",
                        "board": "lisa",
                        "display_name": "Xiaomi 11 Lite 5G NE",
                        "hardware": "qcom",
                    },
                ],
                "build_id_patterns": {"13": ["TKQ1", "TP1A"], "14": ["UKQ1", "UP1A"]},
                "serial_pattern": "{8}",
                "serial_chars": "0123456789abcdef",
                "miui_version_patterns": {  # Example, can be more specific
                    "13": [
                        "V14.0.{random_digit}.0.T{random_letter}CMIXM",
                        "V14.0.{random_digit}.0.S{random_letter}CEUXM",
                    ],
                    "14": [
                        "V15.0.{random_digit}.0.U{random_letter}CMIXM",
                        "HyperOS1.0.{random_digit}.0.U{random_letter}CEUXM",
                    ],
                },
            },
        }

    def _get_default_android_version_release_map(self):
        return {
            "11": "11",
            "12": "12",
            "12L": "12",
            "13": "13",
            "14": "14",
            "15": "15",
        }  # 12L maps to 12 for release string

    def _get_default_internal_sdk_map(self):
        return {"11": 30, "12": 31, "12L": 32, "13": 33, "14": 34, "15": 35}

    def _load_device_patterns_file_or_defaults(self):
        patterns_file = Path(DEVICE_PATTERNS_FILE)
        loaded_data = {}
        if patterns_file.exists():
            try:
                with open(patterns_file, "r", encoding="utf-8") as f_json:
                    loaded_data = json.load(f_json)
                self._log_message(
                    f"Loaded device patterns from {patterns_file}",
                    "info",
                    dim_style=True,
                )
            except Exception as e:
                self._log_message(
                    f"Error loading {patterns_file}: {e}. Using hardcoded defaults for all sections.",
                    "warning",
                )
                loaded_data = {}

        defaults = {
            "manufacturers": self._get_default_manufacturers_patterns(),
            "android_versions": self._get_default_android_version_release_map(),
            "build_fingerprint_format": "{brand}/{product}/{device}:{android_version_release}/{build_id}/{incremental}:user/release-keys",
            "props_to_spoof": list(self.COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF),
            "common_build_tags": "release-keys",
            "common_build_type": "user",
        }

        final_data = {}
        for key, default_value in defaults.items():
            if key in loaded_data:
                final_data[key] = loaded_data[key]
                if key == "props_to_spoof" and not isinstance(loaded_data[key], list):
                    self._log_message(
                        f"'{key}' in {patterns_file} is not a list. Using comprehensive default.",
                        "warning",
                    )
                    final_data[key] = default_value
                elif key == "props_to_spoof" and not loaded_data[key]:
                    self._log_message(
                        f"'{key}' in {patterns_file} is empty. Minimal property spoofing will occur.",
                        "info",
                    )
            else:
                self._log_message(
                    f"Key '{key}' not found in {patterns_file if patterns_file.exists() else 'JSON (file not found)'}. Using hardcoded default.",
                    "info",
                    dim_style=True,
                )
                final_data[key] = default_value

        if not patterns_file.exists():
            self._log_message(
                "Device patterns file not found. Using all hardcoded defaults.",
                "info",
                dim_style=True,
            )
        return final_data

    def _run_adb_shell_command(
        self,
        device_id,
        command_list_or_str,
        timeout=30,
        as_root=False,
        target_user_id=None,
    ):
        base_cmd = [self.adb_path]
        if device_id:
            base_cmd.extend(["-s", device_id])
        base_cmd.append("shell")

        full_command_str_for_su = ""
        command_list_for_direct_exec = []

        if isinstance(command_list_or_str, str):
            # If it's already a string, assume it's pre-formatted for shell
            if as_root:
                full_command_str_for_su = command_list_or_str
            else:  # This path is less common now, usually lists are preferred
                command_list_for_direct_exec = shlex.split(command_list_or_str)
        elif isinstance(command_list_or_str, list):
            # If it's a list, construct the string for su -c, or use list directly
            command_list_for_direct_exec = command_list_or_str
            if as_root:  # Construct string for su -c
                quoted_args = []
                for arg in command_list_or_str:
                    arg_escaped = str(arg).replace(
                        "'", "'\\''"
                    )  # Escape single quotes for shell
                    # Quote if it contains spaces or special characters
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
            # If target_user_id is specified for a root command, it implies context switch.
            # `su <user_id> -c "command"` or `su 0 cmd user <user_id> command_without_quotes`
            # For simplicity and broad compatibility, `su <user_id> -c "command"` is often better.
            # If target_user_id is 0 (root itself), or None (system-wide root), use "su 0 -c ..."
            if target_user_id is not None and str(target_user_id) != "0":
                su_prefix = ["su", str(target_user_id)]
            else:  # Default to root user 0 if no specific user or if root user itself is targeted
                su_prefix = ["su", "0"]

            final_cmd_list = base_cmd + su_prefix + ["-c", full_command_str_for_su]
        else:  # Not as root
            if (
                target_user_id is not None
            ):  # Non-root commands can still be user-specific via `cmd user` or certain `pm` flags
                # This scenario is less common; usually user-specific commands are handled by pm/am flags
                # or are root commands run in that user's context.
                # For now, non-root commands won't automatically use target_user_id unless `command_list_or_str` includes it.
                pass
            final_cmd_list = base_cmd + command_list_for_direct_exec

        log_cmd_str = " ".join(str(c) for c in final_cmd_list)
        # self._log_message(f"Executing: {log_cmd_str}", "debug", dim_style=True) # Optional: for deep debugging

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
            self._log_message(f"⏰ Command timed out: {log_cmd_str}", "warning")
            return subprocess.CompletedProcess(
                args=final_cmd_list, returncode=-1, stdout="", stderr="Timeout"
            )
        except Exception as e:
            self._log_message(
                f"💥 Exception running command {log_cmd_str}: {e}", "error"
            )
            return subprocess.CompletedProcess(
                args=final_cmd_list, returncode=-2, stdout="", stderr=str(e)
            )

    def _log_message(self, message, level="info", dim_style=False):
        if not self.console:
            print(f"[{level.upper()}] {message}")
            return
        style_map = {
            "info": "dim" if dim_style else "",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "debug": "dim blue",
        }
        style = style_map.get(level, "")
        # Enable markup parsing for rich formatting like [b]...[/b]
        self.console.print(message, style=style, markup=True)

    def _generate_random_hex_string(self, length, uppercase=False):
        hex_chars = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
        return "".join(random.choice(hex_chars) for _ in range(length))

    def _generate_random_string(
        self, length, chars=None, uppercase=False, lowercase=False
    ):
        if chars is None:
            chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        if uppercase:
            chars = chars.upper()
        elif lowercase:
            chars = chars.lower()
        return "".join(random.choice(chars) for _ in range(length))

    def get_current_property_value(self, device_id, property_name):
        result = self._run_adb_shell_command(device_id, ["getprop", property_name])
        return result.stdout.strip() if result.returncode == 0 else ""

    def backup_property(self, device_id, property_name):
        if not self.config.getboolean(
            "ADVANCED_SPOOFING", "backup_original_properties", fallback=True
        ):
            return
        if device_id not in self.property_backups:
            self.property_backups[device_id] = {}
        if property_name in self.property_backups[device_id]:  # Already backed up
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
        self.backup_property(device_id, property_name)
        # Ensure value is properly quoted for the shell command passed to su -c
        # `value` itself might contain quotes or special characters.
        # The _run_adb_shell_command handles quoting for `su -c` if `command_list_or_str` is a list.
        
        # Try multiple resetprop strategies for stubborn properties
        strategies = [
            ["resetprop", property_name, str(value)],  # Standard approach
            ["resetprop", "-n", property_name, str(value)],  # Non-persistent (runtime only)
            ["resetprop", "--force", property_name, str(value)],  # Force setting (if supported)
        ]
        
        for strategy_idx, command_list in enumerate(strategies):
            strategy_name = ["Standard", "Non-persistent", "Force"][strategy_idx]
            
            result = self._run_adb_shell_command(device_id, command_list, as_root=True)
            if result.returncode == 0:
                # Some resetprop versions don't output anything on success
                # We can verify by trying to read the prop back
                time.sleep(0.2)  # Brief pause for property service to catch up
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
                    # Continue to next strategy if verification failed
                    continue
            else:
                # Check if this is a "help text" error (common with invalid flags)
                error_output = result.stderr.strip() or result.stdout.strip()
                if "resetprop" in error_output and ("usage" in error_output.lower() or "options:" in error_output.lower()):
                    # This strategy's flags aren't supported, try next
                    if strategy_idx < len(strategies) - 1:
                        continue
                
                # Log detailed error for debugging
                self._log_message(
                    f"  ⚠️ {strategy_name} strategy failed for {property_name}: {error_output.splitlines()[0] if error_output else 'No output'}",
                    "debug",
                    dim_style=True
                )
                
                # Continue to next strategy unless this was the last one
                if strategy_idx < len(strategies) - 1:
                    continue
        
        # All strategies failed
        self._log_message(
            f"  ✗ Failed to set {property_name} (value: '{value}') with all strategies",
            "error",
        )
        
        # Check if property is read-only
        self._check_property_readonly_status(device_id, property_name)
        return False

    def _check_property_readonly_status(self, device_id, property_name):
        """Check and provide feedback about why a property might be read-only"""
        # Common read-only or problematic properties
        readonly_properties = {
            "ro.product.model": "Hardware/bootloader enforced - may require custom ROM or kernel modification",
            "ro.product.device": "Hardware/bootloader enforced - typically unchangeable",
            "ro.product.board": "Hardware/bootloader enforced - typically unchangeable", 
            "ro.hardware": "Hardware identifier - typically unchangeable",
            "ro.bootloader": "Bootloader version - typically unchangeable",
            "ro.boot.bootloader": "Bootloader version - typically unchangeable",
            "ro.product.cpu.abi": "Hardware ABI - typically unchangeable",
            "ro.product.cpu.abilist": "Hardware ABI list - typically unchangeable"
        }
        
        if property_name in readonly_properties:
            self._log_message(
                f"    💡 Note: {property_name} is typically read-only. {readonly_properties[property_name]}",
                "info",
                dim_style=True
            )
        elif property_name.startswith("ro."):
            self._log_message(
                f"    💡 Note: {property_name} is a read-only property (ro.*) and may be protected by SELinux policies",
                "info", 
                dim_style=True
            )
        
        # Check SELinux status as it can affect property setting
        selinux_result = self._run_adb_shell_command(device_id, ["getenforce"], timeout=5)
        if selinux_result.returncode == 0:
            selinux_status = selinux_result.stdout.strip()
            if selinux_status.lower() == "enforcing":
                self._log_message(
                                         f"    💡 SELinux is [bold yellow]Enforcing[/bold yellow] - this may prevent setting certain properties",
                     "info",
                     dim_style=True
                 )
        
        # Provide alternative suggestions
        if property_name.startswith("ro.product."):
            self._log_message(
                f"    💡 Alternative: Consider using app-level spoofing, Xposed modules, or custom ROMs for hardware spoofing",
                "info",
                dim_style=True
            )

    def restore_property(self, device_id, property_name):
        if not self.config.getboolean(
            "ADVANCED_SPOOFING", "backup_original_properties", fallback=True
        ):
            self._log_message(
                f"Property backup was disabled. Cannot restore {property_name} from backup.",
                "warning",
            )
            return (
                False  # Cannot restore if not backed up. Deletion is a separate choice.
            )

        original_value = None
        command_list_to_run = []

        if (
            device_id in self.property_backups
            and property_name in self.property_backups[device_id]
        ):
            original_value = self.property_backups[device_id][property_name]
            if (
                original_value is not None and original_value != ""
            ):  # If there was a meaningful original value
                self._log_message(
                    f"  Restoring {property_name} to original: '{original_value}'",
                    "info",
                    dim_style=True,
                )
                command_list_to_run = ["resetprop", property_name, str(original_value)]
            else:  # Original value was empty or None, so delete the prop
                self._log_message(
                    f"  Original value for {property_name} was empty/null. Deleting prop.",
                    "info",
                    dim_style=True,
                )
                command_list_to_run = ["resetprop", "--delete", property_name]
        else:
            # No backup found, implies property might have been set without backup or is new
            # Default action: try to delete it if we don't have a backup.
            self._log_message(
                f"No backup for {property_name}. Attempting delete.",
                "debug",
                dim_style=True,
            )
            command_list_to_run = ["resetprop", "--delete", property_name]

        if not command_list_to_run:  # Should not happen if logic is correct
            self._log_message(
                f"  No action determined for restoring {property_name}.", "warning"
            )
            return False

        result = self._run_adb_shell_command(
            device_id, command_list_to_run, as_root=True
        )
        if result.returncode == 0:
            # Verify restoration
            time.sleep(0.1)
            current_value_after_restore = self.get_current_property_value(
                device_id, property_name
            )
            action_type = "Restored" if original_value else "Deleted"

            expected_value_after_restore = (
                original_value if original_value else ""
            )  # After delete, getprop returns empty string

            if current_value_after_restore == expected_value_after_restore:
                self._log_message(
                    f"  ✓ {action_type} {property_name} successfully (Verified: '{current_value_after_restore}').",
                    "success",
                    dim_style=True,
                )
            else:
                self._log_message(
                    f"  ⚠️ {action_type} {property_name} (Command OK, but verification failed. Expected: '{expected_value_after_restore}', Got: '{current_value_after_restore}')",
                    "warning",
                    dim_style=True,
                )
            return True  # Command itself was successful
        else:
            error_msg = (
                result.stderr.strip()
                or result.stdout.strip()
                or "Unknown error from resetprop"
            ).splitlines()[0]
            self._log_message(
                f"  ✗ Failed to restore/delete {property_name}: {error_msg}", "error"
            )
            return False

    def restore_all_properties(self, device_id):
        backup_enabled = self.config.getboolean(
            "ADVANCED_SPOOFING", "backup_original_properties", fallback=True
        )

        properties_to_process = []
        if (
            backup_enabled
            and device_id in self.property_backups
            and self.property_backups[device_id]
        ):
            properties_to_process = list(self.property_backups[device_id].keys())
            self._log_message(
                f"🧬 Restoring all ({len(properties_to_process)}) backed up properties for {device_id}...",
                "info",
            )
        elif not backup_enabled:
            self._log_message(
                "Property backup was disabled. Attempting to delete known spoofed props based on current config.",
                "info",
            )
            if self.config.getboolean(
                "ADVANCED_SPOOFING", "enable_magisk_resetprop", fallback=False
            ):
                # Determine which props *might* have been spoofed based on toggles
                # This is a broader list than just COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF
                # as it also considers props that might be generated but not in the default list.
                # However, for deletion, we should rely on the configured `props_to_spoof` from patterns
                # as these are the ones the script would have targeted.
                master_prop_list_from_patterns = self.patterns_data.get(
                    "props_to_spoof", self.COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF
                )
                properties_to_process = list(
                    set(master_prop_list_from_patterns)
                )  # Use the actual list used for spoofing
                self._log_message(
                    f"  Attempting to delete {len(properties_to_process)} potentially spoofed properties.",
                    "debug",
                    dim_style=True,
                )

        if not properties_to_process:
            self._log_message(
                f"No properties identified for restoration/deletion for {device_id}.",
                "info",
                dim_style=True,
            )
            return True

        all_success = True
        for prop_name in properties_to_process:
            if (
                backup_enabled
            ):  # Restore from backup (which might mean delete if original was empty)
                if not self.restore_property(device_id, prop_name):
                    all_success = False
            else:  # Backup was disabled, so just try to delete
                self._log_message(
                    f"  Attempting to delete '{prop_name}' (backup disabled)...",
                    "debug",
                    dim_style=True,
                )
                delete_cmd = ["resetprop", "--delete", prop_name]
                res_delete = self._run_adb_shell_command(
                    device_id, delete_cmd, as_root=True
                )
                if res_delete.returncode == 0:
                    self._log_message(
                        f"    ✓ Deleted '{prop_name}' (or it didn't exist).",
                        "success",
                        dim_style=True,
                    )
                else:
                    # Don't mark as major failure if prop "not found" during delete
                    err_out = (res_delete.stderr + res_delete.stdout).lower()
                    if "not found" not in err_out and "no such property" not in err_out:
                        self._log_message(
                            f"    ✗ Failed to delete '{prop_name}': {res_delete.stderr.strip() or res_delete.stdout.strip()}",
                            "warning",
                        )
                        all_success = False  # Count as failure only if delete cmd fails for other reasons

        if all_success:
            if backup_enabled and device_id in self.property_backups:
                self.property_backups.pop(
                    device_id, None
                )  # Clear backup after successful restore
            self._log_message(
                f"  ✓ All property restoration/deletion attempts completed for {device_id}.",
                "success",
            )
        else:
            self._log_message(
                f"  ✗ Some properties failed to restore/delete for {device_id}.",
                "error",
            )
        return all_success

    def detect_capabilities(self, device_id):
        caps = {
            "multiuser_support": False,
            "root_access": False,
            "magisk_available": False,
            "ephemeral_user_support": False,  # Android 8.0+ (SDK 26)
            "android_sdk_version": 0,
        }
        try:
            res_sdk = self._run_adb_shell_command(
                device_id, ["getprop", "ro.build.version.sdk"]
            )
            if res_sdk.returncode == 0 and res_sdk.stdout.strip().isdigit():
                sdk_version = int(res_sdk.stdout.strip())
                caps["android_sdk_version"] = sdk_version
                if sdk_version >= 26:  # Android 8.0 Oreo
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
                elif max_users_str.isdigit():  # Sometimes it's just a number
                    max_users_val = int(max_users_str)

                if max_users_val > 1:
                    caps["multiuser_support"] = True
                elif (
                    max_users_val == 1 and caps["android_sdk_version"] >= 21
                ):  # Android 5.0+ often supports it even if pm says 1. Check settings.
                    # More robust check: Try reading global setting
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
                # More robust check: Instead of looking for "magisk", check for the actual tool we need: "resetprop".
                # This makes it compatible with APatch/KernelSU if a tools module is installed.
                # `which` is a standard command to find a program in the system's PATH.
                res_resetprop_check = self._run_adb_shell_command(
                    device_id, "which resetprop", as_root=True, timeout=5
                )
                if res_resetprop_check.returncode == 0 and res_resetprop_check.stdout.strip():
                    # If `which resetprop` succeeds and returns a path, the tool is available.
                    caps["magisk_available"] = True
                    self._log_message(
                        f"  Found 'resetprop' utility at: {res_resetprop_check.stdout.strip()}. Property spoofing is available.",
                        "debug",
                        dim_style=True
                    )
            else:  # Simpler root check (sometimes `id` is not enough or behaves weirdly)
                res_root_test = self._run_adb_shell_command(
                    device_id, ["ls", "/system/bin/su"], as_root=True, timeout=3
                )
                if res_root_test.returncode == 0:  # If `su` can list it, probably root
                    # res_root_id might have failed, but this is another indicator.
                    # This part is tricky, `id` is usually better.
                    # Fallback check if primary root check failed.
                    # Only set root if `id` check failed but this basic one passes, less reliable.
                    pass

        except Exception as e:
            self._log_message(
                f"Error detecting capabilities for {device_id}: {e}", "error"
            )
        return caps

    def get_max_users(self, device_id):
        # Tries to get current max users limit from `pm get-max-users`
        # Falls back to `fw.max_users` property or a sensible default.
        result = self._run_adb_shell_command(device_id, "pm get-max-users")
        max_users_val = -1
        if result.returncode == 0 and result.stdout.strip():
            try:
                output = result.stdout.strip()
                if output.isdigit():  # Some ROMs just output the number
                    max_users_val = int(output)
                else:  # Standard output is "Maximum supported users: X"
                    match = re.search(
                        r"Maximum supported users:\s*(\d+)", output, re.IGNORECASE
                    )
                    if match:
                        max_users_val = int(match.group(1))
                    else:  # Try to find any number if format is unexpected
                        match_alt = re.search(r"(\d+)", output)
                        if match_alt:
                            max_users_val = int(match_alt.group(0))
            except ValueError:
                pass  # Failed to parse, will use fallback

        if max_users_val <= 0:  # If pm get-max-users failed or returned 0/1
            # Try reading fw.max_users property
            fw_max_users_prop = self.get_current_property_value(
                device_id, "fw.max_users"
            )
            if (
                fw_max_users_prop
                and fw_max_users_prop.isdigit()
                and int(fw_max_users_prop) > 0
            ):
                max_users_val = int(fw_max_users_prop)
                self._log_message(
                    f"  Used fw.max_users value for max_users: {max_users_val}",
                    "debug",
                    dim_style=True,
                )
            else:  # Ultimate fallback
                self._log_message(
                    f"  Could not determine max_users (pm get-max-users: '{result.stdout.strip()}', "
                    f"fw.max_users: '{fw_max_users_prop}'). Using fallback (default 4).",
                    "warning",
                )
                return 4  # Default reasonable fallback
        return max_users_val

    def adjust_user_limit(self, device_id, new_limit):
        if new_limit < 1:
            self._log_message("New user limit must be at least 1.", "error")
            return False

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if not caps.get("root_access"):
            self._log_message(
                "Root access required to adjust user limit. Adjustment skipped.",
                "error",
            )
            return False

        # Store original limit if not already stored
        if device_id not in self.user_limit_originals:
            original_limit_pm_val = self.get_max_users(
                device_id
            )  # Get current before changing
            stored_original = (
                original_limit_pm_val if original_limit_pm_val > 0 else 4
            )  # Sensible default
            self.user_limit_originals[device_id] = stored_original
            self._log_message(
                f"  Stored original user limit for {device_id}: {self.user_limit_originals[device_id]} (from pm/prop)",
                "debug",
                dim_style=True,
            )

        self._log_message(
            f"  Attempting to adjust user limit to {new_limit} on {device_id}...",
            "info",
        )

        # Method 1: settings put global (affects UI switcher and some pm checks)
        success_global = False
        cmd_global_list = [
            "settings",
            "put",
            "global",
            "user_switcher_max_users",
            str(new_limit),
        ]
        result_global = self._run_adb_shell_command(
            device_id, cmd_global_list, as_root=True
        )
        if result_global.returncode == 0:
            self._log_message(
                f"    ✓ Adjusted global user_switcher_max_users to {new_limit}.",
                "success",
                dim_style=True,
            )
            success_global = True
        else:
            self._log_message(
                f"    ✗ Failed to adjust global user_switcher_max_users: {result_global.stderr.strip() or result_global.stdout.strip()}",
                "warning",
            )

        # Method 2: resetprop fw.max_users (more direct control if ROM respects it)
        success_fw = False
        if caps.get("magisk_available"):  # resetprop is more effective with Magisk's su
            # No need to call self.set_property_with_resetprop as we don't want to backup fw.max_users in the main backup dict
            # and this is a specific adjustment.
            cmd_fw_list = ["resetprop", "fw.max_users", str(new_limit)]
            result_fw = self._run_adb_shell_command(
                device_id, cmd_fw_list, as_root=True
            )
            if result_fw.returncode == 0:
                self._log_message(
                    f"    ✓ Adjusted fw.max_users to {new_limit} via resetprop.",
                    "success",
                    dim_style=True,
                )
                success_fw = True
            else:
                self._log_message(
                    f"    ✗ Failed to adjust fw.max_users via resetprop: {result_fw.stderr.strip() or result_fw.stdout.strip()}",
                    "warning",
                )
        else:
            self._log_message(
                "    Skipping fw.max_users adjustment (Magisk not detected/preferred for resetprop).",
                "debug",
                dim_style=True,
            )

        time.sleep(1)  # Give settings a moment to apply
        current_max_after_adjust = self.get_max_users(
            device_id
        )  # Re-check after adjustment

        if current_max_after_adjust >= new_limit:
            self._log_message(
                f"  ✓ Verified user limit is now at least {new_limit} (Reported by pm/prop: {current_max_after_adjust}).",
                "success",
            )
            return True  # Primary success condition
        else:
            self._log_message(
                f"  ⚠️ User limit adjustment might not have been fully effective. "
                f"Current reported max users: {current_max_after_adjust} (Target was {new_limit}).",
                "warning",
            )
            # Return true if at least one method seemed to work, as it might be partially effective
            # or pm get-max-users might not immediately reflect the change from `settings put global`.
            return success_global or success_fw

    def restore_user_limit(self, device_id):
        if device_id not in self.user_limit_originals:
            self._log_message(
                f"No original user limit stored for {device_id}. Skipping restore.",
                "debug",
                dim_style=True,
            )
            return True  # Nothing to restore

        original_limit = self.user_limit_originals[device_id]
        self._log_message(
            f"  Restoring original user limit to {original_limit} for {device_id}...",
            "info",
            dim_style=True,
        )

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if not caps.get("root_access"):
            self._log_message(
                "Root access lost or not available. Cannot restore user limit.",
                "warning",
            )
            return False

        # Try to restore both global setting and fw.max_users property
        restored_any = False

        cmd_global_list_restore = [
            "settings",
            "put",
            "global",
            "user_switcher_max_users",
            str(original_limit),
        ]
        result_global_restore = self._run_adb_shell_command(
            device_id, cmd_global_list_restore, as_root=True
        )
        if result_global_restore.returncode == 0:
            self._log_message(
                f"    ✓ Restored global user_switcher_max_users to {original_limit}.",
                "success",
                dim_style=True,
            )
            restored_any = True
        else:
            self._log_message(
                f"    ✗ Failed to restore global user_switcher_max_users: {result_global_restore.stderr.strip() or result_global_restore.stdout.strip()}",
                "warning",
            )

        if caps.get("magisk_available"):
            cmd_fw_list_restore = ["resetprop", "fw.max_users", str(original_limit)]
            # Some ROMs might require deleting fw.max_users to restore default behavior if original_limit was a default
            # For simplicity, always try to set it back to the stored original.
            result_fw_restore = self._run_adb_shell_command(
                device_id, cmd_fw_list_restore, as_root=True
            )
            if result_fw_restore.returncode == 0:
                self._log_message(
                    f"    ✓ Restored fw.max_users to {original_limit} via resetprop.",
                    "success",
                    dim_style=True,
                )
                restored_any = True
            else:
                self._log_message(
                    f"    ✗ Failed to restore fw.max_users via resetprop: {result_fw_restore.stderr.strip() or result_fw_restore.stdout.strip()}",
                    "warning",
                )

        if restored_any:
            self._log_message(
                f"  ✓ Original user limit ({original_limit}) restoration attempt completed.",
                "success",
                dim_style=True,
            )
            del self.user_limit_originals[
                device_id
            ]  # Remove from dict after successful attempt
            return True
        else:
            self._log_message(
                "  ✗ Failed to restore user limit using available methods.", "error"
            )
            return False

    def _check_device_storage(self, device_id, min_mb_required=100):
        try:
            result = self._run_adb_shell_command(
                device_id, ["df", "-k", "/data"]
            )  # -k for kilobytes
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    # Find the line for /data, typically the last one or one ending with /data
                    data_line = next(
                        (
                            line
                            for line in reversed(lines)
                            if line.strip().endswith("/data")
                        ),
                        None,
                    )
                    if data_line:
                        parts = data_line.strip().split()
                        # Available KB is usually 4th field (1-indexed) or parts[3] (0-indexed)
                        if len(parts) >= 4 and parts[3].isdigit():
                            available_kb = int(parts[3])
                            available_mb = available_kb / 1024
                            self._log_message(
                                f"  💾 Available storage on /data: {available_mb:.2f} MB",
                                "debug",
                                dim_style=True,
                            )
                            if available_mb < min_mb_required:
                                self._log_message(
                                    f"  ⚠️ Low storage: {available_mb:.2f} MB available, need >{min_mb_required} MB.",
                                    "warning",
                                )
                                return False
                            return True
            self._log_message(
                "  ⚠️ Could not reliably parse 'df /data' output. Assuming enough space.",
                "warning",
            )
        except Exception as e:
            self._log_message(
                f"  ⚠️ Error checking device storage ({e}). Assuming enough space.",
                "warning",
            )
        return True  # Default to true if check fails to avoid blocking

    def _parse_user_id_from_output(self, output):
        # Common patterns for user ID extraction from `pm create-user`
        patterns = [
            r"Success: created user id (\d+)",  # Common AOSP
            r"Success: user added \(id=(\d+)\)",  # Older AOSP
            r"UserInfo\{(\d+):",  # If output is UserInfo object
            r"Created user id (\d+)",  # Some custom ROMs
            r"user id (\d+) created",
            r"New user created: UserInfo\{(\d+):",
            r"id\s*=\s*(\d+)",  # Generic id pattern
            r"userId=(\d+)",
            r"User_(\d+)",  # Fallback for simpler names
        ]
        for p in patterns:
            match = re.search(p, output, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except (ValueError, IndexError):
                    continue  # Malformed match, try next pattern
        return None  # No pattern matched

    def _set_user_android_id(self, device_id, user_id):
        if not self.config.getboolean(
            "UNIQUENESS", "auto_set_random_android_id", fallback=True
        ):
            self._log_message(
                "  Skipping Android ID set for new user (disabled in config).",
                "debug",
                dim_style=True,
            )
            return True  # Not an error, just skipped

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if not caps.get("root_access"):
            self._log_message(
                f"  Root access not detected for {device_id}. Cannot set Android ID for user {user_id}.",
                "warning",
            )
            return False

        android_id_val = self._generate_random_hex_string(16)  # 16 hex characters
        self._log_message(
            f"  🧬 Attempting to set Android ID '{android_id_val}' for user {user_id}...",
            "info",
            dim_style=True,
        )
        # Command: settings put --user <user_id> secure android_id <value>
        # Needs to be run as root to modify settings for another user.
        cmd_list = [
            "settings",
            "put",
            "--user",
            str(user_id),
            "secure",
            "android_id",
            android_id_val,
        ]

        # Run as root, but the command itself targets a specific user context via --user flag
        result = self._run_adb_shell_command(
            device_id, cmd_list, as_root=True
        )  # Root needed to run settings for other users

        if result.returncode != 0:
            self._log_message(
                f"  ✗ Android ID setting failed for user {user_id}: {result.stderr.strip() or result.stdout.strip()}",
                "error",
            )
            return False

        # Verify (optional but good)
        verify_cmd_list = [
            "settings",
            "get",
            "--user",
            str(user_id),
            "secure",
            "android_id",
        ]
        verify_result = self._run_adb_shell_command(
            device_id, verify_cmd_list, as_root=True
        )
        if (
            verify_result.returncode == 0
            and verify_result.stdout.strip() == android_id_val
        ):
            self._log_message(
                f"  ✓ Android ID set and verified for user {user_id}.",
                "success",
                dim_style=True,
            )
            return True
        else:
            self._log_message(
                f"  ⚠️ Android ID set for user {user_id} (command OK), but verification failed. "
                f"(Got: '{verify_result.stdout.strip()}', Expected: '{android_id_val}')",
                "warning",
            )
            return True  # Command was successful, so count as success but warn

    def _switch_to_user_with_validation(self, device_id, user_id):
        self._log_message(
            f"  🔄 Switching to user {user_id} on {device_id}...",
            "info",
            dim_style=True,
        )
        switch_cmd_list = ["am", "switch-user", str(user_id)]
        # `am switch-user` doesn't need root itself, but the system needs to allow it.
        result_switch = self._run_adb_shell_command(
            device_id,
            switch_cmd_list,
            timeout=60,  # Longer timeout for user switch
        )
        if result_switch.returncode != 0:
            # Common error: "SecurityException: Shell does not have permission to switch users." -> Needs ADB over TCP or device unlocked.
            # Or if device is locked.
            err_msg = result_switch.stderr.strip() or result_switch.stdout.strip()
            self._log_message(
                f"  ✗ Switch command for user {user_id} failed: {err_msg}",
                "error",
            )
            if (
                "SecurityException" in err_msg
                and "permission to switch users" in err_msg
            ):
                self._log_message(
                    "    💡 Tip: Ensure device is unlocked. Some devices require ADB over Wi-Fi for user switching, or specific developer options.",
                    "info",
                )
            return False

        # Delay after sending switch command
        initial_delay = self.config.getint(
            "UNIQUENESS", "user_switch_initial_delay_seconds", fallback=3
        )
        if initial_delay > 0:
            time.sleep(initial_delay)

        if self.config.getboolean("UNIQUENESS", "validate_user_switch", fallback=True):
            timeout_seconds = self.config.getint(
                "UNIQUENESS", "validate_user_switch_timeout_seconds", fallback=30
            )
            start_time = time.monotonic()
            self._log_message(
                f"    Validating user switch (timeout: {timeout_seconds}s)...",
                "debug",
                dim_style=True,
            )
            while time.monotonic() - start_time < timeout_seconds:
                time.sleep(2)  # Check every 2 seconds
                current_user_res = self._run_adb_shell_command(
                    device_id, ["am", "get-current-user"]
                )
                if current_user_res.returncode == 0:
                    current_user_id_str = current_user_res.stdout.strip()
                    if (
                        current_user_id_str.isdigit()
                        and int(current_user_id_str) == user_id
                    ):
                        self._log_message(
                            f"  ✓ Successfully switched to user {user_id} (verified).",
                            "success",
                            dim_style=True,
                        )
                        return True
                # Log progress if still waiting
                self._log_message(
                    f"    ..waiting for user switch to {user_id} "
                    f"(current: {current_user_res.stdout.strip() if current_user_res.stdout else 'N/A'}, "
                    f"elapsed: {int(time.monotonic() - start_time)}s)",
                    "debug",
                    dim_style=True,
                )
            self._log_message(
                f"  ✗ Failed to validate switch to user {user_id} after {timeout_seconds}s.",
                "error",
            )
            return False  # Validation timeout
        else:  # No validation
            self._log_message(
                f"  ✓ User switch command sent for user {user_id} (validation skipped).",
                "info",
                dim_style=True,
            )
            no_validation_delay = self.config.getint(
                "UNIQUENESS", "user_switch_no_validation_delay_seconds", fallback=5
            )
            if no_validation_delay > 0:
                time.sleep(no_validation_delay)
            return True

    def _cleanup_failed_user_creation(self, device_id, user_id_to_remove):
        if user_id_to_remove is None or user_id_to_remove == 0:  # Cannot remove user 0
            return
        self._log_message(
            f"  🧹 Attempting cleanup of potentially failed user ID {user_id_to_remove}...",
            "warning",
        )
        # `pm remove-user` might need root if run from shell for other users, or if user is still active.
        # However, often it works without root if user is not current.
        # Try without root first, then with root if it fails and root is available.
        remove_cmd_list = ["pm", "remove-user", str(user_id_to_remove)]
        result = self._run_adb_shell_command(device_id, remove_cmd_list, timeout=30)

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if result.returncode != 0 and caps.get("root_access"):
            self._log_message(
                f"    Cleanup (non-root) failed for user {user_id_to_remove}, retrying with root...",
                "debug",
                dim_style=True,
            )
            result = self._run_adb_shell_command(
                device_id, remove_cmd_list, timeout=30, as_root=True
            )

        if result.returncode == 0:
            self._log_message(
                f"    ✓ User {user_id_to_remove} cleaned up successfully.",
                "success",
                dim_style=True,
            )
        else:
            self._log_message(
                f"    ✗ Failed to cleanup user {user_id_to_remove}: {result.stderr.strip() or result.stdout.strip()}",
                "warning",
            )

    def create_user_profile(self, device_id, create_permanent_user_flag):
        # `create_permanent_user_flag` True means create permanent, False means create ephemeral (if supported)

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )

        # Determine if ephemeral should be attempted
        attempt_ephemeral = False
        if not create_permanent_user_flag:  # If flag requests ephemeral
            if caps.get("ephemeral_user_support"):
                attempt_ephemeral = True
            else:
                self._log_message(
                    f"  Ephemeral users requested but not supported/detected on {device_id} (SDK {caps.get('android_sdk_version', 'N/A')}). "
                    "Will attempt standard (permanent) user creation instead.",
                    "warning",
                )
                # Fallback to permanent if ephemeral requested but not supported
                create_permanent_user_flag = True

        user_type_str = (
            "standard (permanent)" if create_permanent_user_flag else "ephemeral"
        )

        if not caps.get("multiuser_support") and self.config.getboolean(
            "SPOOF_VALIDATION", "check_multiuser_support", fallback=True
        ):
            self._log_message(
                f"Multi-user support not available/enabled on {device_id}. Cannot create new {user_type_str} user.",
                "error",
            )
            return None

        min_storage_for_user = self.config.getint(
            "SPOOF_VALIDATION", "min_storage_mb", fallback=100
        )
        if not self._check_device_storage(device_id, min_storage_for_user):
            self._log_message(
                f"Insufficient storage (need >{min_storage_for_user}MB) on {device_id} for {user_type_str} user creation.",
                "error",
            )
            return None

        # Prompt for user profile name
        default_name = datetime.now().strftime("%m-%d-%y_%H-%M")
        user_name = ""
        if QUESTIONARY_AVAILABLE and self.console:
            try:
                user_name = questionary.text(
                    f"Enter name for new {user_type_str} profile (or press Enter for default: {default_name}):",
                    default="",  # Start with empty to check if user provides input
                    style=questionary.Style([('question', 'fg:yellow'), ('answer', 'fg:cyan bold')])
                ).ask()
                if user_name is None:  # User cancelled
                    self._log_message("User profile creation cancelled.", "yellow")
                    return None
                if not user_name.strip():  # User pressed Enter
                    user_name = default_name
            except KeyboardInterrupt:
                self._log_message("\nUser profile creation cancelled.", "yellow")
                return None
        else:
            try:
                prompt_text = f"Enter name for new {user_type_str} profile (default: {default_name}): "
                user_name = input(prompt_text).strip()
                if not user_name:
                    user_name = default_name
            except KeyboardInterrupt:
                self._log_message("\nUser profile creation cancelled.", "yellow")
                return None

        self._log_message(
            f"👤 Attempting to create {user_type_str} user '{user_name}' on {device_id}...",
            "info",
        )

        # User limit bypass logic
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "bypass_user_limits", fallback=False
        ) and caps.get("root_access"):
            res_list_users = self._run_adb_shell_command(
                device_id, ["pm", "list", "users"]
            )
            current_users_count = 0
            if res_list_users.returncode == 0:
                # Count lines like "UserInfo{0:Owner:c13}"
                current_users_count = len(
                    [
                        line
                        for line in res_list_users.stdout.splitlines()
                        if "UserInfo{" in line
                    ]
                )

            max_users_allowed = self.get_max_users(device_id)  # Get current max users

            if current_users_count >= max_users_allowed:
                self._log_message(
                    f"  User limit ({current_users_count}/{max_users_allowed}) reached or exceeded. "
                    "Attempting to bypass (as per config)...",
                    "warning",
                )
                # Try to increase limit by a small amount, e.g., current_users_count + 2, capped at a reasonable max (e.g., 10)
                new_attempted_limit = min(
                    max(current_users_count + 2, max_users_allowed + 1), 10
                )
                if not self.adjust_user_limit(device_id, new_attempted_limit):
                    self._log_message(
                        "  Failed to effectively increase user limit. User creation might still fail.",
                        "error",
                    )
                else:  # Limit adjustment attempted, re-check
                    max_users_allowed = self.get_max_users(device_id)
                    if current_users_count >= max_users_allowed:
                        self._log_message(
                            f"  Bypass attempt made, but limit still seems restrictive ({current_users_count}/{max_users_allowed}). "
                            "User creation might fail.",
                            "warning",
                        )

        # Construct user creation command
        create_cmd_list = ["pm", "create-user"]
        if attempt_ephemeral:  # Only add --ephemeral if truly attempting ephemeral
            create_cmd_list.append("--ephemeral")
        create_cmd_list.append(user_name)

        # pm create-user may require root on some systems or if device is locked.
        # Try without root first, then with root if needed and available.
        # However, typically it's a non-root command if system allows.

        user_info = None
        retries = self.config.getint("UNIQUENESS", "user_creation_retries", fallback=3)

        for attempt in range(retries):
            self._log_message(
                f"  Attempt {attempt + 1}/{retries} to create user '{user_name}'...",
                "info",
                dim_style=True,
            )
            # `pm create-user` usually doesn't need root unless modifying system settings or if device is locked.
            # For broader compatibility, run without root unless it fails and root is an option.
            result = self._run_adb_shell_command(device_id, create_cmd_list, timeout=90)

            if (
                result.returncode != 0
                and "SecurityException" in result.stderr
                and caps.get("root_access")
            ):
                self._log_message(
                    "    `pm create-user` failed, retrying with root due to SecurityException...",
                    "debug",
                    dim_style=True,
                )
                result = self._run_adb_shell_command(
                    device_id, create_cmd_list, timeout=90, as_root=True
                )

            if result.returncode == 0 and (
                "Success" in result.stdout or "success" in result.stdout.lower()
            ):
                user_id = self._parse_user_id_from_output(result.stdout)
                if user_id is not None:
                    self._log_message(
                        f"  ✓ User '{user_name}' (ID: {user_id}, Type: {user_type_str}) created.",
                        "success",
                        dim_style=True,
                    )
                    if self._set_user_android_id(device_id, user_id):
                        if self._switch_to_user_with_validation(device_id, user_id):
                            # Apply automatic device fingerprint randomization for anti-tracking
                            fingerprint_randomized = self.apply_random_device_fingerprint_for_new_user(device_id)
                            
                            user_info = {
                                "user_id": user_id,
                                "user_name": user_name,
                                "is_ephemeral": attempt_ephemeral,  # True if ephemeral was successfully created
                                "fingerprint_randomized": fingerprint_randomized,  # Track if anti-tracking was applied
                            }
                            self.active_spoofed_users[device_id] = user_info
                            
                            if fingerprint_randomized:
                                self._log_message(
                                    f"  🎯 New user profile created with randomized device fingerprint to prevent app tracking",
                                    "success",
                                    dim_style=True
                                )
                            else:
                                self._log_message(
                                    f"  ⚠️ New user profile created, but device fingerprint randomization was skipped or failed",
                                    "warning",
                                    dim_style=True
                                )
                            break  # Success
                        else:  # Switch failed
                            self._log_message(
                                f"    Failed to switch to new user {user_id}. Cleaning up.",
                                "error",
                            )
                            self._cleanup_failed_user_creation(device_id, user_id)
                    else:  # Android ID set failed
                        self._log_message(
                            f"    Failed to set Android ID for user {user_id}. Cleaning up.",
                            "error",
                        )
                        self._cleanup_failed_user_creation(device_id, user_id)
                else:  # Parse ID failed
                    self._log_message(
                        f"  ✗ User creation command seemed successful, but failed to parse user ID from: {result.stdout.strip()}",
                        "error",
                    )
            else:  # Command failed
                self._log_message(
                    f"  ✗ User creation command failed: {result.stderr.strip() or result.stdout.strip()}",
                    "error",
                )

            if user_info:  # Break outer loop if user successfully created and switched
                break

            if attempt < retries - 1:
                self._log_message(
                    f"    Retrying in {2 ** (attempt + 1)}s...", "debug", dim_style=True
                )
                time.sleep(2 ** (attempt + 1))  # Exponential backoff

        if not user_info:
            self._log_message(
                f"All attempts to create user '{user_name}' failed on {device_id}.",
                "error",
            )
        return user_info

    def cleanup_user_profile(self, device_id):
        if device_id not in self.active_spoofed_users:
            return True  # Nothing to clean for this device from current session

        user_data = self.active_spoofed_users[device_id]
        user_id, user_name = user_data["user_id"], user_data["user_name"]
        is_ephemeral = user_data.get("is_ephemeral", False)

        if user_id == 0 or user_id is None:  # Should not happen if created properly
            if device_id in self.active_spoofed_users:
                del self.active_spoofed_users[device_id]
            return True

        self._log_message(
            f"🧹 Cleaning up {'ephemeral' if is_ephemeral else 'standard'} user '{user_name}' (ID: {user_id}) on {device_id}...",
            "info",
        )
        cleanup_success = True

        # Switch back to owner (user 0) if currently on the spoofed user
        if self.config.getboolean(
            "UNIQUENESS", "auto_switch_back_to_owner", fallback=True
        ):
            current_user_res = self._run_adb_shell_command(
                device_id, ["am", "get-current-user"]
            )
            if (
                current_user_res.returncode == 0
                and current_user_res.stdout.strip().isdigit()
                and int(current_user_res.stdout.strip()) == user_id
            ):
                self._log_message(
                    f"  🔄 Switching back to primary user (0) from {user_id} before removal...",
                    "info",
                    dim_style=True,
                )
                # Use _switch_to_user_with_validation for robust switching
                if not self._switch_to_user_with_validation(device_id, 0):
                    cleanup_success = (
                        False  # Mark as partial failure if switch back fails
                    )
                    self._log_message(
                        f"  ⚠️ Failed to switch back to primary user. Removal of user {user_id} might be affected.",
                        "warning",
                    )
                else:  # Switch back successful, add small delay
                    time.sleep(
                        self.config.getint(
                            "UNIQUENESS",
                            "user_switch_initial_delay_seconds",
                            fallback=3,
                        )
                    )
            else:
                self._log_message(
                    f"  Currently not on user {user_id} (Current: {current_user_res.stdout.strip()}). Skipping switch back before removal.",
                    "debug",
                    dim_style=True,
                )

        # Remove the user profile
        # `pm remove-user` might need root on some systems.
        remove_cmd_list = ["pm", "remove-user", str(user_id)]
        remove_result = self._run_adb_shell_command(
            device_id, remove_cmd_list, timeout=60
        )

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if remove_result.returncode != 0 and caps.get("root_access"):
            self._log_message(
                f"    User removal (non-root) failed, retrying with root for user {user_id}...",
                "debug",
                dim_style=True,
            )
            remove_result = self._run_adb_shell_command(
                device_id, remove_cmd_list, timeout=60, as_root=True
            )

        if remove_result.returncode == 0:
            self._log_message(
                f"  ✓ User profile '{user_name}' (ID: {user_id}) removed successfully.",
                "success",
                dim_style=True,
            )
        else:
            error_text = remove_result.stderr.strip() or remove_result.stdout.strip()
            # Check for common non-fatal errors (e.g., user already gone)
            if any(
                msg_fragment in error_text.lower()
                for msg_fragment in [
                    "could not be removed",
                    "doesn't exist",
                    "no user exists with id",
                    "user will be removed",  # Some systems say this and remove on next reboot for ephemeral
                ]
            ):
                self._log_message(
                    f"  ℹ️ User '{user_name}' (ID: {user_id}) may have been auto-removed, did not exist, or is scheduled for removal.",
                    "info",
                    dim_style=True,
                )
                if is_ephemeral:  # For ephemeral, this is often expected behavior
                    pass  # Not necessarily a failure for cleanup
                else:  # For permanent, this might indicate an issue if we expected it to be there.
                    cleanup_success = False
            else:  # Other errors
                cleanup_success = False
                self._log_message(
                    f"  ⚠️ Failed to remove user '{user_name}': {error_text}", "warning"
                )

        if device_id in self.active_spoofed_users:
            del self.active_spoofed_users[device_id]  # Remove from active list

        return cleanup_success

    def _generate_build_id(self, manufacturer_config_name, android_version_key):
        # manufacturer_config_name is the key used in patterns (e.g., "samsung", "google")
        # android_version_key is the key for version map (e.g., "13", "14")
        patterns = self.device_manufacturers_patterns.get(
            manufacturer_config_name,
            self.device_manufacturers_patterns.get("samsung", {}),  # Fallback
        )
        # Get build ID prefixes for the specific Android version key
        build_id_prefixes = patterns.get("build_id_patterns", {}).get(
            android_version_key,
            ["TP1A"],  # Fallback prefix
        )
        prefix = random.choice(build_id_prefixes)

        # Generate a somewhat realistic date string (e.g., YYMMDD)
        past_date = datetime.now() - timedelta(
            days=random.randint(30, 360)
        )  # Build date from 1-12 months ago
        date_str = past_date.strftime("%y%m%d")  # e.g., 231025

        build_num_suffix = f"{random.randint(1, 999):03d}"  # e.g., 001, 042, 123
        return f"{prefix}.{date_str}.{build_num_suffix}"

    def _generate_incremental(self, manufacturer_config_name, model_data, build_id_str):
        # manufacturer_config_name: "samsung", "google", etc.
        # model_data: dictionary for the selected model
        # build_id_str: the generated build ID (e.g., TP1A.220101.001)

        manufacturer_patterns = self.device_manufacturers_patterns.get(
            manufacturer_config_name, {}
        )

        # Samsung specific pattern for incremental
        if manufacturer_config_name == "samsung":
            model_code = model_data.get(
                "model", "S908B"
            )  # e.g., SM-S908B -> S908B part
            base_model_code = (
                model_code.split("-")[-1] if "-" in model_code else model_code
            )
            # Example format: S908BXXU3DWKJ or G998BXXS4CVBA (Model + Region + Firmware Tier + Year + Month + Build)
            fw_tier = random.choice(
                ["U", "S", "E"]
            )  # U for feature, S for security, E for enterprise?
            year_char = chr(
                ord("A") + (datetime.now().year - 2018 + random.randint(-1, 0))
            )  # Approximates year
            month_char = random.choice("ABCDEFGHIJKL")  # A=Jan..L=Dec
            build_rev = random.randint(1, 9)
            return f"{base_model_code}{random.choice(['XX', 'OXM', 'EUX'])}{fw_tier}{random.randint(1, 5)}{year_char}{month_char}{random.choice('ABCDEFGHJKLMNOPQRSTUVWXYZ1234567890')}{build_rev}"

        # Google specific pattern for incremental (often just a number)
        if manufacturer_config_name == "google":
            return str(random.randint(7000000, 12999999))  # Large build number

        # Xiaomi specific pattern (can be complex, often part of MIUI version string)
        if manufacturer_config_name == "xiaomi":
            # Example: V14.0.5.0.TLCMIXM -> could be just the build_id or more complex
            # Let's use a simpler numeric one for now, or part of build_id
            return f"{build_id_str}.{random.randint(10000, 99999)}"

        # Generic fallback incremental
        return f"{build_id_str}.{random.randint(100000, 999999)}"

    def generate_realistic_fingerprint(
        self,
        manufacturer_name_cfg,
        model_data,
        android_version_key_cfg,  # e.g., "samsung", model_dict, "13"
    ):
        man_patterns = self.device_manufacturers_patterns.get(
            manufacturer_name_cfg,
            self.device_manufacturers_patterns.get(
                "samsung"
            ),  # Fallback to samsung patterns
        )

        brand = man_patterns.get("brand", manufacturer_name_cfg)  # google, samsung
        product = model_data.get(
            "product", model_data.get("device", "generic_product")
        )  # e.g. husky, dm3qxeea
        device_codename = model_data.get("device", product)  # e.g. husky, dm3q

        # Get the display release version (e.g. "13", "14") from the key ("13", "14")
        android_release_str = self.android_version_release_map.get(
            android_version_key_cfg,
            android_version_key_cfg,  # Fallback to the key itself
        )

        build_id = self._generate_build_id(
            manufacturer_name_cfg, android_version_key_cfg
        )
        incremental_version = self._generate_incremental(
            manufacturer_name_cfg, model_data, build_id
        )

        # Get fingerprint format from patterns_data, with a robust fallback
        fp_format_str = self.patterns_data.get(
            "build_fingerprint_format",
            "{brand}/{product}/{device}:{android_version}/{build_id}/{incremental}:user/release-keys",
        )

        common_tags = self.patterns_data.get("common_build_tags", "release-keys")
        common_type = self.patterns_data.get("common_build_type", "user")

        return fp_format_str.format(
            brand=brand,
            product=product,
            device=device_codename,
            android_version=android_release_str,  # Use android_version key to match the expected placeholder in the format string
            build_id=build_id,
            incremental=incremental_version,
            # build_type_tags=f"{common_type}/{common_tags}" # If format includes this combined
        )  # Ensure common_type and common_tags are part of the format string if used directly

    def generate_serial_number(self, manufacturer_config_name):
        man_pattern_data = self.device_manufacturers_patterns.get(
            manufacturer_config_name,
            self.device_manufacturers_patterns.get("samsung", {}),
        )
        serial_pattern_str = man_pattern_data.get(
            "serial_pattern", "{12}"
        )  # e.g. R{8} for Samsung, {12} for Google
        serial_chars = man_pattern_data.get(
            "serial_chars", "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )

        # Handle patterns like "R{8}" or "{12}"
        match = re.fullmatch(
            r"([A-Za-z0-9]*)(\{([0-9]+)\})([A-Za-z0-9]*)", serial_pattern_str
        )
        if match:
            prefix = match.group(1)
            length = int(match.group(3))
            suffix = match.group(4)
            random_part = self._generate_random_string(length, chars=serial_chars)
            return f"{prefix}{random_part}{suffix}"

        # Fallback if pattern is not in the expected {prefix}{length}{suffix} format
        # For example, if serial_pattern_str is just a length like "12" or a fixed string.
        if serial_pattern_str.isdigit():
            return self._generate_random_string(
                int(serial_pattern_str), chars=serial_chars
            )

        # If pattern is complex or not a simple length, use a generic approach
        return self._generate_random_string(
            12, chars=serial_chars
        )  # Default 12 char serial

    def validate_property(self, prop_name, value_to_validate):
        value_str = str(value_to_validate)  # Ensure it's a string for regex
        if not value_str:  # Empty value is usually fine, means delete or unset.
            return True

        if prop_name == "ro.build.version.sdk":
            try:
                sdk_int = int(value_str)
                return 1 <= sdk_int <= 1000  # Reasonable SDK range
            except ValueError:
                return False
        if prop_name in [
            "ro.serialno",
            "ro.boot.serialno",
            "android_serialno",
        ]:  # Common serial props
            # Serials can be quite varied. Alpha-numeric, sometimes with hyphens.
            # Common lengths are 8-20 characters.
            return bool(re.match(r"^[a-zA-Z0-9\-]{4,32}$", value_str))

        if "fingerprint" in prop_name.lower():
            # Fingerprints are complex: brand/product/device:version/id/incremental:type/tags
            # Example: google/husky/husky:14/AP1A.240305.002/11425009:user/release-keys
            # Simplified check:
            # - Min 3 slashes, min 2 colons
            # - Allowed characters: alphanumeric, period, underscore, hyphen, slash, colon
            # - Starts and ends with alphanumeric (usually)
            if value_str.count("/") < 3 or value_str.count(":") < 1:
                return False
            return bool(re.match(r"^[a-zA-Z0-9][\w.\-/:%]+[a-zA-Z0-9]$", value_str))

        if (
            prop_name == "android_id" or "androidid" in prop_name.lower()
        ):  # Magisk context or new user
            return bool(
                re.match(r"^[0-9a-fA-F]{16}$", value_str)
            )  # Standard 16-char hex

        if prop_name in ["ro.build.id", "ro.build.display.id"]:  # E.g., TP1A.220624.014
            return bool(re.match(r"^[A-Z0-9\._\-]{3,64}$", value_str))

        # Generic fallback for other properties (model names, brand names, etc.)
        # Allow alphanumeric, underscore, hyphen, period, space. Max length 128.
        return bool(re.match(r"^[\w\-\.\s:]{1,128}$", value_str))

    def apply_device_spoofing(
        self,
        device_id,
        target_manufacturer_key,
        target_model_name_config,
        target_android_version_key,
    ):
        self._log_message(
            f"🧬 Applying Magisk Property Spoofing for [b]{device_id}[/b]...", "info"
        )
        self._log_message(
            f"   Target: Manufacturer='{target_manufacturer_key}', Model='{target_model_name_config or 'Random'}', Android Version='{target_android_version_key}'",
            "debug",
            dim_style=True,
        )

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(
            device_id
        )
        if not (caps.get("root_access") and caps.get("magisk_available")):
            self._log_message(
                f"Root and Magisk required for property spoofing on {device_id}. Skipping.",
                "warning",
            )
            return False

        # Resolve manufacturer patterns
        manufacturer_patterns = self.device_manufacturers_patterns.get(
            target_manufacturer_key.lower()
        )
        if not manufacturer_patterns:
            self._log_message(
                f"Manufacturer key '{target_manufacturer_key}' not found in patterns. Using 'samsung' as fallback.",
                "warning",
            )
            target_manufacturer_key = "samsung"  # Fallback key
            manufacturer_patterns = self.device_manufacturers_patterns.get(
                target_manufacturer_key
            )

        # Select model
        selected_model_data = None
        available_models = manufacturer_patterns.get("models", [])
        if target_model_name_config and available_models:
            selected_model_data = next(
                (
                    m
                    for m in available_models
                    if m.get("model", "").lower() == target_model_name_config.lower()
                    or m.get("display_name", "").lower()
                    == target_model_name_config.lower()
                ),
                None,
            )
            if not selected_model_data:
                self._log_message(
                    f"Model '{target_model_name_config}' not found for {target_manufacturer_key}. Choosing random model.",
                    "warning",
                )

        if not selected_model_data and available_models:
            selected_model_data = random.choice(available_models)
        elif (
            not selected_model_data and not available_models
        ):  # No models defined for manufacturer
            self._log_message(
                f"No models defined for {target_manufacturer_key} in patterns. Using generic fallback model data.",
                "warning",
            )
            selected_model_data = {  # Generic fallback
                "product": "generic_product",
                "device": "generic_device",
                "model": "GenericModel",
                "board": "generic_board",
                "display_name": "Generic Phone",
                "hardware": "generic_hw",
            }

        # Generate dynamic properties
        fingerprint = self.generate_realistic_fingerprint(
            target_manufacturer_key, selected_model_data, target_android_version_key
        )
        serial = self.generate_serial_number(target_manufacturer_key)

        sdk_int = self.internal_sdk_map.get(
            target_android_version_key, self.internal_sdk_map.get("13", 33)
        )  # Default to SDK 33 for Android 13
        release_str = self.android_version_release_map.get(
            target_android_version_key, target_android_version_key
        )  # e.g. "13" or "14"

        # Extract build_id and incremental from fingerprint if possible, or generate
        fp_parts = fingerprint.split("/")
        build_id_from_fp = (
            fp_parts[3]
            if len(fp_parts) > 4 and ":" in fp_parts[3]
            else self._generate_build_id(
                target_manufacturer_key, target_android_version_key
            )
        )
        incremental_from_fp = (
            fp_parts[4].split(":")[0]
            if len(fp_parts) > 4 and ":" in fp_parts[4]
            else self._generate_incremental(
                target_manufacturer_key, selected_model_data, build_id_from_fp
            )
        )

        # Construct dictionary of all potential properties and their generated values
        all_generated_props = {
            "ro.product.brand": manufacturer_patterns.get(
                "brand", target_manufacturer_key
            ),
            "ro.product.manufacturer": manufacturer_patterns.get(
                "manufacturer", target_manufacturer_key.capitalize()
            ),
            "ro.product.model": selected_model_data.get("model"),
            "ro.product.name": selected_model_data.get(
                "product"
            ),  # often codename + variant
            "ro.product.device": selected_model_data.get("device"),  # codename
            "ro.product.board": selected_model_data.get("board"),
            "ro.build.fingerprint": fingerprint,
            "ro.vendor.build.fingerprint": fingerprint,  # Often same as ro.build.fingerprint
            "ro.system.build.fingerprint": fingerprint,  # Often same
            "ro.odm.build.fingerprint": fingerprint,  # Often same
            "ro.build.id": build_id_from_fp,
            "ro.build.display.id": f"{build_id_from_fp}.{incremental_from_fp}"
            if incremental_from_fp
            else build_id_from_fp,  # Often build_id + incremental
            "ro.build.version.incremental": incremental_from_fp,
            "ro.build.version.release": release_str,
            "ro.build.version.sdk": str(sdk_int),
            "ro.serialno": serial,
            "ro.boot.serialno": serial,  # Often same as ro.serialno
            "ro.build.description": f"{selected_model_data.get('product')}-user {release_str} {build_id_from_fp} {incremental_from_fp} {self.patterns_data.get('common_build_tags', 'release-keys')}",
            "ro.build.type": self.patterns_data.get("common_build_type", "user"),
            "ro.build.tags": self.patterns_data.get(
                "common_build_tags", "release-keys"
            ),
            "ro.build.host": f"android-build-{random.choice(['gke', 'chi', 'sfo'])}{random.randint(10, 99)}.c.android.com",  # Generic build host
            "ro.build.user": "android-build",  # Generic build user
            "ro.build.date.utc": str(
                int(
                    (
                        datetime.now() - timedelta(days=random.randint(30, 180))
                    ).timestamp()
                )
            ),
            "ro.build.date": (
                datetime.now() - timedelta(days=random.randint(30, 180))
            ).strftime("%a %b %d %H:%M:%S %Z %Y"),
        }

        # Add Xiaomi specific MIUI props if applicable
        if (
            target_manufacturer_key == "xiaomi"
            and "miui_version_patterns" in manufacturer_patterns
        ):
            miui_version_template_list = manufacturer_patterns[
                "miui_version_patterns"
            ].get(target_android_version_key, ["V14.0.{rd}.0.T{rl}CMIXM"])
            miui_version_template = random.choice(miui_version_template_list)
            # Replace placeholders like {rd} for random digit, {rl} for random letter
            miui_version_name = miui_version_template.replace(
                "{rd}", str(random.randint(1, 9))
            ).replace("{rl}", random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            all_generated_props["ro.miui.ui.version.name"] = miui_version_name
            all_generated_props["ro.miui.ui.version.code"] = (
                release_str  # Often same as Android release
            )

        # Determine which properties to actually set based on config toggles
        props_to_set_this_session = {}
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_build_fingerprint", fallback=True
        ):
            props_to_set_this_session.update(
                {
                    k: v
                    for k, v in all_generated_props.items()
                    if "fingerprint" in k
                    or "build.id" in k
                    or "display.id" in k
                    or "incremental" in k
                    or "description" in k
                    or "type" in k
                    or "tags" in k
                    or "host" in k
                    or "user" in k
                    or "date" in k
                }
            )
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_serial_number", fallback=True
        ):
            props_to_set_this_session.update(
                {k: v for k, v in all_generated_props.items() if "serialno" in k}
            )
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_device_model", fallback=True
        ):
            props_to_set_this_session.update(
                {
                    k: v
                    for k, v in all_generated_props.items()
                    if "product." in k
                    or "board" in k
                    or ".model" in k
                    or ".device" in k
                    or ".brand" in k
                    or ".manufacturer" in k
                }
            )
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_android_version_props", fallback=True
        ):
            props_to_set_this_session.update(
                {
                    k: v
                    for k, v in all_generated_props.items()
                    if "version.release" in k or "version.sdk" in k
                }
            )

        # Add MIUI props if they were generated and target is Xiaomi
        if target_manufacturer_key == "xiaomi":
            if "ro.miui.ui.version.name" in all_generated_props:
                props_to_set_this_session["ro.miui.ui.version.name"] = (
                    all_generated_props["ro.miui.ui.version.name"]
                )
            if "ro.miui.ui.version.code" in all_generated_props:
                props_to_set_this_session["ro.miui.ui.version.code"] = (
                    all_generated_props["ro.miui.ui.version.code"]
                )

        # Filter by master list from device_patterns.json `props_to_spoof`
        master_prop_list_from_patterns = self.patterns_data.get(
            "props_to_spoof", self.COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF
        )
        final_props_to_apply = {
            k: v
            for k, v in props_to_set_this_session.items()
            if k in master_prop_list_from_patterns and v is not None
        }

        # Spoof Android ID for current user (usually user 0) via Magisk context
        if self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_android_id_magisk", fallback=True
        ):
            new_android_id = self._generate_random_hex_string(16)
            if self.validate_property("android_id", new_android_id):
                # This sets Android ID for the *current* user context where `su` is running (usually user 0)
                # This is different from setting it for a newly created user profile.
                cmd_android_id_list = [
                    "settings",
                    "put",
                    "secure",
                    "android_id",
                    new_android_id,
                ]
                res_android_id = self._run_adb_shell_command(
                    device_id, cmd_android_id_list, as_root=True, timeout=10
                )
                if res_android_id.returncode == 0:
                    self._log_message(
                        f"  ✓ Android ID (Magisk context/current user): Set to {new_android_id}",
                        "success",
                        dim_style=True,
                    )
                else:
                    self._log_message(
                        f"  ✗ Failed to set Android ID (Magisk context/current user): {res_android_id.stderr.strip() or res_android_id.stdout.strip()}",
                        "error",
                    )
            else:
                self._log_message(
                    f"  ✗ Generated Android ID '{new_android_id}' for Magisk context is invalid. Skipping.",
                    "error",
                )

        all_set_success = True
        if not final_props_to_apply:
            self._log_message(
                "  ℹ️ No specific Magisk properties selected for spoofing based on current configuration and patterns.",
                "info",
                dim_style=True,
            )
        else:
            self._log_message(
                f"  🔧 Attempting to set {len(final_props_to_apply)} Magisk properties: {', '.join(sorted(final_props_to_apply.keys()))}",
                "info",
            )

        for prop_name, prop_value in final_props_to_apply.items():
            if not self.validate_property(prop_name, prop_value):
                self._log_message(
                    f"  ✗ Invalid value format for {prop_name}: '{prop_value}'. Skipping.",
                    "warning",
                )
                all_set_success = False  # Mark as partial failure
                continue
            if not self.set_property_with_resetprop(device_id, prop_name, prop_value):
                all_set_success = False

        if all_set_success and final_props_to_apply:
            self._log_message(
                f"  ✓ All selected Magisk properties applied for [b]{device_id}[/b]. A reboot might be needed for all changes to take full effect.",
                "success",
            )
        elif not final_props_to_apply and not self.config.getboolean(
            "ADVANCED_SPOOFING", "spoof_android_id_magisk", fallback=True
        ):
            pass  # No props were meant to be set.
        elif not all_set_success:
            self._log_message(
                f"  ⚠️ Some Magisk properties failed to apply or verify for [b]{device_id}[/b].",
                "warning",
            )
        return all_set_success

    def apply_random_device_fingerprint_for_new_user(self, device_id):
        """
        Automatically applies random device properties when creating a new user profile.
        This makes each user profile appear as a completely unique device to prevent
        app tracking across user profiles.
        """
        if not self.config.getboolean("ADVANCED_SPOOFING", "auto_spoof_on_user_creation", fallback=True):
            self._log_message(
                f"  Auto-spoofing on user creation is disabled. Skipping automatic device randomization.",
                "info",
                dim_style=True
            )
            return True

        caps = self.device_capabilities.get(device_id) or self.detect_capabilities(device_id)
        if not (caps.get("root_access") and caps.get("magisk_available")):
            self._log_message(
                f"  Root/Magisk required for automatic device spoofing. Skipping for {device_id}.",
                "warning",
                dim_style=True
            )
            return False

        self._log_message(
            f"🎲 Applying automatic random device fingerprint for new user profile on {device_id}...",
            "info"
        )
        
        # Choose random manufacturer and model for maximum uniqueness
        available_manufacturers = list(self.device_manufacturers_patterns.keys())
        random_manufacturer_key = random.choice(available_manufacturers)
        
        manufacturer_patterns = self.device_manufacturers_patterns[random_manufacturer_key]
        available_models = manufacturer_patterns.get("models", [])
        
        # Pick random model (or None to get auto-generated)
        if available_models:
            random_model_choice = random.choice(available_models + [None])
            random_model_config = random_model_choice.get("name", "") if random_model_choice is not None else ""
        else:
            random_model_config = ""
        
        # Choose random Android version
        available_android_versions = list(self.android_version_release_map.keys())
        random_android_version = random.choice(available_android_versions)
        
        self._log_message(
            f"  🎯 Random target: {random_manufacturer_key.upper()} | {random_model_config or 'Random Model'} | Android {random_android_version}",
            "debug", 
            dim_style=True
        )

        # Apply the standard device spoofing with random parameters
        spoof_success = self.apply_device_spoofing(
            device_id,
            random_manufacturer_key,
            random_model_config,
            random_android_version
        )

        if spoof_success:
            # Apply additional anti-tracking properties
            additional_success = self._apply_additional_anti_tracking_props(device_id, random_manufacturer_key)
            if additional_success:
                self._log_message(
                    f"  ✅ Complete device fingerprint randomization applied for new user profile on {device_id}",
                    "success"
                )
            else:
                self._log_message(
                    f"  ⚠️ Basic spoofing succeeded, but some additional anti-tracking properties failed on {device_id}",
                    "warning"
                )
            return True
        else:
            self._log_message(
                f"  ❌ Device fingerprint randomization failed for new user profile on {device_id}",
                "error"
            )
            return False

    def _apply_additional_anti_tracking_props(self, device_id, manufacturer_key):
        """
        Applies additional properties beyond the standard spoofing set to prevent
        app tracking through secondary device identifiers.
        """
        self._log_message(
            f"  🔒 Applying additional anti-tracking properties...",
            "debug",
            dim_style=True
        )
        
        additional_props = {}
        
        # Generate additional hardware identifiers using realistic patterns
        platform_chipsets = {
            "samsung": [f"msm{random.choice([8996, 8998, 8150, 8250, 8350])}", f"exynos{random.choice([9820, 9825, 990, 2100, 2200])}"],
            "google": [f"sdm{random.choice([845, 855, 865, 888, 8150])}", f"gs{random.choice([101, 201, 301])}"],
            "xiaomi": [f"msm{random.choice([8996, 8998, 8150, 8250, 8350])}", f"sm{random.choice([8150, 8250, 8350, 8450])}"],
            "oneplus": [f"msm{random.choice([8996, 8998, 8150, 8250, 8350])}", f"sm{random.choice([8150, 8250, 8350])}"],
            "oppo": [f"msm{random.choice([8996, 8998, 8150, 8250])}", f"mt{random.choice([6889, 6893, 6983])}"],
        }
        
        hardware_names = {
            "samsung": [f"qcom", f"exynos{random.choice([9820, 9825, 990, 2100, 2200])}"],
            "google": [f"bramble", f"redfin", f"barbet", f"oriole", f"raven"],
            "xiaomi": [f"qcom", f"mt{random.choice([6889, 6893, 6983])}"],
            "oneplus": [f"qcom", f"msmnile"],
            "oppo": [f"qcom", f"mt{random.choice([6889, 6893, 6983])}"],
        }
        
        selected_platform = random.choice(platform_chipsets.get(manufacturer_key, ["msm8996", "msm8998"]))
        selected_hardware = random.choice(hardware_names.get(manufacturer_key, ["qcom"]))
        
        additional_props.update({
            "ro.hardware": selected_hardware,
            "ro.board.platform": selected_platform,
            "ro.bootloader": self._generate_random_hex_string(8, uppercase=True),
            "ro.boot.revision": f"rev_{random.randint(10, 99)}",
            "ro.baseband": f"{random.choice(['g', 'm'])}{random.randint(950, 5200)}-{self._generate_random_hex_string(6, uppercase=True)}",
        })
        
        # Generate network/connectivity randomization
        additional_props.update({
            "ro.telephony.call_ring.multiple": str(random.choice([True, False])).lower(),
            "ro.wifi.channels": "",  # Clear to avoid network fingerprinting
            "wifi.interface": random.choice(["wlan0", "wlan1", "wifi0"]),
        })
        
        # Generate display properties variation
        density_options = [120, 160, 213, 240, 320, 400, 480, 560, 640]
        additional_props.update({
            "ro.sf.lcd_density": str(random.choice(density_options)),
        })
        
        # Generate locale/regional variation to avoid geographic tracking
        locales = ["en_US", "en_GB", "en_CA", "en_AU", "de_DE", "fr_FR", "ja_JP", "ko_KR"]
        random_locale = random.choice(locales)
        lang, region = random_locale.split("_")
        additional_props.update({
            "ro.product.locale.language": lang,
            "ro.product.locale.region": region,
        })
        
        # Generate system service variations
        ringtones = ["Thema.ogg", "Over_the_Horizon.ogg", "One_UI.ogg", "Spaceline.ogg"]
        notifications = ["Skyline.ogg", "Silk.ogg", "Popcorn.ogg", "Crystal.ogg"]
        alarms = ["Morning_flower.ogg", "Good_morning.ogg", "Homecoming.ogg", "Sunrise.ogg"]
        
        additional_props.update({
            "ro.config.ringtone": random.choice(ringtones),
            "ro.config.notification_sound": random.choice(notifications),
            "ro.config.alarm_alert": random.choice(alarms),
        })
        
        # Filter properties that are safe to set and exist in our master list
        combined_master_list = list(set(
            self.COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF + 
            self.ANTI_TRACKING_EXTENDED_PROPS
        ))
        
        filtered_additional_props = {
            k: v for k, v in additional_props.items() 
            if any(k in master_prop or k.startswith(master_prop.replace("*", "")) for master_prop in combined_master_list)
        }
        
        if not filtered_additional_props:
            self._log_message(
                f"    No additional anti-tracking properties to apply based on current master list",
                "debug",
                dim_style=True
            )
            return True
        
        # Apply the additional properties
        all_success = True
        self._log_message(
            f"    Applying {len(filtered_additional_props)} additional anti-tracking properties...",
            "debug",
            dim_style=True
        )
        
        for prop_name, prop_value in filtered_additional_props.items():
            if not self.validate_property(prop_name, prop_value):
                self._log_message(
                    f"    ⚠️ Invalid additional property format for {prop_name}: '{prop_value}'. Skipping.",
                    "warning",
                    dim_style=True
                )
                continue
                
            if not self.set_property_with_resetprop(device_id, prop_name, prop_value):
                all_success = False
        
        if all_success:
            self._log_message(
                f"    ✓ All additional anti-tracking properties applied successfully",
                "success",
                dim_style=True
            )
        else:
            self._log_message(
                f"    ⚠️ Some additional anti-tracking properties failed to apply",
                "warning",
                dim_style=True
            )
            
        return all_success

    def _prompt_user_for_cleanup_options(self, device_id, console=None):
        """Prompts user for cleanup options instead of automatic restoration."""
        if not console and not QUESTIONARY_AVAILABLE:
            # Fallback to basic input if no console or questionary
            print(f"\n🧹 Cleanup options for {device_id}:")
            user_choice = input("Restore user profiles? (y/n, default n): ").strip().lower() or "n"
            restore_users = user_choice in ["y", "yes"]
            
            props_choice = input("Restore original device properties? (y/n, default n): ").strip().lower() or "n"
            restore_props = props_choice in ["y", "yes"]
            
            limits_choice = input("Restore original user limits? (y/n, default n): ").strip().lower() or "n"
            restore_limits = limits_choice in ["y", "yes"]
            
            return restore_users, restore_props, restore_limits
        
        # Rich/questionary interface
        if console:
            console.print(f"\n🧹 Cleanup Options for {device_id}", style="bold cyan")
            console.print("Choose what to restore (changes will be kept if not restored):", style="dim")
        
        try:
            # Check what can be restored
            has_user_profiles = device_id in self.active_spoofed_users
            has_property_backups = (device_id in self.property_backups and 
                                  self.property_backups[device_id])
            has_user_limits = device_id in self.user_limit_originals
            
            cleanup_choices = []
            
            if has_user_profiles:
                cleanup_choices.append(
                    questionary.Choice(
                        f"Remove created user profiles (current: {self.active_spoofed_users[device_id].get('user_name', 'Unknown')})",
                        "users"
                    )
                )
            
            if has_property_backups:
                prop_count = len(self.property_backups[device_id])
                cleanup_choices.append(
                    questionary.Choice(
                        f"Restore original device properties ({prop_count} properties modified)",
                        "properties"
                    )
                )
            
            if has_user_limits:
                original_limit = self.user_limit_originals[device_id]
                cleanup_choices.append(
                    questionary.Choice(
                        f"Restore original user limit (currently modified, original: {original_limit})",
                        "limits"
                    )
                )
            
            if not cleanup_choices:
                if console:
                    console.print("No modifications detected for this device.", style="dim")
                return False, False, False
            
            cleanup_choices.append(questionary.Choice("Keep all changes (no restoration)", "none"))
            
            selected_cleanups = questionary.checkbox(
                "Select what to restore:",
                choices=cleanup_choices,
                style=questionary.Style([
                    ('pointer', 'fg:yellow bold'),
                    ('highlighted', 'fg:yellow'),
                    ('selected', 'fg:cyan bold'),
                    ('checkbox', 'fg:cyan'),
                    ('checkbox-selected', 'fg:cyan bold')
                ])
            ).ask()
            
            if selected_cleanups is None:  # User cancelled
                return False, False, False
            
            if "none" in selected_cleanups:
                return False, False, False
                
            restore_users = "users" in selected_cleanups
            restore_props = "properties" in selected_cleanups
            restore_limits = "limits" in selected_cleanups
            
            return restore_users, restore_props, restore_limits
            
        except KeyboardInterrupt:
            if console:
                console.print("\nCleanup cancelled - keeping all changes.", style="yellow")
            return False, False, False

    def comprehensive_cleanup(self, device_id, prompt_user=True):
        """Performs cleanup of spoofed users and properties for a device with user choice."""
        self._log_message(
            f"🧹 Cleanup options for {device_id}...", "info"
        )
        
        # Check if there's anything to clean up
        has_modifications = (
            device_id in self.active_spoofed_users or
            (device_id in self.property_backups and self.property_backups[device_id]) or
            device_id in self.user_limit_originals
        )
        
        if not has_modifications:
            self._log_message(
                f"  No modifications detected for {device_id}. Skipping cleanup.",
                "info",
                dim_style=True
            )
            return True
        
        # Get user preferences for cleanup
        if prompt_user:
            restore_users, restore_props, restore_limits = self._prompt_user_for_cleanup_options(
                device_id, self.console
            )
        else:
            # Use config defaults when not prompting (for backwards compatibility)
            restore_users = self.config.getboolean(
                "UNIQUENESS", "cleanup_user_profile_after_session", fallback=False
            )
            restore_props = self.config.getboolean(
                "ADVANCED_SPOOFING", "restore_properties_after_session", fallback=False
            )
            restore_limits = self.config.getboolean(
                "ADVANCED_SPOOFING", "restore_user_limits_after_session", fallback=False
            )
        
        # Perform selected cleanup actions
        user_cleaned = True
        if restore_users:
            user_cleaned = self.cleanup_user_profile(device_id)
        else:
            if device_id in self.active_spoofed_users:
                user_data = self.active_spoofed_users[device_id]
                self._log_message(
                    f"  Keeping user profile '{user_data.get('user_name', 'Unknown')}' (ID: {user_data.get('user_id')}) as requested.",
                    "info",
                    dim_style=True
                )
        
        props_restored = True
        if restore_props:
            props_restored = self.restore_all_properties(device_id)
        else:
            if device_id in self.property_backups and self.property_backups[device_id]:
                prop_count = len(self.property_backups[device_id])
                self._log_message(
                    f"  Keeping {prop_count} modified device properties as requested.",
                    "info",
                    dim_style=True
                )
        
        limit_restored = True
        if restore_limits and self.config.getboolean("ADVANCED_SPOOFING", "bypass_user_limits", fallback=False):
            limit_restored = self.restore_user_limit(device_id)
        else:
            if device_id in self.user_limit_originals:
                self._log_message(
                    f"  Keeping modified user limits as requested.",
                    "info",
                    dim_style=True
                )

        final_success = user_cleaned and props_restored and limit_restored
        if final_success:
            action_summary = []
            if restore_users: action_summary.append("users")
            if restore_props: action_summary.append("properties") 
            if restore_limits: action_summary.append("limits")
            
            if action_summary:
                self._log_message(
                    f"  ✓ Cleanup completed for {device_id} (restored: {', '.join(action_summary)}).", 
                    "success"
                )
            else:
                self._log_message(
                    f"  ✓ All changes kept for {device_id} as requested.", 
                    "success"
                )
        else:
            self._log_message(
                f"  ✗ Some cleanup operations had issues for {device_id}.",
                "warning",
            )
        return final_success

    def get_obb_path_for_user(self, user_id_or_str, package_name):
        """Constructs the OBB path for a given user ID and package name."""
        user_id = 0  # Default to user 0 (owner)
        if user_id_or_str is not None:
            try:
                user_id = int(str(user_id_or_str))
            except ValueError:
                user_id = 0  # Fallback if parsing fails
        return f"/storage/emulated/{user_id}/Android/obb/{package_name}/"

    def get_install_command_args_for_user(self, user_id_or_str=None):
        """Gets ADB install arguments for targeting a specific user."""
        args = []
        if user_id_or_str is not None:
            try:
                # Ensure user_id is not 0, as --user 0 is implicit default and sometimes causes issues
                uid = int(str(user_id_or_str))
                if uid != 0:  # Only add --user flag if it's not for user 0
                    args.extend(["--user", str(uid)])
            except ValueError:
                pass  # Invalid user_id string, install for current/default
        return args


# --- END DeviceSpoofingManager ---


class InteractiveAPKInstaller:
    """Main class orchestrating APK installation and device spoofing."""

    def __init__(self):
        self.console = (
            Console(stderr=True) if RICH_AVAILABLE else None
        )  # stderr for prompts during status
        self.config = configparser.ConfigParser(interpolation=None)
        self.adb_path = "adb"
        self.apk_directory = "apks"
        self.errors = []
        self.successes = []
        self.temp_dir = None
        self.retry_with_all_apks_on_missing_split = True
        self.spoofing_manager = None
        self.uniqueness_settings = {}
        self.advanced_spoofing_settings = {}
        self.device_capabilities = {}  # Store by device_id
        self.always_allow_downgrade = True
        self.prompt_uninstall_on_conflict = True
        self.package_parser_preference = "pyaxmlparser"  # "pyaxmlparser" or "aapt"

    def _log_message(self, message, level="info", dim_style=False):
        if not self.console:
            print(f"[{level.upper()}] {message}")
            return
        style_map = {
            "info": "dim" if dim_style else "",
            "success": "green",
            "warning": "yellow",
            "error": "red",
            "debug": "dim blue",
        }
        style = style_map.get(level, "")
        # Enable markup parsing for rich formatting like [b]...[/b]
        self.console.print(message, style=style, markup=True)

    def ensure_temp_directory(self):
        if (
            self.temp_dir
            and os.path.exists(self.temp_dir)
            and os.access(self.temp_dir, os.W_OK)
        ):
            return True
        try:
            # Use a versioned temp dir prefix
            self.temp_dir = tempfile.mkdtemp(
                prefix=f"apk_installer_{SCRIPT_VERSION.replace('.', '_')}_"
            )
            self._log_message(
                f"📁 Created temp directory: {self.temp_dir}", "debug", dim_style=True
            )
        except Exception as e:
            self._log_message(
                f"⚠️ Failed to create system temp directory: {e}", "warning"
            )
            # Fallback to local temp directory
            local_temp_path = (
                Path.cwd()
                / f"temp_apk_installer_files_{SCRIPT_VERSION.replace('.', '_')}"
            )
            self.temp_dir = str(local_temp_path)
            try:
                local_temp_path.mkdir(parents=True, exist_ok=True)
                self._log_message(
                    f"📁 Using local fallback temp directory: {self.temp_dir}",
                    "debug",
                    dim_style=True,
                )
            except Exception as e_local:
                self._log_message(
                    f"💥 CRITICAL: Failed to create ANY temp directory: {e_local}",
                    "error",
                )
                self.errors.append(
                    f"CRITICAL: Failed to create temp directory: {e_local}"
                )
                return False

        # Test writability
        test_file = Path(self.temp_dir) / "test_write.tmp"
        try:
            with open(test_file, "w", encoding="utf-8") as f_test:
                f_test.write("test")
            test_file.unlink()
            return True
        except Exception as e_write:
            self._log_message(
                f"⚠️ Temp directory not writable: {self.temp_dir}. Error: {e_write}",
                "warning",
            )
            self.errors.append(
                f"Temp directory not writable: {self.temp_dir}. Error: {e_write}"
            )
            return False

    def cleanup_temp_files(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self._log_message(
                    f"🧹 Cleaned up temporary directory: {self.temp_dir}",
                    "debug",
                    dim_style=True,
                )
                self.temp_dir = None
            except Exception as e:
                self._log_message(
                    f"⚠️ Could not clean temp directory {self.temp_dir}: {e}", "warning"
                )

    def get_package_name_from_apk(self, apk_path_str):
        apk_path = Path(apk_path_str)
        if not apk_path.exists():
            self._log_message(
                f"APK not found for package name extraction: {apk_path}", "warning"
            )
            return None

        # Try pyaxmlparser first if available and preferred
        if self.package_parser_preference == "pyaxmlparser" and PYAXMLPARSER_AVAILABLE:
            try:
                apk_obj = AXMLParserAPK(str(apk_path))
                if apk_obj and apk_obj.packagename:
                    return apk_obj.packagename
            except Exception as e:
                self._log_message(
                    f"pyaxmlparser failed for {apk_path.name}: {e}. Trying aapt if available.",
                    "debug",
                    dim_style=True,
                )

        # Fallback to aapt or if aapt is preferred
        if (
            self.package_parser_preference == "aapt"
            or not PYAXMLPARSER_AVAILABLE
        ):  # If pyaxmlparser failed or aapt is preferred
            try:
                adb_dir = Path(self.adb_path).parent
                # Common locations for aapt
                aapt_path_variants = [
                    adb_dir / "aapt.exe"
                    if sys.platform == "win32"
                    else adb_dir / "aapt",  # Next to adb
                    Path("aapt"),  # In PATH
                ]
                android_sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get(
                    "ANDROID_SDK_ROOT"
                )
                if android_sdk_root:
                    build_tools_paths = sorted(
                        list(Path(android_sdk_root).glob("build-tools/*")), reverse=True
                    )
                    if build_tools_paths:  # Get latest build-tools
                        aapt_path_variants.append(
                            build_tools_paths[0]
                            / ("aapt.exe" if sys.platform == "win32" else "aapt")
                        )

                aapt_executable = next(
                    (str(p) for p in aapt_path_variants if shutil.which(str(p))), None
                )

                if not aapt_executable:
                    self._log_message(
                        f"aapt not found. Cannot get package name for {apk_path.name} using aapt.",
                        "debug",
                        dim_style=True,
                    )
                    return None

                result = subprocess.run(
                    [aapt_executable, "dump", "badging", str(apk_path)],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )
                if result.returncode == 0:
                    match = re.search(r"package: name='([^']+)'", result.stdout)
                    if match:
                        return match.group(1)
                    # Fallback for slightly different output formats if any
                    match_alt = re.search(
                        r"name='([^']+)'", result.stdout
                    )  # Broader search
                    if match_alt:
                        return match_alt.group(1)  # Could be app name, be careful
                else:  # aapt command failed
                    self._log_message(
                        f"aapt execution failed for {apk_path.name}. Exit code: {result.returncode}. "
                        f"Error: {(result.stderr or result.stdout).strip()}",
                        "debug",
                        dim_style=True,
                    )
            except Exception as e:
                self._log_message(
                    f"Exception using aapt for {apk_path.name}: {e}", "warning"
                )

        if (
            not PYAXMLPARSER_AVAILABLE
            and self.package_parser_preference == "pyaxmlparser"
        ):
            self._log_message(
                "pyaxmlparser preferred but not available, and aapt fallback failed or also not available.",
                "warning",
            )

        self._log_message(
            f"Could not determine package name for {apk_path.name} using any method.",
            "warning",
        )
        return None

    def get_device_properties(self, device_id):
        # Default properties, good for common arm64 devices
        properties = {
            "abi": "arm64-v8a",
            "dpi": 480,  # xxhdpi default
            "abis": ["arm64-v8a", "armeabi-v7a", "armeabi"],  # Common ABIs
            "sdk": 33,  # Default to Android 13
        }
        if not self.spoofing_manager:
            self._log_message(
                "⚠️ SpoofingManager not initialized for get_device_properties, using defaults.",
                "warning",
            )
            return properties
        try:
            # Primary ABI
            res_abi = self.spoofing_manager._run_adb_shell_command(
                device_id, ["getprop", "ro.product.cpu.abi"]
            )
            if res_abi.returncode == 0 and res_abi.stdout.strip():
                properties["abi"] = res_abi.stdout.strip()

            # List of ABIs
            res_abilist = self.spoofing_manager._run_adb_shell_command(
                device_id, ["getprop", "ro.product.cpu.abilist"]
            )
            if res_abilist.returncode == 0 and res_abilist.stdout.strip():
                properties["abis"] = [
                    x.strip() for x in res_abilist.stdout.strip().split(",")
                ]
            elif properties["abi"]:  # Fallback if abilist is not available
                # Construct a reasonable list based on primary ABI
                if "arm64" in properties["abi"]:
                    properties["abis"] = ["arm64-v8a", "armeabi-v7a", "armeabi"]
                elif "x86_64" in properties["abi"]:
                    properties["abis"] = ["x86_64", "x86"]
                elif (
                    "armeabi" in properties["abi"]
                ):  # Could be armeabi-v7a or just armeabi
                    properties["abis"] = ["armeabi-v7a", "armeabi"]
                else:
                    properties["abis"] = [properties["abi"]]

            # Screen Density (DPI)
            res_dpi = self.spoofing_manager._run_adb_shell_command(
                device_id, ["getprop", "ro.sf.lcd_density"]
            )
            if res_dpi.returncode == 0 and res_dpi.stdout.strip().isdigit():
                properties["dpi"] = int(res_dpi.stdout.strip())

            # SDK Version
            res_sdk = self.spoofing_manager._run_adb_shell_command(
                device_id, ["getprop", "ro.build.version.sdk"]
            )
            if res_sdk.returncode == 0 and res_sdk.stdout.strip().isdigit():
                properties["sdk"] = int(res_sdk.stdout.strip())

        except Exception as e:
            self._log_message(
                f"⚠️ Could not get full device properties for {device_id}: {e}. Using defaults/fallbacks.",
                "warning",
            )
        return properties

    def _get_dpi_bucket(self, dpi):
        # Standard Android DPI buckets
        if dpi <= 120:
            return "ldpi"  # ~120dpi
        if dpi <= 160:
            return "mdpi"  # ~160dpi
        if dpi <= 213:
            return "tvdpi"  # ~213dpi (mostly for TVs)
        if dpi <= 240:
            return "hdpi"  # ~240dpi
        if dpi <= 320:
            return "xhdpi"  # ~320dpi
        if dpi <= 480:
            return "xxhdpi"  # ~480dpi
        if dpi <= 640:
            return "xxxhdpi"  # ~640dpi
        return "nodpi"  # If very high or doesn't fit, or for universal resources

    def extract_xapk(self, xapk_path_str):
        """Extract XAPK, APKM, or ZIP archive containing APK splits and OBB files."""
        xapk_path = Path(xapk_path_str)
        if not self.ensure_temp_directory():
            self.errors.append(
                f"Cannot extract {xapk_path.name} due to temp directory issues."
            )
            return None
        try:
            base_xapk_name = xapk_path.stem
            # Sanitize name for directory creation
            sanitized_xapk_name = "".join(
                c if c.isalnum() or c in (" ", ".", "_", "-") else "_"
                for c in base_xapk_name
            ).replace(" ", "_")

            extract_dir = Path(self.temp_dir) / sanitized_xapk_name
            if extract_dir.exists():  # Clean up if exists from a previous failed run
                shutil.rmtree(extract_dir)
            extract_dir.mkdir(parents=True, exist_ok=True)

            extract_msg = f"[bold cyan]Extracting {xapk_path.name} to {extract_dir}..."
            if self.console:
                with self.console.status(extract_msg, spinner="dots"):
                    with zipfile.ZipFile(xapk_path, "r") as zip_ref:
                        zip_ref.extractall(extract_dir)
            else:  # Basic print for no-rich environment
                print(
                    extract_msg.replace("[bold cyan]", "").replace("[/bold cyan]", "")
                )
                with zipfile.ZipFile(xapk_path, "r") as zip_ref:
                    zip_ref.extractall(extract_dir)

            # Process manifest.json if it exists
            manifest_path = extract_dir / "manifest.json"
            manifest_data = {}
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r", encoding="utf-8") as f_manifest:
                        manifest_data = json.load(f_manifest)
                except Exception as e:
                    self._log_message(
                        f"⚠️ Could not read or parse manifest.json: {e}", "warning"
                    )

            all_apk_files_in_xapk = [str(p) for p in extract_dir.rglob("*.apk")]
            obb_files_in_xapk = [str(p) for p in extract_dir.rglob("*.obb")]

            # Determine package_name and app_name (best effort)
            package_name = manifest_data.get("package_name")
            app_name = manifest_data.get("name")  # App's display name from manifest

            if not package_name and all_apk_files_in_xapk:
                # Try to find a base.apk or the largest APK to guess package name
                base_apk_for_pkg_name = next(
                    (
                        p
                        for p in all_apk_files_in_xapk
                        if Path(p).name.lower() == "base.apk"
                    ),
                    None,
                )
                if (
                    not base_apk_for_pkg_name and all_apk_files_in_xapk
                ):  # If no base.apk, try largest
                    base_apk_for_pkg_name = max(
                        all_apk_files_in_xapk,
                        key=lambda p_path: Path(p_path).stat().st_size,
                        default=None,
                    )

                if base_apk_for_pkg_name:
                    package_name = self.get_package_name_from_apk(base_apk_for_pkg_name)

            if not package_name and obb_files_in_xapk:  # Infer from OBB path structure
                try:  # Example: Android/obb/com.example.app/main.obb
                    first_obb_parent_dir_name = Path(obb_files_in_xapk[0]).parent.name
                    if (
                        first_obb_parent_dir_name.count(".") >= 1
                    ):  # Heuristic for package name
                        package_name = first_obb_parent_dir_name
                except Exception:
                    pass  # Ignore errors in OBB path parsing

            if not package_name:
                package_name = "unknown_package"  # Fallback
            if not app_name:
                app_name = (
                    package_name
                    if package_name != "unknown_package"
                    else xapk_path.stem
                )

            return {
                "extract_dir": str(extract_dir),
                "manifest": manifest_data,
                "all_apk_files": all_apk_files_in_xapk,
                "obb_files": obb_files_in_xapk,
                "package_name": package_name,
                "app_name": app_name,
            }
        except Exception as e:
            error_msg = f"Failed to extract {xapk_path.name}: {e}"
            self.errors.append(error_msg)
            self._log_message(f"✗ {error_msg}", "error")
            return None

    def select_apks_for_installation(
        self, all_extracted_apks, device_props, manifest_data, extract_dir_str
    ):
        # device_props: {'abi': 'arm64-v8a', 'dpi': 480, 'abis': ['arm64-v8a', ...], 'sdk': 30}
        # manifest_data: Parsed manifest.json from XAPK/ZIP
        # all_extracted_apks: List of full paths to all APKs in the extracted archive

        extract_dir = Path(extract_dir_str)
        if not all_extracted_apks:
            self._log_message("No APKs provided for selection.", "warning")
            return []

        selected_apks_paths = set()  # Use a set to avoid duplicates, then sort
        device_main_abi = device_props.get("abi", "arm64-v8a")
        device_all_abis = device_props.get("abis", ["arm64-v8a", "armeabi-v7a"])
        device_sdk_version = device_props.get("sdk", 30)
        device_dpi_bucket = self._get_dpi_bucket(device_props.get("dpi", 480))

        # Common markers for splits
        known_abis_markers = [
            "arm64_v8a",
            "armeabi_v7a",
            "armeabi",
            "x86_64",
            "x86",
        ]  # Underscore typical for splits
        known_dpi_markers = [
            "ldpi",
            "mdpi",
            "hdpi",
            "xhdpi",
            "xxhdpi",
            "xxxhdpi",
            "tvdpi",
            "nodpi",
        ]

        self._log_message(
            f"⚙️ Device Props for Split Selection: Main ABI='{device_main_abi}', "
            f"All ABIs={device_all_abis}, SDK='{device_sdk_version}', DPI Bucket='{device_dpi_bucket}' "
            f"(Actual DPI: {device_props.get('dpi', 480)})",
            "debug",
            dim_style=True,
        )

        # --- Identify Base APK ---
        base_apk_path = None
        # 1. From manifest `split_apks` if `id == "base"`
        if manifest_data and "split_apks" in manifest_data:
            base_info_manifest = next(
                (
                    s
                    for s in manifest_data["split_apks"]
                    if s.get("id") == "base" and s.get("file")
                ),
                None,
            )
            if base_info_manifest:
                path_from_manifest = extract_dir / base_info_manifest["file"]
                if (
                    path_from_manifest.exists()
                    and str(path_from_manifest) in all_extracted_apks
                ):
                    base_apk_path = str(path_from_manifest)

        # 2. If not found, look for `base.apk` literally
        if not base_apk_path:
            base_apk_path = next(
                (p for p in all_extracted_apks if Path(p).name.lower() == "base.apk"),
                None,
            )

        # 3. If still not found, use the largest non-config APK, or largest overall
        if not base_apk_path:
            non_config_apks = [
                p
                for p in all_extracted_apks
                if not any(
                    marker in Path(p).name.lower()
                    for marker in ["config.", "split_", "_config."]
                )
            ]
            if non_config_apks:
                base_apk_path = max(
                    non_config_apks,
                    key=lambda p_path: Path(p_path).stat().st_size,
                    default=None,
                )
            elif all_extracted_apks:  # If all are "config" like, pick largest
                base_apk_path = max(
                    all_extracted_apks,
                    key=lambda p_path: Path(p_path).stat().st_size,
                    default=None,
                )

        if base_apk_path:
            selected_apks_paths.add(base_apk_path)
        else:
            self._log_message(
                "CRITICAL: No base APK could be identified in the XAPK.", "error"
            )
            return []  # Cannot proceed without a base APK

        # --- Select Split APKs ---
        if (
            manifest_data
            and "split_apks" in manifest_data
            and isinstance(manifest_data["split_apks"], list)
        ):
            self._log_message(
                "ℹ️ Using manifest.json for detailed split APK selection.",
                "debug",
                dim_style=True,
            )
            for split_info in manifest_data["split_apks"]:
                split_file_relative_path = split_info.get("file")
                split_id_lower = split_info.get(
                    "id", ""
                ).lower()  # e.g., "config.arm64_v8a", "config.en", "config.xxhdpi"

                if (
                    not split_file_relative_path or split_id_lower == "base"
                ):  # Already handled base
                    continue

                split_file_abs_path = str(extract_dir / split_file_relative_path)
                if split_file_abs_path not in all_extracted_apks:  # Ensure file exists
                    self._log_message(
                        f"  Manifest split '{split_file_relative_path}' not found in extracted files. Skipping.",
                        "debug",
                        dim_style=True,
                    )
                    continue

                # Language splits (always include if "config.lang" or "config.en")
                is_lang_split = "lang" in split_id_lower or any(
                    lang_code in split_id_lower
                    for lang_code in ["config.en", "config.es", "config.fr"]
                )  # etc.
                if is_lang_split:  # For now, include all language splits listed in manifest. Finer control is complex.
                    selected_apks_paths.add(split_file_abs_path)
                    continue

                # ABI splits
                # Check if the split_id contains any of the device's ABIs
                is_abi_split_for_device = any(
                    dev_abi.replace("-", "_") in split_id_lower
                    for dev_abi in device_all_abis
                )
                # If this split is an ABI split but not for this device, exclude it
                if (
                    any(
                        abi_marker in split_id_lower
                        for abi_marker in known_abis_markers
                    )
                    and not is_abi_split_for_device
                ):
                    self._log_message(
                        f"  Excluding ABI split {split_id_lower} (not for device ABIs: {device_all_abis})",
                        "debug",
                        dim_style=True,
                    )
                    continue

                # DPI splits
                is_dpi_split_for_device = (
                    device_dpi_bucket in split_id_lower or "nodpi" in split_id_lower
                )
                if (
                    any(
                        dpi_marker in split_id_lower for dpi_marker in known_dpi_markers
                    )
                    and not is_dpi_split_for_device
                ):
                    self._log_message(
                        f"  Excluding DPI split {split_id_lower} (not for device DPI: {device_dpi_bucket})",
                        "debug",
                        dim_style=True,
                    )
                    continue

                # If not excluded by ABI or DPI, include it
                selected_apks_paths.add(split_file_abs_path)
        else:  # Fallback: Heuristic selection if no detailed manifest.json splits
            self._log_message(
                "ℹ️ No detailed split_apks in manifest.json or manifest missing. Using heuristic APK selection (may include more splits than necessary).",
                "debug",
                dim_style=True,
            )
            for apk_path_str_heuristic in all_extracted_apks:
                if apk_path_str_heuristic == base_apk_path:
                    continue  # Already added

                apk_fname_lower = Path(apk_path_str_heuristic).name.lower()
                include_heuristic = True

                # Heuristic ABI check (less precise than manifest ID)
                if any(
                    marker in apk_fname_lower for marker in known_abis_markers
                ) and not any(
                    dev_abi.replace("-", "_") in apk_fname_lower
                    for dev_abi in device_all_abis
                ):
                    include_heuristic = False

                # Heuristic DPI check
                if (
                    include_heuristic
                    and any(marker in apk_fname_lower for marker in known_dpi_markers)
                    and not (
                        device_dpi_bucket in apk_fname_lower
                        or "nodpi" in apk_fname_lower
                    )
                ):
                    include_heuristic = False

                if include_heuristic:
                    selected_apks_paths.add(apk_path_str_heuristic)

        # Ensure base APK is first in the list for installation
        final_list_sorted = sorted(
            list(selected_apks_paths),
            key=lambda x: (x != base_apk_path, Path(x).name.lower()),
        )

        if self.console:
            self.console.print(
                f"ℹ️ Selected {len(final_list_sorted)} APK(s) for installation:",
                style="dim",
            )
            for i, p_item_path in enumerate(final_list_sorted):
                p_name = Path(p_item_path).name
                prefix_icon = (
                    "👑 Base:" if p_item_path == base_apk_path else "➕ Split:"
                )
                self.console.print(f"  {prefix_icon} {p_name}", style="dim")
        return final_list_sorted

    def print_banner(self):
        banner_text = f"""
 █████╗ ██████╗ ██████╗     █████╗ ██████╗ ██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗   ██╔══██╗██╔══██╗██║ ██╔╝
███████║██║  ██║██████╔╝   ███████║██████╔╝█████╔╝
██╔══██║██║  ██║██╔══██╗   ██╔══██║██╔═══╝ ██╔═██╗
██║  ██║██████╔╝██████╔╝   ██║  ██║██║     ██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        Interactive APK Installation Tool
             {SCRIPT_VERSION} (Odyssey)
"""
        if self.console:
            self.console.print(banner_text, style="bold cyan", highlight=False)
            self.console.print(
                "Professional APK Installation & Advanced Spoofing Assistant",
                style="bold yellow",
                justify="center",
            )
        else:
            print(banner_text)
            print("Professional APK Installation & Advanced Spoofing Assistant")
        print("=" * 60)

    def validate_configuration(self):  # Basic validation, can be expanded
        issues = []
        if not hasattr(self.config, "sections") or not self.config.sections():
            issues.append("Config file not loaded or empty.")
            self._log_message("CRITICAL: Configuration not loaded.", "error")
            return False

        # Example validation: If Magisk spoofing is on, root check should ideally be on.
        user_profile_enabled = self.config.getboolean(
            "UNIQUENESS", "enable_uniqueness_features", fallback=False
        )
        magisk_enabled = self.config.getboolean(
            "ADVANCED_SPOOFING", "enable_magisk_resetprop", fallback=False
        )

        if user_profile_enabled:
            if not self.config.getboolean(
                "SPOOF_VALIDATION", "check_multiuser_support", fallback=True
            ):
                issues.append(
                    "[SPOOF_VALIDATION] 'check_multiuser_support' should ideally be true if User Profile Spoofing is enabled."
                )
            if self.config.getboolean(
                "UNIQUENESS", "auto_set_random_android_id", fallback=True
            ) and not self.config.getboolean(
                "SPOOF_VALIDATION", "validate_root_access", fallback=True
            ):
                issues.append(
                    "[SPOOF_VALIDATION] 'validate_root_access' should be true if 'Auto Set Random Android ID (User Profile)' is enabled."
                )

        if magisk_enabled and not self.config.getboolean(
            "SPOOF_VALIDATION", "validate_root_access", fallback=True
        ):
            issues.append(
                "[SPOOF_VALIDATION] 'validate_root_access' should be true if Magisk Property Spoofing is enabled."
            )

        # Validate manufacturer and Android version against known patterns if spoofing manager is available
        if self.spoofing_manager:
            try:
                if self.config.has_option("ADVANCED_SPOOFING", "spoof_manufacturer"):
                    mfg = self.config.get(
                        "ADVANCED_SPOOFING", "spoof_manufacturer"
                    ).lower()
                    if (
                        mfg
                        and mfg
                        not in self.spoofing_manager.device_manufacturers_patterns
                    ):
                        issues.append(
                            f"Invalid 'spoof_manufacturer': '{mfg}'. Supported keys: {', '.join(self.spoofing_manager.device_manufacturers_patterns.keys())}"
                        )
                if self.config.has_option("ADVANCED_SPOOFING", "spoof_android_version"):
                    av = self.config.get(
                        "ADVANCED_SPOOFING", "spoof_android_version"
                    )  # Key, not release string
                    if (
                        av
                        and av not in self.spoofing_manager.android_version_release_map
                    ):
                        issues.append(
                            f"Invalid 'spoof_android_version': '{av}'. Supported keys: {', '.join(self.spoofing_manager.android_version_release_map.keys())}"
                        )
            except Exception as e:
                issues.append(f"Error during spoofing parameter validation: {e}")

        if issues and self.console:
            self.console.print(
                "⚠️ Configuration validation issues found in config.ini:", style="yellow"
            )
            for issue_idx, issue_msg in enumerate(issues):
                self.console.print(
                    f"  {issue_idx + 1}. {issue_msg}", style="dim yellow"
                )
            self.console.print(
                "  It's recommended to review config.ini or use the interactive configuration menu. Proceeding...",
                style="yellow",
            )
        elif issues:  # No Rich console
            print("⚠️ Configuration validation issues found...")
            for issue_idx, issue_msg in enumerate(issues):
                print(f"  {issue_idx + 1}. {issue_msg}")
        return not issues  # Returns True if no issues, False otherwise

    def load_config(self):
        try:
            self._log_message("\n⚙️ Configuration & Setup", "bold blue")
            if self.console:
                self.console.rule(style="blue")

            config_file_path = Path("config.ini")
            if not config_file_path.exists():
                self.create_default_config(str(config_file_path))

            self.config = configparser.ConfigParser(
                interpolation=None, allow_no_value=True
            )  # allow_no_value for empty keys like spoof_model
            self.config.read(config_file_path)

            # Ensure all expected sections exist, add if not (prevents errors if user deletes a section)
            expected_sections_with_defaults = {
                "PATHS": {"adb_path": "adb", "apk_directory": "apks"},
                "OPTIONS": {
                    "replace_existing": "true",
                    "auto_grant_permissions": "true",
                    "always_allow_downgrade": "true",
                    "prompt_uninstall_on_conflict": "true",
                    "package_parser": "pyaxmlparser",
                },
                "UNIQUENESS": {
                    "enable_uniqueness_features": "false",
                    "cleanup_user_profile_after_session": "false",
                    "auto_switch_back_to_owner": "true",
                    "auto_set_random_android_id": "true",
                    "user_creation_retries": "3",
                    "validate_user_switch": "true",
                    "user_switch_initial_delay_seconds": "3",
                    "validate_user_switch_timeout_seconds": "30",
                    "user_switch_no_validation_delay_seconds": "5",
                    "post_new_user_install_delay_seconds": "10",
                },
                "ADVANCED_SPOOFING": {
                    "enable_magisk_resetprop": "false",
                    "spoof_android_id_magisk": "true",
                    "spoof_build_fingerprint": "true",
                    "spoof_serial_number": "true",
                    "spoof_device_model": "true",
                    "spoof_android_version_props": "true",
                    "auto_spoof_on_user_creation": "true",
                    "backup_original_properties": "true",
                    "bypass_user_limits": "false",
                    "use_ephemeral_users": "true",  # Default to ephemeral, user's config can override
                    "spoof_manufacturer": "samsung",
                    "spoof_model": "",
                    "spoof_android_version": "13",
                },
                "SPOOF_VALIDATION": {
                    "min_storage_mb": "100",
                    "require_unlocked_device": "true",
                    "check_multiuser_support": "true",
                    "validate_root_access": "true",
                },
            }
            for section, defaults in expected_sections_with_defaults.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                    self._log_message(
                        f"  Added missing section [{section}] to in-memory config from defaults.",
                        "debug",
                        dim_style=True,
                    )
                for key, default_value in defaults.items():
                    if not self.config.has_option(section, key):
                        self.config.set(section, key, default_value)
                        self._log_message(
                            f"    Added missing option '{key}={default_value}' to [{section}] in-memory.",
                            "debug",
                            dim_style=True,
                        )

            # Load values from config into class attributes
            self.adb_path = self.config.get("PATHS", "adb_path", fallback="adb")
            self.apk_directory = self.config.get(
                "PATHS", "apk_directory", fallback="apks"
            )
            self.package_parser_preference = self.config.get(
                "OPTIONS", "package_parser", fallback="pyaxmlparser"
            ).lower()
            self.always_allow_downgrade = self.config.getboolean(
                "OPTIONS", "always_allow_downgrade", fallback=True
            )
            self.prompt_uninstall_on_conflict = self.config.getboolean(
                "OPTIONS", "prompt_uninstall_on_conflict", fallback=True
            )

            # UNIQUENESS settings
            self.uniqueness_settings = {
                k: self.config.getboolean(
                    "UNIQUENESS",
                    k,
                    fallback=expected_sections_with_defaults["UNIQUENESS"].get(
                        k, "false"
                    )
                    == "true",
                )
                for k in [
                    "enable_uniqueness_features",
                    "cleanup_user_profile_after_session",
                    "auto_switch_back_to_owner",
                    "auto_set_random_android_id",
                    "validate_user_switch",
                ]
            }
            self.uniqueness_settings.update(
                {  # Integer settings
                    k: self.config.getint(
                        "UNIQUENESS",
                        k,
                        fallback=int(
                            expected_sections_with_defaults["UNIQUENESS"].get(k, "3")
                        ),
                    )
                    for k in [
                        "user_creation_retries",
                        "user_switch_initial_delay_seconds",
                        "validate_user_switch_timeout_seconds",
                        "user_switch_no_validation_delay_seconds",
                        "post_new_user_install_delay_seconds",
                    ]
                }
            )

            # ADVANCED_SPOOFING settings
            self.advanced_spoofing_settings = {
                k: self.config.getboolean(
                    "ADVANCED_SPOOFING",
                    k,
                    fallback=expected_sections_with_defaults["ADVANCED_SPOOFING"].get(
                        k, "false"
                    )
                    == "true",
                )
                for k in [
                    "enable_magisk_resetprop",
                    "spoof_android_id_magisk",
                    "spoof_build_fingerprint",
                    "spoof_serial_number",
                    "spoof_device_model",
                    "spoof_android_version_props",
                    "auto_spoof_on_user_creation",
                    "backup_original_properties",
                    "bypass_user_limits",
                    "use_ephemeral_users",
                ]
            }
            self.advanced_spoofing_settings.update(
                {  # String settings
                    k: self.config.get(
                        "ADVANCED_SPOOFING",
                        k,
                        fallback=expected_sections_with_defaults[
                            "ADVANCED_SPOOFING"
                        ].get(k, ""),
                    )
                    for k in [
                        "spoof_manufacturer",
                        "spoof_model",
                        "spoof_android_version",
                    ]
                }
            )

            # Initialize or update SpoofingManager with the (potentially modified) config
            if not self.spoofing_manager:
                self.spoofing_manager = DeviceSpoofingManager(
                    self.adb_path, self.console, self.config
                )
            else:  # Update existing manager instance
                self.spoofing_manager.adb_path = self.adb_path
                self.spoofing_manager.config = self.config
                # Reload patterns as they might be influenced by config or manager might need re-init with new config
                self.spoofing_manager.patterns_data = (
                    self.spoofing_manager._load_device_patterns_file_or_defaults()
                )
                self.spoofing_manager.device_manufacturers_patterns = (
                    self.spoofing_manager.patterns_data.get(
                        "manufacturers",
                        self.spoofing_manager._get_default_manufacturers_patterns(),
                    )
                )
                self.spoofing_manager.android_version_release_map = self.spoofing_manager.patterns_data.get(
                    "android_versions",
                    self.spoofing_manager._get_default_android_version_release_map(),
                )

            self._log_message(
                f"✓ Configuration loaded from '{config_file_path.name}'", "success"
            )
            self.validate_configuration()  # Validate after loading everything

        except configparser.Error as e_cfg:
            error_msg = f"Error parsing config.ini: {e_cfg}"
            self.errors.append(error_msg)
            self._log_message(f"✗ {error_msg}", "error")
            self._apply_fallback_configs_and_init_manager()  # Attempt to run with pure defaults
        except Exception as e:
            error_msg = f"Failed to load/parse configuration: {str(e)}"
            self.errors.append(error_msg)
            self._log_message(f"✗ {error_msg}", "error")
            self._apply_fallback_configs_and_init_manager()

    def _apply_fallback_configs_and_init_manager(self):
        # This method is called if primary config loading fails catastrophically.
        # It sets up a very basic, default config object to allow the script to *try* to continue.
        self._log_message(
            "  Applying hardcoded fallback default configurations due to load error.",
            "warning",
        )

        # Create a minimal ConfigParser object with absolute defaults
        fallback_cfg_obj = configparser.ConfigParser(
            interpolation=None, allow_no_value=True
        )
        default_sections_for_fallback = {  # Similar to expected_sections_with_defaults, but for complete fallback
            "PATHS": {"adb_path": "adb", "apk_directory": "apks"},
            "OPTIONS": {
                "package_parser": "pyaxmlparser",
                "always_allow_downgrade": "true",
                "prompt_uninstall_on_conflict": "true",
                "replace_existing": "true",
                "auto_grant_permissions": "true",
            },
            "UNIQUENESS": {
                "enable_uniqueness_features": "false",
                "cleanup_user_profile_after_session": "false",
                "auto_switch_back_to_owner": "true",
                "auto_set_random_android_id": "true",
                "user_creation_retries": "3",
                "validate_user_switch": "true",
                "user_switch_initial_delay_seconds": "3",
                "validate_user_switch_timeout_seconds": "30",
                "user_switch_no_validation_delay_seconds": "5",
                "post_new_user_install_delay_seconds": "10",
            },
            "ADVANCED_SPOOFING": {
                "enable_magisk_resetprop": "false",
                "backup_original_properties": "true",
                "spoof_android_id_magisk": "true",
                "spoof_build_fingerprint": "true",
                "spoof_serial_number": "true",
                "spoof_device_model": "true",
                "spoof_android_version_props": "true",
                "auto_spoof_on_user_creation": "true",
                "bypass_user_limits": "false",
                "use_ephemeral_users": "true",
                "spoof_manufacturer": "samsung",
                "spoof_model": "",
                "spoof_android_version": "13",
            },
            "SPOOF_VALIDATION": {
                "min_storage_mb": "100",
                "check_multiuser_support": "true",
                "validate_root_access": "true",
                "require_unlocked_device": "true",
            },
        }
        for section, options in default_sections_for_fallback.items():
            fallback_cfg_obj.add_section(section)
            for key, value in options.items():
                fallback_cfg_obj.set(section, key, str(value))

        self.config = fallback_cfg_obj  # Assign this minimal config

        # Re-populate essential attributes from this minimal config
        self.adb_path = self.config.get("PATHS", "adb_path")
        self.apk_directory = self.config.get("PATHS", "apk_directory")
        self.package_parser_preference = self.config.get("OPTIONS", "package_parser")
        self.always_allow_downgrade = self.config.getboolean(
            "OPTIONS", "always_allow_downgrade"
        )
        self.prompt_uninstall_on_conflict = self.config.getboolean(
            "OPTIONS", "prompt_uninstall_on_conflict"
        )

        # Re-populate settings dictionaries from this minimal config
        self.uniqueness_settings = {
            k: (
                self.config.getboolean("UNIQUENESS", k)
                if k
                not in [
                    "user_creation_retries",
                    "user_switch_initial_delay_seconds",
                    "validate_user_switch_timeout_seconds",
                    "user_switch_no_validation_delay_seconds",
                    "post_new_user_install_delay_seconds",
                ]
                else self.config.getint("UNIQUENESS", k)
            )
            for k in default_sections_for_fallback["UNIQUENESS"]
        }
        self.advanced_spoofing_settings = {
            k: (
                self.config.getboolean("ADVANCED_SPOOFING", k)
                if k
                not in ["spoof_manufacturer", "spoof_model", "spoof_android_version"]
                else self.config.get("ADVANCED_SPOOFING", k)
            )
            for k in default_sections_for_fallback["ADVANCED_SPOOFING"]
        }

        # Ensure SpoofingManager is initialized with this fallback config
        if not self.spoofing_manager:
            self.spoofing_manager = DeviceSpoofingManager(
                self.adb_path, self.console, self.config
            )
        else:  # Update existing one
            self.spoofing_manager.adb_path = self.adb_path
            self.spoofing_manager.config = self.config
            self.spoofing_manager.patterns_data = (
                self.spoofing_manager._load_device_patterns_file_or_defaults()
            )  # Crucial to reload patterns

        self._log_message(
            "Fallback default configuration applied. Some features might be limited.",
            "warning",
        )

    def create_default_config(self, config_file_str):
        default_config_content = f"""[PATHS]
adb_path = adb
apk_directory = apks

[OPTIONS]
# replace_existing: If true, allows overwriting an existing app. (-r flag)
replace_existing = true
# auto_grant_permissions: If true, grants all runtime permissions on install. (-g flag for Android 6+)
auto_grant_permissions = true
# always_allow_downgrade: If true, allows installing an older version over a newer one. (-d flag)
always_allow_downgrade = true
# prompt_uninstall_on_conflict: If true, asks user to uninstall if INSTALL_FAILED_ALREADY_EXISTS or similar.
prompt_uninstall_on_conflict = true
# package_parser: Method to get package name from APK. Options: pyaxmlparser, aapt
# pyaxmlparser is pure Python, aapt requires Android SDK build tools.
package_parser = pyaxmlparser

[UNIQUENESS]
# enable_uniqueness_features: Master toggle for creating isolated Android user profiles for installs.
enable_uniqueness_features = false
# cleanup_user_profile_after_session: Removes created user profiles after installation session for that device.
cleanup_user_profile_after_session = false
# auto_switch_back_to_owner: Switches to primary user (0) before cleaning up a temporary user.
auto_switch_back_to_owner = true
# auto_set_random_android_id: Sets a random Android ID for newly created user profiles (requires Root).
auto_set_random_android_id = true
# user_creation_retries: How many times to attempt creating a user if it fails.
user_creation_retries = 3
# validate_user_switch: Verifies if 'am switch-user' command was successful by checking current user.
validate_user_switch = true
# user_switch_initial_delay_seconds: Wait time after 'am switch-user' before validation starts.
user_switch_initial_delay_seconds = 3
# validate_user_switch_timeout_seconds: Max time to wait for user switch validation.
validate_user_switch_timeout_seconds = 30
# user_switch_no_validation_delay_seconds: Fixed delay if 'validate_user_switch' is false.
user_switch_no_validation_delay_seconds = 5
# post_new_user_install_delay_seconds: Delay after new user creation/switch, before starting installs to that user.
# Helps ensure user environment is fully set up.
post_new_user_install_delay_seconds = 10

[ADVANCED_SPOOFING]
# enable_magisk_resetprop: Master toggle for using Magisk 'resetprop' to change device properties (requires Root & Magisk).
enable_magisk_resetprop = false
# spoof_android_id_magisk: Changes Android ID for the *current* user (usually user 0) via 'settings put secure android_id' (requires Root).
spoof_android_id_magisk = true
# spoof_build_fingerprint: Sets realistic, randomized build fingerprint and related build properties.
spoof_build_fingerprint = true
# spoof_serial_number: Sets realistic, randomized serial numbers (ro.serialno, ro.boot.serialno).
spoof_serial_number = true
# spoof_device_model: Sets realistic model, manufacturer, brand, board, product name, device codename.
spoof_device_model = true
# spoof_android_version_props: Sets realistic SDK level and Android release version string.
spoof_android_version_props = true
# auto_spoof_on_user_creation: Automatically applies random device fingerprint when creating user profiles for anti-tracking.
auto_spoof_on_user_creation = true
# backup_original_properties: (Recommended if Magisk ON) Backs up properties before spoofing for reliable restoration.
backup_original_properties = true
# bypass_user_limits: (Experimental, Root) Attempts to create users beyond device limits by adjusting 'fw.max_users' and global settings.
bypass_user_limits = false
# use_ephemeral_users: If true and User Profile Spoofing is ON, creates temporary users (Android 8+) auto-removed on switch/reboot.
# If false, creates standard (permanent) users. Falls back to standard if ephemeral not supported.
use_ephemeral_users = true

; --- Specific properties for generation (used if enable_magisk_resetprop is true) ---
; Target manufacturer key from device_patterns.json (e.g., samsung, google, xiaomi).
spoof_manufacturer = samsung
; Target model name (e.g., Pixel 8 Pro, SM-S908B). Leave blank to pick a random model for the chosen manufacturer.
spoof_model =
; Target Android version key from device_patterns.json (e.g., 13, 14, 15). Affects SDK, release string, and build ID patterns.
spoof_android_version = 13

[SPOOF_VALIDATION]
# min_storage_mb: Minimum free storage (in MB) required on /data to attempt user creation.
min_storage_mb = 100
# require_unlocked_device: If true, tries to check if device is unlocked before attempting user switch (heuristic).
require_unlocked_device = true
# check_multiuser_support: Validates if device reports multi-user capability.
check_multiuser_support = true
# validate_root_access: Checks for root if features requiring it are enabled.
validate_root_access = true
"""
        try:
            with open(config_file_str, "w", encoding="utf-8") as f_cfg:
                f_cfg.write(default_config_content)
            self._log_message(
                f"✓ Created default configuration file: [i]{config_file_str}[/i]",
                "success",
            )
        except Exception as e:
            self._log_message(
                f"✗ Failed to create default config file '{config_file_str}': {e}",
                "error",
            )

    def verify_adb(self):
        try:
            self._log_message("\n🔧 ADB Verification", "bold blue")
            if self.console:
                self.console.rule(style="blue")

            # Use a common ADB command that shows version info
            result = subprocess.run(
                [self.adb_path, "version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            if (
                result.returncode == 0
                and "Android Debug Bridge version" in result.stdout
            ):
                adb_version_line = result.stdout.splitlines()[0]
                self._log_message(f"✓ ADB verified: {adb_version_line}", "success")
                return True
            else:  # ADB command failed or didn't return expected output
                err_msg = f"ADB verification failed. Command: '{self.adb_path} version'. Output: {result.stderr.strip() or result.stdout.strip()}"
                self.errors.append(err_msg)
                self._log_message(f"✗ {err_msg}", "error")
                return False
        except FileNotFoundError:
            err_msg = f"ADB executable not found at '{self.adb_path}'. Please ensure ADB is installed and in your system PATH, or configure 'adb_path' in config.ini."
            self.errors.append(err_msg)
            self._log_message(f"✗ {err_msg}", "error")
            return False
        except Exception as e:  # Other errors like timeout
            err_msg = f"ADB verification error: {e}"
            self.errors.append(err_msg)
            self._log_message(f"✗ {err_msg}", "error")
            return False

    def display_capability_summary(self, device_id, caps):
        # caps is the dictionary from spoofing_manager.detect_capabilities()
        user_profile_on = self.uniqueness_settings.get(
            "enable_uniqueness_features", False
        )
        magisk_on = self.advanced_spoofing_settings.get(
            "enable_magisk_resetprop", False
        )

        # Only display if a relevant mode is active and console is available
        if not (user_profile_on or magisk_on) or not self.console:
            return

        cap_messages_styled = []  # List of Text objects or styled strings
        recommendations = []

        if user_profile_on:
            mu_status = (
                "[green]✓ Multi-user Support[/]"
                if caps.get("multiuser_support")
                else "[red]✗ No Multi-user Support[/]"
            )
            cap_messages_styled.append(Text.from_markup(mu_status))
            if not caps.get("multiuser_support"):
                recommendations.append(
                    f"{device_id}: Enable 'Multiple users' in Android settings for User Profile Spoofing."
                )

            if self.advanced_spoofing_settings.get(
                "use_ephemeral_users", True
            ):  # If ephemeral is preferred
                eph_status = (
                    "[green]✓ Ephemeral User Support[/]"
                    if caps.get("ephemeral_user_support")
                    else "[orange3]~ No Ephemeral User Support[/]"
                )
                cap_messages_styled.append(Text.from_markup(eph_status))
                if not caps.get("ephemeral_user_support"):
                    recommendations.append(
                        f"{device_id}: Ephemeral users (Android 8+) not detected. Standard (permanent) users will be created if 'Use Ephemeral Users' is on."
                    )

        # Check for root if Magisk is on OR if User Profile with Android ID spoofing is on
        needs_root_for_user_android_id = (
            user_profile_on
            and self.uniqueness_settings.get("auto_set_random_android_id", True)
        )
        if magisk_on or needs_root_for_user_android_id:
            root_status = (
                "[green]✓ Root Access[/]"
                if caps.get("root_access")
                else "[red]✗ No Root Access[/]"
            )
            cap_messages_styled.append(Text.from_markup(root_status))
            if not caps.get("root_access"):
                if magisk_on:
                    recommendations.append(
                        f"{device_id}: Root access is required for Magisk Property Spoofing."
                    )
                if needs_root_for_user_android_id:
                    recommendations.append(
                        f"{device_id}: Root access is required for 'Auto Set Random Android ID (User Profile)'."
                    )

        if magisk_on:  # Magisk specific checks (only if Magisk mode is enabled)
            if caps.get(
                "root_access"
            ):  # Only check Magisk if root is already confirmed
                magisk_status = (
                    "[green]✓ Magisk Available[/]"
                    if caps.get("magisk_available")
                    else "[orange3]~ Magisk Not Detected[/]"
                )
                cap_messages_styled.append(Text.from_markup(magisk_status))
                if not caps.get("magisk_available"):
                    recommendations.append(
                        f"{device_id}: Magisk was not detected (though root access seems present). Magisk Property Spoofing needs functional Magisk."
                    )
            # No need for an "else" for Magisk if no root, as root check above covers it.

        if (
            not cap_messages_styled and not recommendations
        ):  # Nothing relevant to display
            return

        self.console.print(
            f"🔍 Device Capabilities for [b]{device_id}[/b] (relevant to active modes):",
            style="bold cyan",
            highlight=False,
        )
        for msg_text in cap_messages_styled:
            self.console.print(Text("  ") + msg_text)  # Indent

        if recommendations:
            self.console.print("💡 Recommendations:", style="yellow", highlight=False)
            for rec_msg in recommendations:
                self.console.print(
                    Text.from_markup(f"  • {rec_msg}"), style="dim yellow"
                )
        self.console.rule(style="dim cyan")

    def get_connected_devices(self):
        try:
            self._log_message("\n📱 Device Detection & Capability Scan", "bold blue")
            if self.console:
                self.console.rule(style="blue")

            direct_adb_cmd = [
                self.adb_path,
                "devices",
                "-l",
            ]  # -l for more detailed output
            res_devices = subprocess.run(
                direct_adb_cmd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            if res_devices.returncode != 0:
                err_msg = f"Failed to get device list: {res_devices.stderr.strip() or res_devices.stdout.strip()}"
                self.errors.append(err_msg)
                self._log_message(f"✗ {err_msg}", "error")
                return []

            devices_list_found = []
            # Reset device capabilities for this scan
            # self.device_capabilities = {} # Reset at start of run() instead for persistence across selections

            lines = res_devices.stdout.strip().splitlines()
            if not (
                len(lines) <= 1 and "List of devices attached" in lines[0]
            ):  # Ensure there's device data
                for line in lines[1:]:  # Skip header "List of devices attached"
                    if (
                        "\t" in line or " device " in line
                    ):  # Match devices, not unauthorized/offline
                        parts = re.split(r"\s+", line.strip())  # Split by whitespace
                        if len(parts) >= 2 and parts[1].lower() == "device":
                            dev_id = parts[0].strip()
                            # Try to get more model info from -l output if available
                            model_info_from_l = ""
                            for part in parts:
                                if part.startswith("model:"):
                                    model_info_from_l = part.split(":", 1)[1]
                                elif part.startswith("product:"):
                                    model_info_from_l = (
                                        part.split(":", 1)[1]
                                        if not model_info_from_l
                                        else model_info_from_l
                                    )

                            dev_info_str = self.get_device_info_str(
                                dev_id, model_info_from_l
                            )  # Get detailed info string

                            # Scan capabilities if not already scanned in this session
                            if dev_id not in self.device_capabilities:
                                self._log_message(
                                    f"🔬 Scanning capabilities for {dev_id} ({dev_info_str})...",
                                    "debug",
                                    dim_style=True,
                                )
                                current_caps = (
                                    self.spoofing_manager.detect_capabilities(dev_id)
                                )
                                self.device_capabilities[dev_id] = (
                                    current_caps  # Store for later use
                                )

                            # Display summary based on current config and stored caps
                            self.display_capability_summary(
                                dev_id, self.device_capabilities[dev_id]
                            )

                            devices_list_found.append(
                                {"id": dev_id, "info": dev_info_str}
                            )

            if not devices_list_found:
                self._log_message(
                    "✗ No devices/emulators found or authorized. Ensure USB debugging is enabled and device is authorized.",
                    "yellow",
                )
            return devices_list_found
        except Exception as e:
            err_msg = f"Device detection error: {e}"
            self.errors.append(err_msg)
            self._log_message(f"✗ {err_msg}", "error")
            return []

    def get_device_info_str(self, device_id, model_hint=""):
        # Tries to get Model, Android Version, Build ID for a device
        try:

            def get_prop_fast(prop_name):
                if self.spoofing_manager:
                    # Use short timeout for these info props
                    res = self.spoofing_manager._run_adb_shell_command(
                        device_id, ["getprop", prop_name], timeout=3
                    )
                    return (
                        res.stdout.strip()
                        if res.returncode == 0 and res.stdout.strip()
                        else None
                    )
                return None

            model = get_prop_fast("ro.product.model") or model_hint or "Unknown Model"
            android_ver = get_prop_fast("ro.build.version.release") or "Unknown Version"
            build_id = get_prop_fast("ro.build.id") or "Unknown Build"
            return f"{model} (Android {android_ver}, Build: {build_id})"
        except Exception:  # Catchall if ADB fails during this
            return model_hint or "Unknown Device Info (error retrieving props)"

    def _prompt_interactive_selection(self, items_list, item_type_name, item_formatter_func):
        item_type_name_plural = item_type_name + ('s' if not item_type_name.endswith('s') else '')

        if not items_list:
            self._log_message(f"No {item_type_name_plural.lower()} available for selection.", "warning")
            return []

        if not QUESTIONARY_AVAILABLE:
            self._log_message(f"CRITICAL: 'questionary' library is required for interactive selection but is not installed. Please restart.", "error")
            return []

        header_title = f"\n🎯 {item_type_name} Selection"
        self._log_message(header_title, "bold blue")
        if self.console: self.console.rule(style="blue")
        
        try:
            choices = [
                questionary.Choice(
                    title=item_formatter_func(item),
                    value=item
                ) for item in items_list
            ]
            
            while True:
                # Show instructions for better UX
                if self.console:
                    self.console.print(
                        "💡 Use arrow keys to navigate, [space] to select/deselect, [a] to select all, [i] to invert, [enter] to confirm",
                        style="dim"
                    )
                
                selected_items = questionary.checkbox(
                    f"Select {item_type_name_plural.lower()}:",
                    choices=choices,
                    style=questionary.Style([
                        ('pointer', 'bold fg:yellow'),
                        ('highlighted', 'fg:white'),  # No special highlighting until selected
                        ('selected', 'fg:cyan bold')
                    ]),
                    # Using default instructions which are helpful
                ).ask()

                if selected_items is None:  # User pressed Ctrl+C
                    raise KeyboardInterrupt
                
                if selected_items:
                    # Log the successful selection for user feedback
                    self._log_message(f"✓ Selected {len(selected_items)} {item_type_name_plural.lower()}:", "success")
                    if self.console:
                        for item in selected_items:
                            self.console.print(f"  • {item_formatter_func(item)}")
                    return selected_items
                else:  # Empty list returned, user pressed Enter without selecting
                    # Give user clear guidance on what to do
                    if self.console:
                        self.console.print(
                            f"⚠️ No {item_type_name_plural.lower()} selected! Use [space] to select items, then [enter] to confirm.",
                            style="yellow"
                        )
                    
                    if not Confirm.ask(
                        f"Continue with no {item_type_name_plural.lower()} selected?",
                        default=False,
                        console=self.console
                    ):
                        # User wants to re-select, loop will continue
                        self.console.print("Please use spacebar to select items, then press Enter to confirm.", style="dim")
                        continue
                    else:
                        # User confirmed they want an empty selection
                        self._log_message(f"No {item_type_name_plural.lower()} selected.", "yellow")
                        return []
        except KeyboardInterrupt:
            self._log_message(f"\n{item_type_name} selection cancelled.", "yellow")
            return []

    def _prompt_single_selection(self, items_list, item_type_name, item_formatter_func):
        """Single selection that selects the highlighted item when Enter is pressed."""
        if not items_list:
            self._log_message(f"No {item_type_name.lower()} available for selection.", "warning")
            return None

        if not QUESTIONARY_AVAILABLE:
            self._log_message(f"CRITICAL: 'questionary' library is required for interactive selection but is not installed. Please restart.", "error")
            return None

        header_title = f"\n🎯 {item_type_name} Selection"
        self._log_message(header_title, "bold blue")
        if self.console: self.console.rule(style="blue")
        
        try:
            # Show instructions for better UX
            if self.console:
                self.console.print(
                    "💡 Use arrow keys to navigate, [enter] to select highlighted item",
                    style="dim"
                )
            
            choices = [
                questionary.Choice(
                    title=item_formatter_func(item),
                    value=item
                ) for item in items_list
            ]
            
            selected_item = questionary.select(
                f"Select {item_type_name.lower()}:",
                choices=choices,
                style=questionary.Style([
                    ('pointer', 'bold fg:yellow'),
                    ('highlighted', 'fg:yellow bold'),
                    ('selected', 'fg:cyan bold')
                ]),
            ).ask()

            if selected_item is None:  # User pressed Ctrl+C
                raise KeyboardInterrupt
                
            # Log the successful selection for user feedback
            self._log_message(f"✓ Selected {item_type_name.lower()}:", "success")
            if self.console:
                self.console.print(f"  • {item_formatter_func(selected_item)}")
            return [selected_item]  # Return as list for consistency with multi-selection
            
        except KeyboardInterrupt:
            self._log_message(f"\n{item_type_name} selection cancelled.", "yellow")
            return []

    def select_devices(self, devices_list_param):
        def formatter(dev_item):
            caps_str_parts = []
            user_profile_active = self.uniqueness_settings.get("enable_uniqueness_features", False)
            magisk_spoof_active = self.advanced_spoofing_settings.get("enable_magisk_resetprop", False)

            if (user_profile_active or magisk_spoof_active) and dev_item['id'] in self.device_capabilities:
                caps = self.device_capabilities[dev_item['id']]
                if user_profile_active:
                    caps_str_parts.append("Users" if caps.get("multiuser_support") else "NoUsers")
                    if self.advanced_spoofing_settings.get("use_ephemeral_users", True):
                        caps_str_parts.append("Eph" if caps.get("ephemeral_user_support") else "NoEph")
                
                needs_root_check = magisk_spoof_active or (user_profile_active and self.uniqueness_settings.get("auto_set_random_android_id", True))
                if needs_root_check:
                    caps_str_parts.append("Root" if caps.get("root_access") else "NoRoot")
                
                if magisk_spoof_active and caps.get("root_access"):
                    caps_str_parts.append("Magisk" if caps.get("magisk_available") else "NoMagisk")
            
            caps_display_str = f" (Caps: {', '.join(caps_str_parts)})" if caps_str_parts else ""
            return f"{dev_item['id']} - {dev_item['info']}{caps_display_str}"

        def print_additional_device_info():
            if not self.console: return
            active_modes_list = []
            if self.uniqueness_settings.get("enable_uniqueness_features", False):
                user_creation_type = ("Ephemeral User Profiles" if self.advanced_spoofing_settings.get("use_ephemeral_users", True) else "Permanent User Profiles")
                active_modes_list.append(f"[cyan]{user_creation_type}[/cyan]")
            if self.advanced_spoofing_settings.get("enable_magisk_resetprop", False):
                active_modes_list.append("[cyan]Magisk Property Spoofing[/cyan]")
            
            if active_modes_list:
                # Clean the markup for display - remove Rich tags for cleaner output
                clean_modes = []
                for mode in active_modes_list:
                    clean_mode = mode.replace("[cyan]", "").replace("[/cyan]", "")
                    clean_modes.append(clean_mode)
                self.console.print(f"ℹ️ Active Mode(s): {', '.join(clean_modes)}", style="cyan")

        print_additional_device_info()
        
        # Unified device selection interface
        if len(devices_list_param) == 1:
            # Only one device, auto-select it
            self._log_message(f"✓ Auto-selected single device:", "success")
            if self.console:
                self.console.print(f"  • {formatter(devices_list_param[0])}")
            return devices_list_param
        else:
            # Multiple devices - unified selection interface
            if self.console:
                self.console.print(
                    "💡 Use [Enter] to select highlighted device, or [Spacebar] to select multiple devices, then [Enter] to confirm",
                    style="dim"
                )
            
            return self._prompt_interactive_selection(devices_list_param, "Device", formatter)

    def find_apk_files(self):
        """Find APK, XAPK, APKM, and ZIP files in the configured directory."""
        try:
            self._log_message("\n📦 APK/XAPK/APKM/ZIP File Discovery", "bold blue")
            if self.console:
                self.console.rule(style="blue")

            apk_dir_path = Path(self.apk_directory)
            if not apk_dir_path.exists():
                try:
                    apk_dir_path.mkdir(parents=True)
                    self._log_message(
                        f"✓ Created APK directory: [i]{apk_dir_path.resolve()}[/i]",
                        "success",
                    )
                except OSError as e:
                    self.errors.append(
                        f"Failed to create APK directory '{apk_dir_path}': {e}"
                    )
                    self._log_message(f"✗ {self.errors[-1]}", "error")
                    return []  # Cannot proceed if APK dir cannot be created

            found_files_list = []
            for extension_pattern in ["*.apk", "*.xapk", "*.apkm", "*.zip"]:
                for file_path_obj in apk_dir_path.glob(extension_pattern):
                    try:
                        file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
                        file_type = (
                            "APKM"
                            if file_path_obj.suffix.lower() == ".apkm"
                            else "XAPK"
                            if file_path_obj.suffix.lower() == ".xapk"
                            else "ZIP"
                            if file_path_obj.suffix.lower() == ".zip"
                            else "APK"
                        )
                        found_files_list.append(
                            {
                                "path": str(file_path_obj.resolve()),
                                "name": file_path_obj.name,
                                "size": file_size_mb,
                                "type": file_type,
                            }
                        )
                    except (
                        FileNotFoundError
                    ):  # Should not happen with glob, but good practice
                        self._log_message(
                            f"⚠️ File {file_path_obj.name} disappeared during scan.",
                            "warning",
                        )

            if found_files_list:
                self._log_message(
                    f"✓ Found {len(found_files_list)} file(s) in '{apk_dir_path.resolve()}'",
                    "success",
                )
                # Sort by type (APK then XAPK then APKM then ZIP), then by name
                found_files_list.sort(key=lambda f: (f["type"], f["name"].lower()))
            else:
                msg = f"No APK, XAPK, APKM, or ZIP files found in '{apk_dir_path.resolve()}'. Place files there to install."
                self._log_message(f"✗ {msg}", "yellow")
            return found_files_list
        except Exception as e:
            err_msg = f"File discovery error in '{self.apk_directory}': {e}"
            self.errors.append(err_msg)
            self._log_message(f"✗ {err_msg}", "error")
            return []

    def select_apks(self, apk_files_list_param):
        def formatter(f_info):
            # Choose color style based on file type for display in questionary
            if f_info["type"] == "XAPK":
                color_class = "magenta"
            elif f_info["type"] == "APKM":
                color_class = "bright_magenta"
            elif f_info["type"] == "ZIP":
                color_class = "yellow"
            else:  # APK
                color_class = "cyan"
            # Using Rich Text for display in the log after selection
            return f"[{f_info['type']}] {f_info['name']} ({f_info['size']:.1f} MB)"

        def print_additional_apk_info():
            if self.console:
                self.console.print(
                    "💡 Note: XAPK, APKM, and ZIP files will be processed for base, split APKs, and OBB files if present.",
                    style="dim"
                )

        # Display list of found files *before* the interactive prompt
        if self.console:
            self._log_message("Available files:", "yellow")
            for f_data in apk_files_list_param:
                 if f_data["type"] == "XAPK": color_style = "magenta"
                 elif f_data["type"] == "APKM": color_style = "bright_magenta"
                 elif f_data["type"] == "ZIP": color_style = "yellow"
                 else: color_style = "cyan"
                 # Use direct styling instead of markup to avoid display issues
                 self.console.print(f"  • {f_data['type']:<4} {f_data['name']} ({f_data['size']:.1f} MB)", style=color_style)

        print_additional_apk_info()
        
        # Unified file selection interface
        if len(apk_files_list_param) == 1:
            # Only one file, auto-select it
            self._log_message(f"✓ Auto-selected single file:", "success")
            if self.console:
                self.console.print(f"  • {formatter(apk_files_list_param[0])}")
            return apk_files_list_param
        else:
            # Multiple files - unified selection interface
            if self.console:
                self.console.print(
                    "💡 Use [Enter] to select highlighted file, or [Spacebar] to select multiple files, then [Enter] to confirm",
                    style="dim"
                )
            
            return self._prompt_interactive_selection(apk_files_list_param, "APK/XAPK/APKM/ZIP File", formatter)

    def confirm_installation(self, selected_devices_list, selected_files_list):
        self._log_message("\n📋 Installation Summary", "bold blue")
        if self.console:
            self.console.rule(style="blue")

        self.console.print(
            f"Devices ({len(selected_devices_list)}):",
            style="bold yellow",
            highlight=False,
        )
        for dev_data in selected_devices_list:
            self.console.print(
                f"  • {dev_data['id']} - {dev_data['info']}",
                style="cyan",
                highlight=False,
            )

        self.console.print(
            f"\nFiles ({len(selected_files_list)}):",
            style="bold yellow",
            highlight=False,
        )
        for f_data in selected_files_list:
            # Choose color style based on file type
            if f_data["type"] == "XAPK":
                color_style = "magenta"
            elif f_data["type"] == "APKM":
                color_style = "bright_magenta"  # Slightly different color for APKM
            elif f_data["type"] == "ZIP":
                color_style = "yellow"  # Yellow for ZIP files
            else:  # APK
                color_style = "cyan"
            # Use direct styling instead of markup to avoid display issues
            self.console.print(f"  • {f_data['type']:<4} {f_data['name']} ({f_data['size']:.1f} MB)", style=color_style)

        total_install_ops = len(selected_devices_list) * len(selected_files_list)
        self.console.print(
            f"\nTotal installations to perform: {total_install_ops}",
            style="bold magenta",
            highlight=False,
        )

        # Display active spoofing modes
        active_spoof_modes_display = []
        if self.uniqueness_settings.get("enable_uniqueness_features", False):
            user_type_for_display = (
                "Ephemeral User Profiles"
                if self.advanced_spoofing_settings.get("use_ephemeral_users", True)
                else "Permanent User Profiles"
            )
            active_spoof_modes_display.append(user_type_for_display)
        if self.advanced_spoofing_settings.get("enable_magisk_resetprop", False):
            mfg_target = self.advanced_spoofing_settings.get(
                "spoof_manufacturer", "random"
            ).capitalize()
            active_spoof_modes_display.append(
                f"Magisk Property Spoofing (Target: {mfg_target})"
            )

        if active_spoof_modes_display:
            self.console.print(
                f"\n⚠️ Active Spoofing Mode(s): {', '.join(active_spoof_modes_display)}",
                style="bold yellow",
                highlight=False,
            )

        # Confirmation prompt
        if self.console:
            return Confirm.ask(
                "\nProceed with installation(s)?",
                default=True,
                console=self.console,
            )
        else:  # Basic input
            while True:
                choice = (
                    input("\nProceed with installation(s)? (y/n, default y): ")
                    .strip()
                    .lower()
                    or "y"
                )
                if choice in ["y", "yes"]:
                    return True
                if choice in ["n", "no"]:
                    return False
                print("Invalid input. Please enter 'y' or 'n'.")

    def install_obb_files(
        self,
        device_dict,
        obb_files_path_list,
        package_name_str,
        target_user_id_str=None,
    ):
        # device_dict: {'id': ..., 'info': ...}
        # obb_files_path_list: list of local full paths to OBB files
        # package_name_str: e.g., "com.example.app"
        # target_user_id_str: string user ID, or None for current/default

        if not obb_files_path_list:  # No OBB files to install
            return True
        if not package_name_str or package_name_str == "unknown_package":
            err_msg = f"✗ Cannot install OBBs for {device_dict['id']}: Package name is unknown."
            self.errors.append(err_msg)
            self._log_message(err_msg, "error")
            return False

        # Determine OBB directory on device for the target user
        obb_dir_on_device_path = self.spoofing_manager.get_obb_path_for_user(
            target_user_id_str, package_name_str
        )

        user_log_context = (
            f" for user {target_user_id_str}"
            if target_user_id_str and str(target_user_id_str) != "0"
            else ""
        )
        self._log_message(
            f"  📁 Creating OBB directory: {obb_dir_on_device_path} on {device_dict['id']}{user_log_context}",
            "debug",
            dim_style=True,
        )

        # Create OBB directory (adb shell mkdir -p /path/to/obb/dir)
        # This command should generally not require root unless permissions are very restrictive.
        mkdir_cmd_list = ["mkdir", "-p", obb_dir_on_device_path]
        mkdir_res = self.spoofing_manager._run_adb_shell_command(
            device_dict["id"], mkdir_cmd_list
        )
        if mkdir_res.returncode != 0:
            # Try with root if non-root failed and root is available
            caps = self.device_capabilities.get(
                device_dict["id"]
            ) or self.spoofing_manager.detect_capabilities(device_dict["id"])
            if caps.get("root_access"):
                mkdir_res = self.spoofing_manager._run_adb_shell_command(
                    device_dict["id"], mkdir_cmd_list, as_root=True
                )

            if mkdir_res.returncode != 0:  # If still fails
                self._log_message(
                    f"  ⚠️ Could not create OBB dir {obb_dir_on_device_path} (Error: {mkdir_res.stderr.strip() or mkdir_res.stdout.strip()}). "
                    "OBB copy might fail.",
                    "warning",
                )

        # Push each OBB file
        all_obb_copied_successfully = True
        for obb_local_full_path_str in obb_files_path_list:
            obb_local_file = Path(obb_local_full_path_str)
            target_obb_path_on_device = (
                obb_dir_on_device_path.rstrip("/") + "/" + obb_local_file.name
            )

            push_status_msg = f"[bold cyan]  Copying OBB {obb_local_file.name} to {device_dict['id']}{user_log_context}..."
            adb_push_cmd = [
                self.adb_path,
                "-s",
                device_dict["id"],
                "push",
                str(obb_local_file),
                target_obb_path_on_device,
            ]

            push_res = None
            if self.console:
                with self.console.status(push_status_msg, spinner="earth"):
                    push_res = subprocess.run(
                        adb_push_cmd,
                        capture_output=True,
                        text=True,
                        timeout=600,  # Long timeout for large OBBs
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                    )
            else:  # Basic print
                print(
                    push_status_msg.replace("[bold cyan]", "").replace(
                        "[/bold cyan]", ""
                    )
                )
                push_res = subprocess.run(
                    adb_push_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )

            if push_res.returncode != 0:
                err_detail = (
                    push_res.stdout.strip() + " " + push_res.stderr.strip()
                ).strip()
                err_log_msg = f"✗ Failed to copy OBB {obb_local_file.name} to {device_dict['id']}{user_log_context}: {err_detail}"
                self.errors.append(err_log_msg)
                self._log_message(err_log_msg, "error")
                all_obb_copied_successfully = False
                break  # Stop if one OBB fails
            else:
                self._log_message(
                    f"  ✓ Copied OBB {obb_local_file.name} to {device_dict['id']}{user_log_context}",
                    "success",
                    dim_style=True,
                )

        return all_obb_copied_successfully

    def _uninstall_app(
        self,
        device_id_str,
        package_name_str,
        app_name_for_log_str,
        target_user_id_str=None,
    ):
        if not package_name_str or package_name_str == "unknown_package":
            msg = f"⚠️ Cannot uninstall '{app_name_for_log_str}' from {device_id_str}: Package name is unknown."
            self._log_message(msg, "warning")
            return False  # Cannot proceed without package name

        uninstall_cmd_base = [self.adb_path, "-s", device_id_str, "uninstall"]
        user_log_context_part = ""

        # Add --user flag if a specific user is targeted for uninstall
        # Note: `adb uninstall <pkg>` usually uninstalls for all users unless --user is specified.
        # If target_user_id_str is provided, we assume uninstallation only for that user.
        if target_user_id_str:
            uninstall_cmd_base.extend(["--user", str(target_user_id_str)])
            user_log_context_part = f" for user {target_user_id_str}"

        uninstall_cmd_base.append(package_name_str)  # Add package name to uninstall

        status_msg_uninstall = f"[bold yellow]  Uninstalling existing '{app_name_for_log_str}' ({package_name_str}) from {device_id_str}{user_log_context_part}..."

        try:
            uninstall_res = None
            if self.console:
                with self.console.status(status_msg_uninstall, spinner="moon"):
                    uninstall_res = subprocess.run(
                        uninstall_cmd_base,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                    )
            else:  # Basic print
                print(
                    status_msg_uninstall.replace("[bold yellow]", "").replace(
                        "[/bold yellow]", ""
                    )
                )
                uninstall_res = subprocess.run(
                    uninstall_cmd_base,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )

            output_combined = (
                uninstall_res.stdout.strip() + " " + uninstall_res.stderr.strip()
            ).strip()

            if (
                uninstall_res.returncode == 0 and "Success" in uninstall_res.stdout
            ):  # Explicit success
                self._log_message(
                    f"  ✓ Uninstalled '{app_name_for_log_str}' from {device_id_str}{user_log_context_part}.",
                    "success",
                    dim_style=True,
                )
                return True

            # Check for common "not installed" messages which are not failures for this operation's intent
            if (
                "Failure [not installed for user" in output_combined
                or (
                    "DELETE_FAILED_INTERNAL_ERROR" in output_combined
                    and "does not exist" in output_combined.lower()
                )
                or (f"Package {package_name_str} is not installed" in output_combined)
            ):
                self._log_message(
                    f"  ℹ️ '{app_name_for_log_str}' was not found/installed on {device_id_str}{user_log_context_part}.",
                    "debug",
                    dim_style=True,
                )
                return True  # Effectively uninstalled as it's not there

            # Actual failure
            self.errors.append(
                f"✗ Failed to uninstall '{app_name_for_log_str}' from {device_id_str}{user_log_context_part}: {output_combined}"
            )
            self._log_message(
                f"✗ Failed to uninstall '{app_name_for_log_str}': {output_combined}",
                "error",
            )
            return False
        except Exception as e_uninst:  # Catch timeouts or other subprocess errors
            self.errors.append(
                f"✗ Exception during uninstall of '{app_name_for_log_str}': {e_uninst}"
            )
            self._log_message(
                f"✗ Exception during uninstall of '{app_name_for_log_str}': {e_uninst}",
                "error",
            )
            return False

    def _install_apk_set(
        self,
        device_dict,  # {'id': ..., 'info': ...}
        apk_paths_list_to_install,  # List of full local paths to APKs (base + splits)
        package_name_str,  # Package name, can be "unknown_package"
        app_name_for_log_str,  # Display name for logging
        attempt_num=1,
        target_user_id_str=None,  # String user ID, or None
    ):
        if not apk_paths_list_to_install:
            return "NO_APKS_PROVIDED", f"No APKs provided for '{app_name_for_log_str}'."

        # Base ADB command parts
        cmd_install_base = [self.adb_path, "-s", device_dict["id"]]
        action_verb = (
            "install-multiple" if len(apk_paths_list_to_install) > 1 else "install"
        )
        cmd_install_base.append(action_verb)

        # Add user-specific arguments if a target user is defined
        cmd_install_base.extend(
            self.spoofing_manager.get_install_command_args_for_user(target_user_id_str)
        )

        # Add common install flags
        if self.config.getboolean("OPTIONS", "replace_existing", fallback=True):
            cmd_install_base.append("-r")  # Reinstall if already exists
        if self.always_allow_downgrade:
            cmd_install_base.append("-d")  # Allow version downgrade
        if self.config.getboolean("OPTIONS", "auto_grant_permissions", fallback=True):
            # Check device SDK for -g flag (Android 6.0 / SDK 23+)
            dev_caps = self.device_capabilities.get(
                device_dict["id"]
            ) or self.spoofing_manager.detect_capabilities(device_dict["id"])
            if dev_caps.get("android_sdk_version", 0) >= 23:
                cmd_install_base.append("-g")  # Grant all runtime permissions

        # Add APK paths to the command
        final_install_cmd = cmd_install_base + apk_paths_list_to_install

        apk_desc_for_log = (
            Path(apk_paths_list_to_install[0]).name
            if len(apk_paths_list_to_install) == 1
            else f"splits from '{app_name_for_log_str}'"
        )
        user_log_context_install = (
            f" (User {target_user_id_str})"
            if target_user_id_str and str(target_user_id_str) != "0"
            else ""
        )

        status_msg_install_progress = f"[bold green]  Installing {apk_desc_for_log} to {device_dict['id']}{user_log_context_install} (Attempt {attempt_num})..."

        try:
            install_res = None
            if self.console:
                with self.console.status(
                    status_msg_install_progress, spinner="bouncingBar"
                ):
                    install_res = subprocess.run(
                        final_install_cmd,
                        capture_output=True,
                        text=True,
                        timeout=900,  # 15 min timeout for large apps
                        check=False,
                        encoding="utf-8",
                        errors="replace",
                    )
            else:  # Basic print
                print(
                    status_msg_install_progress.replace("[bold green]", "").replace(
                        "[/bold green]", ""
                    )
                )
                install_res = subprocess.run(
                    final_install_cmd,
                    capture_output=True,
                    text=True,
                    timeout=900,
                    check=False,
                    encoding="utf-8",
                    errors="replace",
                )

            output_detail_combined = (
                install_res.stdout.strip() + " " + install_res.stderr.strip()
            ).strip()

            if install_res.returncode == 0 and "Success" in install_res.stdout:
                return "SUCCESS", "Installation successful."

            # Handle common conflict errors that might be resolved by uninstalling
            conflict_error_codes = [
                "INSTALL_FAILED_ALREADY_EXISTS",
                "INSTALL_FAILED_UPDATE_INCOMPATIBLE",
                "INSTALL_FAILED_VERSION_DOWNGRADE",  # Should be rare if -d is used, but some ROMs are picky
                "INSTALL_FAILED_SHARED_USER_INCOMPATIBLE",
            ]
            is_conflict_error = any(
                err_code in output_detail_combined for err_code in conflict_error_codes
            )

            if (
                is_conflict_error
                and self.prompt_uninstall_on_conflict
                and package_name_str
                and package_name_str != "unknown_package"
                and attempt_num == 1
            ):  # Only prompt on first attempt
                self._log_message(
                    f"⚠️ Installation of '{app_name_for_log_str}' failed due to conflict: {output_detail_combined}",
                    "warning",
                )
                prompt_text_uninstall = f"Uninstall existing '{app_name_for_log_str}' ({package_name_str}) from {device_dict['id']}{user_log_context_install} and retry installation?"

                do_uninstall_and_retry = False
                if self.console:
                    do_uninstall_and_retry = Confirm.ask(
                        Text.from_markup(f"[yellow]{prompt_text_uninstall}[/yellow]"),
                        default=False,
                        console=self.console,
                    )
                else:
                    u_choice = (
                        input(f"{prompt_text_uninstall} (y/n, default n): ")
                        .strip()
                        .lower()
                        or "n"
                    )
                    do_uninstall_and_retry = u_choice == "y"

                if do_uninstall_and_retry:
                    if self._uninstall_app(
                        device_dict["id"],
                        package_name_str,
                        app_name_for_log_str,
                        target_user_id_str,
                    ):
                        self._log_message(
                            f"✅ Retrying install of '{app_name_for_log_str}' after uninstall...",
                            "success",
                        )
                        # Recursive call for retry, increment attempt_num
                        return self._install_apk_set(
                            device_dict,
                            apk_paths_list_to_install,
                            package_name_str,
                            app_name_for_log_str,
                            attempt_num + 1,
                            target_user_id_str,
                        )
                    else:  # Uninstall failed
                        return (
                            "UNINSTALL_FAILED",
                            f"Uninstall of '{app_name_for_log_str}' failed. Original install error: {output_detail_combined}",
                        )
                else:  # User chose not to uninstall
                    return (
                        "USER_SKIPPED_UNINSTALL",
                        f"User skipped uninstall. Original install error: {output_detail_combined}",
                    )

            # Specific error categorization
            if "INSTALL_FAILED_MISSING_SPLIT" in output_detail_combined:
                return "MISSING_SPLIT", output_detail_combined
            if "INSTALL_FAILED_INVALID_APK" in output_detail_combined:
                return "INVALID_APK", output_detail_combined
            if "INSTALL_FAILED_INSUFFICIENT_STORAGE" in output_detail_combined:
                return "INSUFFICIENT_STORAGE", output_detail_combined
            # Add more specific error checks as needed

            return (
                "GENERAL_FAILURE",
                output_detail_combined,
            )  # Generic failure if not caught above

        except subprocess.TimeoutExpired:
            return (
                "TIMEOUT",
                f"Install of {apk_desc_for_log} to {device_dict['id']}{user_log_context_install} timed out after 900s.",
            )
        except Exception as e_inst:  # Catchall for other subprocess or logic errors
            return (
                "EXCEPTION",
                f"Exception during install of {apk_desc_for_log} to {device_dict['id']}{user_log_context_install}: {e_inst}",
            )

    def _install_single_apk_file(
        self, device_dict, apk_file_data, target_user_id_str=None
    ):
        # apk_file_data: {'name': ..., 'path': ..., 'type': 'APK', ...}
        apk_name_log = apk_file_data["name"]
        apk_local_path = apk_file_data["path"]

        # Try to get package name for better conflict resolution
        package_name_val = (
            self.get_package_name_from_apk(apk_local_path) or "unknown_package"
        )

        user_log_ctx = (
            f" (User {target_user_id_str})"
            if target_user_id_str and str(target_user_id_str) != "0"
            else ""
        )
        self._log_message(
            f"💿 Installing APK: {apk_name_log} to {device_dict['id']}{user_log_ctx}",
            "bold cyan",
        )

        install_status_code, install_detail_msg = self._install_apk_set(
            device_dict,
            [apk_local_path],
            package_name_val,
            apk_name_log,
            target_user_id_str=target_user_id_str,
        )

        if install_status_code == "SUCCESS":
            success_log_msg = (
                f"✓ '{apk_name_log}' installed to {device_dict['id']}{user_log_ctx}"
            )
            self.successes.append(success_log_msg)
            self._log_message(success_log_msg, "success")
            return True
        else:
            # Clarify MISSING_SPLIT for single APKs
            error_explanation = install_detail_msg
            if install_status_code == "MISSING_SPLIT":
                error_explanation += " (This often means the single APK file is a base APK that requires additional split APKs which were not provided alongside it. Ensure you have the complete set of APKs if this is part of a split application.)"

            err_log_msg_final = f"✗ Failed to install '{apk_name_log}' to {device_dict['id']}{user_log_ctx}: {error_explanation} (Status Code: {install_status_code})"
            # Avoid duplicate error logging if _install_apk_set already logged due to unhandled conflict
            if not any(
                install_detail_msg in e and apk_name_log in e and device_dict["id"] in e
                for e in self.errors
            ):
                self.errors.append(err_log_msg_final)

            # Log to console if not a user-interactive part (like skipped uninstall)
            if install_status_code not in [
                "USER_SKIPPED_UNINSTALL",
                "UNINSTALL_FAILED",
            ]:
                self._log_message(err_log_msg_final, "error")
            return False

    def _install_bundle_file(
        self, device_dict, bundle_file_data, target_user_id_str=None
    ):
        # bundle_file_data: {'name': ..., 'path': ..., 'type': 'XAPK'/'APKM'/'ZIP', ...}
        bundle_name_log = bundle_file_data["name"]
        bundle_type = bundle_file_data["type"]  # Either 'XAPK', 'APKM', or 'ZIP'
        user_log_ctx = (
            f" (User {target_user_id_str})"
            if target_user_id_str and str(target_user_id_str) != "0"
            else ""
        )

        self._log_message(
            f"🔧 Processing {bundle_type}: {bundle_name_log} for {device_dict['id']}{user_log_ctx}",
            "bold cyan",
        )

        # Use the same extraction method for XAPK, APKM, and ZIP files
        # All are ZIP archives with similar structure
        extracted_bundle_data = self.extract_xapk(bundle_file_data["path"])
        if not extracted_bundle_data:  # Extraction failed
            # Error already logged by extract_xapk
            return False

        device_current_props = self.get_device_properties(device_dict["id"])
        package_name_from_bundle = extracted_bundle_data["package_name"]
        app_display_name = extracted_bundle_data.get(
            "app_name", bundle_name_log
        )  # Use manifest name if available

        # Select initial set of APKs based on device properties and manifest
        apks_to_install_initial_set = self.select_apks_for_installation(
            extracted_bundle_data["all_apk_files"],
            device_current_props,
            extracted_bundle_data["manifest"],
            extracted_bundle_data["extract_dir"],
        )
        if not apks_to_install_initial_set:
            err_msg_no_apks = f"✗ No suitable APKs found in {bundle_type} '{app_display_name}' for {device_dict['id']}{user_log_ctx} based on device profile."
            self.errors.append(err_msg_no_apks)
            self._log_message(err_msg_no_apks, "error")
            return False

        # Attempt to install the selected set of APKs
        install_status_code, install_detail_msg = self._install_apk_set(
            device_dict,
            apks_to_install_initial_set,
            package_name_from_bundle,
            app_display_name,
            1,
            target_user_id_str,
        )
        apk_installation_successful = install_status_code == "SUCCESS"

        # If MISSING_SPLIT occurs, and retry is enabled, try installing ALL APKs from the bundle
        if (
            install_status_code == "MISSING_SPLIT"
            and self.retry_with_all_apks_on_missing_split
        ):
            self._log_message(
                f"⚠️ '{app_display_name}': Install failed with MISSING_SPLIT. "
                f"Retrying with ALL {len(extracted_bundle_data['all_apk_files'])} APKs from {bundle_type}...",
                "warning",
            )
            # Sort all APKs with base first if identifiable
            all_apks_sorted_for_retry = sorted(
                extracted_bundle_data["all_apk_files"],
                key=lambda p: (
                    Path(p).name.lower() != "base.apk",
                    Path(p).name.lower(),
                ),  # base.apk first
            )

            if (
                all_apks_sorted_for_retry
                and all_apks_sorted_for_retry != apks_to_install_initial_set
            ):  # Ensure it's a different set
                status_retry, detail_retry = self._install_apk_set(
                    device_dict,
                    all_apks_sorted_for_retry,
                    package_name_from_bundle,
                    app_display_name,
                    2,
                    target_user_id_str,  # Increment attempt number
                )
                apk_installation_successful = status_retry == "SUCCESS"
                if (
                    not apk_installation_successful
                ):  # Update status if retry also failed
                    install_status_code, install_detail_msg = status_retry, detail_retry
            else:
                self._log_message(
                    f"ℹ️ Retry for '{app_display_name}' not attempted: APK set for retry is same as initial or empty.",
                    "debug",
                    dim_style=True,
                )

        # Handle final APK installation outcome
        if not apk_installation_successful:
            final_err_msg_apk_install = f"✗ Failed to install APKs from {bundle_type} '{app_display_name}' to {device_dict['id']}{user_log_ctx}: {install_detail_msg} (Final Status: {install_status_code})"
            if not any(
                install_detail_msg in e
                and app_display_name in e
                and device_dict["id"] in e
                for e in self.errors
            ):
                self.errors.append(final_err_msg_apk_install)
            if install_status_code not in [
                "USER_SKIPPED_UNINSTALL",
                "UNINSTALL_FAILED",
            ]:  # Avoid re-logging user choice
                self._log_message(
                    f"✗ Final error for '{app_display_name}' APKs: {install_detail_msg}",
                    "error",
                )

        # If APKs installed successfully, proceed to OBB installation
        if apk_installation_successful:
            obb_installation_successful = True  # Assume success if no OBBs
            if extracted_bundle_data["obb_files"]:
                self._log_message(
                    f"  📦 Installing {len(extracted_bundle_data['obb_files'])} OBB file(s) for '{app_display_name}'...",
                    "info",
                )
                if not self.install_obb_files(
                    device_dict,
                    extracted_bundle_data["obb_files"],
                    package_name_from_bundle,
                    target_user_id_str,
                ):
                    obb_installation_successful = False  # Mark OBB install as failed

            # Log final success for bundle (APKs + OBBs)
            obb_status_str = ""
            if extracted_bundle_data[
                "obb_files"
            ]:  # Only add OBB status if OBBs were present
                obb_status_str = (
                    " + OBBs" if obb_installation_successful else " + OBBs (issues)"
                )

            final_bundle_success_msg = f"✓ '{app_display_name}' (APKs{obb_status_str}) installed to {device_dict['id']}{user_log_ctx}"
            self.successes.append(final_bundle_success_msg)
            self._log_message(
                final_bundle_success_msg,
                "success" if obb_installation_successful else "yellow",
            )  # Yellow if OBBs had issues
            return True  # Overall bundle installation considered successful if APKs are in, even if OBBs fail (as app might run)

        return False  # APK installation part of bundle failed

    def install_apk_or_xapk(self, device_dict, file_info_dict, target_user_id_str=None):
        # device_dict: {'id': ..., 'info': ...}
        # file_info_dict: {'name': ..., 'path': ..., 'type': 'APK'/'XAPK'/'APKM'/'ZIP', ...}
        # target_user_id_str: string user ID, or None for current/default

        if file_info_dict["type"] == "APK":
            return self._install_single_apk_file(
                device_dict, file_info_dict, target_user_id_str
            )
        elif file_info_dict["type"] in ["XAPK", "APKM", "ZIP"]:
            return self._install_bundle_file(
                device_dict, file_info_dict, target_user_id_str
            )
        else:  # Should not happen if find_apk_files is correct
            err_msg_unknown_type = f"✗ Unknown file type for {file_info_dict['name']}: {file_info_dict['type']}"
            self.errors.append(err_msg_unknown_type)
            self._log_message(err_msg_unknown_type, "error")
            return False

    def show_device_installation_summary(
        self, device_id_str, successes_on_device_count, failures_on_device_count
    ):
        total_ops_on_device = successes_on_device_count + failures_on_device_count
        if total_ops_on_device == 0:
            return  # Nothing to summarize for this device

        user_context_summary_str = ""
        # Check if User Profile Spoofing was active for this device
        if (
            self.spoofing_manager
            and device_id_str in self.spoofing_manager.active_spoofed_users
        ):
            user_profile_data = self.spoofing_manager.active_spoofed_users[
                device_id_str
            ]
            user_type_display = (
                "Ephemeral" if user_profile_data.get("is_ephemeral") else "Standard"
            )
            user_context_summary_str = f" (User Profile: {user_type_display} {user_profile_data['user_id']} '{user_profile_data['user_name']}')"
        # Check if Magisk Spoofing was active (even if no user profile spoofing)
        elif self.advanced_spoofing_settings.get("enable_magisk_resetprop", False):
            # Check if Magisk was actually usable on this device
            dev_caps = self.device_capabilities.get(device_id_str, {})
            if dev_caps.get("root_access") and dev_caps.get("magisk_available"):
                user_context_summary_str = (
                    " (Magisk Property Spoofing was active for current user)"
                )

        summary_text_markup = (
            f"Device [b]{device_id_str}[/b]{user_context_summary_str}: "
        )
        if successes_on_device_count == total_ops_on_device:
            summary_text_markup += (
                f"[green]All {total_ops_on_device} successful.[/green]"
            )
        elif successes_on_device_count > 0:  # Partial success
            summary_text_markup += f"[yellow]{successes_on_device_count}/{total_ops_on_device} successful, {failures_on_device_count} failed.[/yellow]"
        else:  # All failed
            summary_text_markup += f"[red]All {failures_on_device_count} failed.[/red]"

        if self.console:
            self.console.print(Text.from_markup(summary_text_markup))
            self.console.rule(style="dim")  # Separator after each device summary
        else:  # Basic print
            print(re.sub(r"\[/?\w+.*?\]", "", summary_text_markup) + "\n" + "-" * 40)

    def install_selected_apks(self, selected_devices_list, selected_files_info_list):
        self._log_message("\n🚀 Installation Process", "bold blue")
        if self.console:
            self.console.rule(style="blue")

        total_operations_planned = len(selected_devices_list) * len(
            selected_files_info_list
        )
        overall_successful_operations_count = 0

        # Track stats per device for summary
        device_installation_stats = {
            dev["id"]: {"successes": 0, "failures": 0} for dev in selected_devices_list
        }

        # Determine active global spoofing modes from config
        user_profile_spoofing_globally_on = self.uniqueness_settings.get(
            "enable_uniqueness_features", False
        )
        magisk_property_spoofing_globally_on = self.advanced_spoofing_settings.get(
            "enable_magisk_resetprop", False
        )
        # User wants permanent users if use_ephemeral_users is false
        create_permanent_users_preference = not self.advanced_spoofing_settings.get(
            "use_ephemeral_users", True
        )

        for dev_idx, device_data_dict in enumerate(selected_devices_list):
            current_device_id_val = device_data_dict["id"]
            target_user_id_for_this_device_installs = (
                None  # Default to current/owner user
            )

            # Get device capabilities (should be pre-scanned)
            device_specific_caps = self.device_capabilities.get(
                current_device_id_val, {}
            )

            # --- Apply Magisk Property Spoofing (if enabled globally and device supports it) ---
            if magisk_property_spoofing_globally_on:
                if device_specific_caps.get("root_access") and device_specific_caps.get(
                    "magisk_available"
                ):
                    mfg_key_cfg = self.advanced_spoofing_settings.get(
                        "spoof_manufacturer", "samsung"
                    )
                    model_name_cfg = self.advanced_spoofing_settings.get(
                        "spoof_model", ""
                    )
                    android_ver_key_cfg = self.advanced_spoofing_settings.get(
                        "spoof_android_version", "13"
                    )
                    self.spoofing_manager.apply_device_spoofing(
                        current_device_id_val,
                        mfg_key_cfg,
                        model_name_cfg,
                        android_ver_key_cfg,
                    )
                else:
                    self._log_message(
                        f"  Skipping Magisk Property Spoofing for {current_device_id_val} (device lacks Root/Magisk).",
                        "debug",
                        dim_style=True,
                    )

            # --- User Profile Spoofing (if enabled globally) ---
            if user_profile_spoofing_globally_on:
                if device_specific_caps.get("multiuser_support"):
                    # create_user_profile takes a flag: True for permanent, False for ephemeral (if supported)
                    new_user_profile_data = self.spoofing_manager.create_user_profile(
                        current_device_id_val,
                        create_permanent_user_flag=create_permanent_users_preference,
                    )
                    if (
                        new_user_profile_data
                        and new_user_profile_data.get("user_id") is not None
                    ):
                        target_user_id_for_this_device_installs = str(
                            new_user_profile_data["user_id"]
                        )
                        user_type_log_str = (
                            "Permanent"
                            if create_permanent_users_preference
                            or not new_user_profile_data.get("is_ephemeral")
                            else "Ephemeral"
                        )
                        self._log_message(
                            f"✅ Installations for {current_device_id_val} will target new {user_type_log_str} user: "
                            f"{target_user_id_for_this_device_installs} ('{new_user_profile_data.get('user_name', 'N/A')}')",
                            "success",
                        )
                        # Delay after new user setup before installations
                        post_user_delay_sec = self.config.getint(
                            "UNIQUENESS",
                            "post_new_user_install_delay_seconds",
                            fallback=10,
                        )
                        if post_user_delay_sec > 0:
                            self._log_message(
                                f"  ⏳ Waiting {post_user_delay_sec}s for new user environment on {current_device_id_val} to settle...",
                                "debug",
                                dim_style=True,
                            )
                            time.sleep(post_user_delay_sec)
                    else:  # Failed to create/switch to spoofed user
                        msg_user_fail = f"⚠️ Failed to setup spoofed user profile for {current_device_id_val}. Installations will target current/default user."
                        self.errors.append(
                            f"{current_device_id_val}: User profile creation failed."
                        )  # Add to main errors
                        self._log_message(msg_user_fail, "warning")
                else:  # Multi-user not supported on device
                    self._log_message(
                        f"  Skipping User Profile Spoofing for {current_device_id_val} (device lacks multi-user support).",
                        "debug",
                        dim_style=True,
                    )

            # Construct user context string for logging installation lines
            log_context_parts = []
            if target_user_id_for_this_device_installs:  # If a new user was created
                user_profile_active_data = (
                    self.spoofing_manager.active_spoofed_users.get(
                        current_device_id_val, {}
                    )
                )
                active_user_type_str = (
                    "Ephemeral"
                    if user_profile_active_data.get("is_ephemeral")
                    else "Permanent"
                )
                log_context_parts.append(
                    f"User: {active_user_type_str} {target_user_id_for_this_device_installs}"
                )
            else:  # Default user
                log_context_parts.append("User: default/current")

            if (
                magisk_property_spoofing_globally_on
                and device_specific_caps.get("root_access")
                and device_specific_caps.get("magisk_available")
            ):
                log_context_parts.append("[Magisk Spoofed]")
            user_context_for_install_log = (
                f"({', '.join(log_context_parts)})" if log_context_parts else ""
            )

            # Log device header if multiple devices
            if len(selected_devices_list) > 1:
                dev_header_text = f"\n--- Device {dev_idx + 1}/{len(selected_devices_list)}: [b]{current_device_id_val}[/b] {user_context_for_install_log} ---"
                if self.console:
                    self.console.print(
                        Text.from_markup(dev_header_text),
                        style="bold yellow",
                        highlight=False,
                    )
                else:
                    print(re.sub(r"\[/?\w+.*?\]", "", dev_header_text))

            # Iterate through files for this device
            for file_idx, file_data_item in enumerate(selected_files_info_list):
                # Log file header if multiple files or devices
                if len(selected_files_info_list) > 1 or len(selected_devices_list) > 1:
                    file_header_text = (
                        f"\n--- File {file_idx + 1}/{len(selected_files_info_list)}: [cyan]{file_data_item['name']}[/cyan] "
                        f"on [b]{current_device_id_val}[/b] {user_context_for_install_log} ---"
                    )
                    if self.console:
                        self.console.print(
                            Text.from_markup(file_header_text), highlight=False
                        )
                    else:
                        print(re.sub(r"\[/?\w+.*?\]", "", file_header_text))

                install_op_successful = self.install_apk_or_xapk(
                    device_data_dict,
                    file_data_item,
                    target_user_id_for_this_device_installs,
                )

                if install_op_successful:
                    overall_successful_operations_count += 1
                    device_installation_stats[current_device_id_val]["successes"] += 1
                else:
                    device_installation_stats[current_device_id_val]["failures"] += 1

                # Rule line after each file install if more files/devices remain
                if self.console and (
                    len(selected_files_info_list) > 1
                    or (
                        len(selected_devices_list) > 1
                        and file_idx < len(selected_files_info_list) - 1
                    )
                ):
                    self.console.rule(style="dim")

            # Show summary for this device after all its files are processed
            self.show_device_installation_summary(
                current_device_id_val,
                device_installation_stats[current_device_id_val]["successes"],
                device_installation_stats[current_device_id_val]["failures"],
            )

        return overall_successful_operations_count, total_operations_planned

    def _provide_error_suggestions(self):
        if not self.errors or not self.console:
            return  # Only show suggestions if console is available

        error_text_combined_lower = " ".join(self.errors).lower()
        suggestions_list = []

        # General ADB/Device issues
        if (
            "device not found" in error_text_combined_lower
            or "device offline" in error_text_combined_lower
        ):
            suggestions_list.append(
                "Ensure device is connected, USB debugging enabled, and authorized. Device might have disconnected (e.g., during user switch or long operation)."
            )
        if "timeout" in error_text_combined_lower:
            suggestions_list.append(
                "Operation timed out. Check device responsiveness and USB connection stability. Increase timeouts in config if needed for very slow operations."
            )
        if any(
            s in error_text_combined_lower
            for s in [
                "storage",
                "insufficient",
                "enospc",
                "install_failed_insufficient_storage",
            ]
        ):
            suggestions_list.append(
                "Device is low on storage. Free up space on the device's internal storage."
            )
        if any(
            s in error_text_combined_lower
            for s in ["permission", "denied", "securityexception"]
        ):
            suggestions_list.append(
                "Permission denied by Android system. This can happen if device is locked during sensitive operations (like user switch), or if ADB lacks necessary permissions. For root operations, ensure ADB shell has root."
            )

        # Installation specific
        if "install_failed_version_downgrade" in error_text_combined_lower:
            suggestions_list.append(
                "Version downgrade failed. Ensure 'always_allow_downgrade=true' in config.ini. Some ROMs might still block downgrades."
            )
        if "install_failed_missing_split" in error_text_combined_lower:
            suggestions_list.append(
                "INSTALL_FAILED_MISSING_SPLIT: The app requires additional split APKs not found or not correctly selected. For single APKs, this means the file is incomplete. For XAPKs/ZIPs, ensure it's packaged correctly or try enabling retry with all APKs."
            )
        if "install_failed_invalid_apk" in error_text_combined_lower:
            suggestions_list.append(
                "INSTALL_FAILED_INVALID_APK: The APK file is corrupted, not a valid APK, or not compatible with the device architecture."
            )

        # User Profile Spoofing
        user_profile_on_cfg = self.uniqueness_settings.get(
            "enable_uniqueness_features", False
        )
        if user_profile_on_cfg and any(
            s in error_text_combined_lower
            for s in ["user", "multi-user", "failed to create user", "switch user"]
        ):
            user_type_cfg = (
                "Ephemeral (Android 8+)"
                if self.advanced_spoofing_settings.get("use_ephemeral_users", True)
                else "Permanent"
            )
            suggestions_list.append(
                f"{user_type_cfg} user creation/switching failed. Check device's multi-user support (Settings > System > Multiple Users), ensure device is unlocked. "
                "If hitting user limits, enable 'Bypass User Limits (Root)' in config. Some devices have strict limits or require longer delays after user switch (see 'post_new_user_install_delay_seconds' in config.ini)."
            )

        # Magisk/Root Spoofing
        magisk_on_cfg = self.advanced_spoofing_settings.get(
            "enable_magisk_resetprop", False
        )
        if magisk_on_cfg and any(
            s in error_text_combined_lower
            for s in ["root", "magisk", "resetprop", "failed to set prop"]
        ):
            suggestions_list.append(
                "Magisk/Root operation failed. Ensure device is properly rooted with Magisk, Magisk is operational, and ADB shell can gain root access via 'su'. "
                "Check Magisk logs. Some properties might be protected by the ROM even with root."
            )
        if (
            "failed to set ro.product.model" in error_text_combined_lower
        ):  # Specific known issue
            suggestions_list.append(
                "Failed to set 'ro.product.model': This specific property can be highly protected by the Android system at runtime. Changes might not stick or require a Magisk module to set at boot time."
            )

        if (
            "ephemeral" in error_text_combined_lower
            and "not supported" in error_text_combined_lower
        ):
            suggestions_list.append(
                "Ephemeral users require Android 8.0 (SDK 26+). If 'Use Ephemeral Users' is on but device is older, script should fall back to standard users."
            )

        # Pattern file related
        if (
            "failed to load device patterns" in error_text_combined_lower
            or "key 'props_to_spoof' not found" in error_text_combined_lower
        ):
            suggestions_list.append(
                f"Issue with '{DEVICE_PATTERNS_FILE}'. Ensure it's valid JSON. If unsure, delete it to allow the script to regenerate a default version or use internal comprehensive defaults."
            )

        unique_suggestions_final = list(
            dict.fromkeys(suggestions_list)
        )  # Remove duplicates
        if unique_suggestions_final:
            self.console.print(
                "\n🔧 Specific Error Suggestions:", style="cyan", highlight=False
            )
            for s_idx, suggestion_text in enumerate(unique_suggestions_final):
                self.console.print(
                    f"  {s_idx + 1}. {suggestion_text}", style="dim cyan"
                )

    def show_summary(self, successful_ops_count, total_ops_count):
        self._log_message("\n📊 Installation Summary", "bold blue")
        if self.console:
            self.console.rule(style="blue")
            self.console.print(
                "=" * 80, style="blue"
            )  # Extra separator for visual grouping
        else:  # Basic print
            print("=" * 80)

        # Determine overall status title
        title_style_str, title_text_str = (
            "bold blue on black",
            "ℹ️ APK INSTALLER SESSION ENDED - NO OPERATIONS PERFORMED ℹ️",
        )
        if total_ops_count > 0:  # If operations were attempted
            if not self.errors and successful_ops_count == total_ops_count:
                title_style_str, title_text_str = (
                    "bold green on black",
                    "🎉 APK INSTALLER COMPLETED SUCCESSFULLY 🎉",
                )
            elif (
                successful_ops_count > 0 and self.errors
            ):  # Partial success with errors
                title_style_str, title_text_str = (
                    "bold yellow on black",
                    "PARTIALLY SUCCESSFUL - COMPLETED WITH SOME ERRORS",
                )
            elif self.errors:  # All failed or ops attempted but all failed with errors
                title_style_str, title_text_str = (
                    "bold red on black",
                    "⚠️ APK INSTALLER COMPLETED WITH ERRORS ⚠️",
                )
        elif (
            self.errors
        ):  # No ops, but other errors occurred (e.g. ADB fail, config fail)
            title_style_str, title_text_str = (
                "bold red on black",
                "⚠️ APK INSTALLER ENCOUNTERED ERRORS BEFORE OPERATIONS ⚠️",
            )

        if self.console:
            self.console.print(title_text_str, style=title_style_str, justify="center")
        else:  # Basic centered print
            clean_title = (
                title_text_str.replace("🎉", "")
                .replace("⚠️", "")
                .replace("ℹ️", "")
                .strip()
            )
            padding = (80 - len(clean_title)) // 2
            print(f"{'':<{padding}}{clean_title}")

        if self.console:
            self.console.print("=" * 80, style="blue")
        else:
            print("=" * 80)

        # Print success/failure counts
        if total_ops_count > 0:
            if successful_ops_count == total_ops_count and not self.errors:
                msg_overall = f"[SUCCESS] All {total_ops_count}/{total_ops_count} operations completed successfully."
                self._log_message(msg_overall, "bold green")
            elif successful_ops_count > 0:
                msg_overall = f"[PARTIAL SUCCESS] {successful_ops_count}/{total_ops_count} operations completed successfully."
                self._log_message(msg_overall, "bold yellow")
            else:  # successful_ops_count == 0 and total_ops_count > 0
                msg_overall = (
                    f"[FAILURE] 0/{total_ops_count} operations completed successfully."
                )
                self._log_message(msg_overall, "bold red")

        if self.successes:
            self._log_message(
                "\n[INFO] Successful installations/operations (Details):", "bold blue"
            )
            for s_msg_item in self.successes:
                self._log_message(f"  {s_msg_item}", "success")

        if self.errors:
            self._log_message(
                f"\n[ERROR] {len(self.errors)} error(s) encountered overall.",
                "bold red",
            )
            self._log_message("[INFO] Error details:", "bold blue")
            unique_errors_logged = set()
            for e_msg_item in self.errors:
                if e_msg_item not in unique_errors_logged:  # Log each unique error once
                    self._log_message(f"  {e_msg_item}", "error")
                    unique_errors_logged.add(e_msg_item)
            self._provide_error_suggestions()  # Show suggestions based on collected errors

        elif (
            total_ops_count == 0 and not self.successes
        ):  # No ops, no errors, no successes
            self._log_message(
                "No installation operations were performed in this session.", "dim"
            )

        if self.console:
            self.console.print("=" * 80, style="blue")
        else:
            print("=" * 80)

    def ask_restart(self):
        self._log_message("\n🔄 Session Complete", "bold blue")
        if self.console:
            return Confirm.ask(
                Text.from_markup(
                    "[green]Perform another installation session?[/green]"
                ),
                default=False,
                console=self.console,
            )
        else:  # Basic input
            while True:
                choice = (
                    input("Perform another installation session? (y/n, default n): ")
                    .strip()
                    .lower()
                    or "n"
                )
                if choice in ["y", "yes"]:
                    return True
                if choice in ["n", "no"]:
                    return False
                print("Invalid input. Please enter 'y' or 'n'.")

    def _get_spoofing_options_map(self):
        # Central definition of spoofing options for table display and interaction
        mfg_keys = (
            list(self.spoofing_manager.device_manufacturers_patterns.keys())
            if self.spoofing_manager
            else ["samsung", "google"]
        )
        android_ver_keys = (
            list(self.spoofing_manager.android_version_release_map.keys())
            if self.spoofing_manager
            else ["13", "14"]
        )

        # Structure: (ID, Category, Description, Config_Section, Config_Key, Type (bool/str), Notes/Choices)
        return [
            (
                "1",
                "User Profile",
                "Enable User Profile Spoofing",
                "UNIQUENESS",
                "enable_uniqueness_features",
                "bool",
                "Multi-user support needed",
            ),
            (
                "2",
                "User Profile",
                "Use Ephemeral Users (if supported)",
                "ADVANCED_SPOOFING",
                "use_ephemeral_users",
                "bool",
                "User Profiles ON, Android 8+",
            ),
            (
                "3",
                "User Profile",
                "Auto Set Random Android ID",
                "UNIQUENESS",
                "auto_set_random_android_id",
                "bool",
                "User Profiles ON, Root",
            ),
            (
                "4",
                "User Profile",
                "Cleanup Profile After Session",
                "UNIQUENESS",
                "cleanup_user_profile_after_session",
                "bool",
                "User Profiles ON",
            ),
            (
                "5",
                "User Profile",
                "Auto Switch Back to Owner",
                "UNIQUENESS",
                "auto_switch_back_to_owner",
                "bool",
                "User Profiles ON",
            ),
            (
                "6",
                "User Profile",
                "Bypass User Limits (Root)",
                "ADVANCED_SPOOFING",
                "bypass_user_limits",
                "bool",
                "User Profiles ON, Root",
            ),
            (
                "7",
                "Magisk Spoof",
                "Enable Magisk Properties",
                "ADVANCED_SPOOFING",
                "enable_magisk_resetprop",
                "bool",
                "Root, Magisk needed",
            ),
            (
                "8",
                "Magisk Spoof",
                "Backup Original Properties",
                "ADVANCED_SPOOFING",
                "backup_original_properties",
                "bool",
                "Magisk Spoofing ON",
            ),
            (
                "9",
                "Magisk Spoof",
                "Spoof Android ID (Current User)",
                "ADVANCED_SPOOFING",
                "spoof_android_id_magisk",
                "bool",
                "Magisk Spoofing ON, Root",
            ),
            (
                "10",
                "Magisk Spoof",
                "Spoof Target Manufacturer",
                "ADVANCED_SPOOFING",
                "target_manufacturer",
                "str",
                f"Magisk Spoofing ON, choices: {', '.join(mfg_keys[:5])}...",
            ),
            (
                "11",
                "Magisk Spoof",
                "Spoof Target Model",
                "ADVANCED_SPOOFING",
                "target_model",
                "str",
                "Magisk Spoofing ON, varies by manufacturer",
            ),
            (
                "12",
                "Magisk Spoof",
                "Spoof Target Android Version",
                "ADVANCED_SPOOFING",
                "target_android_version",
                "str",
                f"Magisk Spoofing ON, choices: {', '.join(android_ver_keys[:5])}...",
            ),
            (
                "13",
                "Magisk Spoof",
                "Apply Random Fingerprint",
                "ADVANCED_SPOOFING",
                "apply_random_fingerprint",
                "bool",
                "Magisk Spoofing ON, Random selection",
            ),
            (
                "14",
                "Magisk Spoof",
                "Restore After Session",
                "ADVANCED_SPOOFING",
                "restore_after_session",
                "bool",
                "Magisk Spoofing ON, Auto-restore",
            ),
            (
                "15",
                "Magisk Spoof",
                "Comprehensive Cleanup",
                "ADVANCED_SPOOFING",
                "comprehensive_cleanup",
                "bool",
                "Magisk Spoofing ON, Full cleanup",
            ),
            (
                "16",
                "Phone Tools",
                "Enable Clipboard Service",
                "PHONE_TOOLS",
                "enable_clipboard_service",
                "bool",
                "Sets clipboard sync service",
            ),
            (
                "17",
                "Phone Tools",
                "Set Device Clipboard",
                "PHONE_TOOLS",
                "set_device_clipboard",
                "bool",
                "Copies text to device clipboard",
            ),
            (
                "18",
                "Phone Tools",
                "Manage User Profiles",
                "PHONE_TOOLS",
                "manage_user_profiles",
                "bool",
                "List and remove user profiles",
            ),
        ]

    def _collect_config_values_from_options(self, options_list):
        """Collect configuration values from user interaction with options."""
        config_changes = {}
        
        for option_tuple in options_list:
            option_id, category, description, config_section, config_key, value_type, notes = option_tuple
            
            current_value = self.config.get(config_section, config_key, fallback="false" if value_type == "bool" else "")
            
            if value_type == "bool":
                new_value = Confirm.ask(
                    f"[{option_id}] {description}",
                    default=current_value.lower() == "true",
                    console=self.console
                )
                config_changes[f"{config_section}.{config_key}"] = str(new_value).lower()
            else:
                new_value = Prompt.ask(
                    f"[{option_id}] {description}",
                    default=current_value,
                    console=self.console
                )
                config_changes[f"{config_section}.{config_key}"] = new_value
        
        return config_changes

    def _display_configuration_menu(self):
        """Display interactive configuration menu for spoofing options."""
        if not self.console:
            self._log_message("Configuration menu requires Rich console interface", "error")
            return False
        
        options = self._get_spoofing_options_map()
        
        # Create table for display
        table = Table(title="🔧 Advanced Spoofing Configuration", box=box.ROUNDED)
        table.add_column("ID", style="cyan", width=3)
        table.add_column("Category", style="magenta", width=12)
        table.add_column("Description", style="green", width=30)
        table.add_column("Current", style="yellow", width=8)
        table.add_column("Notes", style="dim", width=25)
        
        for option_tuple in options:
            option_id, category, description, config_section, config_key, value_type, notes = option_tuple
            current_value = self.config.get(config_section, config_key, fallback="false" if value_type == "bool" else "")
            
            if value_type == "bool":
                current_display = "✓" if current_value.lower() == "true" else "✗"
            else:
                current_display = current_value[:8] + "..." if len(current_value) > 8 else current_value
            
            table.add_row(option_id, category, description, current_display, notes)
        
        self.console.print(table)
        self.console.print("\n[bold]Configuration Options:[/bold]")
        self.console.print("• [cyan]all[/cyan] - Configure all options interactively")
        self.console.print("• [cyan]<number>[/cyan] - Configure specific option")
        self.console.print("• [cyan]quit[/cyan] - Exit configuration menu")
        
        while True:
            choice = Prompt.ask(
                "\nEnter option (all/number/quit)",
                default="quit",
                console=self.console
            ).strip().lower()
            
            if choice == "quit":
                return True
            elif choice == "all":
                config_changes = self._collect_config_values_from_options(options)
                self._apply_config_changes(config_changes)
                self._log_message("✓ Configuration updated successfully", "success")
                return True
            else:
                try:
                    option_num = int(choice)
                    selected_option = None
                    for option_tuple in options:
                        if option_tuple[0] == str(option_num):
                            selected_option = option_tuple
                            break
                    
                    if selected_option:
                        config_changes = self._collect_config_values_from_options([selected_option])
                        self._apply_config_changes(config_changes)
                        self._log_message(f"✓ Option {option_num} configured successfully", "success")
                    else:
                        self._log_message(f"Invalid option number: {option_num}", "error")
                except ValueError:
                    self._log_message(f"Invalid input: {choice}", "error")

    def _apply_config_changes(self, config_changes):
        """Apply configuration changes to the config object."""
        for full_key, value in config_changes.items():
            section, key = full_key.split(".", 1)
            if not self.config.has_section(section):
                self.config.add_section(section)
            self.config.set(section, key, value)

    def _show_phone_management_tools_menu(self):
        """Display phone management tools menu."""
        if not self.console:
            self._log_message("Phone management tools require Rich console interface", "error")
            return False
        
        while True:
            self.console.print("\n[bold cyan]📱 Phone Management Tools[/bold cyan]")
            self.console.print("1. Set Device Clipboard")
            self.console.print("2. Enable Clipboard Service")
            self.console.print("3. Manage User Profiles")
            self.console.print("4. Back to Main Menu")
            
            choice = Prompt.ask(
                "Select option",
                choices=["1", "2", "3", "4"],
                default="4",
                console=self.console
            )
            
            if choice == "1":
                self._set_device_clipboard_tool()
            elif choice == "2":
                self._enable_clipboard_service_tool()
            elif choice == "3":
                self._manage_user_profiles_tool()
            elif choice == "4":
                break

    def _set_device_clipboard_tool(self):
        """Tool to set text on device clipboard.
        
        NOTE: This feature requires either:
        1. A third-party clipboard app like 'Clipper' (uses 'am broadcast -a clipper.set')
        2. Android 10+ with appropriate permissions for clipboard access
        
        Standard Android does not provide direct clipboard access via ADB.
        """
        self._log_message("⚠️  IMPORTANT: This clipboard feature requires a third-party app like 'Clipper' to be installed on the device.", "warning")
        self._log_message("Standard Android does not allow direct clipboard access via ADB commands.", "warning")
        
        if not Confirm.ask("Do you want to continue anyway?", default=False, console=self.console):
            return
        
        devices = self.get_connected_devices()
        if not devices:
            self._log_message("No connected devices found", "error")
            return
        
        selected_device = self.select_devices(devices)
        if not selected_device:
            return
        
        device_id = selected_device[0]["id"]
        
        text = Prompt.ask(
            "Enter text to set on device clipboard",
            console=self.console
        )
        
        if not text:
            return
        
        try:
            # Try standard clipboard service first (Android 10+)
            std_cmd = ["cmd", "clipboard", "put", text]
            result = self.spoofing_manager._run_adb_shell_command(
                device_id, std_cmd, timeout=10
            )
            
            if result and result.returncode == 0:
                self._log_message(f"✓ Clipboard set on device {device_id} (standard method)", "success")
                return
            
            # Fallback to third-party clipper app
            self._log_message("Standard clipboard method failed, trying third-party 'Clipper' app...", "info")
            
            clipper_cmd = [
                "am", "broadcast",
                "-a", "clipper.set",
                "-e", "text", text
            ]
            
            result = self.spoofing_manager._run_adb_shell_command(
                device_id, clipper_cmd, timeout=10
            )
            
            if result and result.returncode == 0:
                self._log_message(f"✓ Clipboard set on device {device_id} (Clipper app)", "success")
            else:
                self._log_message(f"✗ Failed to set clipboard on device {device_id}. Make sure 'Clipper' app is installed.", "error")
                self._log_message("Install from: https://play.google.com/store/apps/details?id=dk.mathiasfranz.clipper", "info")
                
        except Exception as e:
            self._log_message(f"✗ Error setting clipboard: {str(e)}", "error")

    def _enable_clipboard_service_tool(self):
        """Tool to attempt enabling clipboard service on device.
        
        NOTE: The 'clipboard_service_enabled' setting is not a standard Android setting.
        This function will try several approaches to enable clipboard functionality.
        """
        self._log_message("⚠️  IMPORTANT: Standard Android does not have a 'clipboard_service_enabled' setting.", "warning")
        self._log_message("This tool will attempt various methods to enable clipboard functionality.", "warning")
        
        devices = self.get_connected_devices()
        if not devices:
            self._log_message("No connected devices found", "error")
            return
        
        selected_device = self.select_devices(devices)
        if not selected_device:
            return
        
        device_id = selected_device[0]["id"]
        
        try:
            # Check Android version first
            version_result = self.spoofing_manager._run_adb_shell_command(
                device_id, ["getprop", "ro.build.version.sdk"], timeout=5
            )
            
            sdk_version = 0
            if version_result and version_result.returncode == 0:
                try:
                    sdk_version = int(version_result.stdout.strip())
                except ValueError:
                    pass
            
            self._log_message(f"Device Android SDK version: {sdk_version}", "info")
            
            if sdk_version >= 29:  # Android 10+
                self._log_message("Android 10+ detected. Clipboard access should work via 'cmd clipboard' commands.", "success")
                
                # Test if clipboard service is available
                test_result = self.spoofing_manager._run_adb_shell_command(
                    device_id, ["cmd", "clipboard", "get"], timeout=5
                )
                
                if test_result and test_result.returncode == 0:
                    self._log_message("✓ Clipboard service is already working on this device", "success")
                else:
                    self._log_message("⚠️  Clipboard service test failed. This may be due to device restrictions.", "warning")
            else:
                self._log_message(f"Android {sdk_version} detected. Native clipboard access not available via ADB.", "warning")
                self._log_message("Consider installing a third-party clipboard app like 'Clipper'.", "info")
            
            # Try the non-standard setting anyway (in case it's a custom ROM)
            self._log_message("Attempting to set non-standard clipboard_service_enabled setting...", "info")
            
            custom_cmd = [
                "settings", "put", "secure",
                "clipboard_service_enabled", "1"
            ]
            
            result = self.spoofing_manager._run_adb_shell_command(
                device_id, custom_cmd, timeout=10
            )
            
            if result and result.returncode == 0:
                self._log_message(f"✓ Non-standard clipboard setting applied on device {device_id}", "success")
                self._log_message("Note: This setting may not have any effect on standard Android.", "warning")
            else:
                self._log_message(f"✗ Failed to apply non-standard clipboard setting", "error")
                
        except Exception as e:
            self._log_message(f"✗ Error checking clipboard service: {str(e)}", "error")

    def _manage_user_profiles_tool(self):
        """Tool to manage user profiles on device."""
        devices = self.get_connected_devices()
        if not devices:
            self._log_message("No connected devices found", "error")
            return
        
        selected_device = self.select_devices(devices)
        if not selected_device:
            return
        
        device_id = selected_device[0]["id"]
        
        try:
            # Get list of users
            result = self.spoofing_manager._run_adb_shell_command(
                device_id, ["pm", "list", "users"], timeout=10
            )
            
            if not result or result.returncode != 0:
                self._log_message("Failed to get user list", "error")
                return
            
            users = []
            for line in result.stdout.splitlines():
                if "UserInfo{" in line:
                    # Parse user info
                    user_match = re.search(r'UserInfo\{(\d+):([^:]+):', line)
                    if user_match:
                        user_id = user_match.group(1)
                        user_name = user_match.group(2)
                        is_owner = "FLAG_PRIMARY" in line
                        users.append({
                            "id": user_id,
                            "name": user_name,
                            "is_owner": is_owner
                        })
            
            if not users:
                self._log_message("No users found", "error")
                return
            
            # Display users
            table = Table(title=f"User Profiles on {device_id}", box=box.ROUNDED)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type", style="yellow")
            
            for user in users:
                user_type = "Owner" if user["is_owner"] else "Profile"
                table.add_row(user["id"], user["name"], user_type)
            
            self.console.print(table)
            
            # Ask which users to remove
            removable_users = [u for u in users if not u["is_owner"]]
            if not removable_users:
                self._log_message("No removable user profiles found", "info")
                return
            
            user_choices = []
            for user in removable_users:
                if questionary and QUESTIONARY_AVAILABLE:
                    user_choices.append(questionary.Choice(
                        title=f"{user['name']} (ID: {user['id']})",
                        value=user['id']
                    ))
            
            if questionary and QUESTIONARY_AVAILABLE:
                selected_users = questionary.checkbox(
                    "Select users to remove:",
                    choices=user_choices
                ).ask()
                
                if selected_users:
                    confirm = Confirm.ask(
                        f"Remove {len(selected_users)} user profile(s)?",
                        default=False,
                        console=self.console
                    )
                    
                    if confirm:
                        for user_id in selected_users:
                            remove_result = self.spoofing_manager._run_adb_shell_command(
                                device_id, ["pm", "remove-user", user_id], timeout=30
                            )
                            
                            if remove_result and remove_result.returncode == 0:
                                self._log_message(f"✓ Removed user profile {user_id}", "success")
                            else:
                                self._log_message(f"✗ Failed to remove user profile {user_id}", "error")
            
        except Exception as e:
            self._log_message(f"✗ Error managing user profiles: {str(e)}", "error")

    def _show_spoofing_configuration_menu(self):
        """Show the spoofing configuration menu."""
        return self._display_configuration_menu()

    def _show_main_menu(self):
        """Display main menu and handle user selection."""
        if not self.console:
            return "1"  # Default to APK installation for non-interactive mode
        
        self.console.print("\n[bold cyan]🚀 Main Menu[/bold cyan]")
        self.console.print("1. Install APK/XAPK Files")
        self.console.print("2. Configure Spoofing Settings")
        self.console.print("3. Phone Management Tools")
        self.console.print("4. Exit")
        
        choice = Prompt.ask(
            "Select option",
            choices=["1", "2", "3", "4"],
            default="1",
            console=self.console
        )
        
        return choice

    def run(self):
        """Main application loop."""
        while True:
            self.print_banner()
            
            if not self.verify_adb():
                self._log_message("ADB verification failed", "error")
                if not self.ask_restart():
                    break
                continue
            
            # Load configuration
            self.load_config()
            
            # Show main menu
            choice = self._show_main_menu()
            
            if choice == "1":
                # APK Installation
                self._run_installation_workflow()
            elif choice == "2":
                # Spoofing Configuration
                self._show_spoofing_configuration_menu()
            elif choice == "3":
                # Phone Management Tools
                self._show_phone_management_tools_menu()
            elif choice == "4":
                # Exit
                break
            
            if not self.ask_restart():
                break
        
        self.cleanup_temp_files()
        self._log_message("Application closed", "info")

    def _run_installation_workflow(self):
        """Run the APK installation workflow."""
        devices = self.get_connected_devices()
        if not devices:
            self._log_message("No connected devices found", "error")
            return
        
        files = self.find_apk_files()
        if not files:
            self._log_message("No APK files found", "error")
            return
        
        selected_devices = self.select_devices(devices)
        if not selected_devices:
            return
        
        selected_files = self.select_apks(files)
        if not selected_files:
            return
        
        if not self.confirm_installation(selected_devices, selected_files):
            return
        
        successful, failed = self.install_selected_apks(selected_devices, selected_files)
        self.show_summary(successful, successful + failed)
        
        # Cleanup
        for device in selected_devices:
            if self.spoofing_manager:
                self.spoofing_manager.comprehensive_cleanup(device["id"], prompt_user=True)



def check_and_install_dependencies():
    """Check for and install required dependencies."""
    dependencies = [
        ("rich", "rich"),
        ("pyaxmlparser", "pyaxmlparser"),
        ("questionary", "questionary")
    ]
    
    missing_deps = []
    
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
        except ImportError:
            missing_deps.append(package_name)
    
    if missing_deps:
        print("Missing dependencies detected. Installing:")
        for dep in missing_deps:
            print(f"  - {dep}")
        
        try:
            import subprocess
            import sys
            
            for dep in missing_deps:
                print(f"Installing {dep}...")
                result = subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                                      capture_output=True, text=True)
                if result.returncode != 0:
                    print(f"Failed to install {dep}: {result.stderr}")
                    return False
                else:
                    print(f"✓ {dep} installed successfully")
            
            print("All dependencies installed successfully!")
            return True
            
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False
    
    return True


def main():
    """Main entry point of the application."""
    if not check_and_install_dependencies():
        return 1
    
    installer = InteractiveAPKInstaller()
    try:
        installer.run()
        return 0
    except KeyboardInterrupt:
        if installer.console: 
            installer.console.print("\\nProgram interrupted.", "yellow")
        else:
            print("\\nProgram interrupted.")
        return 1
    except Exception as e:
        if installer.console:
            installer.console.print(f"Error: {e}", "red")
        else:
            print(f"Error: {e}")
        return 1
    finally:
        installer.cleanup_temp_files()
        if installer.console:
            if sys.stdin.isatty(): 
                input("\\nPress Enter to exit.")


if __name__ == "__main__":
    sys.exit(main())
