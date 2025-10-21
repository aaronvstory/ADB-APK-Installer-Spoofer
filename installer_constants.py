#!/usr/bin/env python3
"""
APK Installer Constants - v4.5.2 "Odyssey"
Central configuration constants, patterns, and default values for the APK Installer suite.
"""

# --- Script Information ---
SCRIPT_VERSION = "v4.5.2"
DEVICE_PATTERNS_FILE = "device_patterns.json"
CONFIG_FILE_NAME = "apk_installer_config.ini"

# --- Default Configuration Sections ---
DEFAULT_CONFIG = {
    "PATHS": {
        "adb_path": "adb",
        "apk_directory": "apks",
    },
    "UNIQUENESS": {
        "enable_uniqueness_features": "true",
        "cleanup_user_profile_after_session": "false", 
        "auto_set_random_android_id": "true",
        "user_creation_retries": "3",
        "validate_user_switch": "true",
        "user_switch_initial_delay_seconds": "3",
        "validate_user_switch_timeout_seconds": "30",
        "user_switch_no_validation_delay_seconds": "5",
        "post_new_user_install_delay_seconds": "10",
    },
    "ADVANCED_SPOOFING": {
        "enable_magisk_resetprop": "true",
        "backup_original_properties": "true",
        "bypass_user_limits": "false",
        "use_ephemeral_users": "true",
        "spoof_manufacturer": "samsung",
        "spoof_model": "",
        "spoof_android_version": "13",
        "spoof_android_id_magisk": "true",
        "spoof_build_fingerprint": "true",
        "spoof_serial_number": "true",
        "spoof_device_model": "true",
        "spoof_android_version_props": "true",
        "auto_spoof_on_user_creation": "true",
        "restore_properties_after_session": "false",
        "restore_user_limits_after_session": "false",
    },
    "SPOOF_VALIDATION": {
        "min_storage_mb": "500",
        "check_multiuser_support": "true",
        "validate_root_access": "true",
        "require_unlocked_device": "true",
    },
    "FILE_DISCOVERY": {
        "allowed_extensions": "apk,xapk,apkm,zip",
        "search_subdirectories": "true",
        "exclude_temp_files": "true",
        "max_file_size_mb": "2048",
        "scan_timeout_seconds": "30",
    },
    "INSTALLATION": {
        "allow_downgrade": "false",
        "replace_existing": "false",
        "grant_runtime_permissions": "true",
        "installation_timeout_seconds": "300",
        "parallel_installations": "false",
        "retry_failed_installations": "true",
        "max_installation_retries": "2",
        "uninstall_on_conflict": "ask",
        "handle_obb_files": "true",
        "validate_apk_before_install": "true",
    },
    "LOGGING": {
        "enable_rich_output": "true",
        "log_adb_commands": "false", 
        "verbose_installation_logs": "true",
        "save_session_logs": "false",
        "log_file_path": "apk_installer.log",
    },
}

# --- ASCII Banner ---
ASCII_BANNER = """
 █████╗ ██████╗ ██████╗     █████╗ ██████╗ ██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗   ██╔══██╗██╔══██╗██║ ██╔╝
███████║██║  ██║██████╔╝   ███████║██████╔╝█████╔╝
██╔══██║██║  ██║██╔══██╗   ██╔══██║██╔═══╝ ██╔═██╗
██║  ██║██████╔╝██████╔╝   ██║  ██║██║     ██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        Interactive APK Installation Tool
             v4.5.2 (Odyssey)
"""

