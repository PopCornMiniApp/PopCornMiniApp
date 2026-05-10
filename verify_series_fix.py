#!/usr/bin/env python3
"""
Verification script to check if all series are now registered after the fix.
Expected: 9 series total (was 3 before fix)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "popcorn.db"

def verify_fix():
    """Verify that all series are now registered."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print("=" * 70)
    print("🔍 VERIFICATION: Series Registration Fix")
    print("=" * 70)
    
    # Count series
    series_count = conn.execute("SELECT COUNT(*) as count FROM series").fetchone()['count']
    print(f"\n📺 Total Series Registered: {series_count}")
    print(f"   Expected: 9 series")
    print(f"   Status: {'✅ FIXED' if series_count >= 9 else '❌ STILL MISSING'}")
    
    # List all series
    print(f"\n📋 Series List:")
    series = conn.execute("""
        SELECT id, title, total_seasons, 
               (SELECT COUNT(DISTINCT season_number) FROM episodes WHERE series_id = series.id) as scanned_seasons
        FROM series 
        ORDER BY title
    """).fetchall()
    
    for s in series:
        print(f"   • {s['title']}")
        print(f"     ID: {s['id']}, Total Seasons: {s['total_seasons']}, Scanned: {s['scanned_seasons']}")
    
    # Check seasons table
    try:
        seasons_count = conn.execute("SELECT COUNT(*) as count FROM seasons").fetchone()['count']
        print(f"\n📁 Total Season Records: {seasons_count}")
        print(f"   Expected: ~25 seasons")
        
        # List seasons
        seasons = conn.execute("""
            SELECT s.title, se.season_number, se.topic_id, se.episode_count
            FROM seasons se
            JOIN series s ON s.id = se.series_id
            ORDER BY s.title, se.season_number
        """).fetchall()
        
        print(f"\n📁 Season Details:")
        current_series = None
        for season in seasons:
            if current_series != season['title']:
                current_series = season['title']
                print(f"\n   {current_series}:")
            print(f"      Season {season['season_number']}: topic_id={season['topic_id']}, episodes={season['episode_count']}")
    except sqlite3.OperationalError:
        print("\n⚠️  Seasons table not found (old schema)")
    
    # Count episodes
    episodes_count = conn.execute("SELECT COUNT(*) as count FROM episodes").fetchone()['count']
    print(f"\n🎞  Total Episodes: {episodes_count}")
    
    # Count movies for comparison
    movies_count = conn.execute("SELECT COUNT(*) as count FROM movies").fetchone()['count']
    print(f"\n🎬 Total Movies: {movies_count}")
    print(f"   Expected: 32 movies")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Movies:  {movies_count}/32 {'✅' if movies_count >= 32 else '❌'}")
    print(f"Series:  {series_count}/9 {'✅' if series_count >= 9 else '❌'}")
    print(f"Episodes: {episodes_count}")
    
    if series_count >= 9:
        print("\n🎉 SUCCESS! All series are now registered!")
        print("The fix worked correctly.")
    else:
        print(f"\n⚠️  WARNING: Still missing {9 - series_count} series")
        print("The fix may need adjustment or another scan.")
    
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    verify_fix()

# Made with Bob
