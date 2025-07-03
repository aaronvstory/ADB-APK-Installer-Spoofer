#!/usr/bin/env python3
"""
Test script for DeviceSpoofingManager to verify the fix for android_version KeyError
"""

import configparser
from apk_installer import DeviceSpoofingManager

def test_generate_fingerprint():
    # Create a minimal config for testing
    config = configparser.ConfigParser()
    config.add_section("ADVANCED_SPOOFING")
    config.set("ADVANCED_SPOOFING", "backup_original_properties", "true")
    config.set("ADVANCED_SPOOFING", "spoof_build_fingerprint", "true")
    config.set("ADVANCED_SPOOFING", "spoof_android_id_magisk", "true")
    config.set("ADVANCED_SPOOFING", "spoof_device_model", "true")
    config.set("ADVANCED_SPOOFING", "spoof_android_version_props", "true")
    
    # Create the DeviceSpoofingManager instance
    spoofing_manager = DeviceSpoofingManager(config=config)
    
    # Test model data
    test_model_data = {
        "product": "test_product",
        "device": "test_device",
        "model": "TestModel",
        "board": "test_board",
        "display_name": "Test Phone",
        "hardware": "test_hw",
    }
    
    # Test generating a fingerprint with the target_android_version_key
    try:
        fingerprint = spoofing_manager.generate_realistic_fingerprint(
            "google", test_model_data, "13"
        )
        print(f"Successfully generated fingerprint: {fingerprint}")
        return True
    except KeyError as e:
        print(f"KeyError occurred: {e}")
        return False

if __name__ == "__main__":
    print("Testing DeviceSpoofingManager fingerprint generation...")
    success = test_generate_fingerprint()
    print(f"Test {'succeeded' if success else 'failed'}")
