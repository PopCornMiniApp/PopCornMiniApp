#!/usr/bin/env python3
"""
Comprehensive Verification Script for PopCorn Bot and HuggingFace Space
Checks files on HF, Space status, bot functionality, and synchronization
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from huggingface_hub import HfApi, hf_hub_download
from dotenv import load_dotenv

load_dotenv()

class ComprehensiveVerification:
    def __init__(self):
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.bot_token = os.getenv("MAIN_BOT_TOKEN", "")
        self.space_name = os.getenv("HF_SPACE_NAME", "jamalmohamad1/PopCorn")
        self.dataset_name = os.getenv("HF_DATASET_NAME", "ToolKit-backend/PopCornDB")
        
        # Extract username and space name
        parts = self.space_name.split("/")
        self.username = parts[0] if len(parts) > 0 else ""
        self.space_slug = parts[1] if len(parts) > 1 else ""
        
        self.api_base = f"https://{self.username}-{self.space_slug.lower()}.hf.space"
        self.telegram_api = f"https://api.telegram.org/bot{self.bot_token}"
        
        self.api = HfApi(token=self.hf_token) if self.hf_token else None
        
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "hf_files": {},
            "space_status": {},
            "bot_tests": {},
            "sync_status": {},
            "errors": [],
            "warnings": [],
            "recommendations": [],
            "overall_status": "unknown"
        }
    
    def print_section(self, title: str):
        """Print section header"""
        print("\n" + "="*80)
        print(f"  {title}")
        print("="*80)
    
    def print_status(self, status: str, message: str):
        """Print status message"""
        symbols = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️",
            "progress": "🔄"
        }
        symbol = symbols.get(status, "•")
        print(f"{symbol} {message}")
    
    def check_hf_file(self, filename: str, repo_type: str = "space") -> Dict:
        """Check if a file exists and get its content on HuggingFace"""
        self.print_status("progress", f"Checking {filename}...")
        
        try:
            if not self.api:
                return {
                    "exists": False,
                    "error": "HF_TOKEN not configured"
                }
            
            repo_id = self.space_name if repo_type == "space" else self.dataset_name
            
            # List files in the repository
            files = self.api.list_repo_files(repo_id=repo_id, repo_type=repo_type)
            
            file_exists = filename in files or f"app/{filename}" in files
            
            if file_exists:
                # Try to download and read the file
                try:
                    full_path = filename if filename in files else f"app/{filename}"
                    local_path = hf_hub_download(
                        repo_id=repo_id,
                        filename=full_path,
                        repo_type=repo_type,
                        token=self.hf_token
                    )
                    
                    with open(local_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    self.print_status("success", f"{filename} found ({len(content)} bytes)")
                    
                    return {
                        "exists": True,
                        "path": full_path,
                        "size": len(content),
                        "lines": len(content.split('\n')),
                        "last_modified": "unknown"
                    }
                except Exception as e:
                    self.print_status("warning", f"{filename} exists but couldn't read: {str(e)}")
                    return {
                        "exists": True,
                        "readable": False,
                        "error": str(e)
                    }
            else:
                self.print_status("error", f"{filename} not found")
                return {
                    "exists": False,
                    "error": "File not found in repository"
                }
        
        except Exception as e:
            self.print_status("error", f"Error checking {filename}: {str(e)}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def check_all_hf_files(self):
        """Check all required files on HuggingFace"""
        self.print_section("1. Checking HuggingFace Files")
        
        required_files = [
            "bot_commands.py",
            "config.py",
            "bot_tracking.py",
            "button_builders.py",
            "bot.py",
            "database.py",
            "main.py"
        ]
        
        for filename in required_files:
            self.results["hf_files"][filename] = self.check_hf_file(filename)
            time.sleep(0.5)  # Rate limiting
        
        # Check if all critical files exist
        critical_files = ["bot_commands.py", "config.py", "bot.py", "main.py"]
        missing_critical = [f for f in critical_files if not self.results["hf_files"].get(f, {}).get("exists")]
        
        if missing_critical:
            self.results["errors"].append(f"Missing critical files: {', '.join(missing_critical)}")
        else:
            self.print_status("success", "All critical files present on HuggingFace")
    
    def check_space_status(self) -> Dict:
        """Check HuggingFace Space status"""
        self.print_section("2. Checking Space Status")
        
        try:
            if not self.api:
                self.print_status("error", "Cannot check Space status: HF_TOKEN not configured")
                return {"status": "unknown", "error": "No HF_TOKEN"}
            
            # Get Space info
            space_info = self.api.space_info(repo_id=self.space_name)
            
            runtime_status = getattr(space_info, 'runtime', {})
            if isinstance(runtime_status, dict):
                stage = runtime_status.get('stage', 'unknown')
            else:
                stage = getattr(runtime_status, 'stage', 'unknown') if runtime_status else 'unknown'
            
            self.print_status("info", f"Space stage: {stage}")
            
            # Try to access the Space
            try:
                response = requests.get(f"{self.api_base}/health", timeout=10)
                accessible = response.status_code == 200
                self.print_status("success" if accessible else "warning", 
                                f"Space {'accessible' if accessible else 'not accessible'}")
            except:
                accessible = False
                self.print_status("warning", "Space not accessible")
            
            status = {
                "stage": stage,
                "accessible": accessible,
                "url": self.api_base,
                "space_id": self.space_name
            }
            
            if stage == "RUNNING" and accessible:
                self.print_status("success", "Space is RUNNING and accessible")
            elif stage == "RUNNING":
                self.results["warnings"].append("Space is RUNNING but not accessible")
            else:
                self.results["warnings"].append(f"Space is in {stage} state")
            
            return status
        
        except Exception as e:
            self.print_status("error", f"Error checking Space status: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_space_logs(self):
        """Check Space logs for errors"""
        self.print_status("info", "Checking Space logs...")
        
        try:
            if not self.api:
                return
            
            # Note: HuggingFace API doesn't provide direct log access
            # We'll check the Space's health endpoint instead
            response = requests.get(f"{self.api_base}/health", timeout=10)
            
            if response.status_code == 200:
                self.print_status("success", "Health endpoint responding")
            else:
                self.results["warnings"].append(f"Health endpoint returned {response.status_code}")
        
        except Exception as e:
            self.results["warnings"].append(f"Could not check logs: {str(e)}")
    
    def test_telegram_bot(self) -> Dict:
        """Test Telegram bot functionality"""
        self.print_section("3. Testing Telegram Bot")
        
        if not self.bot_token:
            self.print_status("error", "MAIN_BOT_TOKEN not configured")
            return {"status": "error", "error": "No bot token"}
        
        results = {}
        
        # Test 1: Get bot info
        try:
            response = requests.get(f"{self.telegram_api}/getMe", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    self.print_status("success", f"Bot connected: @{bot_info.get('username')}")
                    results["bot_info"] = bot_info
                    results["connected"] = True
                else:
                    self.print_status("error", "Bot API returned error")
                    results["connected"] = False
            else:
                self.print_status("error", f"Bot API returned {response.status_code}")
                results["connected"] = False
        except Exception as e:
            self.print_status("error", f"Cannot connect to bot: {str(e)}")
            results["connected"] = False
            results["error"] = str(e)
        
        # Test 2: Check webhook status
        try:
            response = requests.get(f"{self.telegram_api}/getWebhookInfo", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    webhook_info = data.get("result", {})
                    webhook_url = webhook_info.get("url", "")
                    
                    if webhook_url:
                        self.print_status("info", f"Webhook: {webhook_url}")
                        results["webhook"] = webhook_info
                    else:
                        self.print_status("info", "No webhook set (polling mode)")
                        results["webhook"] = None
        except Exception as e:
            self.print_status("warning", f"Could not check webhook: {str(e)}")
        
        return results
    
    def test_bot_commands(self) -> Dict:
        """Test bot commands"""
        self.print_status("info", "Testing bot commands...")
        
        try:
            response = requests.get(f"{self.telegram_api}/getMyCommands", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    commands = data.get("result", [])
                    self.print_status("success", f"Bot has {len(commands)} commands registered")
                    return {"commands": commands, "count": len(commands)}
        except Exception as e:
            self.print_status("warning", f"Could not check commands: {str(e)}")
        
        return {}
    
    def check_space_sync(self) -> Dict:
        """Check if multiple spaces are synchronized"""
        self.print_section("4. Checking Space Synchronization")
        
        # Check if multi-space is enabled
        enable_multi_space = os.getenv("ENABLE_MULTI_SPACE", "false").lower() == "true"
        
        if not enable_multi_space:
            self.print_status("info", "Multi-space not enabled")
            return {"enabled": False}
        
        self.print_status("info", "Multi-space enabled - checking synchronization...")
        
        # Try to get sync status from API
        try:
            response = requests.get(f"{self.api_base}/api/sync/status", timeout=10)
            if response.status_code == 200:
                sync_data = response.json()
                self.print_status("success", "Sync status retrieved")
                return {"enabled": True, "status": sync_data}
            else:
                self.print_status("warning", "Could not retrieve sync status")
                return {"enabled": True, "status": "unknown"}
        except Exception as e:
            self.print_status("warning", f"Sync check failed: {str(e)}")
            return {"enabled": True, "error": str(e)}
    
    def generate_recommendations(self):
        """Generate recommendations based on findings"""
        self.print_section("5. Generating Recommendations")
        
        # Check for missing files
        missing_files = [f for f, info in self.results["hf_files"].items() 
                        if not info.get("exists")]
        if missing_files:
            self.results["recommendations"].append(
                f"Upload missing files to HuggingFace: {', '.join(missing_files)}"
            )
        
        # Check Space status
        space_status = self.results["space_status"]
        if space_status.get("stage") != "RUNNING":
            self.results["recommendations"].append(
                "Restart the Space to apply latest changes"
            )
        
        if not space_status.get("accessible"):
            self.results["recommendations"].append(
                "Check Space logs for startup errors"
            )
        
        # Check bot connection
        bot_tests = self.results["bot_tests"]
        if not bot_tests.get("connected"):
            self.results["recommendations"].append(
                "Verify MAIN_BOT_TOKEN is correct and bot is active"
            )
        
        # Print recommendations
        if self.results["recommendations"]:
            for rec in self.results["recommendations"]:
                self.print_status("info", rec)
        else:
            self.print_status("success", "No critical issues found")
    
    def determine_overall_status(self):
        """Determine overall system status"""
        critical_errors = len(self.results["errors"])
        warnings = len(self.results["warnings"])
        
        # Check critical components
        files_ok = all(info.get("exists") for f, info in self.results["hf_files"].items() 
                      if f in ["bot.py", "main.py", "config.py"])
        space_ok = self.results["space_status"].get("stage") == "RUNNING"
        bot_ok = self.results["bot_tests"].get("connected", False)
        
        if critical_errors > 0:
            self.results["overall_status"] = "CRITICAL"
        elif not files_ok or not space_ok or not bot_ok:
            self.results["overall_status"] = "NEEDS_ATTENTION"
        elif warnings > 0:
            self.results["overall_status"] = "WARNING"
        else:
            self.results["overall_status"] = "HEALTHY"
    
    def generate_report(self) -> str:
        """Generate comprehensive verification report"""
        self.print_section("Generating Comprehensive Report")
        
        report = []
        report.append("# 🎬 PopCorn - تقرير التحقق الشامل")
        report.append(f"\n**تاريخ التقرير:** {self.results['timestamp']}")
        report.append(f"**حالة النظام:** {self.results['overall_status']}")
        
        # HuggingFace Files Section
        report.append("\n## 📁 ملفات HuggingFace")
        report.append(f"\n**Space:** `{self.space_name}`")
        report.append(f"**Dataset:** `{self.dataset_name}`")
        
        report.append("\n### الملفات المطلوبة:")
        for filename, info in self.results["hf_files"].items():
            status = "✅" if info.get("exists") else "❌"
            report.append(f"\n**{status} {filename}**")
            if info.get("exists"):
                report.append(f"- الحجم: {info.get('size', 0)} بايت")
                report.append(f"- الأسطر: {info.get('lines', 0)}")
            else:
                report.append(f"- الخطأ: {info.get('error', 'غير موجود')}")
        
        # Space Status Section
        report.append("\n## 🚀 حالة Space")
        space_status = self.results["space_status"]
        report.append(f"- **المرحلة:** {space_status.get('stage', 'unknown')}")
        report.append(f"- **قابل للوصول:** {'✅ نعم' if space_status.get('accessible') else '❌ لا'}")
        report.append(f"- **الرابط:** {space_status.get('url', 'N/A')}")
        
        # Bot Tests Section
        report.append("\n## 🤖 اختبارات البوت")
        bot_tests = self.results["bot_tests"]
        if bot_tests.get("connected"):
            bot_info = bot_tests.get("bot_info", {})
            report.append(f"- **الحالة:** ✅ متصل")
            report.append(f"- **اسم المستخدم:** @{bot_info.get('username', 'N/A')}")
            report.append(f"- **الاسم:** {bot_info.get('first_name', 'N/A')}")
            
            if "commands" in bot_tests:
                report.append(f"- **الأوامر المسجلة:** {bot_tests.get('commands', {}).get('count', 0)}")
        else:
            report.append(f"- **الحالة:** ❌ غير متصل")
            if "error" in bot_tests:
                report.append(f"- **الخطأ:** {bot_tests['error']}")
        
        # Sync Status Section
        report.append("\n## 🔄 حالة المزامنة")
        sync_status = self.results["sync_status"]
        if sync_status.get("enabled"):
            report.append("- **المزامنة متعددة المساحات:** ✅ مفعلة")
            if "status" in sync_status:
                report.append(f"- **الحالة:** {sync_status['status']}")
        else:
            report.append("- **المزامنة متعددة المساحات:** ℹ️ غير مفعلة")
        
        # Errors Section
        if self.results["errors"]:
            report.append("\n## ❌ الأخطاء")
            for error in self.results["errors"]:
                report.append(f"- {error}")
        
        # Warnings Section
        if self.results["warnings"]:
            report.append("\n## ⚠️ التحذيرات")
            for warning in self.results["warnings"]:
                report.append(f"- {warning}")
        
        # Recommendations Section
        if self.results["recommendations"]:
            report.append("\n## 💡 التوصيات")
            for i, rec in enumerate(self.results["recommendations"], 1):
                report.append(f"{i}. {rec}")
        
        # Testing Guide
        report.append("\n## 🧪 دليل الاختبار")
        report.append("\n### اختبار الواجهة:")
        report.append(f"1. زيارة: {self.api_base}")
        report.append("2. تصفح الأفلام والمسلسلات")
        report.append("3. اختبار البحث")
        report.append("4. تجربة تشغيل الفيديو")
        
        report.append("\n### اختبار البوت:")
        if bot_tests.get("bot_info"):
            report.append(f"1. ابدأ محادثة مع: @{bot_tests['bot_info'].get('username')}")
        report.append("2. أرسل `/start`")
        report.append("3. جرب البحث عن محتوى")
        report.append("4. اختبر الأزرار التفاعلية")
        
        # Next Steps
        report.append("\n## 📋 الخطوات التالية")
        if self.results["overall_status"] == "HEALTHY":
            report.append("✅ النظام يعمل بشكل صحيح")
            report.append("1. مراقبة الأداء")
            report.append("2. جمع ملاحظات المستخدمين")
            report.append("3. التخطيط للتحسينات")
        else:
            report.append("⚠️ يحتاج النظام إلى اهتمام")
            report.append("1. معالجة الأخطاء المذكورة")
            report.append("2. تطبيق التوصيات")
            report.append("3. إعادة تشغيل التحقق")
        
        return "\n".join(report)
    
    def run_verification(self):
        """Run complete verification process"""
        self.print_section("🎬 PopCorn - التحقق الشامل")
        
        print("\nسيتم التحقق من:")
        print("1. ملفات HuggingFace")
        print("2. حالة Space")
        print("3. وظائف البوت")
        print("4. حالة المزامنة")
        print("5. توليد التقرير الشامل")
        
        print("\nبدء التحقق...")
        
        # Step 1: Check HuggingFace files
        self.check_all_hf_files()
        
        # Step 2: Check Space status
        self.results["space_status"] = self.check_space_status()
        self.check_space_logs()
        
        # Step 3: Test Telegram bot
        self.results["bot_tests"] = self.test_telegram_bot()
        bot_commands = self.test_bot_commands()
        self.results["bot_tests"].update(bot_commands)
        
        # Step 4: Check synchronization
        self.results["sync_status"] = self.check_space_sync()
        
        # Step 5: Generate recommendations
        self.generate_recommendations()
        
        # Determine overall status
        self.determine_overall_status()
        
        # Generate report
        report = self.generate_report()
        
        # Save report
        report_file = "COMPREHENSIVE_VERIFICATION_REPORT.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
        
        self.print_status("success", f"التقرير محفوظ في: {report_file}")
        
        # Save JSON results
        json_file = "verification_results_comprehensive.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        self.print_status("success", f"النتائج محفوظة في: {json_file}")
        
        # Print report
        print("\n" + report)
        
        return self.results

def main():
    """Main execution"""
    verifier = ComprehensiveVerification()
    results = verifier.run_verification()
    
    # Exit with appropriate code
    if results["overall_status"] in ["CRITICAL", "NEEDS_ATTENTION"]:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()

# Made with Bob
