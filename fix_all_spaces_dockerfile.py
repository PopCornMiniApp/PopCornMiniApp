#!/usr/bin/env python3
"""
Comprehensive script to fix Dockerfile on ALL 5 HuggingFace Spaces.
This script will deploy the corrected Dockerfile to each Space and monitor builds.
"""

import os
import sys
import time
import json
from datetime import datetime
from huggingface_hub import HfApi, SpaceInfo
from typing import Dict, List, Tuple

# Configuration for all 5 Spaces
SPACES_CONFIG = [
    {
        "repo_id": "ToolKit-backend/PopCorn",
        "token_env": "HF_TOKEN_1",
        "description": "Main PopCorn Space"
    },
    {
        "repo_id": "ToolKit-backend/popcorn-main",
        "token_env": "HF_TOKEN_1",
        "description": "PopCorn Main Space"
    },
    {
        "repo_id": "ToolKit-backend/popcorn-streaming",
        "token_env": "HF_TOKEN_1",
        "description": "PopCorn Streaming Space (Currently Failing)"
    },
    {
        "repo_id": "rayig/popcorn-backup",
        "token_env": "HF_TOKEN_2",
        "description": "PopCorn Backup Space"
    },
    {
        "repo_id": "rayig/popcorn-analytics",
        "token_env": "HF_TOKEN_2",
        "description": "PopCorn Analytics Space"
    }
]

# Fixed Dockerfile content
FIXED_DOCKERFILE = """FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    git curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY static/ ./static/

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \\
  CMD curl -f http://localhost:7860/api/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860", \\
     "--workers", "1", "--timeout-keep-alive", "75", "--log-level", "info"]
"""


class SpaceDeploymentManager:
    """Manages deployment of Dockerfile fixes to multiple HuggingFace Spaces."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.results = []
        self.start_time = datetime.now()
        
    def get_token(self, token_env: str) -> str:
        """Get HuggingFace token from environment."""
        token = os.getenv(token_env)
        if not token:
            raise ValueError(f"Environment variable {token_env} not set!")
        return token
    
    def upload_dockerfile(self, repo_id: str, token: str) -> bool:
        """Upload fixed Dockerfile to a Space."""
        try:
            if self.dry_run:
                print(f"[DRY RUN] Would upload Dockerfile to {repo_id}")
                return True
            
            api = HfApi(token=token)
            
            # Create temporary Dockerfile
            temp_file = "/tmp/Dockerfile"
            with open(temp_file, "w") as f:
                f.write(FIXED_DOCKERFILE)
            
            # Upload to Space
            api.upload_file(
                path_or_fileobj=temp_file,
                path_in_repo="Dockerfile",
                repo_id=repo_id,
                repo_type="space",
                commit_message="Fix: Remove error suppression from COPY static/ command"
            )
            
            print(f"✅ Successfully uploaded Dockerfile to {repo_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to upload Dockerfile to {repo_id}: {str(e)}")
            return False
    
    def get_space_status(self, repo_id: str, token: str) -> Dict:
        """Get current status of a Space."""
        try:
            api = HfApi(token=token)
            space_info = api.space_info(repo_id)
            
            # Extract runtime info safely
            runtime_stage = "unknown"
            if hasattr(space_info, "runtime") and space_info.runtime:
                runtime_stage = getattr(space_info.runtime, "stage", "unknown")
            
            return {
                "sdk": getattr(space_info, "sdk", "unknown"),
                "stage": runtime_stage
            }
        except Exception as e:
            return {"error": str(e)}
    
    def wait_for_build(self, repo_id: str, token: str, timeout: int = 600) -> Tuple[bool, str]:
        """Wait for Space build to complete."""
        if self.dry_run:
            return True, "DRY_RUN"
        
        api = HfApi(token=token)
        start = time.time()
        last_stage = None
        
        print(f"\n⏳ Monitoring build for {repo_id}...")
        
        while time.time() - start < timeout:
            try:
                space_info = api.space_info(repo_id)
                
                if hasattr(space_info, "runtime") and space_info.runtime:
                    # Handle runtime as object with attributes, not dict
                    stage = getattr(space_info.runtime, "stage", "unknown")
                    
                    if stage != last_stage:
                        print(f"   Stage: {stage}")
                        last_stage = stage
                    
                    if stage == "RUNNING":
                        print(f"✅ Build completed successfully for {repo_id}")
                        return True, "RUNNING"
                    elif stage in ["BUILD_ERROR", "RUNTIME_ERROR", "PAUSED"]:
                        print(f"❌ Build failed for {repo_id}: {stage}")
                        return False, stage
                
                time.sleep(10)
                
            except Exception as e:
                print(f"⚠️  Error checking status: {str(e)}")
                time.sleep(10)
        
        print(f"⏱️  Timeout waiting for {repo_id} build")
        return False, "TIMEOUT"
    
    def deploy_to_space(self, space_config: Dict) -> Dict:
        """Deploy Dockerfile fix to a single Space."""
        repo_id = space_config["repo_id"]
        token_env = space_config["token_env"]
        description = space_config["description"]
        
        print(f"\n{'='*80}")
        print(f"🚀 Deploying to: {repo_id}")
        print(f"   Description: {description}")
        print(f"{'='*80}")
        
        result = {
            "repo_id": repo_id,
            "description": description,
            "token_env": token_env,
            "upload_success": False,
            "build_success": False,
            "final_status": "UNKNOWN",
            "error": None,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Get token
            token = self.get_token(token_env)
            
            # Get initial status
            print(f"📊 Initial status:")
            initial_status = self.get_space_status(repo_id, token)
            print(f"   {json.dumps(initial_status, indent=2)}")
            
            # Upload Dockerfile
            print(f"\n📤 Uploading fixed Dockerfile...")
            upload_success = self.upload_dockerfile(repo_id, token)
            result["upload_success"] = upload_success
            
            if not upload_success:
                result["error"] = "Failed to upload Dockerfile"
                return result
            
            # Wait for build
            if not self.dry_run:
                time.sleep(5)  # Give HF time to start build
                build_success, final_status = self.wait_for_build(repo_id, token)
                result["build_success"] = build_success
                result["final_status"] = final_status
            else:
                result["build_success"] = True
                result["final_status"] = "DRY_RUN"
            
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Error deploying to {repo_id}: {str(e)}")
        
        return result
    
    def deploy_to_all_spaces(self) -> List[Dict]:
        """Deploy Dockerfile fix to all Spaces."""
        print(f"\n{'#'*80}")
        print(f"# DEPLOYING DOCKERFILE FIX TO ALL 5 HUGGINGFACE SPACES")
        print(f"# Mode: {'DRY RUN' if self.dry_run else 'LIVE DEPLOYMENT'}")
        print(f"# Started: {self.start_time.isoformat()}")
        print(f"{'#'*80}\n")
        
        for space_config in SPACES_CONFIG:
            result = self.deploy_to_space(space_config)
            self.results.append(result)
            
            # Brief pause between deployments
            if not self.dry_run:
                time.sleep(3)
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate comprehensive deployment report."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        successful_uploads = sum(1 for r in self.results if r["upload_success"])
        successful_builds = sum(1 for r in self.results if r["build_success"])
        failed = len(self.results) - successful_builds
        
        report = f"""
{'='*80}
DOCKERFILE FIX DEPLOYMENT REPORT - ALL 5 SPACES
{'='*80}

