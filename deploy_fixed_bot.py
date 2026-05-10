#!/usr/bin/env python3
"""
PopCorn Bot - Critical Fix Deployment Script
Deploys the fixed bot.py with compatible database calls to Hugging Face.
"""
import os
import sys
import time
import json
from datetime import datetime
from huggingface_hub import HfApi, login

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN")
HF_SPACE = "ToolKit-backend/PopCorn"
REPO_TYPE = "space"

# Files to deploy
FILES_TO_DEPLOY = [
    "app/bot.py",  # Fixed bot with compatible database calls
]

def print_header(text):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")

def print_step(step_num, total_steps, description):
    """Print step information."""
    print(f"\n[{step_num}/{total_steps}] {description}")
    print("-" * 80)

def deploy_file(api, file_path, space_id):
    """Deploy a single file to Hugging Face Space."""
    try:
        print(f"📤 Uploading {file_path}...")
        
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=file_path,
            repo_id=space_id,
            repo_type=REPO_TYPE,
            commit_message=f"🔧 Fix: Deploy compatible {file_path}"
        )
        
        print(f"✅ Successfully uploaded {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error uploading {file_path}: {e}")
        return False

def check_space_status(api, space_id):
    """Check the current status of the Space."""
    try:
        print("🔍 Checking Space status...")
        space_info = api.space_info(repo_id=space_id)
        
        runtime = space_info.runtime
        print(f"   Status: {runtime.stage}")
        print(f"   Hardware: {runtime.hardware}")
        
        return runtime.stage
        
    except Exception as e:
        print(f"⚠️  Could not check Space status: {e}")
        return "unknown"

def main():
    """Main deployment function."""
    print_header("🚀 PopCorn Bot - Critical Fix Deployment")
    
    print("📋 Deployment Summary:")
    print(f"   Target Space: {HF_SPACE}")
    print(f"   Files to deploy: {len(FILES_TO_DEPLOY)}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    
    # Step 1: Authenticate
    print_step(1, 5, "Authentication")
    
    if not HF_TOKEN:
        print("❌ HF_TOKEN not found in environment variables")
        print("   Please set HF_TOKEN before running this script")
        return False
    
    try:
        login(token=HF_TOKEN)
        api = HfApi()
        print("✅ Successfully authenticated with Hugging Face")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False
    
    # Step 2: Check current Space status
    print_step(2, 5, "Pre-deployment Status Check")
    initial_status = check_space_status(api, HF_SPACE)
    
    # Step 3: Deploy files
    print_step(3, 5, "Deploying Fixed Files")
    
    deployment_results = {}
    success_count = 0
    
    for file_path in FILES_TO_DEPLOY:
        if not os.path.exists(file_path):
            print(f"⚠️  File not found: {file_path}")
            deployment_results[file_path] = {"success": False, "error": "File not found"}
            continue
        
        success = deploy_file(api, file_path, HF_SPACE)
        deployment_results[file_path] = {
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if success:
            success_count += 1
        
        time.sleep(2)  # Rate limiting
    
    # Step 4: Wait for rebuild
    print_step(4, 5, "Waiting for Space Rebuild")
    
    print("⏳ Waiting 30 seconds for Space to start rebuilding...")
    time.sleep(30)
    
    print("🔄 Checking rebuild status...")
    for i in range(6):  # Check for 3 minutes
        status = check_space_status(api, HF_SPACE)
        
        if status == "RUNNING":
            print("✅ Space is RUNNING!")
            break
        elif status in ["BUILDING", "STARTING"]:
            print(f"   Status: {status} - waiting...")
            time.sleep(30)
        else:
            print(f"   Status: {status}")
            time.sleep(30)
    
    # Step 5: Final report
    print_step(5, 5, "Deployment Report")
    
    print(f"\n📊 Deployment Statistics:")
    print(f"   Total files: {len(FILES_TO_DEPLOY)}")
    print(f"   Successful: {success_count}")
    print(f"   Failed: {len(FILES_TO_DEPLOY) - success_count}")
    
    print(f"\n📝 Detailed Results:")
    for file_path, result in deployment_results.items():
        status_icon = "✅" if result["success"] else "❌"
        print(f"   {status_icon} {file_path}")
        if not result["success"] and "error" in result:
            print(f"      Error: {result['error']}")
    
    # Save deployment report
    report = {
        "deployment_time": datetime.now().isoformat(),
        "space_id": HF_SPACE,
        "files_deployed": FILES_TO_DEPLOY,
        "results": deployment_results,
        "success_count": success_count,
        "total_count": len(FILES_TO_DEPLOY),
        "initial_status": initial_status,
        "fix_description": "Fixed database function calls to use actual signatures"
    }
    
    report_file = "bot_fix_deployment_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Deployment report saved to: {report_file}")
    
    # Final status
    print_header("🎯 Deployment Complete")
    
    if success_count == len(FILES_TO_DEPLOY):
        print("✅ All files deployed successfully!")
        print("\n📌 Next Steps:")
        print("   1. Monitor Space logs at: https://huggingface.co/spaces/ToolKit-backend/PopCorn/logs")
        print("   2. Test bot with /start command")
        print("   3. Verify movies and series browsing works")
        print("   4. Check Arabic UI is displaying correctly")
        return True
    else:
        print("⚠️  Some files failed to deploy")
        print("   Please check the errors above and retry")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Made with Bob
