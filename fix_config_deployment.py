#!/usr/bin/env python3
"""
Fix config.py deployment to HuggingFace Spaces
Ensures SUBSCRIPTION_REQUIRED is available in the deployed config.py
"""

import os
import sys
from pathlib import Path
from huggingface_hub import HfApi, login

def deploy_config_fix():
    """Deploy the fixed config.py to HuggingFace Space"""
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    HF_TOKEN = os.getenv("HF_TOKEN")
    HF_SPACE_NAME = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
    
    if not HF_TOKEN:
        print("❌ Error: HF_TOKEN not found in environment variables")
        print("Please set HF_TOKEN in your .env file")
        return False
    
    print("=" * 80)
    print("🔧 Config.py Deployment Fix")
    print("=" * 80)
    print(f"Target Space: {HF_SPACE_NAME}")
    print()
    
    try:
        # Login to HuggingFace
        print("🔐 Logging in to HuggingFace...")
        login(token=HF_TOKEN)
        api = HfApi(token=HF_TOKEN)
        print("✅ Login successful")
        print()
        
        # Verify config.py exists locally
        config_path = Path("app/config.py")
        if not config_path.exists():
            print(f"❌ Error: {config_path} not found")
            return False
        
        # Read and verify SUBSCRIPTION_REQUIRED exists
        print("📖 Reading local config.py...")
        config_content = config_path.read_text()
        
        if "SUBSCRIPTION_REQUIRED" not in config_content:
            print("❌ Error: SUBSCRIPTION_REQUIRED not found in config.py")
            return False
        
        print("✅ SUBSCRIPTION_REQUIRED found in config.py")
        
        # Count the line where SUBSCRIPTION_REQUIRED is defined
        for i, line in enumerate(config_content.split('\n'), 1):
            if 'SUBSCRIPTION_REQUIRED = ' in line and not line.strip().startswith('#'):
                print(f"   Line {i}: {line.strip()}")
                break
        print()
        
        # Upload config.py to HuggingFace Space
        print("📤 Uploading config.py to HuggingFace Space...")
        api.upload_file(
            path_or_fileobj=str(config_path),
            path_in_repo="app/config.py",
            repo_id=HF_SPACE_NAME,
            repo_type="space",
            commit_message="Fix: Ensure SUBSCRIPTION_REQUIRED is available in config.py"
        )
        print("✅ config.py uploaded successfully")
        print()
        
        # Verify the upload
        print("🔍 Verifying deployment...")
        files = api.list_repo_files(HF_SPACE_NAME, repo_type="space")
        
        if "app/config.py" in files:
            print("✅ app/config.py confirmed in HuggingFace Space")
        else:
            print("⚠️  Warning: app/config.py not found in file list")
        print()
        
        print("=" * 80)
        print("✅ Deployment Complete!")
        print("=" * 80)
        print()
        print("📝 Next Steps:")
        print("1. Wait for HuggingFace Space to rebuild (usually 1-2 minutes)")
        print("2. Check the Space logs for any import errors")
        print("3. Test the application to ensure SUBSCRIPTION_REQUIRED works")
        print()
        print(f"🔗 Space URL: https://huggingface.co/spaces/{HF_SPACE_NAME}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error during deployment: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_config_fix()
    sys.exit(0 if success else 1)

# Made with Bob
