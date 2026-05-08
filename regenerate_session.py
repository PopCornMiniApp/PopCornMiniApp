#!/usr/bin/env python3
"""
Regenerate Pyrogram session after adding User Bot to the private group.
This script creates a fresh session that includes access to the group.
"""
import asyncio
import os
from pyrogram import Client

async def regenerate_session():
    print("=" * 70)
    print("🔄 PopCorn - User Bot Session Regeneration")
    print("=" * 70)
    print()
    print("This script will create a fresh Pyrogram session for your User Bot.")
    print("Make sure you have:")
    print("  1. ✅ Added the User Bot account to the private group")
    print("  2. ✅ Granted it read/send message permissions")
    print()
    
    # Get credentials
    print("📝 Enter your credentials:")
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    phone = input("Phone number (with country code, e.g., +1234567890): ").strip()
    
    if not api_id or not api_hash or not phone:
        print("❌ All fields are required!")
        return
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API ID must be a number!")
        return
    
    print()
    print("🔐 Creating new session...")
    
    # Create client
    client = Client(
        name="new_session",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        workdir="/tmp"
    )
    
    try:
        await client.start()
        print("✅ Successfully logged in!")
        print()
        
        # Get user info
        me = await client.get_me()
        print(f"👤 Logged in as:")
        print(f"   Name: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username or 'N/A'}")
        print(f"   Phone: {me.phone_number}")
        print(f"   ID: {me.id}")
        print()
        
        # Test group access
        group_id = -1003826837517
        print(f"🔍 Testing access to private group ({group_id})...")
        
        try:
            chat = await client.get_chat(group_id)
            print(f"✅ Successfully accessed group!")
            print(f"   Title: {chat.title}")
            print(f"   Type: {chat.type}")
            print(f"   Members: {chat.members_count or 'N/A'}")
            print()
            
            # Check membership
            try:
                member = await client.get_chat_member(group_id, me.id)
                print(f"✅ Membership confirmed!")
                print(f"   Status: {member.status}")
                print()
            except Exception as e:
                print(f"⚠️  Could not verify membership: {e}")
                print()
            
        except Exception as e:
            print(f"❌ Cannot access group: {e}")
            print()
            print("⚠️  Make sure:")
            print("   1. The User Bot is added to the group")
            print("   2. The group ID is correct: -1003826837517")
            print()
            await client.stop()
            return
        
        # Export session string
        print("📤 Exporting session string...")
        session_string = await client.export_session_string()
        print()
        print("=" * 70)
        print("✅ SUCCESS! New session created and tested.")
        print("=" * 70)
        print()
        print("📋 Your new session string:")
        print()
        print(session_string)
        print()
        print("=" * 70)
        print()
        print("🔧 Next steps:")
        print()
        print("1. Copy the session string above")
        print()
        print("2. Update your .env file or environment variables:")
        print(f"   STREAM_BOT_1={session_string}")
        print()
        print("3. Restart your PopCorn application:")
        print("   cd PopCorn && python3 -m uvicorn app.main:app --reload")
        print()
        print("4. Test the sync:")
        print("   cd PopCorn && python3 test_sync.py")
        print()
        print("=" * 70)
        
        await client.stop()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Common issues:")
        print("  - Invalid API credentials")
        print("  - Phone number not registered")
        print("  - Two-factor authentication enabled (enter password when prompted)")

if __name__ == "__main__":
    asyncio.run(regenerate_session())

# Made with Bob
