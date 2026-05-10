#!/usr/bin/env python3
"""
PopCorn Bot System - Deployment Automation Script
Deploys to all 5 HuggingFace Spaces with monitoring and verification.
"""
import os
import sys
import json
import time
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from huggingface_hub import HfApi, SpaceInfo
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Deployment configuration
SPACES_CONFIG = [
    {
        "name": "ToolKit-backend/PopCorn",
        "token_env": "HF_TOKEN_1",
        "description": "Main PopCorn Space",
        "priority": 1
    },
    {
        "name": "ToolKit-backend/popcorn-main",
        "token_env": "HF_TOKEN_1",
        "description": "PopCorn Main Mirror",
        "priority": 2
    },
    {
        "name": "ToolKit-backend/popcorn-streaming",
        "token_env": "HF_TOKEN_1",
        "description": "PopCorn Streaming Space",
        "priority": 3
    },
    {
        "name": "rayig/popcorn-backup",
        "token_env": "HF_TOKEN_2",
        "description": "PopCorn Backup Space",
        "priority": 4
    },
    {
        "name": "rayig/popcorn-analytics",
        "token_env": "HF_TOKEN_2",
        "description": "PopCorn Analytics Space",
        "priority": 5
    }
]

# Environment variables to set in Spaces
ENV_VARS = {
    "MAIN_BOT_TOKEN": os.getenv("MAIN_BOT_TOKEN", ""),
    "ADMIN_ID": os.getenv("ADMIN_ID", ""),
    "PRIVATE_GROUPE_1_ID": os.getenv("PRIVATE_GROUPE_1_ID", ""),
    "SESSION_1_API_ID": os.getenv("SESSION_1_API_ID", ""),
    "SESSION_1_API_HASH": os.getenv("SESSION_1_API_HASH", ""),
}

# Files to deploy
FILES_TO_DEPLOY = [
    "app/__init__.py",
    "app/bot.py",
    "app/main.py",
    "app/config.py",
    "app/database.py",
    "app/admin_panel.py",
    "app/sync_manager.py",
    "app/permissions.py",
    "app/reports_generator.py",
    "app/bot_commands.py",
    "app/user_tracking.py",
    "app/analytics.py",
    "app/cache.py",
    "app/scanner.py",
    "app/stream.py",
    "app/tmdb.py",
    "app/error_handlers.py",
    "app/exceptions.py",
    "app/friends.py",
    "app/health_monitor.py",
    "app/messaging.py",
    "app/mirror_manager.py",
    "app/multi_account_manager.py",
    "app/multi_dataset_manager.py",
    "app/multi_group_sync.py",
    "app/multi_source_config.py",
    "app/multi_space_manager.py",
    "app/notifications.py",
    "app/periodic_tasks.py",
    "app/register_topic_handler.py",
    "app/room_sync.py",
    "app/security.py",
    "app/smart_cache.py",
    "app/smart_sync.py",
    "app/sync_bot.py",
    "app/watch_rooms.py",
    "app/websocket_handler.py",
    "app/websocket_manager.py",
    "app/advanced_streaming.py",
    "app/backup_manager.py",
    "app/db_manager.py",
    "requirements.txt",
    "Dockerfile",
    ".env.example",
    "README.md"
]


