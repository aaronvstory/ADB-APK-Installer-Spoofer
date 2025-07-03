#!/usr/bin/env python3
"""
Professional APK Installation Tool - v4.1.0 "Phoenix"
- Merged Features: Combines the best of v3.5.0 and v4.0.0.
- New Feature: Automatic dependency installer for rich, pyaxmlparser, questionary.
- New Feature: Interactive multi-selection menu for APKs/devices via `questionary`.
- Restored: Full interactive spoofing configuration menu from v3.5.0.
- Restored: "Phone Management Tools" menu with clipboard setter.
- Restored: Robust installation logic with detailed error parsing and uninstall-on-conflict prompts.
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

# --- Constants ---
DEVICE_PATTERNS_FILE = "device_patterns.json"
SCRIPT_VERSION = "v4.1.0"


# --- BEGIN DeviceSpoofingManager (From v3.5.0 - Mature & Complete) ---
class DeviceSpoofingManager:
    """Manages advanced device spoofing capabilities with enhanced validation and patterns."""

    COMPREHENSIVE_DEFAULT_PROPS_TO_SPOOF = [
        "ro.product.brand", "ro.product.manufacturer", "ro.product.model", "ro.product.name",
        "ro.product.device", "ro.product.board", "ro.build.fingerprint", "ro.vendor.build.fingerprint",
        "ro.system.build.fingerprint", "ro.odm.build.fingerprint", "ro.build.id", "ro.build.display.id",
        "ro.build.version.incremental", "ro.build.version.release", "ro.build.version.sdk",
        "ro.serialno", "ro.boot.serialno", "ro.build.description", "ro.build.type", "ro.build.tags",
        "ro.build.host", "ro.build.user", "ro.build.date", "ro.build.date.utc",
        "ro.miui.ui.version.name", "ro.miui.ui.version.code"
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
        self.device_manufacturers_patterns = self.patterns_data.get("manufacturers", self._get_default_manufacturers_patterns())
        self.android_version_release_map = self.patterns_data.get("android_versions", self._get_default_android_version_release_map())
        self.internal_sdk_map = self._get_default_internal_sdk_map()

    def _create_default_config_for_standalone(self):
        config = configparser.ConfigParser()
        config.add_section("UNIQUENESS")
        config.set("UNIQUENESS", "enable_uniqueness_features", "true")
        config.set("UNIQUENESS", "cleanup_user_profile_after_session", "true")
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

        config.add_section("SPOOF_VALIDATION")
        config.set("SPOOF_VALIDATION", "min_storage_mb", "500")
        config.set("SPOOF_VALIDATION", "check_multiuser_support", "true")
        config.set("SPOOF_VALIDATION", "validate_root_access", "true")
        config.set("SPOOF_VALIDATION", "require_unlocked_device", "true")
        return config
