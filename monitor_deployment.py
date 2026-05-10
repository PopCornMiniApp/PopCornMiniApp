#!/usr/bin/env python3
"""
Monitor HuggingFace Space Deployment
Checks build status and fetches logs after deployment
"""
import os
import sys
import time
from huggingface_hub import HfApi
from dotenv import load_dotenv
import requests

def get_space_status(api, space_repo):
    """Get the current status of the Space."""
    try:
        space_info = api.space_info(space_repo)
        return space_info.runtime.stage if space_info.runtime else "UNKNOWN"
    except Exception as e:
        print(f"Error getting space status: {e}")
        return "ERROR"

def fetch_space_logs(space_repo, hf_token):
    """Fetch logs from the Space."""
    try:
        # Get logs from HuggingFace API
        url = f"https://huggingface.co/api/spaces/{space_repo}/runtime/logs"
        headers = {"Authorization": f"Bearer {hf_token}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to fetch logs: {response.status_code}"
    except Exception as e:
        return f"Error fetching logs: {e}"

def monitor_deployment():
    """Monitor the deployment and check logs."""
    
    print("🔍 Monitoring HuggingFace Space Deployment...")
    print("=" * 70)
    
    # Load environment variables
    load_dotenv()
    
    hf_token = os.getenv("HF_TOKEN")
    space_repo = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
    
    if not hf_token:
        print("❌ Error: HF_TOKEN not set")
        return False
    
    try:
        api = HfApi()
        
        print(f"\n📦 Space: {space_repo}")
        print(f"🔗 URL: https://huggingface.co/spaces/{space_repo}")
        print("\n" + "-" * 70)
        
        # Monitor build status
        print("\n⏳ Checking build status...")
        max_checks = 10
        check_interval = 10  # seconds
        
        for i in range(max_checks):
            status = get_space_status(api, space_repo)
            timestamp = time.strftime("%H:%M:%S")
            
            print(f"[{timestamp}] Build Status: {status}")
            
            if status == "RUNNING":
                print("\n✅ Space is RUNNING!")
                break
            elif status == "BUILDING":
                print(f"   Building... (check {i+1}/{max_checks})")
            elif status == "BUILD_ERROR":
                print("\n❌ Build failed!")
                break
            elif status == "STOPPED":
                print("\n⚠️  Space is stopped")
                break
            
            if i < max_checks - 1:
                time.sleep(check_interval)
        
        # Fetch and display logs
        print("\n" + "-" * 70)
        print("📋 Fetching Space Logs...")
        print("-" * 70)
        
        logs = fetch_space_logs(space_repo, hf_token)
        
        # Display last 50 lines of logs
        log_lines = logs.split('\n')
        recent_logs = log_lines[-50:] if len(log_lines) > 50 else log_lines
        
        for line in recent_logs:
            if line.strip():
                # Highlight errors and warnings
                if "error" in line.lower() or "failed" in line.lower():
                    print(f"❌ {line}")
                elif "warning" in line.lower():
                    print(f"⚠️  {line}")
                elif "success" in line.lower() or "running" in line.lower():
                    print(f"✅ {line}")
                else:
                    print(f"   {line}")
        
        print("\n" + "=" * 70)
        print("✅ Monitoring complete!")
        print(f"\n🔗 View full logs at: https://huggingface.co/spaces/{space_repo}/logs")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during monitoring: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = monitor_deployment()
    sys.exit(0 if success else 1)

# Made with Bob