class DeploymentManager:
    """Manages deployment to multiple HuggingFace Spaces."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.base_path = Path(__file__).parent
        self.deployment_results = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "spaces": {},
            "summary": {
                "total": len(SPACES_CONFIG),
                "successful": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
        # Initialize HF API clients
        self.hf_apis = {}
        for space in SPACES_CONFIG:
            token = os.getenv(space["token_env"])
            if token:
                self.hf_apis[space["name"]] = HfApi(token=token)
            else:
                logger.warning(f"⚠️  No token found for {space['name']}")
    
    async def deploy_all_spaces(self) -> Dict:
        """Deploy to all configured spaces."""
        logger.info("=" * 80)
        logger.info("🚀 STARTING DEPLOYMENT TO ALL SPACES")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual deployment will occur")
        
        # Validate environment variables
        if not self.validate_environment():
            logger.error("❌ Environment validation failed!")
            return self.deployment_results
        
        # Deploy to each space
        for space_config in SPACES_CONFIG:
            logger.info(f"\n{'=' * 80}")
            logger.info(f"📦 Deploying to: {space_config['name']}")
            logger.info(f"{'=' * 80}")
            
            result = await self.deploy_to_space(space_config)
            self.deployment_results["spaces"][space_config["name"]] = result
            
            if result["success"]:
                self.deployment_results["summary"]["successful"] += 1
                logger.info(f"✅ Successfully deployed to {space_config['name']}")
            else:
                self.deployment_results["summary"]["failed"] += 1
                logger.error(f"❌ Failed to deploy to {space_config['name']}")
            
            # Wait between deployments to avoid rate limits
            if not self.dry_run:
                await asyncio.sleep(5)
        
        # Generate final report
        self.generate_deployment_report()
        
        return self.deployment_results
    
    def validate_environment(self) -> bool:
        """Validate required environment variables."""
        logger.info("🔍 Validating environment variables...")
        
        missing_vars = []
        for var_name, var_value in ENV_VARS.items():
            if not var_value:
                missing_vars.append(var_name)
                logger.warning(f"⚠️  Missing: {var_name}")
        
        if missing_vars:
            logger.warning(f"⚠️  {len(missing_vars)} environment variables missing")
            logger.warning("Deployment will continue, but Spaces may not function correctly")
            self.deployment_results["summary"]["warnings"] += 1
            return True  # Continue anyway
        
        logger.info("✅ All environment variables present")
        return True
    
    async def deploy_to_space(self, space_config: Dict) -> Dict:
        """Deploy to a single Space."""
        space_name = space_config["name"]
        result = {
            "success": False,
            "space_name": space_name,
            "description": space_config["description"],
            "priority": space_config["priority"],
            "files_uploaded": 0,
            "env_vars_set": 0,
            "build_status": "unknown",
            "errors": [],
            "warnings": [],
            "duration": 0
        }
        
        start_time = time.time()
        
        try:
            # Check if we have API client for this space
            if space_name not in self.hf_apis:
                raise Exception(f"No HF API client available for {space_name}")
            
            api = self.hf_apis[space_name]
            
            # 1. Check if Space exists
            logger.info(f"📋 Checking Space existence...")
            if not self.dry_run:
                try:
                    space_info = api.space_info(repo_id=space_name)
                    logger.info(f"✅ Space exists: {space_name}")
                except Exception as e:
                    logger.warning(f"⚠️  Space may not exist or is inaccessible: {e}")
                    result["warnings"].append(f"Space accessibility issue: {str(e)}")
            
            # 2. Upload files
            logger.info(f"📤 Uploading files...")
            uploaded_count = await self.upload_files(api, space_name, result)
            result["files_uploaded"] = uploaded_count
            
            # 3. Set environment variables
            logger.info(f"⚙️  Setting environment variables...")
            env_count = await self.set_environment_variables(api, space_name, result)
            result["env_vars_set"] = env_count
            
            # 4. Trigger rebuild
            logger.info(f"🔨 Triggering rebuild...")
            if not self.dry_run:
                try:
                    api.restart_space(repo_id=space_name)
                    logger.info(f"✅ Rebuild triggered for {space_name}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not trigger rebuild: {e}")
                    result["warnings"].append(f"Rebuild trigger failed: {str(e)}")
            
            # 5. Monitor build status
            logger.info(f"👀 Monitoring build status...")
            build_status = await self.monitor_build(api, space_name, result)
            result["build_status"] = build_status
            
            # 6. Verify deployment
            logger.info(f"✔️  Verifying deployment...")
            verification = await self.verify_deployment(space_name, result)
            
            result["success"] = (
                result["files_uploaded"] > 0 and
                result["build_status"] in ["running", "building"] and
                verification
            )
            
        except Exception as e:
            logger.error(f"❌ Deployment error: {e}")
            result["errors"].append(str(e))
            result["success"] = False
        
        result["duration"] = time.time() - start_time
        return result
    
    async def upload_files(self, api: HfApi, space_name: str, result: Dict) -> int:
        """Upload files to Space."""
        uploaded = 0
        
        for file_path in FILES_TO_DEPLOY:
            full_path = self.base_path / file_path
            
            if not full_path.exists():
                logger.warning(f"⚠️  File not found: {file_path}")
                result["warnings"].append(f"File not found: {file_path}")
                continue
            
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would upload: {file_path}")
                uploaded += 1
                continue
            
            try:
                api.upload_file(
                    path_or_fileobj=str(full_path),
                    path_in_repo=file_path,
                    repo_id=space_name,
                    repo_type="space"
                )
                logger.info(f"  ✅ Uploaded: {file_path}")
                uploaded += 1
            except Exception as e:
                logger.error(f"  ❌ Failed to upload {file_path}: {e}")
                result["errors"].append(f"Upload failed for {file_path}: {str(e)}")
        
        return uploaded
    
    async def set_environment_variables(self, api: HfApi, space_name: str, result: Dict) -> int:
        """Set environment variables in Space."""
        set_count = 0
        
        for var_name, var_value in ENV_VARS.items():
            if not var_value:
                continue
            
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would set: {var_name}")
                set_count += 1
                continue
            
            try:
                api.add_space_secret(
                    repo_id=space_name,
                    key=var_name,
                    value=var_value
                )
                logger.info(f"  ✅ Set: {var_name}")
                set_count += 1
            except Exception as e:
                logger.warning(f"  ⚠️  Could not set {var_name}: {e}")
                result["warnings"].append(f"Env var {var_name}: {str(e)}")
        
        return set_count
    
    async def monitor_build(self, api: HfApi, space_name: str, result: Dict, timeout: int = 600) -> str:
        """Monitor Space build status with timeout handling."""
        if self.dry_run:
            return "dry_run"
        
        start_time = time.time()
        last_status = "unknown"
        check_count = 0
        max_checks = timeout // 10  # Maximum number of status checks
        
        logger.info(f"  ⏱️  Monitoring build (timeout: {timeout}s, max checks: {max_checks})")
        
        while time.time() - start_time < timeout and check_count < max_checks:
            try:
                space_info = api.space_info(repo_id=space_name)
                status = space_info.runtime.stage if space_info.runtime else "unknown"
                
                if status != last_status:
                    elapsed = time.time() - start_time
                    logger.info(f"  📊 Build status: {status} (elapsed: {elapsed:.1f}s)")
                    last_status = status
                
                if status == "RUNNING":
                    logger.info(f"  ✅ Space is RUNNING")
                    return "running"
                elif status in ["BUILDING", "BUILDING_CONTAINER"]:
                    logger.info(f"  🔨 Space is building... (check {check_count + 1}/{max_checks})")
                elif status in ["FAILED", "BUILD_ERROR"]:
                    logger.error(f"  ❌ Build failed with status: {status}")
                    result["errors"].append(f"Build failed with status: {status}")
                    return "failed"
                elif status == "STOPPED":
                    logger.warning(f"  ⚠️  Space is STOPPED")
                    result["warnings"].append("Space is in STOPPED state")
                    return "stopped"
                
                check_count += 1
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.warning(f"  ⚠️  Could not check status: {e}")
                result["warnings"].append(f"Status check error: {str(e)}")
                await asyncio.sleep(10)
                check_count += 1
        
        # Timeout reached
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            logger.warning(f"  ⏱️  Monitoring timeout reached ({elapsed:.1f}s)")
            result["warnings"].append(f"Build monitoring timeout after {elapsed:.1f}s")
        else:
            logger.warning(f"  ⏱️  Maximum status checks reached ({check_count})")
            result["warnings"].append(f"Maximum status checks reached ({check_count})")
        
        return last_status
    
    async def verify_deployment(self, space_name: str, result: Dict) -> bool:
        """Verify Space is accessible and responding."""
        if self.dry_run:
            return True
        
        # Construct Space URL
        space_url = f"https://{space_name.replace('/', '-')}.hf.space"
        health_url = f"{space_url}/health"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    logger.info(f"  ✅ Health check passed: {health_url}")
                    return True
                else:
                    logger.warning(f"  ⚠️  Health check returned {response.status_code}")
                    result["warnings"].append(f"Health check: HTTP {response.status_code}")
                    return False
                    
        except Exception as e:
            logger.warning(f"  ⚠️  Could not verify deployment: {e}")
            result["warnings"].append(f"Verification failed: {str(e)}")
            return False
    
    def generate_deployment_report(self):
        """Generate comprehensive deployment report."""
        logger.info("\n" + "=" * 80)
        logger.info("📊 DEPLOYMENT SUMMARY")
        logger.info("=" * 80)
        
        summary = self.deployment_results["summary"]
        logger.info(f"Total Spaces: {summary['total']}")
        logger.info(f"✅ Successful: {summary['successful']}")
        logger.info(f"❌ Failed: {summary['failed']}")
        logger.info(f"⚠️  Warnings: {summary['warnings']}")
        
        # Save detailed report
        report_path = self.base_path / "deployment_results.json"
        with open(report_path, 'w') as f:
            json.dump(self.deployment_results, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_path}")
        
        # Print individual space results
        logger.info("\n📋 Individual Space Results:")
        for space_name, space_result in self.deployment_results["spaces"].items():
            status = "✅" if space_result["success"] else "❌"
            logger.info(f"\n{status} {space_name}")
            logger.info(f"   Files uploaded: {space_result['files_uploaded']}")
            logger.info(f"   Env vars set: {space_result['env_vars_set']}")
            logger.info(f"   Build status: {space_result['build_status']}")
            logger.info(f"   Duration: {space_result['duration']:.1f}s")
            
            if space_result["errors"]:
                logger.info(f"   Errors: {len(space_result['errors'])}")
                for error in space_result["errors"][:3]:
                    logger.info(f"     - {error}")
            
            if space_result["warnings"]:
                logger.info(f"   Warnings: {len(space_result['warnings'])}")


async def main():
    """Main deployment execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy PopCorn Bot to HuggingFace Spaces')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actual deployment')
    parser.add_argument('--space', type=str, help='Deploy to specific space only')
    args = parser.parse_args()
    
    logger.info(f"🚀 Starting deployment (dry_run={args.dry_run})")
    
    manager = DeploymentManager(dry_run=args.dry_run)
    results = await manager.deploy_all_spaces()
    
    # Exit with appropriate code
    if results["summary"]["failed"] > 0:
        logger.error("\n❌ Deployment completed with failures!")
        sys.exit(1)
    elif results["summary"]["warnings"] > 0:
        logger.warning("\n⚠️  Deployment completed with warnings.")
        sys.exit(0)
    else:
        logger.info("\n✅ Deployment completed successfully!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
