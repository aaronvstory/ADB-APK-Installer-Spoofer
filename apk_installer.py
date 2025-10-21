#!/usr/bin/env python3
"""
Professional APK Installation Tool - v4.5.2 "Odyssey"
Main entry point for the modular APK installer suite.

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

This modular architecture splits functionality across:
- installer_constants.py: Configuration constants and default patterns
- device_spoofing.py: Device spoofing and anti-tracking capabilities  
- installer_core.py: Core installation logic and interactive workflows
- apk_installer.py: Main entry point and dependency management (this file)
"""

import sys
import subprocess
import os

# Import constants
from installer_constants import SCRIPT_VERSION

# Import the main installer class
from installer_core import InteractiveAPKInstaller


def check_and_install_dependencies():
    """Check for and install required dependencies."""
    dependencies = [
        ("rich", "rich"),
        ("pyaxmlparser", "pyaxmlparser"), 
        ("questionary", "questionary")
    ]
    
    missing_deps = []
    
    # Check which dependencies are missing
    print("Checking dependencies...")
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
            print(f"✓ {import_name} is available")
        except ImportError:
            print(f"✗ {import_name} is missing")
            missing_deps.append(package_name)
    
    if missing_deps:
        print(f"\nAPK Installer {SCRIPT_VERSION} - Missing dependencies detected.")
        print("Installing required packages:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print()
        
        # Check if we should use uv or pip
        use_uv = (os.environ.get('USE_UV') == '1')
        
        if use_uv:
            print("Attempting to use UV for faster package installation...")
            try:
                # Use uv pip install command (compatible with pip interface)
                installer = ["uv", "pip", "install"]
                for dep in missing_deps:
                    print(f"Installing {dep} with uv...")
                    result = subprocess.run(installer + [dep], capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"UV installation failed for {dep}: {result.stderr}")
                        use_uv = False
                        break
                    else:
                        print(f"✓ {dep} installed successfully with uv")
                
                if use_uv:
                    print("\nAll dependencies installed successfully with uv!")
                    return True
            except subprocess.TimeoutExpired:
                print("UV installation timed out, falling back to pip...")
                use_uv = False
            except Exception as e:
                print(f"UV installation error: {e}, falling back to pip...")
                use_uv = False
        
        # Fallback to pip
        if not use_uv:
            print("Using pip for dependency installation...")
            try:
                installer = [sys.executable, "-m", "pip", "install"]
                for dep in missing_deps:
                    print(f"Installing {dep} with pip...")
                    result = subprocess.run(installer + [dep], capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        print(f"Failed to install {dep}: {result.stderr}")
                        return False
                    else:
                        print(f"✓ {dep} installed successfully with pip")
                
                print("\nAll dependencies installed successfully with pip!")
                return True
                
            except subprocess.TimeoutExpired:
                print("Pip installation timed out. Please install dependencies manually.")
                return False
            except Exception as e:
                print(f"Pip installation error: {e}")
                return False
    else:
        print("All dependencies are already installed!")
    
    return True


def main():
    """Main entry point of the application."""
    
    # Check and install dependencies if needed
    if not check_and_install_dependencies():
        print("Failed to install required dependencies. Please install them manually:")
        print("With uv: uv pip install rich pyaxmlparser questionary")
        print("With pip: pip install rich pyaxmlparser questionary")
        return 1
    
    # Create and run the installer
    try:
        installer = InteractiveAPKInstaller()
        installer.run()
        return 0
    except KeyboardInterrupt:
        if installer.console: 
            installer.console.print("\nProgram interrupted.", style="yellow")
        else:
            print("\nProgram interrupted.")
        return 1
    except Exception as e:
        if installer.console:
            installer.console.print(f"Error: {e}", style="red")
        else:
            print(f"Error: {e}")
        return 1
    finally:
        installer.cleanup_temp_files()
        if installer.console:
            if sys.stdin.isatty(): 
                input("\nPress Enter to exit.")


if __name__ == "__main__":
    sys.exit(main()) 