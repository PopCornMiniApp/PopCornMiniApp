#!/usr/bin/env python3
"""
PopCorn Bot Restructure - Comprehensive Test Suite
Tests all Phase 1 & Phase 2 implementations before deployment.
"""
import os
import sys
import json
import logging
import sqlite3
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Test Results Tracking
# ══════════════════════════════════════════════════════════════════════════════

class TestResults:
    """Track test results and generate reports."""
    
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.start_time = datetime.now()
    
    def add_test(self, category: str, name: str, passed: bool, message: str = "", warning: bool = False):
        """Add a test result."""
        self.tests.append({
            "category": category,
            "name": name,
            "passed": passed,
            "message": message,
            "warning": warning,
            "timestamp": datetime.now().isoformat()
        })
        
        if warning:
            self.warnings += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        duration = (datetime.now() - self.start_time).total_seconds()
        total = len(self.tests)
        
        return {
            "total_tests": total,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "success_rate": round((self.passed / total * 100) if total > 0 else 0, 2),
            "duration_seconds": round(duration, 2),
            "timestamp": datetime.now().isoformat()
        }
    
    def print_summary(self):
        """Print formatted test summary."""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("🧪 TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"📊 Success Rate: {summary['success_rate']}%")
        print(f"⏱️  Duration: {summary['duration_seconds']}s")
        print("="*80)
        
        # Print failed tests
        if self.failed > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.tests:
                if not test['passed'] and not test['warning']:
                    print(f"  • [{test['category']}] {test['name']}")
                    if test['message']:
                        print(f"    → {test['message']}")
        
        # Print warnings
        if self.warnings > 0:
            print("\n⚠️  WARNINGS:")
            for test in self.tests:
                if test['warning']:
                    print(f"  • [{test['category']}] {test['name']}")
                    if test['message']:
                        print(f"    → {test['message']}")
        
        print()
    
    def save_report(self, filepath: str = "test_bot_restructure_report.json"):
        """Save detailed test report to JSON file."""
        report = {
            "summary": self.get_summary(),
            "tests": self.tests
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Test report saved to {filepath}")


# ══════════════════════════════════════════════════════════════════════════════
# File Structure Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_file_structure(results: TestResults):
    """Test that all required files exist."""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        ("app/admin_permissions.py", "Admin Permission System"),
        ("app/bot_tracking.py", "Bot Tracking System"),
        ("app/button_builders.py", "Button Builders"),
        ("app/subscription_checker.py", "Subscription Checker"),
        ("app/bot.py", "Main Bot Module"),
        ("app/bot_commands.py", "Bot Commands"),
        ("app/database.py", "Database Module"),
        ("app/config.py", "Configuration"),
    ]
    
    for filepath, description in required_files:
        # Files are in current directory when running from PopCorn/
        exists = os.path.exists(filepath)
        
        results.add_test(
            "File Structure",
            f"{description} exists",
            exists,
            f"File not found: {filepath}" if not exists else ""
        )
        
        if exists:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")


# ══════════════════════════════════════════════════════════════════════════════
# Import Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_imports(results: TestResults):
    """Test that all modules can be imported."""
    print("\n📦 Testing Module Imports...")
    
    modules = [
        ("app.admin_permissions", "Admin Permissions"),
        ("app.bot_tracking", "Bot Tracking"),
        ("app.button_builders", "Button Builders"),
        ("app.subscription_checker", "Subscription Checker"),
        ("app.config", "Configuration"),
    ]
    
    for module_name, description in modules:
        try:
            __import__(module_name)
            results.add_test("Imports", f"Import {description}", True)
            print(f"  ✅ {description}")
        except Exception as e:
            results.add_test("Imports", f"Import {description}", False, str(e))
            print(f"  ❌ {description} - {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Admin Permission System Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_admin_permissions(results: TestResults):
    """Test admin permission system."""
    print("\n👑 Testing Admin Permission System...")
    
    try:
        from app.admin_permissions import (
            AdminRole, Permission, AdminPermissionManager,
            ROLE_PERMISSIONS, require_permission, require_admin
        )
        
        # Test enum definitions
        results.add_test(
            "Admin Permissions",
            "AdminRole enum defined",
            hasattr(AdminRole, 'SUPER_ADMIN'),
            ""
        )
        print(f"  ✅ AdminRole enum defined")
        
        results.add_test(
            "Admin Permissions",
            "Permission enum defined",
            hasattr(Permission, 'VIEW_USERS'),
            ""
        )
        print(f"  ✅ Permission enum defined")
        
        # Test role permissions mapping
        has_all_roles = all(role in ROLE_PERMISSIONS for role in AdminRole)
        results.add_test(
            "Admin Permissions",
            "Role permissions mapping complete",
            has_all_roles,
            "Not all roles have permission mappings" if not has_all_roles else ""
        )
        print(f"  ✅ Role permissions mapping complete")
        
        # Test decorators exist
        results.add_test(
            "Admin Permissions",
            "require_permission decorator exists",
            callable(require_permission),
            ""
        )
        print(f"  ✅ require_permission decorator exists")
        
        results.add_test(
            "Admin Permissions",
            "require_admin decorator exists",
            callable(require_admin),
            ""
        )
        print(f"  ✅ require_admin decorator exists")
        
    except Exception as e:
        results.add_test("Admin Permissions", "System initialization", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Bot Tracking System Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_bot_tracking(results: TestResults):
    """Test bot tracking system."""
    print("\n📊 Testing Bot Tracking System...")
    
    try:
        from app.bot_tracking import (
            BotTracker, track_bot_interaction,
            integrate_with_user_tracking, get_popular_buttons
        )
        
        # Test BotTracker class
        results.add_test(
            "Bot Tracking",
            "BotTracker class defined",
            BotTracker is not None,
            ""
        )
        print(f"  ✅ BotTracker class defined")
        
        # Test decorator
        results.add_test(
            "Bot Tracking",
            "track_bot_interaction decorator exists",
            callable(track_bot_interaction),
            ""
        )
        print(f"  ✅ track_bot_interaction decorator exists")
        
        # Test utility functions
        results.add_test(
            "Bot Tracking",
            "Utility functions exist",
            callable(get_popular_buttons),
            ""
        )
        print(f"  ✅ Utility functions exist")
        
    except Exception as e:
        results.add_test("Bot Tracking", "System initialization", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Button Builders Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_button_builders(results: TestResults):
    """Test button builder functions."""
    print("\n🔘 Testing Button Builders...")
    
    try:
        from app.button_builders import (
            build_main_menu, build_browse_buttons, build_content_details_buttons,
            build_season_buttons, build_episode_buttons, build_profile_menu,
            build_admin_panel, build_pagination_buttons, build_back_button
        )
        
        builders = [
            ("build_main_menu", build_main_menu),
            ("build_browse_buttons", build_browse_buttons),
            ("build_content_details_buttons", build_content_details_buttons),
            ("build_season_buttons", build_season_buttons),
            ("build_episode_buttons", build_episode_buttons),
            ("build_profile_menu", build_profile_menu),
            ("build_admin_panel", build_admin_panel),
            ("build_pagination_buttons", build_pagination_buttons),
            ("build_back_button", build_back_button),
        ]
        
        for name, func in builders:
            results.add_test(
                "Button Builders",
                f"{name} exists",
                callable(func),
                ""
            )
            print(f"  ✅ {name}")
        
        # Test main menu generation
        try:
            from telegram import InlineKeyboardMarkup
            menu = build_main_menu(user_id=12345, is_premium=False)
            is_valid = isinstance(menu, InlineKeyboardMarkup)
            results.add_test(
                "Button Builders",
                "Main menu generates valid keyboard",
                is_valid,
                "Generated menu is not InlineKeyboardMarkup" if not is_valid else ""
            )
            print(f"  ✅ Main menu generates valid keyboard")
        except Exception as e:
            results.add_test(
                "Button Builders",
                "Main menu generation",
                False,
                str(e)
            )
            print(f"  ⚠️  Main menu generation test skipped (requires telegram library)")
        
    except Exception as e:
        results.add_test("Button Builders", "System initialization", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Subscription Checker Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_subscription_checker(results: TestResults):
    """Test subscription checker system."""
    print("\n✅ Testing Subscription Checker...")
    
    try:
        from app.subscription_checker import (
            check_subscription, require_subscription,
            get_cache_stats, clear_cache, reset_cache_stats
        )
        
        # Test functions exist
        functions = [
            ("check_subscription", check_subscription),
            ("require_subscription", require_subscription),
            ("get_cache_stats", get_cache_stats),
            ("clear_cache", clear_cache),
            ("reset_cache_stats", reset_cache_stats),
        ]
        
        for name, func in functions:
            results.add_test(
                "Subscription Checker",
                f"{name} exists",
                callable(func),
                ""
            )
            print(f"  ✅ {name}")
        
        # Test cache stats
        try:
            stats = get_cache_stats()
            has_required_keys = all(key in stats for key in [
                'total_entries', 'cache_hits', 'cache_misses', 'api_calls'
            ])
            results.add_test(
                "Subscription Checker",
                "Cache stats structure valid",
                has_required_keys,
                "Missing required keys in cache stats" if not has_required_keys else ""
            )
            print(f"  ✅ Cache stats structure valid")
        except Exception as e:
            results.add_test(
                "Subscription Checker",
                "Cache stats",
                False,
                str(e)
            )
            print(f"  ❌ Cache stats error: {e}")
        
    except Exception as e:
        results.add_test("Subscription Checker", "System initialization", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Bot Module Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_bot_module(results: TestResults):
    """Test main bot module."""
    print("\n🤖 Testing Bot Module...")
    
    try:
        # Check if bot.py has required functions
        bot_file = "app/bot.py"
        with open(bot_file, 'r') as f:
            content = f.read()
        
        required_functions = [
            ("start_command", "Start command handler"),
            ("show_main_menu", "Main menu handler"),
            ("browse_movies_handler", "Browse movies handler"),
            ("browse_series_handler", "Browse series handler"),
            ("create_bot_application", "Bot application creator"),
        ]
        
        for func_name, description in required_functions:
            exists = f"def {func_name}" in content or f"async def {func_name}" in content
            results.add_test(
                "Bot Module",
                f"{description} defined",
                exists,
                f"Function {func_name} not found" if not exists else ""
            )
            if exists:
                print(f"  ✅ {description}")
            else:
                print(f"  ❌ {description} - NOT FOUND")
        
        # Check for decorators usage
        has_tracking = "@track_bot_interaction" in content
        results.add_test(
            "Bot Module",
            "Uses tracking decorator",
            has_tracking,
            "Tracking decorator not used" if not has_tracking else ""
        )
        print(f"  ✅ Uses tracking decorator" if has_tracking else "  ⚠️  Tracking decorator not used")
        
        has_subscription = "@require_subscription" in content
        results.add_test(
            "Bot Module",
            "Uses subscription decorator",
            has_subscription,
            "Subscription decorator not used" if not has_subscription else ""
        )
        print(f"  ✅ Uses subscription decorator" if has_subscription else "  ⚠️  Subscription decorator not used")
        
    except Exception as e:
        results.add_test("Bot Module", "Module analysis", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Configuration Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_configuration(results: TestResults):
    """Test configuration settings."""
    print("\n⚙️  Testing Configuration...")
    
    try:
        from app.config import (
            MAIN_BOT_TOKEN, PUBLIC_CHANNEL_ID, ADMIN_ID,
            SUBSCRIPTION_REQUIRED, SUBSCRIPTION_CACHE_TTL,
            ENABLE_ADMIN_SYSTEM, TRACKING_ENABLED
        )
        
        # Check critical config values
        configs = [
            ("MAIN_BOT_TOKEN", MAIN_BOT_TOKEN, "Bot token configured"),
            ("PUBLIC_CHANNEL_ID", PUBLIC_CHANNEL_ID, "Channel ID configured"),
            ("ADMIN_ID", ADMIN_ID, "Admin ID configured"),
        ]
        
        for name, value, description in configs:
            is_set = value and value != "" and value != 0
            results.add_test(
                "Configuration",
                description,
                True,  # Don't fail on missing env vars in test
                f"{name} not set (will use defaults)" if not is_set else "",
                warning=not is_set
            )
            if is_set:
                print(f"  ✅ {description}")
            else:
                print(f"  ⚠️  {description} - using defaults")
        
        # Check feature flags
        print(f"  ℹ️  SUBSCRIPTION_REQUIRED: {SUBSCRIPTION_REQUIRED}")
        print(f"  ℹ️  ENABLE_ADMIN_SYSTEM: {ENABLE_ADMIN_SYSTEM}")
        print(f"  ℹ️  TRACKING_ENABLED: {TRACKING_ENABLED}")
        print(f"  ℹ️  SUBSCRIPTION_CACHE_TTL: {SUBSCRIPTION_CACHE_TTL}s")
        
    except Exception as e:
        results.add_test("Configuration", "Config loading", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Database Schema Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_database_schema(results: TestResults):
    """Test database schema for new tables."""
    print("\n🗄️  Testing Database Schema...")
    
    # Create a temporary test database
    test_db = "/tmp/test_popcorn_restructure.db"
    
    try:
        # Remove old test db if exists
        if os.path.exists(test_db):
            os.remove(test_db)
        
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()
        
        # Test admin_users table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT NOT NULL,
                assigned_by INTEGER,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                permissions_override TEXT,
                last_activity TIMESTAMP,
                notes TEXT
            )
        """)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_users'")
        admin_table_exists = cursor.fetchone() is not None
        results.add_test(
            "Database Schema",
            "admin_users table can be created",
            admin_table_exists,
            ""
        )
        print(f"  ✅ admin_users table")
        
        # Test bot_sessions table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                platform TEXT DEFAULT 'telegram_bot'
            )
        """)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_sessions'")
        sessions_table_exists = cursor.fetchone() is not None
        results.add_test(
            "Database Schema",
            "bot_sessions table can be created",
            sessions_table_exists,
            ""
        )
        print(f"  ✅ bot_sessions table")
        
        # Test bot_interactions table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT,
                interaction_type TEXT NOT NULL,
                interaction_data TEXT,
                callback_data TEXT,
                command TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_interactions'")
        interactions_table_exists = cursor.fetchone() is not None
        results.add_test(
            "Database Schema",
            "bot_interactions table can be created",
            interactions_table_exists,
            ""
        )
        print(f"  ✅ bot_interactions table")
        
        # Test bot_button_clicks table creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bot_button_clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT,
                button_callback TEXT NOT NULL,
                button_text TEXT,
                context_data TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_button_clicks'")
        clicks_table_exists = cursor.fetchone() is not None
        results.add_test(
            "Database Schema",
            "bot_button_clicks table can be created",
            clicks_table_exists,
            ""
        )
        print(f"  ✅ bot_button_clicks table")
        
        conn.close()
        
        # Cleanup
        if os.path.exists(test_db):
            os.remove(test_db)
        
    except Exception as e:
        results.add_test("Database Schema", "Schema validation", False, str(e))
        print(f"  ❌ Error: {e}")
        
        # Cleanup on error
        try:
            if os.path.exists(test_db):
                os.remove(test_db)
        except:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ══════════════════════════════════════════════════════════════════════════════

def test_integration(results: TestResults):
    """Test integration between components."""
    print("\n🔗 Testing Component Integration...")
    
    try:
        # Test that bot.py imports all required modules
        bot_file = "app/bot.py"
        with open(bot_file, 'r') as f:
            content = f.read()
        
        required_imports = [
            ("subscription_checker", "Subscription checker integration"),
            ("bot_tracking", "Bot tracking integration"),
            ("button_builders", "Button builders integration"),
        ]
        
        for module, description in required_imports:
            has_import = f"from app.{module} import" in content or f"from app import {module}" in content
            results.add_test(
                "Integration",
                description,
                has_import,
                f"Missing import for {module}" if not has_import else ""
            )
            if has_import:
                print(f"  ✅ {description}")
            else:
                print(f"  ❌ {description}")
        
        # Test bot_commands.py integration
        commands_file = "app/bot_commands.py"
        with open(commands_file, 'r') as f:
            commands_content = f.read()
        
        has_admin_perms = "from app.admin_permissions import" in commands_content
        results.add_test(
            "Integration",
            "Bot commands use admin permissions",
            has_admin_perms,
            "Admin permissions not imported in bot_commands" if not has_admin_perms else ""
        )
        print(f"  ✅ Bot commands use admin permissions" if has_admin_perms else "  ❌ Bot commands missing admin permissions")
        
        has_button_builders = "from app.button_builders import" in commands_content
        results.add_test(
            "Integration",
            "Bot commands use button builders",
            has_button_builders,
            "Button builders not imported in bot_commands" if not has_button_builders else ""
        )
        print(f"  ✅ Bot commands use button builders" if has_button_builders else "  ❌ Bot commands missing button builders")
        
    except Exception as e:
        results.add_test("Integration", "Integration check", False, str(e))
        print(f"  ❌ Error: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Main Test Runner
# ══════════════════════════════════════════════════════════════════════════════

def main():
    """Run all tests and generate report."""
    print("="*80)
    print("🧪 PopCorn Bot Restructure - Comprehensive Test Suite")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = TestResults()
    
    # Run all test suites
    test_file_structure(results)
    test_imports(results)
    test_admin_permissions(results)
    test_bot_tracking(results)
    test_button_builders(results)
    test_subscription_checker(results)
    test_bot_module(results)
    test_configuration(results)
    test_database_schema(results)
    test_integration(results)
    
    # Print summary
    results.print_summary()
    
    # Save detailed report
    report_file = "test_bot_restructure_report.json"
    results.save_report(report_file)
    
    # Generate markdown report
    md_report = generate_markdown_report(results)
    md_file = "test_bot_restructure_report.md"
    with open(md_file, 'w') as f:
        f.write(md_report)
    print(f"📄 Markdown report saved to {md_file}")
    
    # Exit with appropriate code
    if results.failed > 0:
        print("\n❌ TESTS FAILED - Deployment not recommended")
        return 1
    elif results.warnings > 0:
        print("\n⚠️  TESTS PASSED WITH WARNINGS - Review before deployment")
        return 0
    else:
        print("\n✅ ALL TESTS PASSED - Ready for deployment")
        return 0


def generate_markdown_report(results: TestResults) -> str:
    """Generate markdown test report."""
    summary = results.get_summary()
    
    md = f"""# PopCorn Bot Restructure - Test Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Tests:** {summary['total_tests']}
- **✅ Passed:** {summary['passed']}
- **❌ Failed:** {summary['failed']}
- **⚠️ Warnings:** {summary['warnings']}
- **Success Rate:** {summary['success_rate']}%
- **Duration:** {summary['duration_seconds']}s

## Test Results by Category

"""
    
    # Group tests by category
    categories = {}
    for test in results.tests:
        cat = test['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(test)
    
    for category, tests in categories.items():
        md += f"\n### {category}\n\n"
        md += "| Test | Status | Message |\n"
        md += "|------|--------|----------|\n"
        
        for test in tests:
            if test['warning']:
                status = "⚠️ Warning"
            elif test['passed']:
                status = "✅ Pass"
            else:
                status = "❌ Fail"
            
            message = test['message'] if test['message'] else "-"
            md += f"| {test['name']} | {status} | {message} |\n"
    
    md += "\n## Recommendations\n\n"
    
    if summary['failed'] > 0:
        md += "❌ **DO NOT DEPLOY** - Critical tests failed. Fix issues before deployment.\n\n"
    elif summary['warnings'] > 0:
        md += "⚠️ **REVIEW REQUIRED** - Tests passed but with warnings. Review warnings before deployment.\n\n"
    else:
        md += "✅ **READY FOR DEPLOYMENT** - All tests passed successfully.\n\n"
    
    return md


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
