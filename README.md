# ADB APK Installer & Spoofer v4.1.1 (Phoenix)

<div align="center">
  <pre>
 █████╗ ██████╗ ██████╗     █████╗ ██████╗ ██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗   ██╔══██╗██╔══██╗██║ ██╔╝
███████║██║  ██║██████╔╝   ███████║██████╔╝█████╔╝
██╔══██║██║  ██║██╔══██╗   ██╔══██║██╔═══╝ ██╔═██╗
██║  ██║██████╔╝██████╔╝   ██║  ██║██║     ██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        Interactive APK Installation Tool
             v4.1.1 (Phoenix)
</pre>
  <p><strong>An advanced, interactive command-line tool for installing Android applications and dynamically spoofing device identity with a focus on privacy and anti-tracking.</strong></p>

  <p>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python 3.7+"></a>
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
  </p>
</div>

## Overview

This tool provides a professional suite for Android application installation and testing. It elevates the standard `adb install` workflow by integrating a rich, interactive interface with powerful, layered spoofing capabilities. Its core strength lies in its dual-pronged approach to creating unique, sandboxed environments:

1.  **User Profile Isolation**: Creates clean, isolated user profiles on the device for each installation, simulating a "fresh install" environment without affecting the primary user's data.
2.  **Advanced Property Spoofing**: For rooted devices, it leverages Magisk's `resetprop` to fundamentally alter the device's identity, with robust, multi-strategy attempts to ensure properties are set correctly.

The latest version introduces a powerful **anti-tracking engine** that automatically randomizes a device's entire fingerprint for each new user profile, making it significantly harder for applications to track a user across different sandboxes.

## Key Features

### 📦 Universal Installer
-   **Multi-Format Support**: Seamlessly handles `.apk`, `.xapk`, `.apkm`, and `.zip` files.
-   **Intelligent Split-APK Handling**: Automatically parses application bundles, selects the correct splits (ABI, DPI, language), and installs them.
-   **OBB Integration**: Automatically extracts and places OBB data files in the correct directory for the target user profile.
-   **Interactive Menus**: A fluid, multi-selection interface for choosing devices and APK files.
-   **Batch Operations**: Install multiple apps onto multiple devices in a single session.

### 🎭 Advanced Spoofing & Anti-Tracking
-   **Automatic Device Randomization**: (Root) When creating a new user profile, automatically assign it a completely unique, randomized device identity (manufacturer, model, build, etc.) to prevent cross-profile tracking.
-   **Comprehensive Property Spoofing**: Modifies a vast array of properties, including hardware identifiers, build details, network settings, and locale, to create a convincing and unique device fingerprint.
-   **User Profile Management**:
    -   Create temporary **ephemeral users** (Android 8+) that are automatically deleted on reboot.
    -   Create standard (permanent) secondary users for persistent testing environments.
    -   (Root) Automatically set a unique Android ID for each new user profile.
-   **Persistent Spoofing & Interactive Cleanup**: By default, spoofed environments are now persistent. At the end of a session, the script interactively prompts you to choose exactly what you want to restore, giving you full control over your testing environments.

### ✨ Usability & Interface
-   **Automatic Dependency Installation**: On first run, the script detects and offers to install missing Python packages (`rich`, `questionary`, `pyaxmlparser`).
-   **Rich Console UI**: A beautifully formatted interface with tables, panels, status indicators, and color-coded logging.
-   **Interactive Configuration**: A dedicated menu to visually manage all spoofing settings without manually editing `config.ini`.
-   **Capability Detection**: Scans connected devices to report their support for multi-user, ephemeral users, and root access.
-   **Phone Management Tools**: Includes utilities like a PC-to-Android clipboard setter.

## Getting Started

### Prerequisites
-   **Python 3.7+**
-   **Android Debug Bridge (ADB)**: Must be installed and accessible via the system's PATH.

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/aaronvstory/ADB-APK-Installer-Spoofer.git
    cd ADB-APK-Installer-Spoofer
    ```

2.  **Place APKs:**
    -   Put your `.apk`, `.xapk`, `.apkm`, or `.zip` files into the `apks/` directory.

3.  **Run the tool:**
    -   **Windows**: Double-click the `.bat` launcher file.
    -   **Linux/macOS**:
        ```bash
        python3 apk_installer.py
        ```

On the first run, the script will guide you through installing any missing Python dependencies. After that, you're ready to go!

## Configuration Deep Dive

The tool is controlled by two main configuration files, which are created automatically. You can either edit them directly or use the in-script menus.

### 1. `config.ini`
This file contains all operational settings. The defaults are now geared towards creating persistent, unique environments.

| Section                 | Key                                  | Description                                                                                                      |
| ----------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **[UNIQUENESS]**        | `enable_uniqueness_features`         | Master switch for creating isolated user profiles.                                                               |
|                         | `cleanup_user_profile_after_session` | **Defaults to `false`**. If true, will auto-cleanup profiles between sessions instead of prompting at the end.   |
| **[ADVANCED_SPOOFING]** | `enable_magisk_resetprop`            | Master switch for property spoofing. (Requires Root).                                                            |
|                         | `auto_spoof_on_user_creation`        | **(Recommended)** Automatically applies a random device fingerprint to each new user profile for anti-tracking.    |
|                         | `backup_original_properties`         | Backs up device properties before spoofing to ensure perfect restoration when you choose to clean up.            |
|                         | `spoof_manufacturer`                 | The *default* manufacturer to emulate if not using auto-randomization.                                           |
|                         | `spoof_model`                        | The *default* model to emulate. Leave blank to pick a random one.                                                |
|                         | `spoof_android_version`              | The *default* Android version to emulate.                                                                        |
| **[SPOOF_VALIDATION]**  | `validate_root_access`               | If true, checks for root access when a root-dependent feature is enabled.                                        |
|                         | `check_multiuser_support`            | If true, verifies the device can create multiple users.                                                          |

### 2. `device_patterns.json`
This file is the brain behind property generation. It contains patterns for creating realistic device models, build fingerprints, and serial numbers. You can extend this file with your own device definitions.

-   **`manufacturers`**: Holds data for different brands (Samsung, Google, Xiaomi).
-   **`props_to_spoof`**: A comprehensive list of property keys that the script is allowed to modify. The script ships with an extensive default list for robust spoofing.

## Troubleshooting

-   **"No devices found"**: Ensure your device has **USB Debugging** enabled, is properly connected, and that you have authorized the connection on the device's screen. Run `adb devices` to check the connection manually.
-   **"Property spoofing failed"**: This feature strictly requires a **rooted device** with a functioning Magisk, APatch, or KernelSU installation that provides the `resetprop` command. The script now tries multiple methods to set properties, but some may still be protected by the ROM.
-   **"User creation failed"**: Ensure "Multiple users" is enabled in your device's system settings. The device must also be unlocked to switch users. If you hit a limit, try enabling `bypass_user_limits` in the config.

## ⚠️ Disclaimer

This tool is intended for educational, research, and legitimate testing purposes ONLY. Modifying device properties and installing software can have unintended consequences. The user is solely responsible for their actions and for complying with all applicable laws. The authors assume no liability for any misuse of this software.
