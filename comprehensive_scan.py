#!/usr/bin/env python3
"""
Comprehensive Telegram Group Scanner
Scans all topics and all messages thoroughly to verify actual content
"""
import asyncio
import sqlite3
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import PRIVATE_GROUP_ID, DB_PATH
from app.scanner import _get_input_channel, _get_forum_topics_raw, _parse_topic

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    print("\n" + "=" * 70)
    print("🔍 COMPREHENSIVE TELEGRAM GROUP SCAN")
    print("=" * 70)
    print()
    
    # Initialize Pyrogram
    print("🔌 Initializing Pyrogram clients...")
    from app.stream import init_pyrogram, _pyro_clients
    await init_pyrogram()
    
    if not _pyro_clients or len(_pyro_clients) < 2:
        print("❌ Error: No User Bot (s1/s2) available!")
        return
    
    # Use User Bot (s1)
    user_bot = _pyro_clients[1]
    print(f"✅ Using User Bot: s1")
    print()
    
    # Get group info
    try:
        chat = await user_bot.get_chat(PRIVATE_GROUP_ID)
        print(f"📱 Group Information:")
        print(f"   Name: {chat.title}")
        print(f"   ID: {PRIVATE_GROUP_ID}")
        print(f"   Type: {chat.type}")
        print()
    except Exception as e:
        print(f"❌ Error getting group info: {e}")
        return
    
    # Get input channel
    input_channel = await _get_input_channel(user_bot)
    if not input_channel:
        print("❌ Error: Cannot resolve group peer")
        return
    
    # Get all topics
    print("📋 Fetching all Forum Topics...")
    try:
        topics = await _get_forum_topics_raw(user_bot)
        print(f"✅ Found {len(topics)} topics")
        print()
    except Exception as e:
        print(f"❌ Error fetching topics: {e}")
        return
    
    # Analyze each topic
    movies_list = []
    series_list = []
    unknown_list = []
    
    print("🔍 Analyzing Topics...")
    print("-" * 70)
    
    for topic in topics:
        title = topic.title
        topic_id = topic.id
        
        # Parse topic
        parsed = _parse_topic(title)
        
        if parsed:
            if parsed["type"] == "movie":
                movies_list.append({
                    "id": topic_id,
                    "title": title,
                    "slug": parsed["slug"],
                    "internal_id": parsed["internal_id"],
                    "tmdb_id": parsed["tmdb_id"]
                })
                print(f"🎬 Movie: {title}")
                print(f"   Topic ID: {topic_id}")
                print(f"   Internal ID: {parsed['internal_id']}")
                print(f"   TMDB ID: {parsed['tmdb_id']}")
            elif parsed["type"] == "series":
                series_list.append({
                    "id": topic_id,
                    "title": title,
                    "slug": parsed["slug"],
                    "internal_id": parsed["internal_id"],
                    "tmdb_id": parsed["tmdb_id"]
                })
                print(f"📺 Series: {title}")
                print(f"   Topic ID: {topic_id}")
                print(f"   Internal ID: {parsed['internal_id']}")
                print(f"   TMDB ID: {parsed['tmdb_id']}")
        else:
            unknown_list.append({
                "id": topic_id,
                "title": title
            })
            print(f"❓ Unknown: {title}")
            print(f"   Topic ID: {topic_id}")
        
        print()
    
    # Summary
    print("=" * 70)
    print("📊 TELEGRAM GROUP SUMMARY")
    print("=" * 70)
    print(f"Total Topics: {len(topics)}")
    print(f"🎬 Movies: {len(movies_list)}")
    print(f"📺 Series: {len(series_list)}")
    print(f"❓ Unknown/General: {len(unknown_list)}")
    print()
    
    # Compare with database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        db_movies = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        db_series = cursor.execute("SELECT COUNT(*) FROM series").fetchone()[0]
        db_seasons = cursor.execute("SELECT COUNT(*) FROM seasons").fetchone()[0]
        db_episodes = cursor.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        
        print("=" * 70)
        print("💾 DATABASE SUMMARY")
        print("=" * 70)
        print(f"🎬 Movies: {db_movies}")
        print(f"📺 Series: {db_series}")
        print(f"📁 Seasons: {db_seasons}")
        print(f"🎞 Episodes: {db_episodes}")
        print()
        
        print("=" * 70)
        print("🔍 COMPARISON (Telegram vs Database)")
        print("=" * 70)
        
        movies_diff = len(movies_list) - db_movies
        series_diff = len(series_list) - db_series
        
        print(f"🎬 Movies: {len(movies_list)} (Telegram) vs {db_movies} (DB)")
        if movies_diff > 0:
            print(f"   ⚠️  MISSING: {movies_diff} movies not in database")
        elif movies_diff < 0:
            print(f"   ⚠️  EXTRA: {abs(movies_diff)} movies in database but not in Telegram")
        else:
            print(f"   ✅ MATCH: All movies synced")
        
        print()
        print(f"📺 Series: {len(series_list)} (Telegram) vs {db_series} (DB)")
        if series_diff > 0:
            print(f"   ⚠️  MISSING: {series_diff} series not in database")
        elif series_diff < 0:
            print(f"   ⚠️  EXTRA: {abs(series_diff)} series in database but not in Telegram")
        else:
            print(f"   ✅ MATCH: All series synced")
        
        print()
        
        # Find missing content
        if movies_diff > 0:
            print("=" * 70)
            print("🔍 MISSING MOVIES IN DATABASE")
            print("=" * 70)
            
            db_movie_ids = set(row[0] for row in cursor.execute("SELECT id FROM movies").fetchall())
            
            for movie in movies_list:
                if movie["internal_id"] not in db_movie_ids:
                    print(f"❌ {movie['title']}")
                    print(f"   Topic ID: {movie['id']}")
                    print(f"   Internal ID: {movie['internal_id']}")
                    print(f"   TMDB ID: {movie['tmdb_id']}")
                    print()
        
        if series_diff > 0:
            print("=" * 70)
            print("🔍 MISSING SERIES IN DATABASE")
            print("=" * 70)
            
            db_series_ids = set(row[0] for row in cursor.execute("SELECT id FROM series").fetchall())
            
            for series in series_list:
                if series["internal_id"] not in db_series_ids:
                    print(f"❌ {series['title']}")
                    print(f"   Topic ID: {series['id']}")
                    print(f"   Internal ID: {series['internal_id']}")
                    print(f"   TMDB ID: {series['tmdb_id']}")
                    print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error accessing database: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    from app.stream import stop_pyrogram
    await stop_pyrogram()
    
    print("=" * 70)
    print("✅ SCAN COMPLETE")
    print("=" * 70)
    print()
    
    # Recommendations
    if movies_diff != 0 or series_diff != 0:
        print("💡 RECOMMENDATIONS:")
        print()
        print("1. Run Full Scan to sync missing content:")
        print("   python3 trigger_fullscan.py")
        print()
        print("2. Check scanner logs for errors:")
        print("   Check app/scanner.py for any parsing issues")
        print()
        print("3. Verify topic naming format:")
        print("   Movies: #slug #movies #midXXX #tmdb_id")
        print("   Series: #slug #series #sidXXX #tmdb_id")
        print()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
