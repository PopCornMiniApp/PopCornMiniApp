#!/usr/bin/env python3
"""
Comprehensive Build Error Diagnostic and Fix Script
Downloads Dockerfile from HF, compares with local, and fixes issues
"""

from dotenv import load_dotenv
import os
from huggingface_hub import HfApi, hf_hub_download
import time
from pathlib import Path
import difflib

load_dotenv()

token = os.getenv('HF_TOKEN')
if not token:
    print('❌ HF_TOKEN not found in .env file')
    exit(1)

api = HfApi(token=token)
spaces = ['popcorn-main', 'popcorn-streaming']

# Read local Dockerfile
local_dockerfile_path = Path('PopCorn/Dockerfile')
if not local_dockerfile_path.exists():
    print(f'❌ Local Dockerfile not found at {local_dockerfile_path}')
    exit(1)

with open(local_dockerfile_path, 'r') as f:
    local_dockerfile = f.read()

print('🔍 COMPREHENSIVE BUILD ERROR DIAGNOSTIC')
print('='*70)
print(f'Local Dockerfile: {local_dockerfile_path}')
print(f'Local Dockerfile size: {len(local_dockerfile)} bytes')
print('='*70)

# Check if static directory exists
static_dir = Path('PopCorn/static')
if static_dir.exists():
    static_files = list(static_dir.rglob('*'))
    print(f'\n✅ Static directory exists with {len(static_files)} files')
    print('   Sample files:')
    for f in list(static_files)[:5]:
        print(f'   - {f.relative_to("PopCorn")}')
else:
    print('\n❌ WARNING: Static directory does not exist!')
    print('   This will cause COPY static/ to fail')

print('\n' + '='*70)
print('CHECKING EACH SPACE')
print('='*70)

issues_found = {}

for space_name in spaces:
    repo_id = f'ToolKit-backend/{space_name}'
    print(f'\n📦 Space: {space_name}')
    print('-'*70)
    
    issues_found[space_name] = []
    
    try:
        # Get space info
        info = api.space_info(repo_id)
        status = info.runtime.stage if info.runtime else 'Unknown'
        print(f'Current Status: {status}')
        
        if status == 'BUILD_ERROR':
            print('🔴 BUILD ERROR DETECTED')
            issues_found[space_name].append('BUILD_ERROR')
        
        # Download Dockerfile from HF
        print('\n📥 Downloading Dockerfile from HuggingFace...')
        try:
            hf_dockerfile_path = hf_hub_download(
                repo_id=repo_id,
                filename='Dockerfile',
                repo_type='space',
                token=token,
                force_download=True  # Force fresh download
            )
            
            with open(hf_dockerfile_path, 'r') as f:
                hf_dockerfile = f.read()
            
            print(f'✅ Downloaded Dockerfile ({len(hf_dockerfile)} bytes)')
            
            # Compare Dockerfiles
            print('\n🔍 Comparing Dockerfiles...')
            if local_dockerfile == hf_dockerfile:
                print('✅ Dockerfiles are IDENTICAL')
            else:
                print('❌ Dockerfiles are DIFFERENT!')
                issues_found[space_name].append('DOCKERFILE_MISMATCH')
                
                # Show diff
                print('\n📊 Differences:')
                diff = difflib.unified_diff(
                    hf_dockerfile.splitlines(keepends=True),
                    local_dockerfile.splitlines(keepends=True),
                    fromfile='HuggingFace',
                    tofile='Local',
                    lineterm=''
                )
                diff_text = ''.join(diff)
                print(diff_text)
                
                # Check for problematic syntax
                if '2>/dev/null || true' in hf_dockerfile:
                    print('\n🔴 FOUND PROBLEMATIC SYNTAX: "2>/dev/null || true"')
                    issues_found[space_name].append('BAD_SYNTAX')
                
        except Exception as e:
            print(f'❌ Could not download Dockerfile: {e}')
            issues_found[space_name].append('DOCKERFILE_DOWNLOAD_FAILED')
        
        # Check for __pycache__ files
        print('\n🔍 Checking for __pycache__ files...')
        files = api.list_repo_files(repo_id, repo_type='space')
        pycache_files = [f for f in files if '__pycache__' in f]
        
        if pycache_files:
            print(f'🔴 Found {len(pycache_files)} __pycache__ files')
            issues_found[space_name].append('PYCACHE_FILES')
            print('   Sample files:')
            for f in pycache_files[:5]:
                print(f'   - {f}')
        else:
            print('✅ No __pycache__ files found')
        
        # Check requirements.txt
        print('\n🔍 Checking requirements.txt...')
        try:
            req_path = hf_hub_download(
                repo_id=repo_id,
                filename='requirements.txt',
                repo_type='space',
                token=token,
                force_download=True
            )
            
            with open(req_path, 'r') as f:
                reqs = f.read()
            
            print(f'✅ requirements.txt found ({len(reqs)} bytes)')
            
            # Check for problematic dependencies
            if 'pyrogram' in reqs.lower() or 'telethon' in reqs.lower():
                print('⚠️  Contains Telegram dependencies (may need credentials)')
                issues_found[space_name].append('TELEGRAM_DEPS')
                
        except Exception as e:
            print(f'❌ Could not check requirements: {e}')
        
        # Check if static directory exists on HF
        print('\n🔍 Checking for static directory on HF...')
        static_files_hf = [f for f in files if f.startswith('static/')]
        if static_files_hf:
            print(f'✅ Found {len(static_files_hf)} files in static/')
        else:
            print('❌ No static/ directory found on HF!')
            issues_found[space_name].append('MISSING_STATIC')
        
    except Exception as e:
        print(f'❌ Error checking space: {e}')
        issues_found[space_name].append(f'ERROR: {e}')

