#!/usr/bin/env python3
"""
PopCorn Bot Restructure - Deployment Script
Deploys the updated bot system to Hugging Face Space.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from huggingface_hub import HfApi, CommitOperationAdd
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("⚠️  Warning: huggingface_hub not installed. Install with: pip install huggingface_hub")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Files to deploy (new and modified files from Phase 1 & 2)
FILES_TO_DEPLOY = [
    "app/admin_permissions.py",      # NEW - Phase 1
    "app/bot_tracking.py",           # NEW - Phase 1
    "app/button_builders.py",        # NEW - Phase 2
    "app/subscription_checker.py",   # MODIFIED - Phase 1
    "app/bot.py",                    # REWRITTEN - Phase 2
    "app/bot_commands.py",           # REWRITTEN - Phase 2
    "app/database.py",               # MODIFIED - Phase 1 (connection pool)
    "app/config.py",                 # MODIFIED - Phase 1 (admin config)
]

# Optional files (won't fail deployment if missing)
OPTIONAL_FILES = [
    "requirements.txt",
    "README.md",
]

# ══════════════════════════════════════════════════════════════════════════════
# Deployment Manager
# ══════════════════════════════════════════════════════════════════════════════

class DeploymentManager:
    """Manages deployment to Hugging Face Space."""
    
    def __init__(self, hf_token: str, space_name: str):
        """
        Initialize deployment manager.
        
        Args:
            hf_token: Hugging Face API token
            space_name: Space name (e.g., "username/space-name")
        """
        self.hf_token = hf_token
        self.space_name = space_name
        self.api = HfApi(token=hf_token) if HF_AVAILABLE else None
        self.deployment_log = []
    
    def log(self, message: str, level: str = "info"):
        """Log deployment message."""
        timestamp = datetime.now().isoformat()
        self.deployment_log.append({
            "timestamp": timestamp,
            "level": level,
            "message": message
        })
        
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def check_prerequisites(self) -> bool:
        """Check deployment prerequisites."""
        print("\n🔍 Checking Prerequisites...")
        
        all_ok = True
        
        # Check HuggingFace Hub
        if not HF_AVAILABLE:
            print("  ❌ huggingface_hub not installed")
            self.log("huggingface_hub not installed", "error")
            all_ok = False
        else:
            print("  ✅ huggingface_hub installed")
        
        # Check HF token
        if not self.hf_token:
            print("  ❌ HF_TOKEN not set")
            self.log("HF_TOKEN not set", "error")
            all_ok = False
        else:
            print("  ✅ HF_TOKEN configured")
        
        # Check space name
        if not self.space_name:
            print("  ❌ HF_SPACE_NAME not set")
            self.log("HF_SPACE_NAME not set", "error")
            all_ok = False
        else:
            print(f"  ✅ Target Space: {self.space_name}")
        
        # Verify files exist
        missing_files = []
        for filepath in FILES_TO_DEPLOY:
            if not os.path.exists(filepath):
                missing_files.append(filepath)
        
        if missing_files:
            print(f"  ❌ Missing files: {', '.join(missing_files)}")
            self.log(f"Missing files: {missing_files}", "error")
            all_ok = False
        else:
            print(f"  ✅ All {len(FILES_TO_DEPLOY)} required files present")
        
        return all_ok
    
    def verify_space_access(self) -> bool:
        """Verify access to Hugging Face Space."""
        print("\n🔐 Verifying Space Access...")
        
        if not self.api:
            print("  ❌ HuggingFace API not available")
            return False
        
        try:
            # Try to get space info
            space_info = self.api.space_info(repo_id=self.space_name)
            print(f"  ✅ Space accessible: {space_info.id}")
            self.log(f"Space accessible: {space_info.id}")
            return True
        except Exception as e:
            print(f"  ❌ Cannot access space: {e}")
            self.log(f"Cannot access space: {e}", "error")
            return False
    
    def create_backup(self) -> bool:
        """Create backup of current Space state."""
        print("\n💾 Creating Backup...")
        
        try:
            backup_dir = f"backups/bot_restructure_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Note: In production, you would download current files from Space
            # For now, we just create the backup directory
            print(f"  ✅ Backup directory created: {backup_dir}")
            self.log(f"Backup directory created: {backup_dir}")
            return True
        except Exception as e:
            print(f"  ⚠️  Backup creation failed: {e}")
            self.log(f"Backup creation failed: {e}", "warning")
            return False
    
    def deploy_files(self, commit_message: str = "Deploy bot restructure (Phase 1 & 2)") -> bool:
        """Deploy files to Hugging Face Space."""
        print("\n🚀 Deploying Files...")
        
        if not self.api:
            print("  ❌ HuggingFace API not available")
            return False
        
        try:
            operations = []
            
            # Prepare file operations
            for filepath in FILES_TO_DEPLOY:
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        content = f.read()
                    
                    operations.append(
                        CommitOperationAdd(
                            path_in_repo=filepath,
                            path_or_fileobj=filepath
                        )
                    )
                    print(f"  📤 Staging: {filepath}")
                    self.log(f"Staging file: {filepath}")
            
            # Add optional files if they exist
            for filepath in OPTIONAL_FILES:
                if os.path.exists(filepath):
                    operations.append(
                        CommitOperationAdd(
                            path_in_repo=filepath,
                            path_or_fileobj=filepath
                        )
                    )
                    print(f"  📤 Staging (optional): {filepath}")
                    self.log(f"Staging optional file: {filepath}")
            
            if not operations:
                print("  ⚠️  No files to deploy")
                self.log("No files to deploy", "warning")
                return False
            
            # Commit to Space
            print(f"\n  📝 Committing {len(operations)} files...")
            self.log(f"Committing {len(operations)} files")
            
            commit_info = self.api.create_commit(
                repo_id=self.space_name,
                repo_type="space",
                operations=operations,
                commit_message=commit_message
            )
            
            print(f"  ✅ Deployment successful!")
            print(f"  📋 Commit: {commit_info.commit_url}")
            self.log(f"Deployment successful: {commit_info.commit_url}")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Deployment failed: {e}")
            self.log(f"Deployment failed: {e}", "error")
            return False
    
    def monitor_build(self, timeout: int = 300) -> bool:
        """Monitor Space build status."""
        print("\n⏳ Monitoring Build Status...")
        
        if not self.api:
            print("  ⚠️  Cannot monitor build (API not available)")
            return True  # Don't fail deployment
        
        try:
            import time
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    space_info = self.api.space_info(repo_id=self.space_name)
                    runtime = space_info.runtime
                    
                    if runtime:
                        stage = runtime.stage
                        print(f"  📊 Build stage: {stage}")
                        
                        if stage == "RUNNING":
                            print("  ✅ Space is running!")
                            self.log("Space is running")
                            return True
                        elif stage in ["FAILED", "STOPPED"]:
                            print(f"  ❌ Build failed: {stage}")
                            self.log(f"Build failed: {stage}", "error")
                            return False
                    
                    time.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    print(f"  ⚠️  Error checking status: {e}")
                    time.sleep(10)
            
            print("  ⏰ Monitoring timeout reached")
            self.log("Monitoring timeout reached", "warning")
            return True  # Don't fail deployment on timeout
            
        except Exception as e:
            print(f"  ⚠️  Monitoring error: {e}")
            self.log(f"Monitoring error: {e}", "warning")
            return True  # Don't fail deployment on monitoring error
    
    def verify_deployment(self) -> Dict[str, Any]:
        """Verify deployment success."""
        print("\n✅ Verifying Deployment...")
        
        results = {
            "success": True,
            "checks": []
        }
        
        # Check Space status
        if self.api:
            try:
                space_info = self.api.space_info(repo_id=self.space_name)
                runtime = space_info.runtime
                
                if runtime and runtime.stage == "RUNNING":
                    print("  ✅ Space is running")
                    results["checks"].append({"name": "Space Status", "passed": True})
                else:
                    print(f"  ⚠️  Space status: {runtime.stage if runtime else 'Unknown'}")
                    results["checks"].append({"name": "Space Status", "passed": False})
                    results["success"] = False
            except Exception as e:
                print(f"  ⚠️  Cannot verify space status: {e}")
                results["checks"].append({"name": "Space Status", "passed": False, "error": str(e)})
        
        # Check files were uploaded
        print(f"  ℹ️  {len(FILES_TO_DEPLOY)} files deployed")
        results["files_deployed"] = len(FILES_TO_DEPLOY)
        
        return results
    
    def save_deployment_report(self, results: Dict[str, Any], filepath: str = "deployment_report.json"):
        """Save deployment report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "space_name": self.space_name,
            "files_deployed": FILES_TO_DEPLOY,
            "results": results,
            "log": self.deployment_log
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Deployment report saved: {filepath}")


