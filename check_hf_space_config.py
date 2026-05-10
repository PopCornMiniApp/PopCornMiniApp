#!/usr/bin/env python3
"""
Check HuggingFace Space Configuration and Logs
"""

import os
import sys
import json
import requests
from datetime import datetime

def check_space_config():
    """Check HuggingFace Space configuration"""
    print("🔍 Checking HuggingFace Space Configuration...")
    print("="*80)
    
    # Get credentials
    hf_token = os.getenv("HF_TOKEN")
    space_name = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
    
    if not hf_token:
        print("❌ ERROR: HF_TOKEN not found in environment")
        print("💡 Set HF_TOKEN to check Space configuration")
        return False
    
    headers = {"Authorization": f"Bearer {hf_token}"}
    
    # 1. Check Space Status
    print(f"\n📦 Space: {space_name}")
    try:
        url = f"https://huggingface.co/api/spaces/{space_name}"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            runtime = data.get("runtime", {})
            
            print(f"  Status: {runtime.get('stage', 'UNKNOWN')}")
            print(f"  Hardware: {runtime.get('hardware', 'N/A')}")
            print(f"  SDK: {data.get('sdk', 'N/A')}")
            
            if runtime.get('stage') != 'RUNNING':
                print(f"  ⚠️  Space is not RUNNING!")
        else:
            print(f"  ❌ Failed to get Space info: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # 2. Check Space Variables (Secrets)
    print(f"\n🔐 Checking Space Secrets...")
    try:
        url = f"https://huggingface.co/api/spaces/{space_name}/variables"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            variables = response.json()
            
            required_vars = [
                "MAIN_BOT_TOKEN",
                "HF_TOKEN", 
                "ADMIN_ID",
                "PRIVATE_GROUP_ID",
                "SESSION_1_API_ID",
                "SESSION_1_API_HASH"
            ]
            
            if isinstance(variables, list):
                var_names = [v.get("key") for v in variables]
                print(f"  Found {len(var_names)} variables")
                
                missing = []
                for var in required_vars:
                    if var in var_names:
                        print(f"  ✅ {var}")
                    else:
                        print(f"  ❌ {var} - MISSING")
                        missing.append(var)
                
                if missing:
                    print(f"\n  ⚠️  Missing {len(missing)} required variables!")
                    print(f"  💡 Add these in Space Settings → Variables and secrets")
                    return False
                else:
                    print(f"\n  ✅ All required variables are set")
            else:
                print(f"  ⚠️  Unexpected response format")
        else:
            print(f"  ❌ Failed to get variables: HTTP {response.status_code}")
            if response.status_code == 403:
                print(f"  💡 Token may not have permission to read Space secrets")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 3. Get Space Logs
    print(f"\n📋 Fetching Space Logs...")
    try:
        url = f"https://huggingface.co/api/spaces/{space_name}/runtime"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            runtime_data = response.json()
            
            # Try to get logs
            if "logs" in runtime_data:
                logs = runtime_data["logs"]
                print(f"  Found {len(logs)} log entries")
                
                # Show last 20 lines
                print(f"\n  📄 Last 20 log lines:")
                print("  " + "-"*76)
                for log in logs[-20:]:
                    print(f"  {log}")
                print("  " + "-"*76)
            else:
                print(f"  ⚠️  No logs available in runtime data")
                
            # Save full runtime data
            with open("space_runtime_data.json", "w") as f:
                json.dump(runtime_data, f, indent=2)
            print(f"\n  💾 Full runtime data saved to: space_runtime_data.json")
        else:
            print(f"  ❌ Failed to get runtime data: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 4. Check Space Files
    print(f"\n📁 Checking Space Files...")
    try:
        url = f"https://huggingface.co/api/spaces/{space_name}/tree/main"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            files = response.json()
            
            required_files = [
                "app/main.py",
                "app/config.py",
                "app/sync_bot.py",
                "app/bot_commands.py",
                "requirements.txt",
                "Dockerfile"
            ]
            
            file_paths = [f.get("path") for f in files if isinstance(f, dict)]
            
            print(f"  Found {len(file_paths)} files in Space")
            
            for req_file in required_files:
                if req_file in file_paths:
                    print(f"  ✅ {req_file}")
                else:
                    print(f"  ❌ {req_file} - MISSING")
        else:
            print(f"  ❌ Failed to get files: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    print("\n" + "="*80)
    return True


def main():
    """Main function"""
    print("🚀 HuggingFace Space Configuration Checker")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    success = check_space_config()
    
    if not success:
        print("\n❌ Configuration check failed!")
        print("💡 Please fix the issues above and try again")
        sys.exit(1)
    else:
        print("\n✅ Configuration check completed")
        sys.exit(0)


if __name__ == "__main__":
    main()

# Made with Bob
