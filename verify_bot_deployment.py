#!/usr/bin/env python3
"""
PopCorn Bot Deployment Verification Script
Verifies that the bot restructure deployment is working correctly.
"""
import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Verification Manager
# ══════════════════════════════════════════════════════════════════════════════

class DeploymentVerifier:
    """Verifies bot deployment on Hugging Face."""
    
    def __init__(self, space_name: str, bot_token: Optional[str] = None):
        """
        Initialize deployment verifier.
        
        Args:
            space_name: Hugging Face Space name
            bot_token: Telegram bot token (optional, for bot testing)
        """
        self.space_name = space_name
        self.bot_token = bot_token
        self.verification_results = []
        self.start_time = datetime.now()
    
    def log_result(self, check_name: str, passed: bool, details: str = "", error: str = ""):
        """Log verification result."""
        result = {
            "check": check_name,
            "passed": passed,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.verification_results.append(result)
        
        status = "✅" if passed else "❌"
        print(f"  {status} {check_name}")
        if details:
            print(f"     {details}")
        if error:
            print(f"     Error: {error}")
    
    def check_files_deployed(self) -> bool:
        """Check if all required files are present locally."""
        print("\n📁 Checking Deployed Files...")
        
        required_files = [
            "app/admin_permissions.py",
            "app/bot_tracking.py",
            "app/button_builders.py",
            "app/subscription_checker.py",
            "app/bot.py",
            "app/bot_commands.py",
            "app/database.py",
            "app/config.py",
        ]
        
        all_present = True
        for filepath in required_files:
            exists = os.path.exists(filepath)
            if exists:
                size = os.path.getsize(filepath)
                self.log_result(
                    f"File: {filepath}",
                    True,
                    f"Size: {size} bytes"
                )
            else:
                self.log_result(
                    f"File: {filepath}",
                    False,
                    error="File not found"
                )
                all_present = False
        
        return all_present
    
    def check_database_schema(self) -> bool:
        """Check if database tables are created correctly."""
        print("\n🗄️  Checking Database Schema...")
        
        try:
            from app.database import Database
            
            db = Database()
            
            # Check required tables
            required_tables = [
                "users",
                "subscriptions",
                "admin_permissions",
                "bot_interactions",
                "button_clicks"
            ]
            
            all_tables_exist = True
            for table in required_tables:
                # Try to query the table
                try:
                    result = db.execute_query(f"SELECT COUNT(*) FROM {table}")
                    count = result[0][0] if result else 0
                    self.log_result(
                        f"Table: {table}",
                        True,
                        f"Records: {count}"
                    )
                except Exception as e:
                    self.log_result(
                        f"Table: {table}",
                        False,
                        error=str(e)
                    )
                    all_tables_exist = False
            
            return all_tables_exist
            
        except Exception as e:
            self.log_result(
                "Database Connection",
                False,
                error=str(e)
            )
            return False
    
    def check_configuration(self) -> bool:
        """Check if configuration is loaded properly."""
        print("\n⚙️  Checking Configuration...")
        
        try:
            from app.config import Config
            
            config = Config()
            
            # Check critical config values
            checks = [
                ("BOT_TOKEN", config.BOT_TOKEN is not None),
                ("ADMIN_IDS", len(config.ADMIN_IDS) > 0),
                ("CHANNEL_ID", config.CHANNEL_ID is not None),
                ("DATABASE_URL", config.DATABASE_URL is not None),
            ]
            
            all_ok = True
            for name, value in checks:
                self.log_result(
                    f"Config: {name}",
                    value,
                    "Configured" if value else "Not set"
                )
                if not value:
                    all_ok = False
            
            return all_ok
            
        except Exception as e:
            self.log_result(
                "Configuration Load",
                False,
                error=str(e)
            )
            return False
    
    def check_imports(self) -> bool:
        """Check if all modules can be imported."""
        print("\n📦 Checking Module Imports...")
        
        modules = [
            "app.admin_permissions",
            "app.bot_tracking",
            "app.button_builders",
            "app.subscription_checker",
            "app.bot",
            "app.bot_commands",
            "app.database",
            "app.config",
        ]
        
        all_imported = True
        for module in modules:
            try:
                __import__(module)
                self.log_result(
                    f"Import: {module}",
                    True,
                    "Successfully imported"
                )
            except Exception as e:
                self.log_result(
                    f"Import: {module}",
                    False,
                    error=str(e)
                )
                all_imported = False
        
        return all_imported
    
    async def test_bot_responsiveness(self) -> bool:
        """Test if bot responds to commands."""
        print("\n🤖 Testing Bot Responsiveness...")
        
        if not self.bot_token:
            self.log_result(
                "Bot Test",
                False,
                error="Bot token not provided"
            )
            return False
        
        try:
            from telegram import Bot
            
            bot = Bot(token=self.bot_token)
            
            # Test getMe
            me = await bot.get_me()
            self.log_result(
                "Bot API Connection",
                True,
                f"Bot: @{me.username}"
            )
            
            # Test getUpdates
            updates = await bot.get_updates(limit=1)
            self.log_result(
                "Bot Updates",
                True,
                f"Can receive updates"
            )
            
            return True
            
        except Exception as e:
            self.log_result(
                "Bot Responsiveness",
                False,
                error=str(e)
            )
            return False
    
    def check_space_status(self) -> bool:
        """Check Hugging Face Space status."""
        print("\n🌐 Checking Space Status...")
        
        try:
            from huggingface_hub import HfApi
            
            api = HfApi()
            space_info = api.space_info(repo_id=self.space_name)
            
            runtime = space_info.runtime
            if runtime:
                stage = runtime.stage
                self.log_result(
                    "Space Status",
                    stage == "RUNNING",
                    f"Stage: {stage}"
                )
                return stage == "RUNNING"
            else:
                self.log_result(
                    "Space Status",
                    False,
                    error="No runtime information"
                )
                return False
                
        except Exception as e:
            self.log_result(
                "Space Status",
                False,
                error=str(e)
            )
            return False
    
    def generate_report(self, filepath: str = "verification_report.json"):
        """Generate verification report."""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        passed_checks = sum(1 for r in self.verification_results if r["passed"])
        total_checks = len(self.verification_results)
        success_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "space_name": self.space_name,
            "duration_seconds": duration,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "success_rate": success_rate,
            "results": self.verification_results
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Verification report saved: {filepath}")
        return report
    
    def print_summary(self):
        """Print verification summary."""
        passed = sum(1 for r in self.verification_results if r["passed"])
        total = len(self.verification_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "="*80)
        print("📊 VERIFICATION SUMMARY")
        print("="*80)
        print(f"Total Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {success_rate:.1f}%")
        print("="*80)
        
        if success_rate == 100:
            print("✅ All verification checks passed!")
            print("\n🎉 Deployment is fully functional!")
        elif success_rate >= 80:
            print("⚠️  Most checks passed, but some issues detected")
            print("Please review the failed checks above")
        else:
            print("❌ Multiple verification checks failed")
            print("Deployment may have issues - please investigate")


# ══════════════════════════════════════════════════════════════════════════════
# Main Verification Function
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    """Main verification function."""
    print("="*80)
    print("🔍 PopCorn Bot Deployment Verification")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    space_name = os.getenv("HF_SPACE_NAME", "")
    bot_token = os.getenv("BOT_TOKEN", "")
    
    if not space_name:
        print("⚠️  Warning: HF_SPACE_NAME not set, skipping Space status check")
    
    # Initialize verifier
    verifier = DeploymentVerifier(space_name, bot_token)
    
    # Run verification checks
    verifier.check_files_deployed()
    verifier.check_imports()
    verifier.check_configuration()
    verifier.check_database_schema()
    
    if space_name:
        verifier.check_space_status()
    
    if bot_token:
        await verifier.test_bot_responsiveness()
    else:
        print("\n⚠️  Bot token not provided, skipping bot responsiveness test")
    
    # Generate report
    report = verifier.generate_report()
    
    # Print summary
    verifier.print_summary()
    
    # Return exit code based on success rate
    success_rate = report["success_rate"]
    if success_rate == 100:
        return 0
    elif success_rate >= 80:
        return 0  # Warning but not failure
    else:
        return 1  # Failure


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

# Made with Bob