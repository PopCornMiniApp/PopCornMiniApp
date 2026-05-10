#!/usr/bin/env python3
"""
Quick Setup Script for HuggingFace Space Variables
This script helps you set up all required environment variables in your HuggingFace Space.
"""

import os
import sys
import json
import requests
from getpass import getpass

def print_header():
    print("="*80)
    print("🚀 HuggingFace Space Variables Setup")
    print("="*80)
    print()

def print_section(title):
    print(f"\n{'='*80}")
    print(f"📋 {title}")
    print("="*80)

def get_hf_credentials():
    """Get HuggingFace credentials"""
    print_section("HuggingFace Authentication")
    
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("⚠️  HF_TOKEN not found in environment")
        hf_token = getpass("Enter your HuggingFace token (hf_xxx...): ").strip()
    else:
        print(f"✅ Using HF_TOKEN from environment")
    
    space_name = input("Enter Space name (e.g., username/space-name) [ToolKit-backend/PopCorn]: ").strip()
    if not space_name:
        space_name = "ToolKit-backend/PopCorn"
    
    return hf_token, space_name

def get_variable_value(name, description, example="", secret=True):
    """Get a variable value from user"""
    print(f"\n📝 {name}")
    print(f"   Description: {description}")
    if example:
        print(f"   Example: {example}")
    
    if secret:
        value = getpass(f"   Enter value (hidden): ").strip()
    else:
        value = input(f"   Enter value: ").strip()
    
    return value

