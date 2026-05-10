#!/usr/bin/env python3
"""
Fix HuggingFace Space Build Errors
Diagnoses and fixes common build issues
"""

import os
from huggingface_hub import HfApi, hf_hub_download
import subprocess
import time

def main():
    token = os.getenv('HF_TOKEN')
    if not token:
        print("❌ HF_TOKEN not found")
        return
    
    api = HfApi(token=token)
    spaces = ['popcorn-main', 'popcorn-streaming']
    
    print("🔍 Diagnosing Build Errors...\n")
    
    for space_name in spaces:
        repo_id = f'ToolKit-backend/{space_name}'
        print(f"\n{'='*60}")
        print(f"📦 Space: {space_name}")
        print(f"{'='*60}")
        
        try:
            # Get space info
            info = api.space_info(repo_id)
            print(f"Status: {info.runtime.stage}")
            
            # Download and check requirements.txt
            try:
                req_path = hf_hub_download(
                    repo_id=repo_id,
                    filename='requirements.txt',
                    repo_type='space',
                    token=token
                )
                
                print("\n📄 requirements.txt:")
                with open(req_path, 'r') as f:
                    reqs = f.read()
                    print(reqs)
                    
                # Check for problematic dependencies
                issues = []
                if 'pyrogram' in reqs.lower():
                    issues.append("⚠️  Pyrogram requires Telegram credentials")
                if 'telethon' in reqs.lower():
                    issues.append("⚠️  Telethon requires Telegram credentials")
                    
                if issues:
                    print("\n🔴 Potential Issues:")
                    for issue in issues:
                        print(f"  {issue}")
                        
            except Exception as e:
                print(f"❌ Could not check requirements: {e}")
            
            # Check for __pycache__ files
            files = api.list_repo_files(repo_id, repo_type='space')
            pycache_files = [f for f in files if '__pycache__' in f]
            
            if pycache_files:
                print(f"\n🔴 Found {len(pycache_files)} __pycache__ files (should be removed)")
                print("   These can cause build issues")
            
            # Check if .env or secrets are needed
            if 'BOT_TOKEN' in reqs or 'API_ID' in reqs:
                print("\n⚠️  This space requires environment variables/secrets")
                print("   Make sure to set them in Space settings")
                
        except Exception as e:
            print(f"❌ Error checking {space_name}: {e}")
    
    print("\n" + "="*60)
    print("🔧 Recommended Fixes:")
    print("="*60)
    print("""
1. Remove __pycache__ files from repository
2. Simplify requirements.txt (remove Telegram dependencies for now)
3. Add .gitignore to prevent __pycache__ upload
4. Use environment variables for sensitive data
5. Test build locally with Docker first

Would you like to apply automatic fixes? (This will clean the repos)
""")
    
    response = input("Apply fixes? (yes/no): ").strip().lower()
    
    if response == 'yes':
        print("\n🔧 Applying fixes...")
        apply_fixes(api, spaces, token)
    else:
        print("\n✋ Skipping automatic fixes")
        print("You can manually fix the issues in HuggingFace Space settings")

def apply_fixes(api, spaces, token):
    """Apply automatic fixes to spaces"""
    
    for space_name in spaces:
        repo_id = f'ToolKit-backend/{space_name}'
        print(f"\n🔧 Fixing {space_name}...")
        
        try:
            # Delete __pycache__ files
            files = api.list_repo_files(repo_id, repo_type='space')
            pycache_files = [f for f in files if '__pycache__' in f]
            
            if pycache_files:
                print(f"  🗑️  Deleting {len(pycache_files)} __pycache__ files...")
                for file in pycache_files:
                    try:
                        api.delete_file(
                            path_in_repo=file,
                            repo_id=repo_id,
                            repo_type='space',
                            token=token,
                            commit_message=f"Remove {file}"
                        )
                        print(f"    ✅ Deleted {file}")
                    except Exception as e:
                        print(f"    ❌ Failed to delete {file}: {e}")
            
            # Create simplified requirements.txt
            simplified_reqs = """fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
aiofiles==23.2.1
httpx==0.25.1
pydantic==2.5.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dotenv==1.0.0
requests==2.31.0
"""
            
            print("  📝 Uploading simplified requirements.txt...")
            api.upload_file(
                path_or_fileobj=simplified_reqs.encode(),
                path_in_repo='requirements.txt',
                repo_id=repo_id,
                repo_type='space',
                token=token,
                commit_message="Simplify requirements for build"
            )
            print("    ✅ requirements.txt updated")
            
            # Add .gitignore
            gitignore_content = """__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.db
*.sqlite
*.sqlite3
.env
.venv
venv/
"""
            
            print("  📝 Adding .gitignore...")
            api.upload_file(
                path_or_fileobj=gitignore_content.encode(),
                path_in_repo='.gitignore',
                repo_id=repo_id,
                repo_type='space',
                token=token,
                commit_message="Add .gitignore"
            )
            print("    ✅ .gitignore added")
            
            # Restart space
            print("  🔄 Restarting space...")
            api.restart_space(repo_id, token=token)
            print("    ✅ Space restarted")
            
            print(f"✅ {space_name} fixed successfully")
            
        except Exception as e:
            print(f"❌ Error fixing {space_name}: {e}")
    
    print("\n✅ All fixes applied!")
    print("⏳ Spaces are rebuilding... Check status in 5-10 minutes")

if __name__ == '__main__':
    main()

# Made with Bob
