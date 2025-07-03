@echo off
setlocal enabledelayedexpansion

:: Get the directory of the batch file
set "BATCH_DIR=%~dp0"
set "SCRIPT_PATH=%BATCH_DIR%apk_installer.py"
set "APK_DIR=%BATCH_DIR%apks"
set "CONFIG_FILE=%BATCH_DIR%config.ini"

:: Display enhanced banner
echo.
echo ===============================================================================
echo                       ADB APK INSTALLER v4.0.0
echo              "(Interactive Selection & Auto-Dependency)"
echo ===============================================================================
echo.
echo  Professional APK Installation Tool for Android Devices
echo  Install APKs, XAPKs with User Profile or Magisk Spoofing
echo.
echo  APK Directory: "%APK_DIR%"
echo  Script Path:   "%SCRIPT_PATH%"
echo  Config File:   "%CONFIG_FILE%"
echo.

:: Create APK directory if needed
if not exist "%APK_DIR%" (
    echo [INFO] Creating APK directory...
    mkdir "%APK_DIR%" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create APK directory. Please check permissions.
        pause
        exit /b 1
    )
    echo [SUCCESS] APK directory created.
    echo.
)

:: Check if Python script exists
if not exist "%SCRIPT_PATH%" (
    echo [ERROR] APK Installer script not found at "%SCRIPT_PATH%"
    echo Please ensure apk_installer.py is in the same directory as this batch file.
    pause
    exit /b 1
)

:: Enhanced Python environment check
echo [INFO] Checking Python environment...

set "PYTHON_EXE="

:: First, try the 'py' launcher which is recommended for Windows
py --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_EXE=py"
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    echo [INFO] Using 'py' launcher (Version: !PYTHON_VERSION!)
) else (
    :: If 'py' fails, check for 'python' in PATH
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
        echo [INFO] Using 'python' executable from PATH (Version: !PYTHON_VERSION!)
    )
)

:: If still no Python found, show an error and exit
if not defined PYTHON_EXE (
    echo [ERROR] Python is not installed or not found in the system PATH.
    echo Please install Python 3.7+ and ensure it's added to your PATH.
    echo You can download Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.

:: Change to script directory for consistent relative paths
cd /D "%BATCH_DIR%"

:: Run the Python script
echo [INFO] Starting APK Installer v4.0.0...
echo [INFO] The script will check for and offer to install missing dependencies.
echo.

"%PYTHON_EXE%" "%SCRIPT_PATH%"
set "EXIT_CODE=!errorlevel!"

:: Enhanced exit status handling
echo.
if !EXIT_CODE! equ 0 (
    echo ===============================================================================
    echo                        APK INSTALLER COMPLETED SUCCESSFULLY
    echo ===============================================================================
    echo.
) else if !EXIT_CODE! equ 1 (
    echo ===============================================================================
    echo                       APK INSTALLER COMPLETED WITH ERRORS
    echo ===============================================================================
    echo.
    echo [WARNING] The process finished, but one or more errors occurred.
    echo [INFO] Please review the summary and error messages above for details.
) else (
     echo ===============================================================================
    echo                  APK INSTALLER EXITED UNEXPECTEDLY (Code: !EXIT_CODE!)
    echo ===============================================================================
    echo.
    echo [ERROR] The script terminated unexpectedly.
)

echo.
echo Press any key to close this window...
pause >nul

endlocal