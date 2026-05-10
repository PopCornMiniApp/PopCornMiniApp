#!/usr/bin/env python3
"""
Deploy Fixed Bot Files to HuggingFace Space
Uploads app/bot.py and app/bot_commands.py to HuggingFace Space
"""
import os
import sys
from huggingface_hub import HfApi, login
from pathlib import Path
import time
from dotenv import load_dotenv

def deploy_fixed_files():
    """Deploy the fixed bot files to HuggingFace Space."""
    
    print("🚀 Starting deployment of fixed bot files to HuggingFace Space...")
    print("=" * 70)
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Get HuggingFace token and space name
    hf_token = os.getenv("HF_TOKEN")
    space_repo = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
    
    if not hf_token:
        print("❌ Error: HF_TOKEN environment variable not set")
        print("   Please check your .env file")
        return False
    
    if not space_repo:
        print("❌ Error: HF_SPACE_NAME environment variable not set")
        print("   Please check your .env file")
        return False
    
    try:
        # Login to HuggingFace
        print("\n📝 Logging in to HuggingFace...")
        login(token=hf_token)
        api = HfApi()
        
        # Files to upload
        files_to_upload = [
            ("app/bot.py", "app/bot.py"),
            ("app/bot_commands.py", "app/bot_commands.py")
        ]
        
        print(f"\n📦 Uploading files to {space_repo}...")
        print("-" * 70)
        
        for local_path, repo_path in files_to_upload:
            if not os.path.exists(local_path):
                print(f"❌ File not found: {local_path}")
                continue
            
            print(f"\n📤 Uploading {local_path} -> {repo_path}")
            
            try:
                api.upload_file(
                    path_or_fileobj=local_path,
                    path_in_repo=repo_path,
                    repo_id=space_repo,
                    repo_type="space",
                    token=hf_token,
                    commit_message=f"Fix: Deploy corrected {os.path.basename(local_path)} with proper database calls"
                )
                print(f"✅ Successfully uploaded {local_path}")
                time.sleep(1)  # Small delay between uploads
                
            except Exception as e:
                print(f"❌ Error uploading {local_path}: {e}")
                return False
        
        print("\n" + "=" * 70)
        print("✅ All files uploaded successfully!")
        print("\n📊 Deployment Summary:")
        print(f"   • Space: {space_repo}")
        print(f"   • Files uploaded: {len(files_to_upload)}")
        print(f"   • Status: Success")
        
        print("\n🔄 Space will rebuild automatically...")
        print("   Monitor at: https://huggingface.co/spaces/jamalfit/PopCorn")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_fixed_files()
    sys.exit(0 if success else 1)

# Made with Bob
