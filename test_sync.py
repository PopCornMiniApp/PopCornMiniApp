#!/usr/bin/env python3
"""
Test script to verify User Bot can access the private group
and sync works correctly after adding the bot to the group.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.stream import init_pyrogram, _pyro_clients, stop_pyrogram
from app.scanner import run_full_scan
from app.database import get_stats
from app.config import PRIVATE_GROUP_ID

async def test_sync():
    print("=" * 60)
    print("🧪 PopCorn Sync Test")
    print("=" * 60)
    print()
    
    # Step 1: Initialize Pyrogram
    print("📡 Step 1: Initializing Pyrogram clients...")
    try:
        await init_pyrogram()
        print(f"✅ Initialized {len(_pyro_clients)} clients")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    if len(_pyro_clients) < 2:
        print("❌ User Bot (s1) not available!")
        return
    
    user_bot = _pyro_clients[1]
    print(f"✅ User Bot (s1) ready")
    print()
    
    # Step 2: Test group access
    print("🔍 Step 2: Testing group access...")
    try:
        # Try to resolve peer
        peer = await user_bot.resolve_peer(PRIVATE_GROUP_ID)
        print(f"✅ Successfully resolved group peer")
        print(f"   Channel ID: {peer.channel_id}")
        print(f"   Access Hash: {peer.access_hash}")
        
        # Try to get chat info
        chat = await user_bot.get_chat(PRIVATE_GROUP_ID)
        print(f"✅ Group info retrieved:")
        print(f"   Title: {chat.title}")
        print(f"   Type: {chat.type}")
        print(f"   Members: {chat.members_count or 'N/A'}")
    except Exception as e:
        print(f"❌ Cannot access group: {e}")
        print("   Make sure User Bot is added to the group!")
        await stop_pyrogram()
        return
    print()
    
    # Step 3: Check current database stats
    print("📊 Step 3: Current database stats...")
    try:
        stats = get_stats()
        print(f"   Movies: {stats.get('movies', 0)}")
        print(f"   Series: {stats.get('series', 0)}")
        print(f"   Episodes: {stats.get('episodes', 0)}")
    except Exception as e:
        print(f"⚠️  Could not get stats: {e}")
    print()
    
    # Step 4: Run Full Scan
    print("🔄 Step 4: Running Full Scan...")
    print("   This may take a few minutes...")
    try:
        results = await run_full_scan(user_bot)
        print(f"✅ Full Scan complete!")
        print(f"   Topics found: {results.get('topics_found', 0)}")
        print(f"   Movies registered: {results.get('registered', 0)}")
        print(f"   Files attached: {results.get('files_attached', 0)}")
        print(f"   Errors: {results.get('errors', 0)}")
    except Exception as e:
        print(f"❌ Full Scan failed: {e}")
        await stop_pyrogram()
        return
    print()
    
    # Step 5: Check updated database stats
    print("📊 Step 5: Updated database stats...")
    try:
        stats = get_stats()
        print(f"   Movies: {stats.get('movies', 0)}")
        print(f"   Series: {stats.get('series', 0)}")
        print(f"   Episodes: {stats.get('episodes', 0)}")
        
        if stats.get('movies', 0) == 33:
            print("✅ SUCCESS! All 33 movies are now in the database!")
        elif stats.get('movies', 0) > 22:
            print(f"✅ PROGRESS! Database updated from 22 to {stats.get('movies', 0)} movies")
        else:
            print(f"⚠️  Still showing {stats.get('movies', 0)} movies (expected 33)")
    except Exception as e:
        print(f"⚠️  Could not get stats: {e}")
    print()
    
    # Cleanup
    print("🧹 Cleaning up...")
    await stop_pyrogram()
    print("✅ Done!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sync())

# Made with Bob