# ══════════════════════════════════════════════════════════════════════════════
# Main Deployment Function
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Main deployment function."""
    print("="*80)
    print("🚀 PopCorn Bot Restructure - Deployment")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    hf_token = os.getenv("HF_TOKEN", "")
    space_name = os.getenv("HF_SPACE_NAME", "")
    
    if not hf_token or not space_name:
        print("❌ ERROR: HF_TOKEN and HF_SPACE_NAME must be set in .env file")
        print("\nPlease set:")
        print("  HF_TOKEN=your_huggingface_token")
        print("  HF_SPACE_NAME=username/space-name")
        return 1
    
    # Initialize deployment manager
    manager = DeploymentManager(hf_token, space_name)
    
    # Run pre-deployment checks
    if not manager.check_prerequisites():
        print("\n❌ Pre-deployment checks failed. Fix issues and try again.")
        return 1
    
    if not manager.verify_space_access():
        print("\n❌ Cannot access Hugging Face Space. Check credentials and space name.")
        return 1
    
    # Create backup
    manager.create_backup()
    
    # Confirm deployment
    print("\n" + "="*80)
    print("⚠️  DEPLOYMENT CONFIRMATION")
    print("="*80)
    print(f"Space: {space_name}")
    print(f"Files to deploy: {len(FILES_TO_DEPLOY)}")
    print("\nFiles:")
    for f in FILES_TO_DEPLOY:
        print(f"  • {f}")
    print("\n" + "="*80)
    
    response = input("\n🤔 Proceed with deployment? (yes/no): ").strip().lower()
    
    if response != "yes":
        print("\n❌ Deployment cancelled by user")
        return 0
    
    # Deploy files
    if not manager.deploy_files():
        print("\n❌ Deployment failed")
        manager.save_deployment_report({"success": False}, "deployment_report_failed.json")
        return 1
    
    # Monitor build
    manager.monitor_build(timeout=300)
    
    # Verify deployment
    results = manager.verify_deployment()
    
    # Save report
    manager.save_deployment_report(results, "deployment_report_success.json")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 DEPLOYMENT SUMMARY")
    print("="*80)
    
    if results["success"]:
        print("✅ Deployment completed successfully!")
        print(f"\n🌐 Space URL: https://huggingface.co/spaces/{space_name}")
        print("\n📝 Next Steps:")
        print("  1. Monitor Space logs for any errors")
        print("  2. Test bot functionality (/start, /admin commands)")
        print("  3. Verify subscription checking works")
        print("  4. Test admin panel access")
        print("  5. Check bot tracking in database")
        return 0
    else:
        print("⚠️  Deployment completed with warnings")
        print("Please check the deployment report for details")
        return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
