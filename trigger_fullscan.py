#!/usr/bin/env python3
"""
Trigger Full Scan manually - bypasses admin authentication
Run this script to scan all Forum Topics in the private group
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

async def main():
    print("=" * 60)
    print("🔍 PopCorn Full Scan - Manual Trigger")
    print("=" * 60)
    print()
    
    # Initialize database
    from app.database import init_db, get_stats, push_db_to_hf
    from app.cache import cache_clear_all
    
    print("📦 Initializing database...")
    init_db()
    
    # Get initial stats
    stats_before = get_stats()
    print(f"📊 Current stats:")
    print(f"   🎬 Movies: {stats_before['movies_count']}")
    print(f"   📺 Series: {stats_before['series_count']}")
    print(f"   🎞 Episodes: {stats_before['episodes_count']}")
    print()
    
    # Initialize Pyrogram
    print("🔌 Initializing Pyrogram clients...")
    from app.stream import init_pyrogram, _pyro_clients
    await init_pyrogram()
    
    if not _pyro_clients:
        print("❌ Error: No Pyrogram clients available!")
        return
    
    print(f"✅ {len(_pyro_clients)} Pyrogram client(s) ready")
    
    # Use User Bot (s1 or s2) instead of Bot Account (main)
    # Bot accounts cannot use GetForumTopics API
    # _pyro_clients is a list: [main, s1, s2]
    # We need s1 or s2 (index 1 or 2)
    user_bot = None
    if len(_pyro_clients) >= 2:
        # Try s1 first (index 1)
        user_bot = _pyro_clients[1]
        print(f"✅ Using User Bot: s1 (index 1)")
    elif len(_pyro_clients) >= 3:
        # Fallback to s2 (index 2)
        user_bot = _pyro_clients[2]
        print(f"✅ Using User Bot: s2 (index 2)")
    
    if not user_bot:
        print("❌ Error: No User Bot (s1/s2) available!")
        print("   Bot accounts cannot access Forum Topics")
        print(f"   Available clients: {len(_pyro_clients)}")
        return
    
    print()
    
    # Run full scan
    print("🔍 Starting full scan of private group...")
    print("   This will scan all Forum Topics and messages")
    print("   Please wait, this may take a few minutes...")
    print()
    
    from app.scanner import run_full_scan
    
    try:
        results = await run_full_scan(user_bot)
        
        print()
        print("=" * 60)
        print("✅ SCAN COMPLETE!")
        print("=" * 60)
        print(f"📋 Topics scanned: {results['topics_scanned']}")
        print(f"➕ New content registered: {results['registered']}")
        print(f"🎬 Files attached: {results['files_attached']}")
        print(f"⚠️  Errors: {results['errors']}")
        print()
        
        # Get final stats
        stats_after = get_stats()
        print("📊 Updated stats:")
        print(f"   🎬 Movies: {stats_after['movies_count']} (+{stats_after['movies_count'] - stats_before['movies_count']})")
        print(f"   📺 Series: {stats_after['series_count']} (+{stats_after['series_count'] - stats_before['series_count']})")
        print(f"   🎞 Episodes: {stats_after['episodes_count']} (+{stats_after['episodes_count'] - stats_before['episodes_count']})")
        print()
        
        # Push to HuggingFace
        if results['registered'] > 0 or results['files_attached'] > 0:
            print("📤 Pushing changes to HuggingFace...")
            push_db_to_hf()
            cache_clear_all()
            print("✅ Changes pushed successfully!")
        else:
            print("ℹ️  No changes to push")
        
    except Exception as e:
        print(f"❌ Error during scan: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    from app.stream import stop_pyrogram
    await stop_pyrogram()
    
    print()
    print("=" * 60)
    print("🎬 Done!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
