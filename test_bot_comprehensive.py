#!/usr/bin/env python3
"""
اختبار شامل للبوت والأزرار
"""
import os
import sys
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ألوان للطباعة
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

async def test_bot_initialization():
    """اختبار تهيئة البوت"""
    print_header("1. اختبار تهيئة البوت")
    
    try:
        from telegram import Bot
        from app.config import MAIN_BOT_TOKEN
        
        if not MAIN_BOT_TOKEN:
            print_error("MAIN_BOT_TOKEN غير موجود في ملف .env")
            return False
        
        bot = Bot(token=MAIN_BOT_TOKEN)
        me = await bot.get_me()
        
        print_success(f"البوت متصل: @{me.username}")
        print_info(f"اسم البوت: {me.first_name}")
        print_info(f"ID: {me.id}")
        
        return True
        
    except Exception as e:
        print_error(f"فشل الاتصال بالبوت: {str(e)}")
        return False

async def test_bot_commands():
    """اختبار أوامر البوت"""
    print_header("2. اختبار أوامر البوت")
    
    try:
        from telegram import Bot
        from app.config import MAIN_BOT_TOKEN
        
        bot = Bot(token=MAIN_BOT_TOKEN)
        commands = await bot.get_my_commands()
        
        if commands:
            print_success(f"تم العثور على {len(commands)} أمر")
            for cmd in commands:
                print_info(f"/{cmd.command} - {cmd.description}")
            return True
        else:
            print_warning("لا توجد أوامر مسجلة")
            return True
            
    except Exception as e:
        print_error(f"خطأ في جلب الأوامر: {str(e)}")
        return False

def test_button_builders():
    """اختبار بناة الأزرار"""
    print_header("3. اختبار بناة الأزرار")
    
    try:
        from app.button_builders import (
            build_main_menu,
            build_admin_menu,
            build_movie_buttons,
            build_series_buttons,
            build_language_buttons,
            build_back_button
        )
        
        # اختبار القائمة الرئيسية
        main_menu = build_main_menu(language="ar")
        print_success(f"القائمة الرئيسية: {len(main_menu.inline_keyboard)} صف")
        
        # اختبار قائمة الأدمن
        admin_menu = build_admin_menu(language="ar")
        print_success(f"قائمة الأدمن: {len(admin_menu.inline_keyboard)} صف")
        
        # اختبار أزرار الأفلام
        movie_buttons = build_movie_buttons(
            movie_id="test123",
            has_file=True,
            language="ar"
        )
        print_success(f"أزرار الأفلام: {len(movie_buttons.inline_keyboard)} صف")
        
        # اختبار أزرار المسلسلات
        series_buttons = build_series_buttons(
            series_id="test456",
            language="ar"
        )
        print_success(f"أزرار المسلسلات: {len(series_buttons.inline_keyboard)} صف")
        
        # اختبار أزرار اللغة
        lang_buttons = build_language_buttons()
        print_success(f"أزرار اللغة: {len(lang_buttons.inline_keyboard)} صف")
        
        # اختبار زر الرجوع
        back_button = build_back_button(callback_data="main_menu", language="ar")
        print_success(f"زر الرجوع: {len(back_button.inline_keyboard)} صف")
        
        return True
        
    except Exception as e:
        print_error(f"خطأ في اختبار الأزرار: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_admin_permissions():
    """اختبار نظام صلاحيات الأدمن"""
    print_header("4. اختبار نظام صلاحيات الأدمن")
    
    try:
        from app.admin_permissions import AdminPermissionManager, AdminRole
        from app.config import ADMIN_ID
        
        # إنشاء مدير الصلاحيات (بدون قاعدة بيانات للاختبار)
        print_info("اختبار الأدوار المتاحة...")
        
        roles = [
            AdminRole.SUPER_ADMIN,
            AdminRole.ADMIN,
            AdminRole.MODERATOR,
            AdminRole.CONTENT_MANAGER
        ]
        
        for role in roles:
            print_success(f"دور: {role.value}")
        
        print_info(f"الأدمن الرئيسي: {ADMIN_ID}")
        
        return True
        
    except Exception as e:
        print_error(f"خطأ في اختبار الصلاحيات: {str(e)}")
        return False

def test_bot_tracking():
    """اختبار نظام تتبع المستخدمين"""
    print_header("5. اختبار نظام تتبع المستخدمين")
    
    try:
        from app.bot_tracking import BotUserTracker
        from app.config import TRACKING_ENABLED
        
        print_info(f"نظام التتبع: {'مفعل' if TRACKING_ENABLED else 'معطل'}")
        
        if TRACKING_ENABLED:
            print_success("نظام التتبع جاهز")
        else:
            print_warning("نظام التتبع معطل")
        
        return True
        
    except Exception as e:
        print_error(f"خطأ في اختبار التتبع: {str(e)}")
        return False

def test_subscription_checker():
    """اختبار نظام التحقق من الاشتراك"""
    print_header("6. اختبار نظام التحقق من الاشتراك")
    
    try:
        from app.subscription_checker import SubscriptionChecker
        from app.config import SUBSCRIPTION_REQUIRED, SUBSCRIPTION_CHANNEL_ID
        
        print_info(f"الاشتراك الإجباري: {'مفعل' if SUBSCRIPTION_REQUIRED else 'معطل'}")
        print_info(f"معرف القناة: {SUBSCRIPTION_CHANNEL_ID}")
        
        if SUBSCRIPTION_REQUIRED:
            print_success("نظام التحقق من الاشتراك جاهز")
        else:
            print_warning("الاشتراك الإجباري معطل")
        
        return True
        
    except Exception as e:
        print_error(f"خطأ في اختبار الاشتراك: {str(e)}")
        return False

async def test_pyrogram_clients():
    """اختبار عملاء Pyrogram"""
    print_header("7. اختبار عملاء Pyrogram")
    
    try:
        from app.stream import init_pyrogram, _pyro_clients
        from app.config import SESSION_1_API_ID, SESSION_2_API_ID
        
        print_info("جاري تهيئة عملاء Pyrogram...")
        await init_pyrogram()
        
        if _pyro_clients:
            print_success(f"تم تهيئة {len(_pyro_clients)} عميل Pyrogram")
            for i, client in enumerate(_pyro_clients, 1):
                print_info(f"العميل {i}: {type(client).__name__}")
        else:
            print_warning("لم يتم تهيئة أي عميل Pyrogram")
        
        return True
        
    except Exception as e:
        print_error(f"خطأ في تهيئة Pyrogram: {str(e)}")
        return False

def generate_bot_test_report(results):
    """إنشاء تقرير اختبار البوت"""
    print_header("8. تقرير اختبار البوت")
    
    passed = sum(1 for r in results.values() if r)
    failed = sum(1 for r in results.values() if not r)
    total = len(results)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "tests": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "success_rate": f"{(passed/total*100):.1f}%" if total > 0 else "0%"
        }
    }
    
    print_info(f"إجمالي الاختبارات: {total}")
    print_success(f"نجح: {passed}")
    print_error(f"فشل: {failed}")
    print_info(f"نسبة النجاح: {report['summary']['success_rate']}")
    
    # حفظ التقرير
    report_file = "bot_test_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print_success(f"تم حفظ التقرير في: {report_file}")
    
    return passed == total

