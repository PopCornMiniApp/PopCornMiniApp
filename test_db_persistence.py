#!/usr/bin/env python3
"""
Test script to verify database persistence across restarts.
This ensures the fix prevents downloading old DB from HuggingFace.
"""
import sqlite3
import os
import time
from datetime import datetime

DB_PATH = "/tmp/popcorn.db"

def get_movie_count():
    """Get current movie count from database."""
    if not os.path.exists(DB_PATH):
        return 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM movies')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_db_age():
    """Get database file age in hours."""
    if not os.path.exists(DB_PATH):
        return None
    age_seconds = time.time() - os.path.getmtime(DB_PATH)
    return age_seconds / 3600

def main():
    print("=" * 60)
    print("🔍 Database Persistence Test")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at: {DB_PATH}")
        print("   Start the server first to create the database.")
        return
    
    # Get current stats
    movie_count = get_movie_count()
    db_age = get_db_age()
    db_mtime = datetime.fromtimestamp(os.path.getmtime(DB_PATH))
    
    print(f"\n📊 Current Database Status:")
    print(f"   Path: {DB_PATH}")
    print(f"   Movies: {movie_count}")
    print(f"   Age: {db_age:.2f} hours")
    print(f"   Last Modified: {db_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n✅ Expected Behavior:")
    print(f"   • If age < 24 hours: Server will use existing DB")
    print(f"   • If age ≥ 24 hours: Server will download from HuggingFace")
    print(f"   • Current movie count ({movie_count}) should persist on restart")
    
    print(f"\n🧪 Test Instructions:")
    print(f"   1. Note the current movie count: {movie_count}")
    print(f"   2. Restart the server (Ctrl+C and restart)")
    print(f"   3. Check logs for: 'Using existing local database'")
    print(f"   4. Run this script again to verify count is still {movie_count}")
    
    print(f"\n💡 To force download from HuggingFace:")
    print(f"   rm {DB_PATH}")
    print(f"   # Then restart server")
    
    print("=" * 60)

if __name__ == "__main__":
    main()

# Made with Bob