Execution Mode: {'DRY RUN' if self.dry_run else 'LIVE DEPLOYMENT'}
Start Time: {self.start_time.isoformat()}
End Time: {end_time.isoformat()}
Duration: {duration:.1f} seconds

SUMMARY:
--------
Total Spaces: {len(self.results)}
Successful Uploads: {successful_uploads}/{len(self.results)}
Successful Builds: {successful_builds}/{len(self.results)}
Failed: {failed}/{len(self.results)}

DETAILED RESULTS:
-----------------
"""
        
        for i, result in enumerate(self.results, 1):
            status_icon = "✅" if result["build_success"] else "❌"
            report += f"\n{i}. {status_icon} {result['repo_id']}\n"
            report += f"   Description: {result['description']}\n"
            report += f"   Token: {result['token_env']}\n"
            report += f"   Upload: {'✅ Success' if result['upload_success'] else '❌ Failed'}\n"
            report += f"   Build: {'✅ Success' if result['build_success'] else '❌ Failed'}\n"
            report += f"   Final Status: {result['final_status']}\n"
            if result.get("error"):
                report += f"   Error: {result['error']}\n"
            report += f"   Timestamp: {result['timestamp']}\n"
        
        report += f"\n{'='*80}\n"
        
        if successful_builds == len(self.results):
            report += "🎉 SUCCESS! All Spaces deployed and built successfully!\n"
        elif successful_builds > 0:
            report += f"⚠️  PARTIAL SUCCESS: {successful_builds}/{len(self.results)} Spaces built successfully\n"
        else:
            report += "❌ FAILURE: No Spaces built successfully\n"
        
        report += f"{'='*80}\n"
        
        return report
    
    def save_report(self, filename: str = "ALL_SPACES_DOCKERFILE_FIX_REPORT.md"):
        """Save report to file."""
        report = self.generate_report()
        
        # Save in current directory, not nested PopCorn folder
        with open(filename, "w") as f:
            f.write(report)
        
        print(f"\n📄 Report saved to: {filename}")
        return filename


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Deploy Dockerfile fix to all 5 HuggingFace Spaces"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without actually deploying"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for builds to complete"
    )
    
    args = parser.parse_args()
    
    # Check environment variables
    print("\n🔍 Checking environment variables...")
    for space in SPACES_CONFIG:
        token_env = space["token_env"]
        if os.getenv(token_env):
            print(f"   ✅ {token_env} is set")
        else:
            print(f"   ❌ {token_env} is NOT set!")
            if not args.dry_run:
                print(f"\n❌ Error: {token_env} environment variable is required!")
                sys.exit(1)
    
    # Create manager and deploy
    manager = SpaceDeploymentManager(dry_run=args.dry_run)
    
    try:
        results = manager.deploy_to_all_spaces()
        
        # Print and save report
        report = manager.generate_report()
        print(report)
        
        report_file = manager.save_report()
        
        # Save JSON results in current directory
        json_file = "all_spaces_deployment_results.json"
        with open(json_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"📊 JSON results saved to: {json_file}")
        
        # Exit with appropriate code
        successful_builds = sum(1 for r in results if r["build_success"])
        if successful_builds == len(results):
            print("\n✅ All deployments successful!")
            sys.exit(0)
        else:
            print(f"\n⚠️  Only {successful_builds}/{len(results)} deployments successful")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
