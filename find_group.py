#!/usr/bin/env python3
"""
Find ALL groups the user is a member of, including archived and hidden ones.
"""
import asyncio
from pyrogram import Client
from pyrogram.enums import ChatType

async def find_all_groups():
    print("=" * 70)
    print("🔍 Finding ALL Groups - PopCorn (Enhanced)")
    print("=" * 70)
    print()
    
    api_id = 32360090
    api_hash = "c7b022dcf0b1d3021197857e51be9375"
    phone = "+213549160496"
    
    print("🔐 Logging in...")
    client = Client(
        name="find_all_groups",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        workdir="/tmp"
    )
    
    try:
        await client.start()
        print("✅ Logged in successfully!")
        print()
        
        me = await client.get_me()
        print(f"👤 User: {me.first_name} (ID: {me.id})")
        print()
        
        print("📋 Scanning ALL chats (including archived)...")
        print("=" * 70)
        print()
        
        all_groups = []
        popcorn_groups = []
        
        # Get ALL dialogs including archived
        dialog_count = 0
        async for dialog in client.get_dialogs(limit=None):
            dialog_count += 1
            chat = dialog.chat
            
            # Check all types of groups
            if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                all_groups.append(chat)
                
                title = (chat.title or "").lower()
                
                # Check if it's POPCORN DB
                if "popcorn" in title or "db" in title:
                    popcorn_groups.append(chat)
                    print(f"🎯 FOUND: {chat.title}")
                    print(f"   ID: {chat.id}")
                    print(f"   Type: {chat.type}")
                    print(f"   Username: @{chat.username or 'N/A'}")
                    print(f"   Members: {chat.members_count or 'N/A'}")
                    
                    # Check if forum
                    if hasattr(chat, 'is_forum'):
                        print(f"   Forum: {'Yes 🔥' if chat.is_forum else 'No'}")
                    
                    # Check permissions
                    if hasattr(chat, 'permissions'):
                        print(f"   Permissions: {chat.permissions}")
                    
                    print()
        
        print(f"📊 Total dialogs scanned: {dialog_count}")
        print(f"📊 Total groups found: {len(all_groups)}")
        print(f"📊 POPCORN-related groups: {len(popcorn_groups)}")
        print()
        
        if not popcorn_groups:
            print("⚠️  No POPCORN groups found!")
            print()
            print("📋 Listing first 20 groups for reference:")
            print("=" * 70)
            print()
            
            for i, chat in enumerate(all_groups[:20], 1):
                print(f"{i}. {chat.title}")
                print(f"   ID: {chat.id}")
                print(f"   Type: {chat.type}")
                if hasattr(chat, 'is_forum') and chat.is_forum:
                    print(f"   🔥 FORUM")
                print()
        
        # Try to access the specific group ID directly
        print("=" * 70)
        print("🔍 Trying to access group ID: -1003826837517")
        print()
        
        try:
            specific_chat = await client.get_chat(-1003826837517)
            print(f"✅ SUCCESS! Found the group:")
            print(f"   Title: {specific_chat.title}")
            print(f"   ID: {specific_chat.id}")
            print(f"   Type: {specific_chat.type}")
            print(f"   Members: {specific_chat.members_count or 'N/A'}")
            
            if hasattr(specific_chat, 'is_forum'):
                print(f"   Forum: {'Yes 🔥' if specific_chat.is_forum else 'No'}")
            
            print()
            print("✅ The group ID is CORRECT!")
            print("✅ The user CAN access this group!")
            print()
            
        except Exception as e:
            print(f"❌ Cannot access group: {e}")
            print()
            print("This means:")
            print("  1. The group ID might be wrong")
            print("  2. OR the user is not a member")
            print("  3. OR the group was deleted")
            print()
        
        print("=" * 70)
        print()
        print("💡 Next steps:")
        print("1. If POPCORN DB was found above, use its ID")
        print("2. If not found, check if the group still exists")
        print("3. Make sure the user account is still a member")
        print()
        
        await client.stop()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(find_all_groups())

# Made with Bob
