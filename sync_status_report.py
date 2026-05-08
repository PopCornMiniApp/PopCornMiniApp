#!/usr/bin/env python3
"""Generate comprehensive sync status report"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("/tmp/popcorn.db")

def generate_report():
    """Generate full sync status report"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📊 POPCORN DATABASE SYNC STATUS REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Sync Status
    cursor.execute("SELECT * FROM sync_status")
    sync_data = cursor.fetchone()
    if sync_data:
        print("🔄 SYNC STATUS:")
        print(f"   Full Scan Completed: {'✅ Yes' if sync_data[1] else '❌ No'}")
        print(f"   Last Sync: {sync_data[2]}")
        print(f"   Sync Type: {sync_data[3]}")
    print()
    
    # Movies Summary
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_movies = cursor.fetchone()[0]
    print(f"🎬 MOVIES: {total_movies}")
    
    cursor.execute("""
        SELECT COUNT(*) FROM movies 
        WHERE poster_path IS NOT NULL AND backdrop_path IS NOT NULL
    """)
    movies_with_images = cursor.fetchone()[0]
    print(f"   With Images: {movies_with_images} ({movies_with_images*100//total_movies if total_movies else 0}%)")
    
    cursor.execute("SELECT COUNT(*) FROM movies WHERE tmdb_id IS NOT NULL")
    movies_with_tmdb = cursor.fetchone()[0]
    print(f"   With TMDB Data: {movies_with_tmdb} ({movies_with_tmdb*100//total_movies if total_movies else 0}%)")
    print()
    
    # Series Summary
    cursor.execute("SELECT COUNT(*) FROM series")
    total_series = cursor.fetchone()[0]
    print(f"📺 SERIES: {total_series}")
    
    cursor.execute("SELECT SUM(total_seasons) FROM series")
    total_seasons_count = cursor.fetchone()[0] or 0
    print(f"   Total Seasons (from TMDB): {total_seasons_count}")
    
    cursor.execute("SELECT COUNT(DISTINCT topic_id) FROM topic_series_map")
    topics_mapped = cursor.fetchone()[0]
    print(f"   Topics Mapped: {topics_mapped}")
    
    cursor.execute("SELECT COUNT(*) FROM episodes")
    total_episodes = cursor.fetchone()[0]
    print(f"   Total Episodes: {total_episodes}")
    print()
    
    # Series Breakdown
    print("📺 SERIES DETAILS:")
    cursor.execute("""
        SELECT 
            s.id,
            s.title,
            s.total_seasons,
            COUNT(DISTINCT e.season_number) as actual_seasons,
            COUNT(e.id) as episodes,
            (SELECT COUNT(*) FROM topic_series_map WHERE series_id = s.id) as topics
        FROM series s
        LEFT JOIN episodes e ON s.id = e.series_id
        GROUP BY s.id
        ORDER BY s.id
    """)
    
    for sid, title, tmdb_seasons, actual_seasons, episodes, topics in cursor.fetchall():
        print(f"\n   {title} ({sid}):")
        print(f"      TMDB Seasons: {tmdb_seasons}")
        print(f"      Actual Seasons: {actual_seasons}")
        print(f"      Episodes: {episodes}")
        print(f"      Topics: {topics}")
        
        # Show season breakdown
        cursor.execute("""
            SELECT season_number, COUNT(*) as ep_count
            FROM episodes
            WHERE series_id = ?
            GROUP BY season_number
            ORDER BY season_number
        """, (sid,))
        
        seasons_data = cursor.fetchall()
        if seasons_data:
            print(f"      Season Breakdown:")
            for season_num, ep_count in seasons_data:
                print(f"         S{season_num:02d}: {ep_count} episodes")
    
    print("\n" + "=" * 80)
    print("🗺️  TOPIC MAPPING:")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            tsm.topic_id,
            s.title,
            s.id,
            COUNT(e.id) as episodes_in_topic
        FROM topic_series_map tsm
        JOIN series s ON tsm.series_id = s.id
        LEFT JOIN episodes e ON e.series_id = s.id
        GROUP BY tsm.topic_id
        ORDER BY tsm.topic_id
    """)
    
    for topic_id, title, sid, ep_count in cursor.fetchall():
        print(f"   Topic {topic_id}: {title} ({sid}) - {ep_count} episodes")
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY:")
    print("=" * 80)
    print(f"   Total Content Items: {total_movies + total_series}")
    print(f"   Movies: {total_movies}")
    print(f"   Series: {total_series}")
    print(f"   Seasons: {actual_seasons if 'actual_seasons' in locals() else 'N/A'}")
    print(f"   Episodes: {total_episodes}")
    print(f"   Topics: {topics_mapped + total_movies}")
    print()
    
    # Check for issues
    print("=" * 80)
    print("⚠️  POTENTIAL ISSUES:")
    print("=" * 80)
    
    # Movies without TMDB data
    cursor.execute("SELECT COUNT(*) FROM movies WHERE tmdb_id IS NULL")
    movies_no_tmdb = cursor.fetchone()[0]
    if movies_no_tmdb > 0:
        print(f"   ⚠️  {movies_no_tmdb} movies without TMDB data")
    
    # Series without episodes
    cursor.execute("""
        SELECT s.title, s.id
        FROM series s
        LEFT JOIN episodes e ON s.id = e.series_id
        WHERE e.id IS NULL
    """)
    series_no_episodes = cursor.fetchall()
    if series_no_episodes:
        print(f"   ⚠️  {len(series_no_episodes)} series without episodes:")
        for title, sid in series_no_episodes:
            print(f"      - {title} ({sid})")
    
    # Series with mismatched season counts
    cursor.execute("""
        SELECT 
            s.title,
            s.id,
            s.total_seasons,
            COUNT(DISTINCT e.season_number) as actual_seasons
        FROM series s
        LEFT JOIN episodes e ON s.id = e.series_id
        GROUP BY s.id
        HAVING s.total_seasons != actual_seasons
    """)
    mismatched = cursor.fetchall()
    if mismatched:
        print(f"   ⚠️  {len(mismatched)} series with season count mismatch:")
        for title, sid, tmdb_s, actual_s in mismatched:
            print(f"      - {title} ({sid}): TMDB={tmdb_s}, Actual={actual_s}")
    
    if not movies_no_tmdb and not series_no_episodes and not mismatched:
        print("   ✅ No issues detected!")
    
    conn.close()

if __name__ == "__main__":
    generate_report()

# Made with Bob
