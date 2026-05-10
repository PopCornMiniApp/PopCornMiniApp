#!/usr/bin/env python3
"""
Emergency Bot Diagnostic Script
Diagnoses why the bot is not responding to /start commands.
"""
import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_imports():
    """Check if all required modules can be imported."""
    print("\n🔍 Checking Module Imports...")
    
    modules_to_check = [
        ("telegram", "python-telegram-bot"),
        ("app.config", "Config module"),
        ("app.database", "Database module"),
        ("app.bot", "Bot module"),
        ("app.bot_commands", "Bot commands module"),
    ]
    
    issues = []
    for module_name, description in modules_to_check:
        try:
            __import__(module_name)
            print(f"  ✅ {description}: OK")
        except Exception as e:
            print(f"  ❌ {description}: FAILED - {e}")
            issues.append(f"{description}: {e}")
    
    return len(issues) == 0, issues

def check_config():
    """Check configuration."""
    print("\n⚙️  Checking Configuration...")
    
    try:
        from app.config import Config
        config = Config()
        
        checks = {
            "BOT_TOKEN": config.BOT_TOKEN,
            "DATABASE_URL": config.DATABASE_URL,
            "CHANNEL_ID": config.CHANNEL_ID,
        }
        
        issues = []
        for key, value in checks.items():
            if value:
                print(f"  ✅ {key}: Configured")
            else:
                print(f"  ❌ {key}: NOT SET")
                issues.append(f"{key} not configured")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        print(f"  ❌ Config Error: {e}")
        return False, [str(e)]

def check_database():
    """Check database connection."""
    print("\n🗄️  Checking Database...")
    
    try:
        from app.database import Database
        db = Database()
        
        # Try a simple query
        result = db.execute_query("SELECT 1")
        if result:
            print("  ✅ Database connection: OK")
            return True, []
        else:
            print("  ❌ Database query failed")
            return False, ["Database query returned no results"]
            
    except Exception as e:
        print(f"  ❌ Database Error: {e}")
        return False, [str(e)]

def check_bot_files():
    """Check if bot files exist and are valid."""
    print("\n📁 Checking Bot Files...")
    
    required_files = [
        "app/bot.py",
        "app/bot_commands.py",
        "app/config.py",
        "app/database.py",
    ]
    
    issues = []
    for filepath in required_files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            if size > 0:
                print(f"  ✅ {filepath}: {size} bytes")
            else:
                print(f"  ❌ {filepath}: Empty file")
                issues.append(f"{filepath} is empty")
        else:
            print(f"  ❌ {filepath}: NOT FOUND")
            issues.append(f"{filepath} not found")
    
    return len(issues) == 0, issues

def check_bot_syntax():
    """Check for syntax errors in bot files."""
    print("\n🔧 Checking Bot Syntax...")
    
    try:
        import py_compile
        
        files_to_check = [
            "app/bot.py",
            "app/bot_commands.py",
        ]
        
        issues = []
        for filepath in files_to_check:
            try:
                py_compile.compile(filepath, doraise=True)
                print(f"  ✅ {filepath}: No syntax errors")
            except py_compile.PyCompileError as e:
                print(f"  ❌ {filepath}: Syntax error - {e}")
                issues.append(f"{filepath}: {e}")
        
        return len(issues) == 0, issues
        
    except Exception as e:
        print(f"  ⚠️  Could not check syntax: {e}")
        return True, []  # Don't fail on this

def check_space_status():
    """Check Hugging Face Space status."""
    print("\n🌐 Checking Space Status...")
    
    try:
        from huggingface_hub import HfApi
        from dotenv import load_dotenv
        load_dotenv()
        
        space_name = os.getenv("HF_SPACE_NAME")
        if not space_name:
            print("  ⚠️  HF_SPACE_NAME not set")
            return True, []
        
        api = HfApi()
        space_info = api.space_info(repo_id=space_name)
        runtime = space_info.runtime
        
        if runtime:
            stage = runtime.stage
            print(f"  📊 Space Status: {stage}")
            
            if stage == "RUNNING":
                print("  ✅ Space is running")
                return True, []
            elif stage == "BUILDING":
                print("  ⏳ Space is building")
                return False, ["Space is still building"]
            else:
                print(f"  ❌ Space status: {stage}")
                return False, [f"Space in {stage} state"]
        else:
            print("  ⚠️  No runtime information")
            return True, []
            
    except Exception as e:
        print(f"  ⚠️  Could not check space: {e}")
        return True, []  # Don't fail on this

def main():
    """Main diagnostic function."""
    print("="*80)
    print("🚨 EMERGENCY BOT DIAGNOSTIC")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_checks = []
    
    # Run all checks
    checks = [
        ("Module Imports", check_imports),
        ("Configuration", check_config),
        ("Database", check_database),
        ("Bot Files", check_bot_files),
        ("Bot Syntax", check_bot_syntax),
        ("Space Status", check_space_status),
    ]
    
    for check_name, check_func in checks:
        passed, issues = check_func()
        all_checks.append({
            "name": check_name,
            "passed": passed,
            "issues": issues
        })
    
    # Print summary
    print("\n" + "="*80)
    print("📊 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    failed_checks = [c for c in all_checks if not c["passed"]]
    
    if not failed_checks:
        print("✅ All checks passed!")
        print("\nThe bot should be working. If it's not responding:")
        print("  1. Check Hugging Face Space logs")
        print("  2. Verify the bot is actually running")
        print("  3. Check if there are any runtime errors")
        return 0
    else:
        print(f"❌ {len(failed_checks)} check(s) failed:\n")
        
        for check in failed_checks:
            print(f"  ❌ {check['name']}:")
            for issue in check['issues']:
                print(f"     • {issue}")
        
        print("\n🔧 RECOMMENDED ACTIONS:")
        print("  1. Fix the issues listed above")
        print("  2. Check Hugging Face Space logs for errors")
        print("  3. Verify environment variables are set correctly")
        print("  4. Consider rolling back the deployment if issues persist")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob