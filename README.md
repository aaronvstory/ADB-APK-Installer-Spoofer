# ADB APK Installer & Spoofer v4.1.1 (Phoenix)

🚀 **Professional APK Installation Tool for Android Devices**  
*Advanced Spoofing & User Profile Management*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yourusername/ADB-APK-Installer-Spoofer)

## ✨ Features

### 📱 **APK Installation**
- **Multi-format Support**: APK, XAPK, APKM, and ZIP archives
- **Interactive Selection**: Smart single/multi-selection modes
- **Batch Installation**: Install multiple apps to multiple devices simultaneously
- **Split APK Handling**: Automatic detection and installation of app bundles
- **OBB File Support**: Automatic OBB extraction and installation

### 🎭 **Advanced Spoofing**
- **Device Property Spoofing**: Change manufacturer, model, Android version
- **User Profile Management**: Create isolated user environments
- **Magisk Integration**: Property spoofing via resetprop
- **APatch/KernelSU Support**: Compatible with modern root solutions
- **Automatic Cleanup**: Restore original properties after sessions

### 🛡️ **Security & Privacy**
- **Ephemeral Users**: Temporary profiles that auto-delete
- **Property Backup**: Automatic backup and restore of original values
- **Capability Detection**: Smart detection of device capabilities
- **Safe Cleanup**: Comprehensive cleanup on exit

## 🚀 Quick Start

### Prerequisites
- **ADB (Android Debug Bridge)** installed and in PATH
- **Python 3.7+**
- **USB Debugging** enabled on target device(s)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/ADB-APK-Installer-Spoofer.git
   cd ADB-APK-Installer-Spoofer
   ```

2. **Install dependencies** (auto-installed on first run):
   ```bash
   pip install rich questionary pyaxmlparser
   ```

3. **Run the installer**:
   ```bash
   python apk_installer.py
   ```

### First Run Setup
The script will automatically:
- Check and install missing dependencies
- Create default configuration files
- Detect connected devices
- Scan for APK files in the `apks/` directory

## 📁 Project Structure

```
ADB_APK_Installer_Spoofer_v3.6/
├── apk_installer.py          # Main application
├── config.ini               # Configuration settings
├── device_patterns.json     # Device spoofing patterns
├── apks/                    # Place your APK/XAPK/APKM/ZIP files here
├── otherAPKs/              # Additional APK storage
└── README.md               # This file
```

## 🎮 Usage

### Basic APK Installation
1. Place APK/XAPK/APKM/ZIP files in the `apks/` folder
2. Connect your Android device(s) via USB
3. Run `python apk_installer.py`
4. Select installation mode and follow prompts

### Selection Modes
- **Single Selection**: Navigate with arrow keys, press Enter to select
- **Multi Selection**: Use spacebar to select multiple items, press Enter to confirm
- **Auto Selection**: Single items are automatically selected

### Advanced Spoofing
1. Choose "Configure Advanced Spoofing" from the main menu
2. Enable desired spoofing features:
   - **User Profile Spoofing**: Create isolated user environments
   - **Magisk Property Spoofing**: Change device properties
3. Configure target manufacturer, model, and Android version
4. Install apps with spoofed identity

## ⚙️ Configuration

### Main Settings (`config.ini`)

#### User Profile Management
```ini
[UNIQUENESS]
enable_uniqueness_features = true
cleanup_user_profile_after_session = true
auto_set_random_android_id = true
```

#### Advanced Spoofing
```ini
[ADVANCED_SPOOFING]
enable_magisk_resetprop = true
spoof_manufacturer = samsung
spoof_android_version = 13
use_ephemeral_users = true
```

### Device Patterns (`device_patterns.json`)
Customize device spoofing patterns for different manufacturers:
- Samsung Galaxy devices
- Google Pixel devices  
- Xiaomi/Redmi devices
- Custom device definitions

## 🔧 Requirements

### System Requirements
- **Operating System**: Windows 10+, Linux, macOS
- **Python**: 3.7 or higher
- **ADB**: Latest version recommended
- **USB Cable**: For device connection

### Device Requirements
- **Android 7.0+** (API level 24+)
- **USB Debugging** enabled
- **Root Access** (optional, for advanced spoofing)
- **Magisk/APatch/KernelSU** (optional, for property spoofing)

### Python Dependencies
- `rich` - Beautiful terminal output
- `questionary` - Interactive prompts
- `pyaxmlparser` - APK metadata parsing

## 🛠️ Advanced Features

### Root-based Features
When root access is detected:
- **Property Spoofing**: Change device fingerprint, model, manufacturer
- **User Limit Bypass**: Create more user profiles than device allows
- **Advanced Cleanup**: Comprehensive restoration of system state

### Multi-device Support
- Install to multiple devices simultaneously
- Device capability detection and recommendations
- Per-device configuration and status tracking

### Error Recovery
- Automatic retry mechanisms for failed installations
- Detailed error reporting and suggestions
- Graceful handling of device disconnections

## 🐛 Troubleshooting

### Common Issues

**"No devices found"**
- Ensure USB debugging is enabled
- Check ADB connection: `adb devices`
- Try different USB cable/port

**"Installation failed"**
- Check device storage space
- Verify APK compatibility with device architecture
- Enable "Install from unknown sources"

**"Property spoofing failed"**
- Ensure device is rooted
- Verify Magisk/resetprop is installed
- Check if device supports property modification

### Debug Mode
Run with debug output:
```bash
python apk_installer.py --debug
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and legitimate testing purposes only. Users are responsible for complying with all applicable laws and regulations. The authors are not responsible for any misuse of this software.

## 🙏 Acknowledgments

- Android Debug Bridge (ADB) team
- Magisk project for property spoofing capabilities
- APatch and KernelSU projects for modern root solutions
- Rich library for beautiful terminal output
- Questionary library for interactive prompts

## 📞 Support

If you encounter issues or have questions:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed information

---

**Made with ❤️ for the Android development community** 