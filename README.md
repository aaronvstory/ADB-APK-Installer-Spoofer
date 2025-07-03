<<<<<<< HEAD
# ADB APK Installer & Spoofer v4.1.1 (Phoenix)

<div align="center">
  <pre>
 █████╗ ██████╗ ██████╗     █████╗ ██████╗ ██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗   ██╔══██╗██╔══██╗██║ ██╔╝
███████║██║  ██║██████╔╝   ███████║██████╔╝█████╔╝
██╔══██║██║  ██║██╔══██╗   ██╔══██║██╔═══╝ ██╔═██╗
██║  ██║██████╔╝██████╔╝   ██║  ██║██║     ██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        Interactive APK Installation Tool
             v4.1.1 (Phoenix)
</pre>
  <p><strong>An advanced, interactive command-line tool for installing Android applications and dynamically spoofing device identity with a focus on privacy and anti-tracking.</strong></p>

  <p>
    <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
    <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.7+-blue.svg" alt="Python 3.7+"></a>
    <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg" alt="Platform">
  </p>
</div>

## Overview

This tool provides a professional suite for Android application installation and testing. It elevates the standard `adb install` workflow by integrating a rich, interactive interface with powerful, layered spoofing capabilities. Its core strength lies in its dual-pronged approach to creating unique, sandboxed environments:

1.  **User Profile Isolation**: Creates clean, isolated user profiles on the device for each installation, simulating a "fresh install" environment without affecting the primary user's data.
2.  **Advanced Property Spoofing**: For rooted devices, it leverages Magisk's `resetprop` to fundamentally alter the device's identity, with robust, multi-strategy attempts to ensure properties are set correctly.

The latest version introduces a powerful **anti-tracking engine** that automatically randomizes a device's entire fingerprint for each new user profile, making it significantly harder for applications to track a user across different sandboxes.

## Key Features

### 📦 Universal Installer
-   **Multi-Format Support**: Seamlessly handles `.apk`, `.xapk`, `.apkm`, and `.zip` files.
-   **Intelligent Split-APK Handling**: Automatically parses application bundles, selects the correct splits (ABI, DPI, language), and installs them.
-   **OBB Integration**: Automatically extracts and places OBB data files in the correct directory for the target user profile.
-   **Interactive Menus**: A fluid, multi-selection interface for choosing devices and APK files.
-   **Batch Operations**: Install multiple apps onto multiple devices in a single session.

### 🎭 Advanced Spoofing & Anti-Tracking
-   **Automatic Device Randomization**: (Root) When creating a new user profile, automatically assign it a completely unique, randomized device identity (manufacturer, model, build, etc.) to prevent cross-profile tracking.
-   **Comprehensive Property Spoofing**: Modifies a vast array of properties, including hardware identifiers, build details, network settings, and locale, to create a convincing and unique device fingerprint.
-   **User Profile Management**:
    -   Create temporary **ephemeral users** (Android 8+) that are automatically deleted on reboot.
    -   Create standard (permanent) secondary users for persistent testing environments.
    -   (Root) Automatically set a unique Android ID for each new user profile.
-   **Persistent Spoofing & Interactive Cleanup**: By default, spoofed environments are now persistent. At the end of a session, the script interactively prompts you to choose exactly what you want to restore, giving you full control over your testing environments.

### ✨ Usability & Interface
-   **Automatic Dependency Installation**: On first run, the script detects and offers to install missing Python packages (`rich`, `questionary`, `pyaxmlparser`).
-   **Rich Console UI**: A beautifully formatted interface with tables, panels, status indicators, and color-coded logging.
-   **Interactive Configuration**: A dedicated menu to visually manage all spoofing settings without manually editing `config.ini`.
-   **Capability Detection**: Scans connected devices to report their support for multi-user, ephemeral users, and root access.
-   **Phone Management Tools**: Includes utilities like a PC-to-Android clipboard setter.

## Getting Started

