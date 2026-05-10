#!/usr/bin/env python3
"""
Monitor HuggingFace Space build status
Checks every 30 seconds until all spaces are running
"""

from dotenv import load_dotenv
import os
from huggingface_hub import HfApi
import time
from datetime import datetime

load_dotenv()

token = os.getenv('HF_TOKEN')
if not token:
    print('❌ HF_TOKEN not found')
    exit(1)

api = HfApi(token=token)
spaces = ['popcorn-main', 'popcorn-streaming']

def check_status():
    """Check status of all spaces"""
    results = {}
    for space_name in spaces:
        repo_id = f'ToolKit-backend/{space_name}'
        try:
            info = api.space_info(repo_id)
            status = info.runtime.stage if info.runtime else 'Unknown'
            results[space_name] = status
        except Exception as e:
            results[space_name] = f'Error: {e}'
    return results

def print_status(results, iteration=0):
    """Print formatted status"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'\n[{timestamp}] Build Status Check #{iteration}')
    print('='*60)
    
    all_running = True
    for space_name, status in results.items():
        emoji = '✅' if status == 'RUNNING' else '🔄' if status == 'BUILDING' else '❌'
        print(f'{emoji} {space_name:20s} : {status}')
        if status != 'RUNNING':
            all_running = False
    
    print('='*60)
    return all_running

def main():
    print('🔍 Monitoring HuggingFace Space Build Status')
    print('Press Ctrl+C to stop monitoring\n')
    
    iteration = 0
    while True:
        try:
            iteration += 1
            results = check_status()
            all_running = print_status(results, iteration)
            
            if all_running:
                print('\n🎉 All spaces are RUNNING!')
                print('✅ Build successful!')
                break
            
            # Check if any failed
            if any('ERROR' in status for status in results.values()):
                print('\n❌ Some spaces have BUILD_ERROR')
                print('Run: python3 diagnose_build.py')
                break
            
            # Wait 30 seconds before next check
            print('\n⏳ Waiting 30 seconds before next check...')
            time.sleep(30)
            
        except KeyboardInterrupt:
            print('\n\n⏸️  Monitoring stopped by user')
            break
        except Exception as e:
            print(f'\n❌ Error: {e}')
            break

if __name__ == '__main__':
    main()

# Made with Bob
