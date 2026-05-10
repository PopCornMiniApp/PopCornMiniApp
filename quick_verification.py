#!/usr/bin/env python3
"""
Quick Verification Script - Checks bot and space status without HF API
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def print_section(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_status(status, message):
    symbols = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️"
    }
    print(f"{symbols.get(status, '•')} {message}")


def check_space_status():
    """Check HuggingFace Space status"""
    print_section("1. Checking Space Status")
    
    space_name = os.getenv("HF_SPACE_NAME", "jamalmohamad1/PopCorn")
    parts = space_name.split("/")
    username = parts[0] if len(parts) > 0 else ""
    space_slug = parts[1] if len(parts) > 1 else ""
    api_base = f"https://{username}-{space_slug.lower()}.hf.space"
    
    print_status("info", f"Space URL: {api_base}")
    
    results = {"url": api_base}
    
    # Check health endpoint
    try:
        response = requests.get(f"{api_base}/health", timeout=10)
        if response.status_code == 200:
            print_status("success", "Health endpoint responding")
            results["health"] = "OK"
        else:
            print_status("warning", f"Health endpoint returned {response.status_code}")
            results["health"] = f"Status {response.status_code}"
    except Exception as e:
        print_status("error", f"Cannot access health endpoint: {str(e)}")
        results["health"] = "ERROR"
    
    # Check API endpoints
    endpoints = {
        "stats": "/api/stats",
        "movies": "/api/movies",
        "series": "/api/series"
    }
    
    results["endpoints"] = {}
    for name, endpoint in endpoints.items():
        try:
            response = requests.get(f"{api_base}{endpoint}", timeout=10)
            if response.status_code == 200:
                print_status("success", f"{name} API: OK")
                results["endpoints"][name] = "OK"
            else:
                print_status("warning", f"{name} API: Status {response.status_code}")
                results["endpoints"][name] = f"Status {response.status_code}"
        except Exception as e:
            print_status("error", f"{name} API: {str(e)}")
            results["endpoints"][name] = "ERROR"
    
    return results


def check_telegram_bot():
    """Check Telegram bot status"""
    print_section("2. Checking Telegram Bot")
    
    bot_token = os.getenv("MAIN_BOT_TOKEN", "")
    if not bot_token:
        print_status("error", "MAIN_BOT_TOKEN not configured")
        return {"status": "ERROR", "error": "No token"}
    
    telegram_api = f"https://api.telegram.org/bot{bot_token}"
    results = {}
    
    # Get bot info
    try:
        response = requests.get(f"{telegram_api}/getMe", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                bot_info = data.get("result", {})
                print_status("success", f"Bot connected: @{bot_info.get('username')}")
                print_status("info", f"Bot name: {bot_info.get('first_name')}")
                results["connected"] = True
                results["username"] = bot_info.get("username")
                results["name"] = bot_info.get("first_name")
            else:
                print_status("error", "Bot API returned error")
                results["connected"] = False
        else:
            print_status("error", f"Bot API returned {response.status_code}")
            results["connected"] = False
    except Exception as e:
        print_status("error", f"Cannot connect to bot: {str(e)}")
        results["connected"] = False
        results["error"] = str(e)
    
    # Check webhook
    try:
        response = requests.get(f"{telegram_api}/getWebhookInfo", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                webhook_info = data.get("result", {})
                webhook_url = webhook_info.get("url", "")
                if webhook_url:
                    print_status("info", f"Webhook: {webhook_url}")
                    results["webhook"] = webhook_url
                else:
                    print_status("info", "No webhook (polling mode)")
                    results["webhook"] = None
    except Exception as e:
        print_status("warning", f"Could not check webhook: {str(e)}")
    
    # Check commands
    try:
        response = requests.get(f"{telegram_api}/getMyCommands", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                commands = data.get("result", [])
                print_status("success", f"Bot has {len(commands)} commands")
                results["commands_count"] = len(commands)
    except Exception as e:
        print_status("warning", f"Could not check commands: {str(e)}")
    
    return results


def check_local_files():
    """Check local bot files"""
    print_section("3. Checking Local Files")
    
    required_files = [
        "app/bot_commands.py",
        "app/config.py",
        "app/bot_tracking.py",
        "app/button_builders.py",
        "app/bot.py",
        "app/database.py",
        "app/main.py"
    ]
    
    results = {}
    for filepath in required_files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print_status("success", f"{filepath} ({size} bytes)")
            results[filepath] = {"exists": True, "size": size}
        else:
            print_status("error", f"{filepath} NOT FOUND")
            results[filepath] = {"exists": False}
    
    return results


def generate_report(space_results, bot_results, files_results):
    """Generate verification report"""
    print_section("Generating Report")
    
    report = []
    report.append("# 🎬 PopCorn - تقرير التحقق السريع")
    report.append(f"\n**التاريخ:** {datetime.now().isoformat()}")
    
    # Space Status
    report.append("\n## 🚀 حالة Space")
    report.append(f"- **الرابط:** {space_results.get('url')}")
    report.append(f"- **الصحة:** {space_results.get('health')}")
    
    if "endpoints" in space_results:
        report.append("\n### نقاط النهاية API:")
        for name, status in space_results["endpoints"].items():
            icon = "✅" if status == "OK" else "❌"
            report.append(f"- {icon} **{name}:** {status}")
    
    # Bot Status
    report.append("\n## 🤖 حالة البوت")
    if bot_results.get("connected"):
        report.append(f"- **الحالة:** ✅ متصل")
        report.append(f"- **اسم المستخدم:** @{bot_results.get('username')}")
        report.append(f"- **الاسم:** {bot_results.get('name')}")
        if "commands_count" in bot_results:
            report.append(f"- **الأوامر:** {bot_results['commands_count']}")
        if bot_results.get("webhook"):
            report.append(f"- **Webhook:** {bot_results['webhook']}")
    else:
        report.append(f"- **الحالة:** ❌ غير متصل")
        if "error" in bot_results:
            report.append(f"- **الخطأ:** {bot_results['error']}")
    
    # Files Status
    report.append("\n## 📁 الملفات المحلية")
    missing_files = [f for f, info in files_results.items() if not info.get("exists")]
    if missing_files:
        report.append(f"\n**ملفات مفقودة:** {len(missing_files)}")
        for f in missing_files:
            report.append(f"- ❌ {f}")
    else:
        report.append("- ✅ جميع الملفات موجودة")
    
    # Overall Status
    report.append("\n## 📊 الحالة العامة")
    
    space_ok = space_results.get("health") == "OK"
    bot_ok = bot_results.get("connected", False)
    files_ok = len(missing_files) == 0
    
    if space_ok and bot_ok and files_ok:
        report.append("### ✅ النظام يعمل بشكل صحيح")
    else:
        report.append("### ⚠️ يحتاج النظام إلى اهتمام")
        if not space_ok:
            report.append("- Space غير متاح")
        if not bot_ok:
            report.append("- البوت غير متصل")
        if not files_ok:
            report.append(f"- {len(missing_files)} ملفات مفقودة")
    
    # Testing Guide
    report.append("\n## 🧪 دليل الاختبار")
    report.append(f"\n1. **اختبار الواجهة:** {space_results.get('url')}")
    if bot_results.get("username"):
        report.append(f"2. **اختبار البوت:** @{bot_results.get('username')}")
    report.append("3. أرسل `/start` للبوت")
    report.append("4. جرب البحث والتصفح")
    
    return "\n".join(report)


def main():
    print_section("🎬 PopCorn - التحقق السريع")
    
    # Run checks
    space_results = check_space_status()
    bot_results = check_telegram_bot()
    files_results = check_local_files()
    
    # Generate report
    report = generate_report(space_results, bot_results, files_results)
    
    # Save report
    report_file = "QUICK_VERIFICATION_REPORT.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print_status("success", f"التقرير محفوظ في: {report_file}")
    
    # Save JSON
    results = {
        "timestamp": datetime.now().isoformat(),
        "space": space_results,
        "bot": bot_results,
        "files": files_results
    }
    
    json_file = "quick_verification_results.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print_status("success", f"النتائج محفوظة في: {json_file}")
    
    # Print report
    print("\n" + report)

if __name__ == "__main__":
    main()

# Made with Bob
