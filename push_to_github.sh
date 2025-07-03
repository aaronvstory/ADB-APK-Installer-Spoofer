#!/bin/bash

# Script to push ADB APK Installer Spoofer to GitHub
# PAPESLAY - Autonomous GitHub repository setup

echo "[INFO] Starting GitHub push process..."

# Set up Git configuration
git config --global user.email "aaronvstory@users.noreply.github.com"
git config --global user.name "aaronvstory"

# Navigate to project directory
cd "C:\Users\d0nbx\MAIN\ADB_APK_Installer_Spoofer_v3.6"

# Check git status
echo "[INFO] Checking git status..."
git status

# Add all files (excluding the temporary scripts)
echo "[INFO] Adding files to git..."
git add .
git add -A

# Commit changes
echo "[INFO] Committing changes..."
git commit -m "feat: Initial release of ADB APK Installer & Spoofer v4.1.1 Phoenix

- Professional APK Installation Tool with advanced spoofing capabilities
- Multi-format support: APK, XAPK, APKM, and ZIP archives
- Interactive selection with questionary library
- Advanced device spoofing with Magisk integration
- User profile management with ephemeral users
- Batch installation to multiple devices
- Comprehensive error handling and recovery
- Auto-dependency installation for required packages
- Device capability detection and validation
- Property backup and restore functionality

Technical Features:
- Python 3.7+ with Rich UI library
- Configurable spoofing patterns via JSON
- Root access detection and validation
- Multi-user support with user limit bypass
- Comprehensive logging and debugging
- Cross-platform compatibility (Windows/Linux/macOS)

This release merges the best features from v3.5.0 and v4.0.0 with
improved stability, user experience, and expanded device compatibility."

# Push to GitHub with authentication
echo "[INFO] Pushing to GitHub..."
git push -u origin main

echo "[INFO] GitHub push completed!"
