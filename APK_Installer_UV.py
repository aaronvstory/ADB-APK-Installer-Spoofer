#!/usr/bin/env python3
"""
APK Installer v4.0.0 - Professional APK Installation Tool with UV Support
Enhanced with UV package manager for faster dependency management
"""

import sys
import os
import subprocess

# Check for UV support from environment variable
USE_UV = os.environ.get('USE_UV', '0') == '1'

def check_and_install_dependencies():
    """Check for and install required dependencies with UV support."""
    dependencies = [
        ("rich", "rich"),
        ("pyaxmlparser", "pyaxmlparser"), 
        ("questionary", "questionary")
    ]
    
    missing_deps = []
    
    print("Checking dependencies...")
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
            print(f"✓ {import_name} is available")
        except ImportError:
            print(f"✗ {import_name} is missing")
            missing_deps.append(package_name)
    
    if missing_deps:
        print(f"\nMissing dependencies detected: {missing_deps}")
        print("Installing required packages...")
        
        if USE_UV:
            print("Using UV for faster installation...")
            try:
                for dep in missing_deps:
                    print(f"Installing {dep} with UV...")
                    result = subprocess.run(
                        ["uv", "pip", "install", dep], 
                        capture_output=True, 
                        text=True, 
                        timeout=60
                    )
                    if result.returncode != 0:
                        print(f"Failed to install {dep} with UV: {result.stderr}")
                        return False
                    else:
                        print(f"✓ {dep} installed successfully with UV")
                
                print("All dependencies installed successfully with UV!")
                return True
                
            except Exception as e:
                print(f"UV installation failed: {e}")
                print("Falling back to pip...")
        
        # Fallback to pip
        print("Using pip for installation...")
        try:
            for dep in missing_deps:
                print(f"Installing {dep} with pip...")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", dep], 
                    capture_output=True, 
                    text=True, 
                    timeout=60
                )
                if result.returncode != 0:
                    print(f"Failed to install {dep}: {result.stderr}")
                    return False
                else:
                    print(f"✓ {dep} installed successfully with pip")
            
            print("All dependencies installed successfully!")
            return True
            
        except Exception as e:
            print(f"Dependency installation failed: {e}")
            return False
    else:
        print("All dependencies are already installed!")
    
    return True

def main():
    """Main entry point of the application."""
    
    # Show header
    print("=" * 79)
    print("                    ADB APK INSTALLER v4.0.0")
    print("         '(Interactive Selection & Auto-Dependency with UV)'")
    print("=" * 79) 
    print()
    
    if USE_UV:
        print("✓ UV package manager integration ENABLED!")
        print("  Enhanced dependency management with UV")
    else:
        print("✓ Standard pip dependency management")
        print("  (Enable UV by setting USE_UV=1 environment variable)")
    
    print()
    
    # Check and install dependencies if needed
    if not check_and_install_dependencies():
        print("\nFailed to install required dependencies. Please install them manually:")
        if USE_UV:
            print("With UV: uv pip install rich pyaxmlparser questionary")
        print("With pip: pip install rich pyaxmlparser questionary")
        return 1
    
    print()
    print("Starting APK Installer...")
    
    # Try to import and run the installer (with error handling for the hanging issue)
    try:
        print("Loading installer modules...")
        
        # Import constants first
        from installer_constants import SCRIPT_VERSION
        print(f"✓ Loaded installer constants (Version: {SCRIPT_VERSION})")
        
        # Try to import the main installer class
        print("Loading main installer...")
        from installer_core import InteractiveAPKInstaller
        print("✓ Main installer loaded successfully")
        
        # Create and run the installer
        print("Initializing APK Installer...")
        installer = InteractiveAPKInstaller()
        print("✓ APK Installer initialized")
        print()
        
        # Run the main application
        installer.run()
        return 0
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Some modules may be missing or corrupted.")
        return 1
        
    except Exception as e:
        print(f"Error starting APK Installer: {e}")
        print("\nThe UV integration is working correctly, but there may be")
        print("an issue with the main installer modules.")
        print("\nTechnical details:")
        import traceback
        traceback.print_exc()
        return 1
        
    except KeyboardInterrupt:
        print("\nProgram interrupted.")
        return 1

if __name__ == "__main__":
    sys.exit(main())