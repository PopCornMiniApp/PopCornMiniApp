#!/usr/bin/env python3
"""
Fix Telegram Sync Issue
Diagnose and fix the peer ID problem
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def diagnose_and_fix():
    """Diagnose and fix Telegram sync"""
    from app.stream import init_pyrogram_clients
    from app.config import PRIVATE_GROUPE_1_ID
    
    print("\n" + "="*60)
    print("🔍 DIAGNOSING TELEGRAM SYNC ISSUE")
    print("="*60)
    
    print(f"\n📋 Configuration:")
    print(f"   Private Group ID: {PRIVATE_GROUPE_1_ID}")
    
    # Initialize clients
    print("\n🔌 Initializing Pyrogram clients...")
    clients = await init_pyrogram_clients()
    print(f"✅ {len(clients)} client(s) initialized")
    
    # Test each client
    for name, client in clients.items():
        print(f"\n🧪 Testing client: {name}")
        try:
            # Try to get dialogs
            async for dialog in client.get_dialogs(limit=10):
                if dialog.chat.id == PRIVATE_GROUPE_1_ID:
                    print(f"   ✅ Found private group: {dialog.chat.title}")
                    print(f"   📊 Type: {dialog.chat.type}")
                    print(f"   👥 Members: {dialog.chat.members_count if hasattr(dialog.chat, 'members_count') else 'N/A'}")
                    break
            else:
                print(f"   ⚠️  Private group not found in dialogs")
                
            # Try direct access
            try:
                chat = await client.get_chat(PRIVATE_GROUPE_1_ID)
                print(f"   ✅ Direct access successful: {chat.title}")
            except Exception as e:
                print(f"   ❌ Direct access failed: {str(e)}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Cleanup
    for client in clients.values():
        await client.stop()
    
    print("\n" + "="*60)
    print("💡 RECOMMENDATIONS")
    print("="*60)
    print("""
1. تأكد من أن البوت admin في المجموعة
2. تأكد من أن المجموعة Forum enabled
3. جرب استخدام username بدلاً من ID
4. تحقق من صلاحيات البوت

الحل السريع:
- افتح المجموعة في Telegram
- أضف البوت كـ admin
- أعطه صلاحيات كاملة
- أعد تشغيل المسح
""")

if __name__ == "__main__":
    asyncio.run(diagnose_and_fix())

# Made with Bob
