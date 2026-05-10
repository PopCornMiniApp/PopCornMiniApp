#!/usr/bin/env python3
"""
🚨 CRITICAL BOT DIAGNOSTIC SCRIPT
==================================
Deep diagnostic investigation for bot non-responsiveness issue.
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class BotDiagnostic:
    def __init__(self):
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "errors": [],
            "warnings": [],
            "critical_issues": [],
            "recommendations": []
        }
        
    def add_check(self, name, status, details=None, error=None):
        """Add a check result"""
        self.results["checks"][name] = {
            "status": status,
            "details": details,
            "error": str(error) if error else None
        }
        if status == "FAIL":
            self.results["critical_issues"].append(name)
        
    def add_warning(self, message):
        """Add a warning"""
        self.results["warnings"].append(message)
        logger.warning(f"⚠️  {message}")
        
    def add_error(self, message):
        """Add an error"""
        self.results["errors"].append(message)
        logger.error(f"❌ {message}")
        
    def add_recommendation(self, message):
        """Add a recommendation"""
        self.results["recommendations"].append(message)
        
    async def check_environment_variables(self):
        """Check all required environment variables"""
        logger.info("🔍 Checking environment variables...")
        
        required_vars = {
            "MAIN_BOT_TOKEN": "Telegram Bot Token",
            "HF_TOKEN": "HuggingFace Token",
            "ADMIN_ID": "Admin User ID",
            "PRIVATE_GROUP_ID": "Private Group ID",
            "SESSION_1_API_ID": "Pyrogram API ID",
            "SESSION_1_API_HASH": "Pyrogram API Hash",
        }
        
        missing = []
        invalid = []
        
        for var, description in required_vars.items():
            value = os.getenv(var)
            if not value or value == "0" or value == "":
                missing.append(f"{var} ({description})")
            else:
                # Validate format
                if var == "MAIN_BOT_TOKEN":
                    if not value.count(":") == 1 or len(value) < 40:
                        invalid.append(f"{var}: Invalid format (should be like 123456:ABC-DEF...)")
                elif var in ["ADMIN_ID", "PRIVATE_GROUP_ID", "SESSION_1_API_ID"]:
                    try:
                        int(value)
                    except ValueError:
                        invalid.append(f"{var}: Must be a number")
        
        if missing:
            self.add_check("environment_variables", "FAIL", 
                          {"missing": missing, "invalid": invalid})
            self.add_error(f"Missing environment variables: {', '.join(missing)}")
            self.add_recommendation("Set all required environment variables in HuggingFace Space settings")
        elif invalid:
            self.add_check("environment_variables", "WARN", 
                          {"missing": [], "invalid": invalid})
            self.add_warning(f"Invalid environment variables: {', '.join(invalid)}")
        else:
            self.add_check("environment_variables", "PASS", 
                          {"all_required_vars_present": True})
            logger.info("✅ All environment variables present")
            
    async def check_telegram_api_connectivity(self):
        """Test Telegram API connectivity"""
        logger.info("🔍 Testing Telegram API connectivity...")
        
        token = os.getenv("MAIN_BOT_TOKEN")
        if not token:
            self.add_check("telegram_api", "SKIP", 
                          {"reason": "No bot token available"})
            return
            
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{token}/getMe"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            bot_info = data.get("result", {})
                            self.add_check("telegram_api", "PASS", {
                                "bot_username": bot_info.get("username"),
                                "bot_id": bot_info.get("id"),
                                "bot_name": bot_info.get("first_name"),
                                "can_join_groups": bot_info.get("can_join_groups"),
                                "can_read_all_group_messages": bot_info.get("can_read_all_group_messages")
                            })
                            logger.info(f"✅ Bot connected: @{bot_info.get('username')}")
                        else:
                            self.add_check("telegram_api", "FAIL", 
                                          {"error": data.get("description")})
                            self.add_error(f"Telegram API error: {data.get('description')}")
                    elif response.status == 401:
                        self.add_check("telegram_api", "FAIL", 
                                      {"error": "Invalid bot token (401 Unauthorized)"})
                        self.add_error("Bot token is invalid or expired")
                        self.add_recommendation("Generate a new bot token from @BotFather")
                    else:
                        self.add_check("telegram_api", "FAIL", 
                                      {"error": f"HTTP {response.status}"})
                        self.add_error(f"Telegram API returned status {response.status}")
                        
        except asyncio.TimeoutError:
            self.add_check("telegram_api", "FAIL", 
                          {"error": "Connection timeout"})
            self.add_error("Telegram API connection timeout")
            self.add_recommendation("Check network connectivity")
        except Exception as e:
            self.add_check("telegram_api", "FAIL", 
                          {"error": str(e)})
            self.add_error(f"Telegram API test failed: {e}")
            
    async def check_webhook_status(self):
        """Check if webhook is set (should be deleted for polling)"""
        logger.info("🔍 Checking webhook status...")
        
        token = os.getenv("MAIN_BOT_TOKEN")
        if not token:
            self.add_check("webhook_status", "SKIP", 
                          {"reason": "No bot token available"})
            return
            
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            webhook_info = data.get("result", {})
                            webhook_url = webhook_info.get("url", "")
                            
                            if webhook_url:
                                self.add_check("webhook_status", "WARN", {
                                    "webhook_url": webhook_url,
                                    "pending_update_count": webhook_info.get("pending_update_count", 0),
                                    "last_error_date": webhook_info.get("last_error_date"),
                                    "last_error_message": webhook_info.get("last_error_message")
                                })
                                self.add_warning(f"Webhook is set to: {webhook_url}")
                                self.add_recommendation("Delete webhook to use polling mode")
                            else:
                                self.add_check("webhook_status", "PASS", {
                                    "webhook_url": None,
                                    "status": "No webhook set (polling mode)"
                                })
                                logger.info("✅ No webhook set (polling mode active)")
                                
        except Exception as e:
            self.add_check("webhook_status", "FAIL", 
                          {"error": str(e)})
            self.add_error(f"Webhook check failed: {e}")
            
    async def check_bot_commands(self):
        """Check if bot commands are registered"""
        logger.info("🔍 Checking bot commands...")
        
        token = os.getenv("MAIN_BOT_TOKEN")
        if not token:
            self.add_check("bot_commands", "SKIP", 
                          {"reason": "No bot token available"})
            return
            
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{token}/getMyCommands"
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("ok"):
                            commands = data.get("result", [])
                            self.add_check("bot_commands", "PASS", {
                                "commands_count": len(commands),
                                "commands": [f"/{cmd['command']} - {cmd['description']}" 
                                           for cmd in commands]
                            })
                            if commands:
                                logger.info(f"✅ {len(commands)} commands registered")
                            else:
                                self.add_warning("No commands registered")
                                
        except Exception as e:
            self.add_check("bot_commands", "FAIL", 
                          {"error": str(e)})
            self.add_error(f"Commands check failed: {e}")
            
    async def check_code_files(self):
        """Check if all required code files exist"""
        logger.info("🔍 Checking code files...")
        
        required_files = [
            "app/main.py",
            "app/config.py",
            "app/sync_bot.py",
            "app/bot_commands.py",
            "app/database.py",
            "app/stream.py",
            "requirements.txt",
            "Dockerfile"
        ]
        
        missing = []
        present = []
        
        for file_path in required_files:
            full_path = Path(file_path)
            if full_path.exists():
                present.append(file_path)
            else:
                missing.append(file_path)
                
        if missing:
            self.add_check("code_files", "FAIL", {
                "missing": missing,
                "present": present
            })
            self.add_error(f"Missing files: {', '.join(missing)}")
        else:
            self.add_check("code_files", "PASS", {
                "all_files_present": True,
                "count": len(present)
            })
            logger.info(f"✅ All {len(present)} required files present")
            
    async def check_bot_initialization_code(self):
        """Check bot initialization code in main.py"""
        logger.info("🔍 Checking bot initialization code...")
        
        try:
            with open("app/main.py", "r", encoding="utf-8") as f:
                content = f.read()
                
            checks = {
                "imports_telegram": "from telegram" in content or "import telegram" in content,
                "imports_sync_bot": "from app.sync_bot import build_sync_app" in content,
                "imports_bot_commands": "from app.bot_commands import" in content,
                "has_lifespan": "@asynccontextmanager" in content and "async def lifespan" in content,
                "checks_bot_token": "if MAIN_BOT_TOKEN:" in content,
                "creates_bot_task": "_bot_task = asyncio.create_task(_run_bot" in content,
                "has_run_bot_function": "async def _run_bot" in content,
                "deletes_webhook": "delete_webhook" in content,
                "starts_polling": "start_polling" in content
            }
            
            failed_checks = [k for k, v in checks.items() if not v]
            
            if failed_checks:
                self.add_check("bot_initialization", "WARN", {
                    "checks": checks,
                    "failed": failed_checks
                })
                self.add_warning(f"Bot initialization checks failed: {', '.join(failed_checks)}")
            else:
                self.add_check("bot_initialization", "PASS", {
                    "all_checks_passed": True
                })
                logger.info("✅ Bot initialization code looks correct")
                
        except Exception as e:
            self.add_check("bot_initialization", "FAIL", 
                          {"error": str(e)})
            self.add_error(f"Failed to check bot initialization: {e}")
            
    async def check_huggingface_space_status(self):
        """Check HuggingFace Space status"""
        logger.info("🔍 Checking HuggingFace Space status...")
        
        hf_token = os.getenv("HF_TOKEN")
        space_name = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
        
        if not hf_token:
            self.add_check("hf_space_status", "SKIP", 
                          {"reason": "No HF_TOKEN available"})
            return
            
        try:
            import aiohttp
            
            headers = {"Authorization": f"Bearer {hf_token}"}
            url = f"https://huggingface.co/api/spaces/{space_name}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        runtime = data.get("runtime", {})
                        
                        self.add_check("hf_space_status", "PASS", {
                            "space_name": space_name,
                            "stage": runtime.get("stage"),
                            "hardware": runtime.get("hardware"),
                            "sdk": data.get("sdk"),
                            "likes": data.get("likes", 0)
                        })
                        
                        stage = runtime.get("stage", "UNKNOWN")
                        logger.info(f"✅ Space status: {stage}")
                        
                        if stage != "RUNNING":
                            self.add_warning(f"Space is not RUNNING (current: {stage})")
                            self.add_recommendation("Check Space logs for build/runtime errors")
                    else:
                        self.add_check("hf_space_status", "FAIL", 
                                      {"error": f"HTTP {response.status}"})
                        self.add_error(f"Failed to get Space status: HTTP {response.status}")
                        
        except Exception as e:
            self.add_check("hf_space_status", "FAIL", 
                          {"error": str(e)})
            self.add_error(f"HuggingFace Space check failed: {e}")
            
    async def test_bot_locally(self):
        """Try to initialize bot locally to catch errors"""
        logger.info("🔍 Testing bot initialization locally...")
        
        token = os.getenv("MAIN_BOT_TOKEN")
        if not token:
            self.add_check("local_bot_test", "SKIP", 
                          {"reason": "No bot token available"})
            return
            
        try:
            # Try to import and initialize
            from telegram.ext import Application
            
            app = Application.builder().token(token).build()
            
            # Try to initialize
            await app.initialize()
            
            # Try to get bot info
            bot_info = await app.bot.get_me()
            
            self.add_check("local_bot_test", "PASS", {
                "bot_username": bot_info.username,
                "bot_id": bot_info.id,
                "initialization": "successful"
            })
            logger.info(f"✅ Bot initialized successfully: @{bot_info.username}")
            
            # Cleanup
            await app.shutdown()
            
        except Exception as e:
            self.add_check("local_bot_test", "FAIL", 
                          {"error": str(e), "error_type": type(e).__name__})
            self.add_error(f"Bot initialization failed: {e}")
            self.add_recommendation("Check bot token validity and network connectivity")
            
    def generate_report(self):
        """Generate diagnostic report"""
        logger.info("\n" + "="*80)
        logger.info("📊 DIAGNOSTIC REPORT")
        logger.info("="*80)
        
        # Summary
        total_checks = len(self.results["checks"])
        passed = sum(1 for c in self.results["checks"].values() if c["status"] == "PASS")
        failed = sum(1 for c in self.results["checks"].values() if c["status"] == "FAIL")
        warnings = sum(1 for c in self.results["checks"].values() if c["status"] == "WARN")
        skipped = sum(1 for c in self.results["checks"].values() if c["status"] == "SKIP")
        
        logger.info(f"\n📈 Summary:")
        logger.info(f"  Total Checks: {total_checks}")
        logger.info(f"  ✅ Passed: {passed}")
        logger.info(f"  ❌ Failed: {failed}")
        logger.info(f"  ⚠️  Warnings: {warnings}")
        logger.info(f"  ⏭️  Skipped: {skipped}")
        
        # Critical Issues
        if self.results["critical_issues"]:
            logger.info(f"\n🚨 CRITICAL ISSUES ({len(self.results['critical_issues'])}):")
            for issue in self.results["critical_issues"]:
                logger.info(f"  • {issue}")
                
        # Errors
        if self.results["errors"]:
            logger.info(f"\n❌ ERRORS ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                logger.info(f"  • {error}")
                
        # Warnings
        if self.results["warnings"]:
            logger.info(f"\n⚠️  WARNINGS ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                logger.info(f"  • {warning}")
                
        # Recommendations
        if self.results["recommendations"]:
            logger.info(f"\n💡 RECOMMENDATIONS ({len(self.results['recommendations'])}):")
            for i, rec in enumerate(self.results["recommendations"], 1):
                logger.info(f"  {i}. {rec}")
                
        logger.info("\n" + "="*80)
        
        # Determine root cause
        logger.info("\n🔍 ROOT CAUSE ANALYSIS:")
        if "environment_variables" in self.results["critical_issues"]:
            logger.info("  ⚠️  Missing or invalid environment variables")
            logger.info("  → Bot cannot start without proper configuration")
        elif "telegram_api" in self.results["critical_issues"]:
            logger.info("  ⚠️  Cannot connect to Telegram API")
            logger.info("  → Check bot token and network connectivity")
        elif "local_bot_test" in self.results["critical_issues"]:
            logger.info("  ⚠️  Bot initialization fails")
            logger.info("  → Check error details in the report")
        elif failed == 0 and warnings == 0:
            logger.info("  ✅ All checks passed!")
            logger.info("  → Bot should be working. Check Space logs for runtime errors.")
        else:
            logger.info("  ⚠️  Multiple issues detected")
            logger.info("  → Review all failed checks and warnings above")
            
        logger.info("="*80 + "\n")
        
        # Save to file
        report_file = "bot_diagnostic_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 Full report saved to: {report_file}")
        
        return self.results
        
    async def run_all_checks(self):
        """Run all diagnostic checks"""
        logger.info("🚀 Starting comprehensive bot diagnostic...\n")
        
        await self.check_environment_variables()
        await self.check_code_files()
        await self.check_bot_initialization_code()
        await self.check_telegram_api_connectivity()
        await self.check_webhook_status()
        await self.check_bot_commands()
        await self.check_huggingface_space_status()
        await self.test_bot_locally()
        
        return self.generate_report()


async def main():
    """Main diagnostic function"""
    diagnostic = BotDiagnostic()
    
    try:
        results = await diagnostic.run_all_checks()
        
        # Exit code based on results
        if results["critical_issues"]:
            sys.exit(1)
        elif results["errors"]:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Diagnostic failed: {e}", exc_info=True)
        sys.exit(3)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
