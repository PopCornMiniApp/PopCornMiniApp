#!/usr/bin/env python3
"""Check series, seasons, and episodes details"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/tmp/popcorn.db")

def check_series_details():
    """Check series, seasons, and episodes"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📺 SERIES DETAILS")
    print("=" * 80)
    
    # Get series with seasons and episodes count
    cursor.execute("""
        SELECT 
            s.sid,
            s.title,
            s.tmdb_id,
            COUNT(DISTINCT se.id) as seasons_count,
            COUNT(e.id) as episodes_count
        FROM series s
        LEFT JOIN seasons se ON s.id = se.series_id
        LEFT JOIN episodes e ON se.id = e.season_id
        GROUP BY s.id
        ORDER BY s.sid
    """)
    
    series_list = cursor.fetchall()
    
    for sid, title, tmdb_id, seasons, episodes in series_list:
        print(f"\n🎬 {title}")
        print(f"   SID: {sid}")
        print(f"   TMDB ID: {tmdb_id}")
        print(f"   Seasons: {seasons}")
        print(f"   Episodes: {episodes}")
        
        # Get seasons details
        cursor.execute("""
            SELECT 
                se.season_number,
                se.topic_id,
                COUNT(e.id) as episodes_count
            FROM seasons se
            LEFT JOIN episodes e ON se.id = e.season_id
            WHERE se.series_id = (SELECT id FROM series WHERE sid = ?)
            GROUP BY se.id
            ORDER BY se.season_number
        """, (sid,))
        
        seasons_data = cursor.fetchall()
        if seasons_data:
            print(f"   Seasons breakdown:")
            for season_num, topic_id, ep_count in seasons_data:
                print(f"      S{season_num:02d}: {ep_count} episodes (Topic: {topic_id})")
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    # Total counts
    cursor.execute("SELECT COUNT(*) FROM series")
    total_series = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM seasons")
    total_seasons = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM episodes")
    total_episodes = cursor.fetchone()[0]
    
    print(f"Total Series: {total_series}")
    print(f"Total Seasons: {total_seasons}")
    print(f"Total Episodes: {total_episodes}")
    
    # Check for series without seasons
    cursor.execute("""
        SELECT s.sid, s.title
        FROM series s
        LEFT JOIN seasons se ON s.id = se.series_id
        WHERE se.id IS NULL
    """)
    
    no_seasons = cursor.fetchall()
    if no_seasons:
        print(f"\n⚠️  Series without seasons: {len(no_seasons)}")
        for sid, title in no_seasons:
            print(f"   - {title} ({sid})")
    
    # Check for seasons without episodes
    cursor.execute("""
        SELECT s.title, se.season_number
        FROM seasons se
        JOIN series s ON se.series_id = s.id
        LEFT JOIN episodes e ON se.id = e.season_id
        WHERE e.id IS NULL
    """)
    
    no_episodes = cursor.fetchall()
    if no_episodes:
        print(f"\n⚠️  Seasons without episodes: {len(no_episodes)}")
        for title, season_num in no_episodes:
            print(f"   - {title} S{season_num:02d}")
    
    conn.close()

if __name__ == "__main__":
    check_series_details()

# Made with Bob
