# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the ADB APK Installer & Spoofer v4.5.2 "Odyssey" - an advanced Python-based tool for installing Android applications with device spoofing capabilities. The tool uses a modular architecture split across four main Python files:

- `apk_installer.py`: Main entry point with dependency management
- `installer_core.py`: Core installation logic and interactive workflows  
- `device_spoofing.py`: Advanced device spoofing and anti-tracking capabilities
- `installer_constants.py`: Configuration constants and device patterns

## Development Commands

### Running the Application
```bash
# Windows (recommended)
APK_Installer.bat

# Cross-platform
python apk_installer.py
# or
python3 apk_installer.py
```

### Dependencies
The application automatically installs required dependencies on first run:
```bash
pip install rich pyaxmlparser questionary
```

### Testing Device Spoofing
```bash
python test_spoofing.py
```

### Configuration Testing
The application validates configuration through:
- `config.ini` for operational settings
- `device_patterns.json` for spoofing patterns
- Both files are auto-created with defaults if missing

## Architecture & Key Components

### Modular Design
The codebase follows a clean separation of concerns:

1. **Entry Point (`apk_installer.py`)**
   - Handles dependency checking and installation
   - Imports and initializes the main installer class
   - Manages application lifecycle and error handling

2. **Core Engine (`installer_core.py`)**
   - `InteractiveAPKInstaller` class manages the main workflow
   - Multi-format APK support (.apk, .xapk, .apkm, .zip files)
   - Interactive device/file selection using questionary
   - Rich console UI with tables, panels, and progress indicators

3. **Spoofing Engine (`device_spoofing.py`)**
   - `DeviceSpoofingManager` class handles device identity manipulation
   - Enterprise-grade persistent fingerprints and anti-tracking
   - User profile management (creation, deletion, switching)
   - Magisk resetprop integration for rooted devices

4. **Configuration System (`installer_constants.py`)**
   - Centralized configuration constants and defaults
   - Device manufacturer patterns for realistic spoofing
   - Configurable spoofing options with validation
   - ASCII banner and version management

### Key Design Patterns

**Configuration Management**: Two-tier config system with `config.ini` for operational settings and `device_patterns.json` for spoofing data. Both auto-generate with sensible defaults.

**Error Handling**: Graceful degradation when optional dependencies are missing. Rich UI falls back to plain text, advanced features disable cleanly.

**User Experience**: Interactive menus throughout using questionary for device/file selection, with rich console formatting for status and progress.

**Security Focus**: All spoofing capabilities are defensive-oriented for testing and privacy, with automatic cleanup options and restoration features.

## Configuration Files

### config.ini Structure
- `[UNIQUENESS]`: User profile management settings
- `[ADVANCED_SPOOFING]`: Device spoofing configuration  
- `[SPOOF_VALIDATION]`: Validation and safety checks
- `[FILE_DISCOVERY]`: APK file scanning options
- `[INSTALLATION]`: Installation behavior settings
- `[LOGGING]`: Output and logging preferences

### device_patterns.json Structure
- `manufacturers`: Device spoofing patterns by brand (Samsung, Google, Xiaomi, OnePlus, OPPO)
- Each manufacturer includes models, build patterns, and serial number generation rules
- `props_to_spoof`: Comprehensive list of Android properties to modify

## Important Implementation Notes

### ADB Integration
- Requires ADB in system PATH or configured path in config.ini
- Device detection and capability scanning (multi-user, ephemeral users, root access)
- Robust command execution with timeout handling and error parsing

### File Format Support
- **APK**: Standard Android packages
- **XAPK**: Split APK bundles with automatic architecture/DPI selection
- **APKM**: APKMirror bundles
- **ZIP**: Generic archives containing APKs
- **OBB**: Automatic extraction and placement for expansion files

### User Profile Management
- Creates isolated Android user profiles for testing
- Supports ephemeral users (auto-delete on reboot) for Android 8+
- Custom profile naming with timestamp fallbacks
- Interactive profile cleanup with selective restoration

### Anti-Tracking Features
- Automatic random device fingerprint assignment per user profile
- Comprehensive property spoofing (build, hardware, network, locale)
- Persistent spoofing with optional restoration
- Enterprise-grade fingerprint patterns for realistic device emulation

## Development Workflow

When modifying this codebase:

1. **Maintain Modular Structure**: Keep the four-file architecture clean with proper imports
2. **Preserve Configuration Compatibility**: Changes to config structure should maintain backward compatibility
3. **Test Spoofing Safely**: Use test devices or emulators when developing spoofing features
4. **Validate Rich UI**: Ensure UI degrades gracefully when rich library is unavailable
5. **Handle ADB Errors**: Device connections can be unstable, implement robust retry logic
6. **Respect Security Focus**: This tool is for defensive testing only, maintain privacy-focused implementation

## Main Menu Options

The application provides several installation modes:

1. **🚀 Install APKs/XAPKs (Main Workflow)**: Full featured installation with user profile management and spoofing options
2. **📦 Simple Install APK(s)**: Streamlined force installation that:
   - Allows multi-selection of devices and APK files
   - Automatically uninstalls existing packages if present
   - Force installs with overwrite using aggressive ADB flags (`-r -t -d -g`)
   - Bypasses all confirmation dialogs for quick deployment
3. **⚙️ Spoofing Configuration**: Configure device spoofing settings
4. **📱 Phone Management Tools**: Device management utilities
5. **🔧 Configuration Settings**: Application configuration
6. **❌ Exit**: Exit the application

## Key Dependencies

- **rich**: Enhanced console UI (auto-installed)
- **questionary**: Interactive prompts (auto-installed) 
- **pyaxmlparser**: APK manifest parsing (auto-installed)
- **ADB**: Android Debug Bridge (external requirement)
- **Magisk/resetprop**: Required for property spoofing on rooted devices (optional)