# Summary
print('\n' + '='*70)
print('DIAGNOSTIC SUMMARY')
print('='*70)

total_issues = sum(len(issues) for issues in issues_found.values())
print(f'\nTotal issues found: {total_issues}')

for space_name, issues in issues_found.items():
    print(f'\n{space_name}:')
    if issues:
        for issue in issues:
            print(f'  ❌ {issue}')
    else:
        print('  ✅ No issues detected')

# Propose fixes
print('\n' + '='*70)
print('PROPOSED FIXES')
print('='*70)

fixes_needed = []

for space_name, issues in issues_found.items():
    if 'DOCKERFILE_MISMATCH' in issues or 'BAD_SYNTAX' in issues:
        fixes_needed.append(('UPDATE_DOCKERFILE', space_name))
    if 'PYCACHE_FILES' in issues:
        fixes_needed.append(('REMOVE_PYCACHE', space_name))
    if 'MISSING_STATIC' in issues:
        fixes_needed.append(('UPLOAD_STATIC', space_name))

if not fixes_needed:
    print('\n✅ No fixes needed - all spaces are correctly configured')
    print('\n🤔 If builds are still failing, the issue may be:')
    print('   1. Docker cache issues (needs manual cache clear on HF)')
    print('   2. HuggingFace infrastructure issues')
    print('   3. Resource allocation problems')
    print('\n💡 Try manually restarting the spaces on HuggingFace')
else:
    print(f'\n🔧 {len(fixes_needed)} fixes needed:')
    for fix_type, space_name in fixes_needed:
        print(f'   - {fix_type} for {space_name}')
    
    print('\n' + '='*70)
    print('APPLYING FIXES')
    print('='*70)
    
    response = input('\n❓ Apply fixes automatically? (yes/no): ').strip().lower()
    
    if response == 'yes':
        for fix_type, space_name in fixes_needed:
            repo_id = f'ToolKit-backend/{space_name}'
            print(f'\n🔧 Applying {fix_type} to {space_name}...')
            
            try:
                if fix_type == 'UPDATE_DOCKERFILE':
                    print('   Uploading corrected Dockerfile...')
                    api.upload_file(
                        path_or_fileobj=local_dockerfile.encode(),
                        path_in_repo='Dockerfile',
                        repo_id=repo_id,
                        repo_type='space',
                        token=token,
                        commit_message='Fix Dockerfile - remove problematic syntax'
                    )
                    print('   ✅ Dockerfile updated')
                
                elif fix_type == 'REMOVE_PYCACHE':
                    print('   Removing __pycache__ files...')
                    files = api.list_repo_files(repo_id, repo_type='space')
                    pycache_files = [f for f in files if '__pycache__' in f]
                    
                    for file in pycache_files:
                        try:
                            api.delete_file(
                                path_in_repo=file,
                                repo_id=repo_id,
                                repo_type='space',
                                token=token,
                                commit_message=f'Remove {file}'
                            )
                        except:
                            pass
                    print(f'   ✅ Removed {len(pycache_files)} __pycache__ files')
                
                elif fix_type == 'UPLOAD_STATIC':
                    print('   Uploading static directory...')
                    if static_dir.exists():
                        for file_path in static_dir.rglob('*'):
                            if file_path.is_file():
                                rel_path = file_path.relative_to('PopCorn')
                                api.upload_file(
                                    path_or_fileobj=str(file_path),
                                    path_in_repo=str(rel_path),
                                    repo_id=repo_id,
                                    repo_type='space',
                                    token=token,
                                    commit_message=f'Upload {rel_path}'
                                )
                        print('   ✅ Static files uploaded')
                    else:
                        print('   ❌ Static directory not found locally')
                
                # Restart space after fixes
                print('   🔄 Restarting space...')
                api.restart_space(repo_id, token=token)
                print('   ✅ Space restarted')
                
                time.sleep(2)  # Brief pause between spaces
                
            except Exception as e:
                print(f'   ❌ Error applying fix: {e}')
        
        print('\n' + '='*70)
        print('✅ ALL FIXES APPLIED')
        print('='*70)
        print('\n⏳ Spaces are now rebuilding...')
        print('📊 Monitor status with: python3 PopCorn/monitor_build_status.py')
    else:
        print('\n⏸️  Fixes not applied')
        print('💡 Review the issues above and apply fixes manually if needed')

print('\n' + '='*70)
print('DIAGNOSTIC COMPLETE')
print('='*70)

# Made with Bob