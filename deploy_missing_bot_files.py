#!/usr/bin/env python3
"""
Deploy Missing Bot Files to Hugging Face
Fixes the RUNTIME_ERROR by uploading bot_tracking.py and button_builders.py
"""
import os
from huggingface_hub import HfApi
from datetime import datetime

SPACE_ID = "ToolKit-backend/PopCorn"
HF_TOKEN = os.getenv("HF_TOKEN")

def deploy_missing_files():
    """Deploy bot_tracking.py and button_builders.py"""
    print("="*70)
    print("  🚀 DEPLOYING MISSING BOT FILES")
    print("="*70)
    print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    api = HfApi(token=HF_TOKEN)
    
    missing_files = [
        ("app/bot_tracking.py", "Bot tracking module"),
        ("app/button_builders.py", "Button builders module")
    ]
    
    print(f"\n📦 Deploying to: {SPACE_ID}")
    print("-"*70)
    
    success_count = 0
    
    for file_path, description in missing_files:
        try:
            print(f"\n📤 Uploading {description}...")
            print(f"   File: {file_path}")
            
            # Check if file exists locally
            if not os.path.exists(file_path):
                print(f"   ❌ File not found locally: {file_path}")
                continue
            
            # Get file size
            file_size = os.path.getsize(file_path)
            print(f"   Size: {file_size:,} bytes")
            
            # Upload file
            api.upload_file(
                path_or_fileobj=file_path,
                path_in_repo=file_path,
                repo_id=SPACE_ID,
                repo_type="space",
                token=HF_TOKEN,
                commit_message=f"Add missing {description}"
            )
            
            print(f"   ✅ Successfully uploaded!")
            success_count += 1
            
        except Exception as e:
            print(f"   ❌ Error uploading {file_path}: {e}")
    
    print("\n" + "="*70)
    print("  📊 DEPLOYMENT SUMMARY")
    print("="*70)
    print(f"\n✅ Successfully deployed: {success_count}/{len(missing_files)} files")
    
    if success_count == len(missing_files):
        print("\n🎉 All missing files deployed successfully!")
        print("\n📝 Next steps:")
        print("   1. Wait for Space to rebuild (2-3 minutes)")
        print("   2. Check Space status")
        print("   3. Verify bot is running")
        print(f"\n🌐 Monitor at: https://huggingface.co/spaces/{SPACE_ID}")
        return True
    else:
        print("\n⚠️  Some files failed to deploy")
        print("   Please check the errors above and try again")
        return False

def main():
    try:
        success = deploy_missing_files()
        
        print("\n" + "="*70)
        print(f"  ⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70 + "\n")
        
        return success
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

# Made with Bob
