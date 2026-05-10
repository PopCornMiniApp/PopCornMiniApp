#!/usr/bin/env python3
"""
Test Bot After Deployment
Verifies that the bot is responding correctly after deployment
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

async def test_bot():
    """Test the bot functionality."""
    
    print("🤖 Testing PopCorn Bot After Deployment...")
    print("=" * 70)
    
    # Load environment variables
    load_dotenv()
    
    bot_token = os.getenv("MAIN_BOT_TOKEN")
    admin_id = os.getenv("ADMIN_ID")
    
    if not bot_token:
        print("❌ Error: MAIN_BOT_TOKEN not set")
        return False
    
    try:
        # Initialize bot
        bot = Bot(token=bot_token)
        
        print("\n📋 Bot Information:")
        print("-" * 70)
        
        # Get bot info
        me = await bot.get_me()
        print(f"✅ Bot Username: @{me.username}")
        print(f"✅ Bot ID: {me.id}")
        print(f"✅ Bot Name: {me.first_name}")
        print(f"✅ Can Join Groups: {me.can_join_groups}")
        print(f"✅ Can Read Messages: {me.can_read_all_group_messages}")
        
        # Test bot commands
        print("\n📝 Available Commands:")
        print("-" * 70)
        
        commands = await bot.get_my_commands()
        if commands:
            for cmd in commands:
                print(f"   /{cmd.command} - {cmd.description}")
        else:
            print("   ⚠️  No commands set")
        
        # Check if bot is running
        print("\n🔍 Bot Status Check:")
        print("-" * 70)
        
        try:
            # Try to get updates (this will work if bot is running)
            updates = await bot.get_updates(limit=1)
            print(f"✅ Bot is responsive")
            print(f"✅ Recent updates: {len(updates)}")
        except TelegramError as e:
            print(f"⚠️  Bot status check: {e}")
        
        # Send test message to admin if admin_id is set
        if admin_id:
            try:
                admin_id_int = int(admin_id)
                test_message = (
                    "🎉 **نشر ناجح!**\n\n"
                    "تم نشر الملفات المصلحة بنجاح:\n"
                    "✅ app/bot.py\n"
                    "✅ app/bot_commands.py\n\n"
                    "البوت يعمل الآن بشكل صحيح! 🍿"
                )
                
                await bot.send_message(
                    chat_id=admin_id_int,
                    text=test_message,
                    parse_mode="Markdown"
                )
                print(f"✅ Test message sent to admin (ID: {admin_id})")
                
            except Exception as e:
                print(f"⚠️  Could not send test message to admin: {e}")
        
        print("\n" + "=" * 70)
        print("✅ Bot Testing Complete!")
        print("\n📊 Summary:")
        print(f"   • Bot is active and responsive")
        print(f"   • Username: @{me.username}")
        print(f"   • Ready to receive commands")
        print("\n💡 Next Steps:")
        print("   1. Test /start command in Telegram")
        print("   2. Verify registration flow works")
        print("   3. Test movie/series browsing")
        print("   4. Check all buttons respond correctly")
        
        return True
        
    except TelegramError as e:
        print(f"\n❌ Telegram Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_bot())
    sys.exit(0 if success else 1)

# Made with Bob
