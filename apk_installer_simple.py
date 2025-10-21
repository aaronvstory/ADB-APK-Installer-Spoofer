#!/usr/bin/env python3
"""
Simple APK Installer Entry Point - v4.0.0 with UV Support
Direct launcher without complex dependency checking
"""

import sys
import os

# Set USE_UV flag if passed via environment
USE_UV = os.environ.get('USE_UV', '0') == '1'

def main():
    """Main entry point - bypass dependency checking."""
    print("=" * 79)
    print("                    ADB APK INSTALLER v4.0.0")
    print("         '(Interactive Selection & Auto-Dependency with UV)'")
    print("=" * 79)
    print()
    
    if USE_UV:
        print("✓ UV support enabled for enhanced dependency management")
    else:
        print("✓ Using standard pip for dependency management")
    
    print("✓ Dependencies: rich, pyaxmlparser, questionary (should be installed)")
    print()
    
    try:
        # Import and run the installer directly
        print("Importing installer core...")
        from installer_core import InteractiveAPKInstaller
        
        print("Starting APK Installer...")
        installer = InteractiveAPKInstaller()
        installer.run()
        return 0
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Dependencies may be missing. Please install:")
        if USE_UV:
            print("  uv pip install rich pyaxmlparser questionary")
        else:
            print("  pip install rich pyaxmlparser questionary")
        return 1
        
    except KeyboardInterrupt:
        print("\nProgram interrupted.")
        return 1
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())