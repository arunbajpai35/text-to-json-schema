#!/usr/bin/env python3
"""
Test script to validate configuration and dependencies
"""
import os
import sys
from configparser import ConfigParser

def test_config():
    """Test if configuration is properly set up"""
    print("🔍 Testing configuration...")
    
    # Check if config.ini exists
    if not os.path.exists("config.ini"):
        print("❌ config.ini not found. Please copy config.template.ini to config.ini and configure your Azure OpenAI settings.")
        return False
    
    # Load and validate config
    try:
        config = ConfigParser()
        config.read("config.ini")
        
        if "azure" not in config:
            print("❌ Azure configuration section not found in config.ini")
            return False
        
        azure_config = config["azure"]
        required_fields = ["api_key", "api_base", "deployment_name", "api_version"]
        
        for field in required_fields:
            value = azure_config.get(field, "")
            if not value or value == f"your-{field.replace('_', '-')}-here":
                print(f"❌ Please configure {field} in config.ini")
                return False
        
        print("✅ Configuration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Error reading config.ini: {e}")
        return False

def test_files():
    """Test if required files exist"""
    print("📁 Testing required files...")
    
    required_files = [
        "prompts/base_prompt.txt",
        "samples/input_large.txt",
        "utils/azure_llm.py",
        "utils/chunker.py",
        "utils/config_loader.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ All required files found!")
    return True

def test_dependencies():
    """Test if required Python packages are installed"""
    print("📦 Testing dependencies...")
    
    required_packages = [
        "openai",
        "backoff",
        "httpx"
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("💡 Run: pip install -r requirements.txt")
        return False
    
    print("✅ All dependencies installed!")
    return True

def main():
    print("🚀 Text-to-JSON Schema Configuration Test")
    print("=" * 50)
    
    config_ok = test_config()
    files_ok = test_files()
    deps_ok = test_dependencies()
    
    print("\n" + "=" * 50)
    if config_ok and files_ok and deps_ok:
        print("✅ All tests passed! You can now run: python main.py")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 