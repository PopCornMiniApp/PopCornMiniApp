#!/usr/bin/env python3
"""
Deploy Complete Series Fix to HuggingFace
Uploads database and code changes
"""
import os
import sys
from huggingface_hub import HfApi, login
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_DATASET_REPO = "ToolKit-backend/PopCornDB"
HF_SPACE_REPO = "ToolKit-backend/PopCorn"
DB_PATH = "/tmp/popcorn.db"

def main():
    print("🚀 Deploying Complete Series Fix to HuggingFace\n")
    
    # Login
    print("🔐 Logging in to HuggingFace...")
    login(token=HF_TOKEN)
    api = HfApi()
    
    # 1. Upload database
    print("\n📤 Uploading updated database...")
    try:
        api.upload_file(
            path_or_fileobj=DB_PATH,
            path_in_repo="popcorn.db",
            repo_id=HF_DATASET_REPO,
            repo_type="dataset",
            commit_message="✅ Fix: Register all 9 series (25 seasons) - Scanner logic fixed"
        )
        print("✅ Database uploaded successfully")
    except Exception as e:
        print(f"❌ Database upload failed: {e}")
        return False
    
    # 2. Upload code changes
    print("\n📤 Uploading code changes...")
    files_to_upload = [
        ("app/scanner.py", "app/scanner.py"),
        ("app/database.py", "app/database.py"),
    ]
    
    for local_path, repo_path in files_to_upload:
        try:
            api.upload_file(
                path_or_fileobj=local_path,
                path_in_repo=repo_path,
                repo_id=HF_SPACE_REPO,
                repo_type="space",
                commit_message=f"✅ Fix: Update {repo_path} - Register all series properly"
            )
            print(f"✅ {repo_path} uploaded")
        except Exception as e:
            print(f"❌ {repo_path} upload failed: {e}")
    
    print("\n🎉 Deployment complete!")
    print("\n📋 Next steps:")
    print("1. Wait for HuggingFace Space to rebuild (~2-3 minutes)")
    print("2. Test the application at: https://huggingface.co/spaces/ToolKit-backend/PopCorn")
    print("3. Verify all 9 series appear in the frontend")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

# Made with Bob
