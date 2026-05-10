#!/usr/bin/env python3
"""Quick diagnostic for HuggingFace Space build errors"""

from dotenv import load_dotenv
import os
from huggingface_hub import HfApi, hf_hub_download

load_dotenv()

token = os.getenv('HF_TOKEN')
if not token:
    print('❌ HF_TOKEN not found')
    exit(1)

api = HfApi(token=token)
spaces = ['popcorn-main', 'popcorn-streaming']

print('🔍 Diagnosing Build Errors...\n')

for space_name in spaces:
    repo_id = f'ToolKit-backend/{space_name}'
    print('='*60)
    print(f'📦 Space: {space_name}')
    print('='*60)
    
    try:
        # Get space info
        info = api.space_info(repo_id)
        status = info.runtime.stage if info.runtime else 'Unknown'
        print(f'Status: {status}')
        
        # Check requirements.txt
        try:
            req_path = hf_hub_download(
                repo_id=repo_id,
                filename='requirements.txt',
                repo_type='space',
                token=token
            )
            
            print('\n📄 requirements.txt (first 500 chars):')
            with open(req_path, 'r') as f:
                reqs = f.read()
                print(reqs[:500])
                
            # Check for issues
            if 'pyrogram' in reqs.lower():
                print('\n⚠️  Contains Pyrogram (needs Telegram credentials)')
            if 'telethon' in reqs.lower():
                print('\n⚠️  Contains Telethon (needs Telegram credentials)')
                    
        except Exception as e:
            print(f'❌ Could not check requirements: {e}')
        
        # Check for __pycache__
        files = api.list_repo_files(repo_id, repo_type='space')
        pycache_files = [f for f in files if '__pycache__' in f]
        
        if pycache_files:
            print(f'\n🔴 Found {len(pycache_files)} __pycache__ files (PROBLEM!)')
            
    except Exception as e:
        print(f'❌ Error: {e}')
    
    print()

print('='*60)
print('🔧 SOLUTION: Remove __pycache__ and simplify requirements')
print('='*60)

# Made with Bob
