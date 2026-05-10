#!/usr/bin/env python3
"""
Test script to verify bot initialization and button system
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from app.bot_commands import (
            cmd_start,
            cmd_app,
            cmd_help,
            cmd_admin,
            registration_name,
            registration_language,
            cancel_registration,
            get_callback_handlers,
            REGISTRATION_NAME,
            REGISTRATION_LANGUAGE,
        )
        logger.info("✅ Bot commands imported successfully")
        
        from app.button_builders import (
            build_main_menu,
            build_admin_panel,
            build_admin_content_menu,
            build_admin_user_menu,
        )
        logger.info("✅ Button builders imported successfully")
        
        from app.admin_permissions import (
            AdminPermissionManager,
            AdminRole,
            Permission,
        )
        logger.info("✅ Admin permissions imported successfully")
        
        return True
    except Exception as e:
        logger.error(f"❌ Import error: {e}", exc_info=True)
        return False

def test_button_builders():
    """Test button builder functions"""
    try:
        from app.button_builders import build_main_menu, build_admin_panel
        
        # Test main menu
        menu = build_main_menu(user_id=123456, is_premium=False)
        logger.info(f"✅ Main menu created with {len(menu.inline_keyboard)} rows")
        
        # Test admin panel
        admin_panel = build_admin_panel("super_admin")
        logger.info(f"✅ Admin panel created with {len(admin_panel.inline_keyboard)} rows")
        
        return True
    except Exception as e:
        logger.error(f"❌ Button builder error: {e}", exc_info=True)
        return False

def test_conversation_states():
    """Test conversation state constants"""
    try:
        from app.bot_commands import REGISTRATION_NAME, REGISTRATION_LANGUAGE
        logger.info(f"✅ Conversation states: NAME={REGISTRATION_NAME}, LANGUAGE={REGISTRATION_LANGUAGE}")
        return True
    except Exception as e:
        logger.error(f"❌ Conversation state error: {e}", exc_info=True)
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting bot initialization tests...\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("Button Builders", test_button_builders),
        ("Conversation States", test_conversation_states),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📋 Testing: {test_name}")
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info("="*60)
    logger.info(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("⚠️ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
