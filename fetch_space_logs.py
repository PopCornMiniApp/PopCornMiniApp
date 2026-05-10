#!/usr/bin/env python3
"""
Fetch and analyze Hugging Face Space logs
"""
import os
from huggingface_hub import HfApi
import json
from datetime import datetime

SPACE_ID = "ToolKit-backend/PopCorn"
HF_TOKEN = os.getenv("HF_TOKEN")


def fetch_logs():
    """Fetch Space runtime logs"""
    print("="*70)
    print("  📋 FETCHING SPACE LOGS")
    print("="*70)
    
    try:
        api = HfApi(token=HF_TOKEN)
        
        # Get space info
        print(f"\n🔍 Fetching info for: {SPACE_ID}")
        space_info = api.space_info(SPACE_ID)
        
        print(f"\n📊 Space Information:")
        print(f"   ID: {space_info.id}")
        print(f"   Author: {space_info.author}")
        print(f"   SDK: {space_info.sdk}")
        
        if space_info.runtime:
            runtime = space_info.runtime
            print(f"\n🔧 Runtime Status:")
            print(f"   Stage: {runtime.stage}")
            print(f"   Hardware: {runtime.hardware}")
            
            if hasattr(runtime, 'error_message') and runtime.error_message:
                print(f"\n❌ ERROR MESSAGE:")
                print(f"   {runtime.error_message}")
            
            if hasattr(runtime, 'resources') and runtime.resources:
                print(f"\n💾 Resources:")
                print(f"   {runtime.resources}")
        
        # Try to get logs via API
        print(f"\n📜 Attempting to fetch logs...")
        
        # Note: Logs might not be directly accessible via API
        # We need to check the Space's files for any log outputs
        
        files = api.list_repo_files(SPACE_ID, repo_type="space")
        log_files = [f for f in files if 'log' in f.lower() or f.endswith('.log')]
        
        if log_files:
            print(f"\n📁 Found log files:")
            for log_file in log_files:
                print(f"   - {log_file}")
        else:
            print(f"\n⚠️  No log files found in repository")
        
        # Check for common error indicators in files
        print(f"\n🔍 Checking for error indicators...")
        
        # Save space info to file
        report = {
            "timestamp": datetime.now().isoformat(),
            "space_id": SPACE_ID,
            "stage": runtime.stage if space_info.runtime else "unknown",
            "hardware": runtime.hardware if space_info.runtime else "unknown",
            "error_message": runtime.error_message if (space_info.runtime and hasattr(runtime, 'error_message')) else None,
            "sdk": space_info.sdk,
            "log_files": log_files
        }
        
        with open("space_logs_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved to: space_logs_report.json")
        
        # Provide recommendations based on error
        print(f"\n" + "="*70)
        print("  💡 DIAGNOSIS & RECOMMENDATIONS")
        print("="*70)
        
        if runtime.stage == "RUNTIME_ERROR":
            print("\n❌ RUNTIME_ERROR detected")
            print("\nCommon causes:")
            print("   1. Import errors (missing dependencies)")
            print("   2. Configuration errors (missing env variables)")
            print("   3. Code errors (syntax or runtime exceptions)")
            print("   4. Port binding issues")
            print("   5. Bot token issues")
            
            print("\n📝 Recommended actions:")
            print("   1. Check Space logs on Hugging Face web interface")
            print("   2. Verify all environment variables are set")
            print("   3. Check bot_commands.py for import errors")
            print("   4. Verify Dockerfile CMD is correct")
            print("   5. Test bot locally first")
            
            print(f"\n🌐 Check logs at:")
            print(f"   https://huggingface.co/spaces/{SPACE_ID}/logs")
        
        return report
        
    except Exception as e:
        print(f"\n❌ Error fetching logs: {e}")
        return None


def check_bot_commands_file():
    """Check the deployed bot_commands.py file"""
    print("\n" + "="*70)
    print("  📄 CHECKING BOT_COMMANDS.PY")
    print("="*70)
    
    try:
        # Try to read the file content
        file_path = "app/bot_commands.py"
        print(f"\n🔍 Checking: {file_path}")
        
        # Download and check the file
        from huggingface_hub import hf_hub_download
        
        local_file = hf_hub_download(
            repo_id=SPACE_ID,
            filename=file_path,
            repo_type="space",
            token=HF_TOKEN
        )
        
        with open(local_file, 'r') as f:
            content = f.read()
        
        print(f"✅ File found, size: {len(content)} bytes")
        
        # Check for common issues
        issues = []
        
        if "from telegram" not in content.lower():
            issues.append("Missing telegram imports")
        
        if "async def" not in content:
            issues.append("No async functions found")
        
        if "__all__" not in content:
            issues.append("Missing __all__ export")
        
        if issues:
            print(f"\n⚠️  Potential issues found:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print(f"\n✅ No obvious issues detected in bot_commands.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error checking bot_commands.py: {e}")
        return False


def main():
    print("\n" + "="*70)
    print("  🚀 SPACE LOGS ANALYZER")
    print("="*70)
    print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Fetch logs
    report = fetch_logs()
    
    # Check bot_commands.py
    check_bot_commands_file()
    
    print("\n" + "="*70)
    print(f"  ⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    if report and report.get("stage") == "RUNTIME_ERROR":
        print("⚠️  Action required: Fix runtime errors before bot can start")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

# Made with Bob
