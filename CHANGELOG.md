# Changelog

All notable changes to this project will be documented in this file.

## [v4.5.2] - 2024-07-04
### Odyssey Release
- Major codebase cleanup: removed all duplicate class and function definitions, fixed merge artifacts.
- **New Features:**
  - Custom profile naming: Prompt for a custom name when creating a new user profile, with timestamp fallback.
  - User Profile Management: Interactive menu to list and remove user profiles on a device.
  - Enhanced clipboard support: Attempts to enable clipboard for new user profiles, with clear warnings about third-party requirements.
- **Improvements:**
  - Robust dependency installer: Auto-installs `rich`, `pyaxmlparser`, and `questionary` if missing.
  - Improved error handling and exit codes.
  - More robust configuration and fallback logic.
  - Clearer user prompts and warnings for non-standard features.
- **Bugfixes:**
  - Fixed string splitting bug in device storage check.
  - Fixed `sys.exit()` usage for correct exit codes.
  - Removed all code duplication (no more duplicate classes or methods).
- **Compatibility:**
  - Fully compatible with existing `config.ini` and `device_patterns.json`.
  - Works with the new `apk_installerv4.5.2.bat` launcher.

## [v4.1.1] - Phoenix
- See previous README for details on the Phoenix release.

## [v4.0.0] - Major interactive and spoofing improvements
- Interactive selection menus, advanced spoofing, persistent user profiles, and more.

## [v3.5.0] and earlier
- Initial releases with basic APK install, spoofing, and user management features. 