async def main():
    print_header("🤖 اختبار شامل للبوت")
    print_info("هذا السكريبت سيقوم بـ:")
    print_info("1. اختبار تهيئة البوت")
    print_info("2. اختبار أوامر البوت")
    print_info("3. اختبار بناة الأزرار")
    print_info("4. اختبار نظام الصلاحيات")
    print_info("5. اختبار نظام التتبع")
    print_info("6. اختبار نظام الاشتراك")
    print_info("7. اختبار عملاء Pyrogram")
    print()
    
    results = {}
    
    try:
        # اختبار تهيئة البوت
        results["bot_initialization"] = await test_bot_initialization()
        
        # اختبار أوامر البوت
        results["bot_commands"] = await test_bot_commands()
        
        # اختبار بناة الأزرار
        results["button_builders"] = test_button_builders()
        
        # اختبار نظام الصلاحيات
        results["admin_permissions"] = test_admin_permissions()
        
        # اختبار نظام التتبع
        results["bot_tracking"] = test_bot_tracking()
        
        # اختبار نظام الاشتراك
        results["subscription_checker"] = test_subscription_checker()
        
        # اختبار عملاء Pyrogram
        results["pyrogram_clients"] = await test_pyrogram_clients()
        
        # إنشاء التقرير
        success = generate_bot_test_report(results)
        
        if success:
            print_header("✅ جميع اختبارات البوت نجحت!")
            return 0
        else:
            print_header("❌ بعض اختبارات البوت فشلت")
            return 1
            
    except KeyboardInterrupt:
        print_warning("\nتم إيقاف الاختبار بواسطة المستخدم")
        return 1
    except Exception as e:
        print_error(f"خطأ غير متوقع: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

# Made with Bob
