#!/usr/bin/env python3
"""
Check HuggingFace Space Build Status
Monitors the space rebuild and reports status
"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_space_status():
    """Check the current status of HuggingFace Space"""
    print("\n" + "="*60)
    print("🔍 Checking HuggingFace Space Build Status")
    print("="*60)
    print(f"⏰ Check time: {datetime.utcnow().isoformat()} UTC\n")
    
    try:
        from huggingface_hub import HfApi
        
        # Get configuration
        token = os.getenv('HF_TOKEN')
        space_name = os.getenv('HF_SPACE_NAME', 'ToolKit-backend/PopCorn')
        
        if not token:
            print("❌ ERROR: HF_TOKEN not found")
            return None
        
        # Initialize API
        api = HfApi(token=token)
        
        print(f"📦 Space: {space_name}")
        print(f"🔗 URL: https://huggingface.co/spaces/{space_name}\n")
        
        # Get space info
        space_info = api.space_info(space_name)
        
        # Extract runtime info
        runtime = space_info.runtime
        stage = runtime.stage if runtime else "UNKNOWN"
        hardware = runtime.hardware if runtime else None
        
        print(f"📊 Space Status:")
        print(f"   Stage: {stage}")
        print(f"   Hardware: {hardware or 'Not assigned'}")
        
        # Status interpretation
        status_emoji = {
            'RUNNING': '✅',
            'BUILDING': '🔨',
            'RUNTIME_ERROR': '❌',
            'STOPPED': '⏸️',
            'PAUSED': '⏸️',
            'NO_APP_FILE': '❌',
            'CONFIG_ERROR': '❌',
            'UNKNOWN': '❓'
        }
        
        emoji = status_emoji.get(stage, '❓')
        print(f"\n{emoji} Status: {stage}")
        
        if stage == 'RUNNING':
            print("\n✅ Space is RUNNING successfully!")
            print(f"   Access at: https://{space_name.replace('/', '-').lower()}.hf.space")
            return 'RUNNING'
            
        elif stage == 'BUILDING':
            print("\n🔨 Space is BUILDING...")
            print("   This usually takes 2-5 minutes")
            print("   Please wait and check again")
            return 'BUILDING'
            
        elif stage == 'RUNTIME_ERROR':
            print("\n❌ Space has RUNTIME_ERROR")
            if runtime and hasattr(runtime, 'raw') and 'errorMessage' in runtime.raw:
                error_msg = runtime.raw['errorMessage']
                print(f"\n📋 Error Details:")
                # Show first 500 chars of error
                print(error_msg[:500])
                if len(error_msg) > 500:
                    print("   ... (truncated)")
            return 'RUNTIME_ERROR'
            
        else:
            print(f"\n⚠️  Unexpected status: {stage}")
            return stage
            
    except ImportError:
        print("❌ huggingface_hub not installed")
        return None
    except Exception as e:
        print(f"❌ Error checking status: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def monitor_build(max_wait_minutes=10, check_interval=30):
    """Monitor the build process until completion or timeout"""
    print("\n" + "="*60)
    print("⏱️  Monitoring Build Process")
    print("="*60)
    print(f"Max wait time: {max_wait_minutes} minutes")
    print(f"Check interval: {check_interval} seconds\n")
    
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60
    check_count = 0
    
    while True:
        check_count += 1
        elapsed = time.time() - start_time
        
        print(f"\n{'─'*60}")
        print(f"Check #{check_count} (Elapsed: {int(elapsed)}s)")
        print(f"{'─'*60}")
        
        status = check_space_status()
        
        if status == 'RUNNING':
            print("\n" + "="*60)
            print("🎉 Build completed successfully!")
            print("="*60)
            return True
            
        elif status == 'RUNTIME_ERROR':
            print("\n" + "="*60)
            print("❌ Build failed with runtime error")
            print("="*60)
            print("\n📋 Recommended actions:")
            print("1. Check the error message above")
            print("2. Review the space logs on HuggingFace")
            print("3. Fix the issue and redeploy")
            return False
            
        elif status == 'BUILDING':
            if elapsed >= max_wait_seconds:
                print("\n" + "="*60)
                print("⏰ Timeout reached")
                print("="*60)
                print("\nBuild is still in progress but taking longer than expected")
                print("Please check manually at: https://huggingface.co/spaces/ToolKit-backend/PopCorn")
                return None
            
            print(f"\n⏳ Still building... waiting {check_interval}s before next check")
            time.sleep(check_interval)
            
        else:
            print(f"\n⚠️  Unexpected status: {status}")
            print("Waiting before retry...")
            time.sleep(check_interval)
            
            if elapsed >= max_wait_seconds:
                print("\n⏰ Timeout reached")
                return None


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check HuggingFace Space build status')
    parser.add_argument('--monitor', action='store_true', help='Monitor build until completion')
    parser.add_argument('--max-wait', type=int, default=10, help='Max wait time in minutes (default: 10)')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    if args.monitor:
        result = monitor_build(max_wait_minutes=args.max_wait, check_interval=args.interval)
        if result is True:
            return 0
        elif result is False:
            return 1
        else:
            return 2
    else:
        status = check_space_status()
        if status == 'RUNNING':
            return 0
        elif status in ['BUILDING', None]:
            return 2
        else:
            return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
