# AGENTS.md - ADB APK Installer Commands & Guidelines

## Build/Test Commands
```bash
python test_spoofing.py          # Run device spoofing tests
python apk_installer.py          # Run main application
python -m pytest test_*.py       # Run all tests (if pytest available)
```

## Code Style
- **Imports**: Standard library first, then third-party, then local modules
- **Formatting**: Use 4 spaces for indentation, 79-char line limit
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Types**: Use type hints for function parameters and return values
- **Error Handling**: Use try/except with specific exception types, log errors
- **Constants**: UPPER_SNAKE_CASE for constants in installer_constants.py
- **Config**: Use configparser for .ini files, json for structured data
- **Comments**: Docstrings for classes/functions, inline comments sparingly