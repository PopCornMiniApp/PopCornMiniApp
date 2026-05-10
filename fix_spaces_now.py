#!/usr/bin/env python3
"""
Automatic fix for HuggingFace Space build errors
Removes __pycache__ files and simplifies requirements
"""

from dotenv import load_dotenv
import os
from huggingface_hub import HfApi
import time

load_dotenv()

token = os.getenv('HF_TOKEN')
if not token:
    print('❌ HF_TOKEN not found')
    exit(1)

api = HfApi(token=token)
spaces = ['popcorn-main', 'popcorn-streaming']

print('🔧 Fixing HuggingFace Spaces...\n')

for space_name in spaces:
    repo_id = f'ToolKit-backend/{space_name}'
    print('='*60)
    print(f'📦 Fixing: {space_name}')
    print('='*60)
    
    try:
        # Step 1: Delete __pycache__ files
        print('\n🗑️  Step 1: Removing __pycache__ files...')
        files = api.list_repo_files(repo_id, repo_type='space')
        pycache_files = [f for f in files if '__pycache__' in f]
        
        deleted_count = 0
        for file in pycache_files:
            try:
                api.delete_file(
                    path_in_repo=file,
                    repo_id=repo_id,
                    repo_type='space',
                    token=token,
                    commit_message=f'Remove {file}'
                )
                deleted_count += 1
                if deleted_count % 5 == 0:
                    print(f'   Deleted {deleted_count}/{len(pycache_files)} files...')
            except Exception as e:
                print(f'   ⚠️  Could not delete {file}: {e}')
        
        print(f'   ✅ Deleted {deleted_count} __pycache__ files')
        
        # Step 2: Upload simplified requirements.txt
        print('\n📝 Step 2: Uploading simplified requirements.txt...')
        simplified_reqs = """fastapi==0.115.6
uvicorn[standard]==0.32.1
httpx==0.28.1
huggingface-hub==0.27.1
aiofiles==24.1.0
python-multipart==0.0.20
pydantic==2.10.4
aiohttp==3.11.11
python-dotenv==1.0.1
cachetools==5.5.0
requests==2.31.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
"""
        
        api.upload_file(
            path_or_fileobj=simplified_reqs.encode(),
            path_in_repo='requirements.txt',
            repo_id=repo_id,
            repo_type='space',
            token=token,
            commit_message='Simplify requirements - remove Telegram dependencies'
        )
        print('   ✅ requirements.txt updated')
        
        # Step 3: Add .gitignore
        print('\n📝 Step 3: Adding .gitignore...')
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
env/
"""
        
        api.upload_file(
            path_or_fileobj=gitignore_content.encode(),
            path_in_repo='.gitignore',
            repo_id=repo_id,
            repo_type='space',
            token=token,
            commit_message='Add .gitignore to prevent __pycache__ upload'
        )
        print('   ✅ .gitignore added')
        
        # Step 4: Restart space
        print('\n🔄 Step 4: Restarting space...')
        api.restart_space(repo_id, token=token)
        print('   ✅ Space restarted')
        
        print(f'\n✅ {space_name} fixed successfully!\n')
        
        # Wait a bit between spaces to avoid rate limits
        if space_name != spaces[-1]:
            print('⏳ Waiting 5 seconds before next space...\n')
            time.sleep(5)
        
    except Exception as e:
        print(f'\n❌ Error fixing {space_name}: {e}\n')

print('='*60)
print('✅ All fixes applied!')
print('='*60)
print('\n⏳ Spaces are now rebuilding...')
print('📊 Check status in 5-10 minutes')
print('\nRun: python3 diagnose_build.py')

# Made with Bob