def collect_variables():
    """Collect all required variables from user"""
    print_section("Collecting Required Variables")
    
    variables = {}
    
    # Telegram Bot Configuration
    print("\n🤖 Telegram Bot Configuration")
    print("-" * 80)
    
    variables["MAIN_BOT_TOKEN"] = get_variable_value(
        "MAIN_BOT_TOKEN",
        "Main bot token from @BotFather",
        "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    )
    
    variables["ADMIN_ID"] = get_variable_value(
        "ADMIN_ID",
        "Your Telegram user ID (get from @userinfobot)",
        "123456789",
        secret=False
    )
    
    variables["ADMIN_USERNAME"] = get_variable_value(
        "ADMIN_USERNAME",
        "Your Telegram username",
        "@username",
        secret=False
    )
    
    variables["PRIVATE_GROUP_ID"] = get_variable_value(
        "PRIVATE_GROUP_ID",
        "Private group ID where content is stored (get from @RawDataBot)",
        "-1001234567890",
        secret=False
    )
    
    variables["PUBLIC_CHANNEL_ID"] = get_variable_value(
        "PUBLIC_CHANNEL_ID",
        "Public channel ID for announcements",
        "-1003944402689",
        secret=False
    )
    
    # Pyrogram Sessions
    print("\n🔐 Pyrogram Sessions (for streaming)")
    print("-" * 80)
    
    variables["SESSION_1_API_ID"] = get_variable_value(
        "SESSION_1_API_ID",
        "Telegram API ID from https://my.telegram.org/apps",
        "12345678",
        secret=False
    )
    
    variables["SESSION_1_API_HASH"] = get_variable_value(
        "SESSION_1_API_HASH",
        "Telegram API Hash from https://my.telegram.org/apps",
        "abcdef1234567890abcdef1234567890"
    )
    
    # HuggingFace Configuration
    print("\n🤗 HuggingFace Configuration")
    print("-" * 80)
    
    hf_token = os.getenv("HF_TOKEN", "")
    if hf_token:
        variables["HF_TOKEN"] = hf_token
        print("✅ Using HF_TOKEN from environment")
    else:
        variables["HF_TOKEN"] = get_variable_value(
            "HF_TOKEN",
            "HuggingFace token with write access",
            "hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        )
    
    variables["HF_DATASET_NAME"] = get_variable_value(
        "HF_DATASET_NAME",
        "Dataset name for storing database",
        "ToolKit-backend/PopCornDB",
        secret=False
    )
    
    variables["HF_SPACE_NAME"] = get_variable_value(
        "HF_SPACE_NAME",
        "Space name",
        "ToolKit-backend/PopCorn",
        secret=False
    )
    
    # Optional: TMDB API
    print("\n🎬 TMDB API (Optional)")
    print("-" * 80)
    add_tmdb = input("Add TMDB API key? (y/n) [n]: ").strip().lower()
    if add_tmdb == 'y':
        variables["TMDB_API_KEY"] = get_variable_value(
            "TMDB_API_KEY",
            "TMDB API key from https://www.themoviedb.org/settings/api",
            "abcdef1234567890abcdef1234567890"
        )
    
    return variables

def set_space_variable(hf_token, space_name, key, value):
    """Set a variable in HuggingFace Space"""
    url = f"https://huggingface.co/api/spaces/{space_name}/variables"
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    data = {
        "key": key,
        "value": value,
        "description": f"Auto-configured by setup script"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code in [200, 201]:
            return True, "Success"
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        return False, str(e)

def apply_variables(hf_token, space_name, variables):
    """Apply all variables to HuggingFace Space"""
    print_section("Applying Variables to Space")
    
    success_count = 0
    failed_count = 0
    
    for key, value in variables.items():
        print(f"\n📤 Setting {key}...", end=" ")
        success, message = set_space_variable(hf_token, space_name, key, value)
        
        if success:
            print("✅")
            success_count += 1
        else:
            print(f"❌ {message}")
            failed_count += 1
    
    print(f"\n{'='*80}")
    print(f"📊 Results:")
    print(f"  ✅ Success: {success_count}")
    print(f"  ❌ Failed: {failed_count}")
    print("="*80)
    
    return success_count, failed_count

def save_to_env_file(variables):
    """Save variables to .env file for local testing"""
    print_section("Saving to .env File")
    
    env_file = ".env"
    
    try:
        with open(env_file, "w") as f:
            f.write("# Auto-generated by setup_space_variables.py\n")
            f.write(f"# Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
            
            for key, value in variables.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Variables saved to {env_file}")
        print(f"💡 You can use this file for local development")
        return True
    except Exception as e:
        print(f"❌ Failed to save .env file: {e}")
        return False

def main():
    """Main setup function"""
    print_header()
    
    print("This script will help you set up all required environment variables")
    print("for your HuggingFace Space.")
    print()
    print("⚠️  IMPORTANT: You will need:")
    print("  • HuggingFace token with write access")
    print("  • Telegram bot token from @BotFather")
    print("  • Your Telegram user ID")
    print("  • Private group ID")
    print("  • Pyrogram API credentials from https://my.telegram.org/apps")
    print()
    
    proceed = input("Ready to proceed? (y/n) [y]: ").strip().lower()
    if proceed == 'n':
        print("❌ Setup cancelled")
        sys.exit(0)
    
    # Get HuggingFace credentials
    hf_token, space_name = get_hf_credentials()
    
    # Collect all variables
    variables = collect_variables()
    
    # Show summary
    print_section("Summary")
    print(f"\n📦 Space: {space_name}")
    print(f"📝 Variables to set: {len(variables)}")
    print("\nVariables:")
    for key in variables.keys():
        print(f"  • {key}")
    
    print()
    confirm = input("Apply these variables to Space? (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        print("❌ Setup cancelled")
        sys.exit(0)
    
    # Apply variables
    success_count, failed_count = apply_variables(hf_token, space_name, variables)
    
    # Save to .env file
    save_local = input("\nSave variables to .env file for local testing? (y/n) [y]: ").strip().lower()
    if save_local != 'n':
        save_to_env_file(variables)
    
    # Final message
    print_section("Setup Complete!")
    
    if failed_count == 0:
        print("\n✅ All variables configured successfully!")
        print("\n📋 Next Steps:")
        print("  1. Go to your Space: https://huggingface.co/spaces/" + space_name)
        print("  2. Wait for Space to restart (automatic)")
        print("  3. Check logs for 'Telegram bot started' message")
        print("  4. Test bot with /start command in Telegram")
        print("\n🎉 Your bot should now be responsive!")
    else:
        print(f"\n⚠️  {failed_count} variables failed to set")
        print("\n💡 You can set them manually:")
        print(f"  1. Go to: https://huggingface.co/spaces/{space_name}/settings")
        print("  2. Scroll to 'Variables and secrets'")
        print("  3. Add each variable as a secret")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)

# Made with Bob