# --- Default Device Manufacturers Patterns ---
DEFAULT_MANUFACTURERS_PATTERNS = {
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
                "hardware": "slider",
            },
        ],
        "build_id_patterns": {"13": ["TQ1A", "TQ2A"], "14": ["UQ1A", "UD1A"]},
        "serial_pattern": "{8}{8}",
        "serial_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    },
    "xiaomi": {
        "brand": "xiaomi",
        "manufacturer": "Xiaomi",
        "models": [
            {
                "product": "venus",
                "device": "venus",
                "model": "M2011K2G",
                "board": "kona",
                "display_name": "Mi 11",
                "hardware": "qcom",
            },
            {
                "product": "marble",
                "device": "marble",
                "model": "2211133C",
                "board": "taro",
                "display_name": "13 Pro",
                "hardware": "qcom",
            },
        ],
        "build_id_patterns": {"13": ["TQ1A", "TQ2A"], "14": ["UQ1A", "UD1A"]},
        "serial_pattern": "{10}",
        "serial_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    },
    "oneplus": {
        "brand": "oneplus",
        "manufacturer": "OnePlus",
        "models": [
            {
                "product": "OnePlus11",
                "device": "OP5915L1",
                "model": "CPH2449",
                "board": "kalama",
                "display_name": "OnePlus 11",
                "hardware": "qcom",
            },
            {
                "product": "OnePlus10Pro",
                "device": "OP515BL1",
                "model": "NE2213",
                "board": "lahaina",
                "display_name": "OnePlus 10 Pro",
                "hardware": "qcom",
            },
        ],
        "build_id_patterns": {"13": ["TP1A", "TQ1A"], "14": ["UP1A", "UQ1A"]},
        "serial_pattern": "{16}",
        "serial_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    },
    "oppo": {
        "brand": "oppo",
        "manufacturer": "OPPO",
        "models": [
            {
                "product": "OP4F2FL1",
                "device": "OP4F2F",
                "model": "CPH2423",
                "board": "kalama",
                "display_name": "Find X6 Pro",
                "hardware": "qcom",
            },
        ],
        "build_id_patterns": {"13": ["TP1A", "TQ1A"], "14": ["UP1A", "UQ1A"]},
        "serial_pattern": "{15}",
        "serial_chars": "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
    },
}

# --- Spoofing Options Map for Configuration Menu ---
SPOOFING_OPTIONS_MAP = {
    "enable_uniqueness_features": {
        "section": "UNIQUENESS",
        "description": "Enable User Profile Management",
        "type": "boolean",
        "default": "true",
    },
    "enable_magisk_resetprop": {
        "section": "ADVANCED_SPOOFING", 
        "description": "Enable Magisk Property Spoofing",
        "type": "boolean",
        "default": "true",
    },
    "auto_spoof_on_user_creation": {
        "section": "ADVANCED_SPOOFING",
        "description": "Auto-apply Device Spoofing for New Users", 
        "type": "boolean",
        "default": "true",
    },
    "spoof_manufacturer": {
        "section": "ADVANCED_SPOOFING",
        "description": "Default Manufacturer for Spoofing",
        "type": "choice",
        "choices": ["samsung", "google", "xiaomi", "oneplus", "oppo"],
        "default": "samsung",
    },
    "spoof_android_version": {
        "section": "ADVANCED_SPOOFING", 
        "description": "Default Android Version for Spoofing",
        "type": "choice",
        "choices": ["13", "14"],
        "default": "13",
    },
}

# --- Default Android Version Release Map ---
DEFAULT_ANDROID_VERSION_RELEASE_MAP = {
    "13": {"release": "13", "sdk": 33},
    "14": {"release": "14", "sdk": 34},
    "12": {"release": "12", "sdk": 31},
    "11": {"release": "11", "sdk": 30},
    "10": {"release": "10", "sdk": 29},
}

# --- Default Internal SDK Map ---
DEFAULT_INTERNAL_SDK_MAP = {
    33: "13",
    34: "14", 
    31: "12",
    30: "11",
    29: "10",
}

# --- Spoofing Options Map ---
SPOOFING_OPTIONS_MAP = {
    "enable_magisk_resetprop": {
        "display_name": "Enable Magisk resetprop",
        "description": "Use Magisk's resetprop for property modification",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "enable_magisk_resetprop",
        "value_type": "boolean",
        "default_value": "true",
    },
    "backup_original_properties": {
        "display_name": "Backup Original Properties",
        "description": "Create backups before modifying device properties",
        "config_section": "ADVANCED_SPOOFING", 
        "config_key": "backup_original_properties",
        "value_type": "boolean",
        "default_value": "true",
    },
    "bypass_user_limits": {
        "display_name": "Bypass User Limits",
        "description": "Attempt to increase device user limits if needed",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "bypass_user_limits", 
        "value_type": "boolean",
        "default_value": "false",
    },
    "use_ephemeral_users": {
        "display_name": "Use Ephemeral Users",
        "description": "Create temporary users that are auto-deleted on reboot",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "use_ephemeral_users",
        "value_type": "boolean",
        "default_value": "true",
    },
    "spoof_manufacturer": {
        "display_name": "Target Manufacturer",
        "description": "Manufacturer to spoof (samsung, google, xiaomi, oneplus, oppo)",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "spoof_manufacturer",
        "value_type": "string",
        "default_value": "samsung",
        "allowed_values": ["samsung", "google", "xiaomi", "oneplus", "oppo"],
    },
    "spoof_model": {
        "display_name": "Target Model",
        "description": "Specific device model to spoof (leave empty for random)",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "spoof_model",
        "value_type": "string",
        "default_value": "",
    },
    "spoof_android_version": {
        "display_name": "Target Android Version", 
        "description": "Android version to spoof (10, 11, 12, 13, 14)",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "spoof_android_version",
        "value_type": "string",
        "default_value": "13",
        "allowed_values": ["10", "11", "12", "13", "14"],
    },
    "auto_spoof_on_user_creation": {
        "display_name": "Auto-Spoof on User Creation",
        "description": "Automatically randomize device properties for new users",
        "config_section": "ADVANCED_SPOOFING",
        "config_key": "auto_spoof_on_user_creation",
        "value_type": "boolean", 
        "default_value": "true",
    },
    "validate_root_access": {
        "display_name": "Validate Root Access",
        "description": "Check for root access before spoofing operations",
        "config_section": "SPOOF_VALIDATION",
        "config_key": "validate_root_access",
        "value_type": "boolean",
        "default_value": "true",
    },
    "check_multiuser_support": {
        "display_name": "Check Multi-User Support",
        "description": "Validate device supports multiple users before creation",
        "config_section": "SPOOF_VALIDATION",
        "config_key": "check_multiuser_support",
        "value_type": "boolean",
        "default_value": "true",
    },
} 