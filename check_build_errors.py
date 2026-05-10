#!/usr/bin/env python3
"""Check build errors for HuggingFace Spaces"""

from dotenv import load_dotenv
import os
from huggingface_hub import HfApi

load_dotenv()

# Check both tokens
token1 = os.getenv('HF_TOKEN_1')
token2 = os.getenv('HF_TOKEN_2')

print(f"HF_TOKEN_1: {'✅ Found' if token1 else '❌ Missing'}")
print(f"HF_TOKEN_2: {'✅ Found' if token2 else '❌ Missing'}")
print()

if not token2:
    print("❌ Cannot check rayig spaces without HF_TOKEN_2")
    exit(1)

api = HfApi(token=token2)

spaces = [
    'rayig/popcorn-backup',
    'rayig/popcorn-analytics'
]

print('🔍 Checking Build Status...\n')

for space_id in spaces:
    print('='*70)
    print(f'📦 Space: {space_id}')
    print('='*70)
    
    try:
        info = api.space_info(repo_id=space_id)
        
        if info.runtime:
            print(f'Status: {info.runtime.stage}')
            print(f'Hardware: {info.runtime.hardware}')
            
            if hasattr(info.runtime, 'error_message') and info.runtime.error_message:
                print(f'\n❌ Error Message:')
                print(info.runtime.error_message)
        else:
            print('Status: No runtime info available')
            
        # Check files
        files = api.list_repo_files(space_id, repo_type='space')
        print(f'\n📁 Files in repo: {len(files)}')
        
        # Check for common issues
        has_dockerfile = 'Dockerfile' in files
        has_requirements = 'requirements.txt' in files
        has_app = any('app/' in f for f in files)
        
        print(f'  Dockerfile: {"✅" if has_dockerfile else "❌"}')
        print(f'  requirements.txt: {"✅" if has_requirements else "❌"}')
        print(f'  app/ directory: {"✅" if has_app else "❌"}')
        
    except Exception as e:
        print(f'❌ Error checking space: {e}')
    
    print()

print('='*70)
print('💡 Common BUILD_ERROR causes:')
print('  1. Missing or invalid Dockerfile')
print('  2. Dependency conflicts in requirements.txt')
print('  3. Missing required files')
print('  4. Pyrogram session file issues')
print('='*70)

# Made with Bob
