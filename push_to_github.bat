@echo off
title ADB APK Installer Spoofer - GitHub Push Script

REM Script to push ADB APK Installer Spoofer to GitHub
REM PAPESLAY - Autonomous GitHub repository setup

echo [INFO] Starting GitHub push process...

REM Set up Git configuration
git config --global user.email "aaronvstory@users.noreply.github.com"
git config --global user.name "aaronvstory"

REM Navigate to project directory
cd /d "C:\Users\d0nbx\MAIN\ADB_APK_Installer_Spoofer_v3.6"

REM Check git status
echo [INFO] Checking git status...
git status

REM Add all files (excluding the temporary scripts)
echo [INFO] Adding files to git...
git add .
git add -A

REM Commit changes
echo [INFO] Committing changes...
git commit -m "feat: Initial release of ADB APK Installer & Spoofer v4.1.1 Phoenix - Professional APK Installation Tool with advanced spoofing capabilities"

REM Push to GitHub with authentication
echo [INFO] Pushing to GitHub...
git push -u origin main

echo [INFO] GitHub push completed!
pause
