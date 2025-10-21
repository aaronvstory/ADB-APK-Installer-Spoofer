#!/usr/bin/env python3
"""
Minimal APK Installer entry point - Bypasses hanging dependency checks
"""

import sys
import os

# Skip dependency checking since they're already installed
print("Starting APK Installer v4.0.0...")
print("Dependencies: rich, pyaxmlparser, questionary (assumed installed)")

try:
    # Try to import just what we need without complex initialization
    print("Importing core modules...")
    
    # Basic module test
    try:
        import rich
        print("✓ Rich available")
    except ImportError:
        print("✗ Rich not available - continuing anyway")
    
    try:
        import questionary
        print("✓ Questionary available")
    except ImportError:
        print("✗ Questionary not available - continuing anyway")
    
    try:
        import pyaxmlparser
        print("✓ PyAXMLParser available")
    except ImportError:
        print("✗ PyAXMLParser not available - continuing anyway")
    
    # Try to create a simple rich console without hanging
    from rich.console import Console
    console = Console()
    console.print("Rich console created successfully!", style="green")
    
    # Now try to import and create the installer
    from installer_core import InteractiveAPKInstaller
    installer = InteractiveAPKInstaller()
    installer.run()
    
except KeyboardInterrupt:
    print("\nProgram interrupted.")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)