### Prerequisites
-   **Python 3.7+**
-   **Android Debug Bridge (ADB)**: Must be installed and accessible via the system's PATH.

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/aaronvstory/ADB-APK-Installer-Spoofer.git
    cd ADB-APK-Installer-Spoofer
    ```

2.  **Place APKs:**
    -   Put your `.apk`, `.xapk`, `.apkm`, or `.zip` files into the `apks/` directory.

3.  **Run the tool:**
    -   **Windows**: Double-click the `.bat` launcher file.
    -   **Linux/macOS**:
        ```bash
        python3 apk_installer.py
        ```

On the first run, the script will guide you through installing any missing Python dependencies. After that, you're ready to go!

## Configuration Deep Dive

The tool is controlled by two main configuration files, which are created automatically. You can either edit them directly or use the in-script menus.

### 1. `config.ini`
This file contains all operational settings. The defaults are now geared towards creating persistent, unique environments.

| Section                 | Key                                  | Description                                                                                                      |
| ----------------------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| **[UNIQUENESS]**        | `enable_uniqueness_features`         | Master switch for creating isolated user profiles.                                                               |
|                         | `cleanup_user_profile_after_session` | **Defaults to `false`**. If true, will auto-cleanup profiles between sessions instead of prompting at the end.   |
| **[ADVANCED_SPOOFING]** | `enable_magisk_resetprop`            | Master switch for property spoofing. (Requires Root).                                                            |
|                         | `auto_spoof_on_user_creation`        | **(Recommended)** Automatically applies a random device fingerprint to each new user profile for anti-tracking.    |
|                         | `backup_original_properties`         | Backs up device properties before spoofing to ensure perfect restoration when you choose to clean up.            |
|                         | `spoof_manufacturer`                 | The *default* manufacturer to emulate if not using auto-randomization.                                           |
|                         | `spoof_model`                        | The *default* model to emulate. Leave blank to pick a random one.                                                |
|                         | `spoof_android_version`              | The *default* Android version to emulate.                                                                        |
| **[SPOOF_VALIDATION]**  | `validate_root_access`               | If true, checks for root access when a root-dependent feature is enabled.                                        |
|                         | `check_multiuser_support`            | If true, verifies the device can create multiple users.                                                          |

### 2. `device_patterns.json`
This file is the brain behind property generation. It contains patterns for creating realistic device models, build fingerprints, and serial numbers. You can extend this file with your own device definitions.

-   **`manufacturers`**: Holds data for different brands (Samsung, Google, Xiaomi).
-   **`props_to_spoof`**: A comprehensive list of property keys that the script is allowed to modify. The script ships with an extensive default list for robust spoofing.

## Troubleshooting

-   **"No devices found"**: Ensure your device has **USB Debugging** enabled, is properly connected, and that you have authorized the connection on the device's screen. Run `adb devices` to check the connection manually.
-   **"Property spoofing failed"**: This feature strictly requires a **rooted device** with a functioning Magisk, APatch, or KernelSU installation that provides the `resetprop` command. The script now tries multiple methods to set properties, but some may still be protected by the ROM.
-   **"User creation failed"**: Ensure "Multiple users" is enabled in your device's system settings. The device must also be unlocked to switch users. If you hit a limit, try enabling `bypass_user_limits` in the config.

## ⚠️ Disclaimer

This tool is intended for educational, research, and legitimate testing purposes ONLY. Modifying device properties and installing software can have unintended consequences. The user is solely responsible for their actions and for complying with all applicable laws. The authors assume no liability for any misuse of this software.
=======
# ADB APK Installer & Spoofer v4.1.1 (Phoenix) 🔥

<div align="center">

```ascii
 █████╗ ██████╗ ██████╗     █████╗ ██████╗ ██╗  ██╗
