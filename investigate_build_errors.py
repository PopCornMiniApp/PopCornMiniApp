#!/usr/bin/env python3
"""
Script to investigate build errors on all HuggingFace Spaces.
Fetches detailed error logs and provides recommendations.
"""

import os
import sys
from huggingface_hub import HfApi
from datetime import datetime

SPACES_CONFIG = [
    {
        "repo_id": "ToolKit-backend/PopCorn",
        "token_env": "HF_TOKEN_1",
        "status": "RUNNING"
    },
    {
        "repo_id": "ToolKit-backend/popcorn-main",
        "token_env": "HF_TOKEN_1",
        "status": "BUILD_ERROR"
    },
    {
        "repo_id": "ToolKit-backend/popcorn-streaming",
        "token_env": "HF_TOKEN_1",
        "status": "BUILD_ERROR"
    },
    {
        "repo_id": "rayig/popcorn-backup",
        "token_env": "HF_TOKEN_2",
        "status": "BUILD_ERROR"
    },
    {
        "repo_id": "rayig/popcorn-analytics",
        "token_env": "HF_TOKEN_2",
        "status": "BUILD_ERROR"
    }
]


def get_space_runtime_info(repo_id: str, token: str):
    """Get detailed runtime information for a Space."""
    try:
        api = HfApi(token=token)
        space_info = api.space_info(repo_id)
        
        runtime_info = {
            "repo_id": repo_id,
            "sdk": getattr(space_info, "sdk", "unknown"),
            "stage": "unknown",
            "hardware": "unknown",
            "error_message": None
        }
        
        if hasattr(space_info, "runtime") and space_info.runtime:
            runtime = space_info.runtime
            runtime_info["stage"] = getattr(runtime, "stage", "unknown")
            runtime_info["hardware"] = getattr(runtime, "hardware", "unknown")
            
            # Try to get error message
            if hasattr(runtime, "error"):
                runtime_info["error_message"] = str(runtime.error)
        
        return runtime_info
        
    except Exception as e:
        return {
            "repo_id": repo_id,
            "error": str(e)
        }


def main():
    print("\n" + "="*80)
    print("INVESTIGATING BUILD ERRORS ON ALL SPACES")
    print("="*80 + "\n")
    
    # Get tokens
    hf_token_1 = os.getenv("HF_TOKEN_1")
    hf_token_2 = os.getenv("HF_TOKEN_2")
    
    if not hf_token_1 or not hf_token_2:
        print("❌ Error: HF_TOKEN_1 and HF_TOKEN_2 must be set!")
        sys.exit(1)
    
    tokens = {
        "HF_TOKEN_1": hf_token_1,
        "HF_TOKEN_2": hf_token_2
    }
    
    results = []
    
    for space in SPACES_CONFIG:
        repo_id = space["repo_id"]
        token_env = space["token_env"]
        expected_status = space["status"]
        
        print(f"\n{'='*80}")
        print(f"Space: {repo_id}")
        print(f"Expected Status: {expected_status}")
        print(f"{'='*80}")
        
        token = tokens[token_env]
        info = get_space_runtime_info(repo_id, token)
        results.append(info)
        
        if "error" in info:
            print(f"❌ Error fetching info: {info['error']}")
        else:
            print(f"SDK: {info['sdk']}")
            print(f"Stage: {info['stage']}")
            print(f"Hardware: {info['hardware']}")
            if info['error_message']:
                print(f"Error Message: {info['error_message']}")
    
    # Generate report
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80 + "\n")
    
    running = sum(1 for r in results if r.get('stage') == 'RUNNING')
    build_error = sum(1 for r in results if r.get('stage') == 'BUILD_ERROR')
    other = len(results) - running - build_error
    
    print(f"✅ Running: {running}/5")
    print(f"❌ Build Error: {build_error}/5")
    print(f"⚠️  Other: {other}/5")
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80 + "\n")
    
    if build_error > 0:
        print("The Dockerfile fix was applied, but build errors persist.")
        print("This suggests the issue is NOT just the Dockerfile COPY command.")
        print("\nPossible causes:")
        print("1. Missing files (app/ or static/ directories)")
        print("2. Missing requirements.txt or dependency issues")
        print("3. Python version incompatibility")
        print("4. Missing environment variables")
        print("5. Code errors in the application")
        print("\nNext steps:")
        print("1. Check HuggingFace Space logs directly in the web interface")
        print("2. Verify all required files are present in the repository")
        print("3. Test the application locally with Docker")
        print("4. Check if requirements.txt has all dependencies")
    
    # Save report
    report_file = "BUILD_ERROR_INVESTIGATION.md"
    with open(report_file, "w") as f:
        f.write(f"# Build Error Investigation Report\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"## Summary\n\n")
        f.write(f"- ✅ Running: {running}/5\n")
        f.write(f"- ❌ Build Error: {build_error}/5\n")
        f.write(f"- ⚠️  Other: {other}/5\n\n")
        f.write(f"## Detailed Results\n\n")
        
        for info in results:
            f.write(f"### {info['repo_id']}\n\n")
            if "error" in info:
                f.write(f"- Error: {info['error']}\n\n")
            else:
                f.write(f"- SDK: {info['sdk']}\n")
                f.write(f"- Stage: {info['stage']}\n")
                f.write(f"- Hardware: {info['hardware']}\n")
                if info.get('error_message'):
                    f.write(f"- Error Message: {info['error_message']}\n")
                f.write("\n")
    
    print(f"\n📄 Report saved to: {report_file}")


if __name__ == "__main__":
    main()

# Made with Bob
