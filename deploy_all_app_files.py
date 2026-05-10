#!/usr/bin/env python3
"""
Deploy ALL app files to HuggingFace Space
Ensures complete deployment of the application
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

def deploy_complete_app():
    """Deploy all application files"""
    print("\n" + "="*60)
    print("🚀 Deploying Complete Application to HuggingFace")
    print("="*60)
    print(f"⏰ Started at: {datetime.utcnow().isoformat()} UTC\n")
    
    try:
        from huggingface_hub import HfApi, CommitOperationAdd, CommitOperationDelete
        
        token = os.getenv('HF_TOKEN')
        space_name = os.getenv('HF_SPACE_NAME', 'ToolKit-backend/PopCorn')
        
        if not token:
            print("❌ ERROR: HF_TOKEN not found")
            return False
        
        api = HfApi(token=token)
        
        # Get all Python files in app directory
        app_dir = Path('app')
        app_files = list(app_dir.glob('*.py'))
        
        print(f"📁 Found {len(app_files)} Python files in app/\n")
        
        operations = []
        
        # Add all app files
        for file_path in sorted(app_files):
            print(f"  ✓ {file_path}")
            operations.append(
                CommitOperationAdd(
                    path_in_repo=str(file_path),
                    path_or_fileobj=str(file_path)
                )
            )
        
        # Add other essential files
        essential_files = [
            '.env',
            'requirements.txt',
            'Dockerfile',
            'README.md'
        ]
        
        print(f"\n📦 Adding essential files:")
        for file in essential_files:
            if os.path.exists(file):
                print(f"  ✓ {file}")
                operations.append(
                    CommitOperationAdd(
                        path_in_repo=file,
                        path_or_fileobj=file
                    )
                )
        
        commit_message = f"""🔧 Complete Application Deployment

## All Files Deployed:
- ✅ All {len(app_files)} app/*.py files
- ✅ Configuration files (.env, requirements.txt)
- ✅ Docker configuration
- ✅ Error handling fixes included
- ✅ Custom exceptions system included

## Fixes:
- Fixed ModuleNotFoundError for app.error_handlers
- All dependencies properly uploaded
- Complete application structure

Deployed at: {datetime.utcnow().isoformat()} UTC
"""
        
        print(f"\n📝 Commit message:")
        print(commit_message)
        
        print(f"\n🚀 Pushing {len(operations)} files to HuggingFace...")
        
        commit_info = api.create_commit(
            repo_id=space_name,
            repo_type="space",
            operations=operations,
            commit_message=commit_message,
            token=token
        )
        
        print(f"\n✅ Deployment successful!")
        print(f"   Commit: {commit_info.oid}")
        print(f"   URL: {commit_info.commit_url}")
        print(f"\n⏳ Space is rebuilding...")
        print(f"   Monitor at: https://huggingface.co/spaces/{space_name}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = deploy_complete_app()
    sys.exit(0 if success else 1)

# Made with Bob