██╔══██╗██╔══██╗██╔══██╗   ██╔══██╗██╔══██╗██║ ██╔╝
███████║██║  ██║██████╔╝   ███████║██████╔╝█████╔╝ 
██╔══██║██║  ██║██╔══██╗   ██╔══██║██╔═══╝ ██╔═██╗ 
██║  ██║██████╔╝██████╔╝   ██║  ██║██║     ██║  ██╗
╚═╝  ╚═╝╚═════╝ ╚═════╝    ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
        Professional Interactive APK Installation Tool
                    v4.1.1 (Phoenix) 🔥
```

**🚀 A comprehensive, interactive command-line tool for installing Android applications and dynamically spoofing device identity**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/aaronvstory/ADB-APK-Installer-Spoofer)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/aaronvstory/ADB-APK-Installer-Spoofer/graphs/commit-activity)

</div>

---

## 🌟 What Makes This Special?

This isn't just another APK installer. **Phoenix v4.1.1** combines the power of professional Android development tools with an intuitive, interactive interface that makes complex device spoofing and app testing accessible to everyone.

### 🎯 **Core Philosophy**
Moving beyond simple `adb install` commands, this tool provides a **two-pronged approach** to comprehensive Android testing:

1. **🔒 User Profile Isolation** - Create clean, isolated user environments for testing
2. **🎭 Advanced Property Spoofing** - Fundamentally alter device identity for thorough compatibility testing

---

## ✨ Key Features

### 📦 **Universal APK Installer**
- 🎯 **Multi-Format Support** - Seamlessly handles `.apk`, `.xapk`, `.apkm`, and `.zip` files
- 🧩 **Intelligent Split-APK Handling** - Auto-parses bundles and selects correct architecture splits
- 📱 **OBB Integration** - Automatically extracts and places OBB files for games and large apps
- 🎛️ **Interactive Menus** - Beautiful `questionary`-powered selection interfaces
- ⚡ **Batch Operations** - Install multiple apps across multiple devices simultaneously
- 🔄 **Smart Retry Logic** - Automatic conflict resolution and installation retries

### 🎭 **Advanced Spoofing System**

#### 👤 **User Profile Management**
- 🆕 **Ephemeral Users** (Android 8+) - Temporary profiles that auto-delete on reboot
- 🔐 **Isolated Testing** - Create clean environments without affecting primary user
- 🎲 **Random Android ID** - Automatic generation for enhanced privacy
- 🧹 **Session Cleanup** - Automatic restoration to original state

#### 🔧 **Magisk Property Spoofing** (Root Required)
- 🏭 **Manufacturer Spoofing** - Emulate Samsung, Google, Xiaomi, and more
- 📱 **Model Simulation** - Dynamic generation of realistic device properties
- 🔢 **Build Fingerprint** - Complete system identity transformation
- 💾 **Safe Backup & Restore** - Reliable property backup with verification
- 🛡️ **Multi-Root Support** - Compatible with Magisk, APatch, and KernelSU

### 🎨 **Premium User Experience**
- 🌈 **Rich Console UI** - Beautiful formatting with the `rich` library
- 🚀 **Auto-Dependency Installation** - Seamless first-run setup
- 📊 **Real-time Status** - Live progress indicators and detailed logging
- 🔍 **Smart Detection** - Automatic capability scanning for connected devices
- ⚙️ **Interactive Configuration** - Visual settings management without file editing
- 📋 **Phone Management Tools** - PC-to-Android clipboard and utilities

---

## 🚀 Quick Start Guide

### 📋 **Prerequisites**
- 🐍 **Python 3.7+** - [Download here](https://www.python.org/downloads/)
- 🔧 **ADB (Android Debug Bridge)** - Must be in your system PATH
- 📱 **Android Device** with USB Debugging enabled

### 💾 **Installation**

1. **📥 Clone the Repository**
   ```bash
   git clone https://github.com/aaronvstory/ADB-APK-Installer-Spoofer.git
   cd ADB-APK-Installer-Spoofer
   ```

2. **📂 Prepare Your APKs**
   - Place your `.apk`, `.xapk`, `.apkm`, or `.zip` files in the `apks/` directory
   - The script will create this folder automatically if it doesn't exist

3. **🎬 Launch the Tool**
   
   **Windows:**
   ```cmd
   python apk_installer.py
   ```
   
   **Linux/macOS:**
   ```bash
   python3 apk_installer.py
   ```

### 🎉 **First Run Experience**
The script will automatically:
- ✅ Detect and install missing Python dependencies (`rich`, `questionary`, `pyaxmlparser`)
- 📄 Create default configuration files (`config.ini`, `device_patterns.json`)
- 🔍 Scan for connected Android devices
- 📁 Set up the APK directory structure

---

## 📖 Usage Guide

### 🎯 **Basic APK Installation**

1. **📱 Connect Device** - Enable USB Debugging and connect via USB
2. **📁 Add APKs** - Place files in the `apks/` folder
3. **▶️ Run Script** - Execute `python apk_installer.py`
4. **🎛️ Select Options** - Use interactive menus to choose devices and apps
5. **🚀 Install** - Watch the magic happen with real-time progress

### 🎮 **Interactive Menu System**

- **📱 Single Selection** - Use arrow keys ↑↓, press Enter to select
- **📦 Multi-Selection** - Use spacebar to toggle selections, Enter to confirm
- **⚡ Auto-Selection** - Single items are automatically selected for convenience

### 🎭 **Advanced Spoofing Workflow**

1. **⚙️ Configure Spoofing** - Choose "Configure Advanced Spoofing" from main menu
2. **🔧 Select Features**:
   - 👤 **User Profile Spoofing** - Create isolated testing environments
   - 🎭 **Magisk Property Spoofing** - Transform device identity (requires root)
3. **🏭 Choose Target** - Select manufacturer (Samsung, Google, Xiaomi, etc.)
4. **📱 Pick Model** - Choose specific device or let the script pick randomly
5. **🤖 Set Android Version** - Target specific Android versions for testing
6. **🚀 Install & Test** - Your apps now see a completely different device!

---

## ⚙️ Configuration Deep Dive

### 📄 **config.ini - Main Settings**

<details>
<summary>🔧 <strong>Click to expand configuration sections</strong></summary>

#### 📁 **[PATHS] - Directory Settings**
```ini
apk_directory = apks          # Folder to scan for installation files
adb_path = adb               # Path to ADB executable
```

#### 🎛️ **[OPTIONS] - Installation Behavior**
```ini
replace_existing = true                    # Allow app updates/downgrades
auto_grant_permissions = true              # Auto-grant app permissions
prompt_uninstall_on_conflict = true        # Ask to uninstall conflicting apps
package_parser = pyaxmlparser              # APK metadata parser engine
```

#### 👤 **[UNIQUENESS] - User Profile Management**
```ini
enable_uniqueness_features = true         # Master switch for user profiles
cleanup_user_profile_after_session = true # Auto-remove created users
auto_set_random_android_id = true         # Generate random Android ID
user_creation_retries = 3                 # Retry attempts for user creation
validate_user_switch = true               # Verify user switches work
```

#### 🎭 **[ADVANCED_SPOOFING] - Property Spoofing**
```ini
enable_magisk_resetprop = true            # Master switch for property spoofing
backup_original_properties = true         # Safe backup before changes
use_ephemeral_users = false               # Use temporary users (Android 8+)
spoof_manufacturer = samsung              # Target manufacturer
spoof_model =                             # Specific model (blank = random)
spoof_android_version = 13                # Target Android version
```

</details>

### 📱 **device_patterns.json - Spoofing Brain**

This file contains the intelligence behind realistic device spoofing:

- **🏭 Manufacturers** - Samsung, Google, Xiaomi patterns with realistic codenames
- **📱 Device Models** - Complete model databases with proper hardware specs  
- **🔢 Build Patterns** - Authentic build ID formats per Android version
- **🎯 Property Lists** - Comprehensive property keys for spoofing

<details>
<summary>📱 <strong>Supported Manufacturer Patterns</strong></summary>

- **Samsung** - Galaxy S series, Note series, A series, tablets
- **Google** - Pixel phones, Nexus devices
- **Xiaomi** - Mi series, Redmi, POCO devices
- **OnePlus** - Flagship and Nord series
- **Huawei** - P series, Mate series, Honor devices
- **Custom** - Add your own device definitions

</details>

---

## 🛠️ Advanced Features

### 🔑 **Root-Powered Capabilities**
When root access is detected, unlock these premium features:

- **🎭 Deep Property Spoofing** - Modify core system properties
- **👥 User Limit Bypass** - Create unlimited user profiles  
- **🧹 Advanced Cleanup** - Complete system state restoration
- **🔐 Enhanced Privacy** - Deeper Android ID randomization

### 🌐 **Multi-Device Management**
- **📱 Parallel Installation** - Deploy to multiple devices simultaneously
- **🔍 Smart Detection** - Automatic capability assessment per device
- **📊 Status Tracking** - Real-time progress across all targets
- **⚙️ Per-Device Config** - Individual settings for each connected device

### 🛡️ **Enterprise-Grade Error Handling**
- **🔄 Smart Retry Logic** - Automatic recovery from common failures
- **📝 Detailed Logging** - Comprehensive error reporting with solutions
- **🔌 Connection Management** - Graceful handling of device disconnections
- **📊 Status Monitoring** - Real-time feedback on all operations

---

## 🐛 Troubleshooting Guide

### ❗ **Common Issues & Solutions**

<details>
<summary>🔍 <strong>Click to expand troubleshooting guide</strong></summary>

#### 📱 **"No devices found"**
- ✅ Enable **USB Debugging** in Developer Options
- 🔌 Try a different USB cable (data transfer, not just charging)
- 🖥️ Run `adb devices` to verify ADB connection
- 📱 Check device screen for authorization prompt
- 🔄 Restart ADB service: `adb kill-server && adb start-server`

#### ❌ **"Installation failed: INSTALL_FAILED_MISSING_SPLIT"**
- 📦 You're installing a split APK that needs additional components
- 🔄 For XAPK/APKM files: Script will auto-retry with all components
- 📁 For single APKs: Ensure you have the complete app bundle

#### 🎭 **"Property spoofing failed"**
- 🔑 Requires **rooted device** with working su access
- ⚙️ Verify Magisk/APatch/KernelSU installation
- 🛠️ Ensure `resetprop` command is available
- 🔍 Check root detection: Run script and verify "Root Access: ✓"

#### 👤 **"User creation failed"**
- 📱 Enable **Multiple users** in Settings
- 🔓 Device must be **unlocked** during user creation
- 💾 Ensure sufficient storage space (500MB+ recommended)
- 🔢 Check current user count: Some devices have limits

#### 🐍 **Python/Dependency Issues**
- 📊 Missing Rich: `pip install rich`
- ❓ Missing Questionary: `pip install questionary`
- 📱 Missing APK Parser: `pip install pyaxmlparser`
- 🔄 Or let the script auto-install on first run

</details>

### 🔧 **Debug Mode**
Enable verbose logging for troubleshooting:
```bash
python apk_installer.py --debug
```

---

## 📊 System Requirements

### 💻 **Host System**
| Component | Requirement | Recommended |
|-----------|-------------|-------------|
| **OS** | Windows 10+, Linux, macOS | Latest versions |
| **Python** | 3.7+ | 3.9+ |
| **RAM** | 2GB | 4GB+ |
| **Storage** | 100MB | 1GB+ (for APK cache) |
| **ADB** | Latest platform-tools | Android SDK |

### 📱 **Target Device**
| Feature | Requirement | Notes |
|---------|-------------|-------|
| **Android Version** | 7.0+ (API 24) | Recommended 8.0+ for full features |
| **USB Debugging** | ✅ Required | Enable in Developer Options |
| **Root Access** | Optional | Required for property spoofing |
| **Multi-user** | Optional | Required for user profile features |
| **Storage** | 500MB+ free | For app installation and user profiles |

---

## 🤝 Contributing

We welcome contributions! Here's how to get involved:

### 🚀 **Quick Contribution Guide**
1. **🍴 Fork** the repository
2. **🌿 Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **💻 Code** your improvements
4. **✅ Test** thoroughly on multiple devices
5. **📝 Commit** with clear messages (`git commit -m 'Add amazing feature'`)
6. **📤 Push** to your branch (`git push origin feature/amazing-feature`)
7. **🔄 Submit** a Pull Request

### 🎯 **Areas We Need Help**
- 📱 Additional device patterns and manufacturers
- 🌍 Internationalization and localization
- 🧪 Testing on various Android versions and devices
- 📚 Documentation improvements
- 🐛 Bug fixes and performance optimizations

### 🏆 **Contributor Recognition**
All contributors will be credited in our [Contributors](CONTRIBUTORS.md) file!

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

**TL;DR**: You can use, modify, and distribute this software freely, just keep the original copyright notice.

---

## ⚠️ Important Disclaimer

**🔒 For Educational and Legal Testing Only**

This tool is designed for:
- ✅ **App developers** testing compatibility across devices
- ✅ **Security researchers** conducting authorized testing
- ✅ **QA engineers** validating app behavior
- ✅ **Personal use** on your own devices

**❌ NOT for:**
- Bypassing app restrictions or DRM
- Fraudulent activities or deception
- Violating terms of service
- Any illegal activities

**⚖️ Legal Notice**: Users are solely responsible for compliance with all applicable laws and regulations. The authors assume no liability for misuse of this software.

---

## 🙏 Acknowledgments & Credits

### 🏆 **Core Technologies**
- **🤖 Android Debug Bridge** - The foundation of Android development
- **🎨 Rich Library** - Beautiful terminal interfaces by [Will McGugan](https://github.com/willmcgugan)
- **❓ Questionary** - Interactive command-line prompts
- **📱 pyaxmlparser** - Python APK metadata parsing

### 🔧 **Root Solutions**
- **⚡ Magisk** - The gold standard for Android rooting by [topjohnwu](https://github.com/topjohnwu)
- **🛡️ APatch** - Modern kernel patching solution
- **👑 KernelSU** - Kernel-based root solution

### 🌟 **Special Thanks**
- **Android Developer Community** - For continuous innovation
- **XDA Developers** - For fostering Android development knowledge
- **Open Source Contributors** - Making tools like this possible

---

## 📞 Support & Community

### 🆘 **Getting Help**

1. **📖 Documentation** - Check this README and inline help first
2. **🔍 Search Issues** - Look through [existing GitHub issues](https://github.com/aaronvstory/ADB-APK-Installer-Spoofer/issues)
3. **🆕 Create Issue** - [Open a new issue](https://github.com/aaronvstory/ADB-APK-Installer-Spoofer/issues/new) with:
   - 📱 Device model and Android version
   - 💻 Host OS and Python version  
   - 📝 Complete error messages
   - 🔄 Steps to reproduce the issue

### 🌐 **Connect With Us**
- **⭐ Star** this repo if it helped you!
- **🐛 Report bugs** via GitHub Issues
- **💡 Suggest features** through feature requests
- **🤝 Contribute** code improvements

---

<div align="center">

### 🎉 **Thank you for using ADB APK Installer & Spoofer!**

**Made with ❤️ for the Android development community**

*If this tool saved you time or helped your project, consider giving it a ⭐!*

---

**🔥 Phoenix v4.1.1** - *Rising from the ashes of complexity to bring you simplicity*

</div>
>>>>>>> 6a8bad17e3946e45be898298ba507f3bd82e40a6
