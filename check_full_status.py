#!/usr/bin/env python3
"""
Check complete database status including seasons
"""
import sqlite3
from datetime import datetime

DB_PATH = "/tmp/popcorn.db"

def check_status():
    print("=" * 70)
    print("🔍 COMPLETE DATABASE STATUS CHECK")
    print("=" * 70)
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Database: {DB_PATH}")
    print()
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Check all tables
    print("📋 TABLES IN DATABASE:")
    print("-" * 70)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    
    for table in tables:
        table_name = table['name']
        count = conn.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()['count']
        print(f"  ✓ {table_name}: {count} records")
    print()
    
    # Movies
    print("🎬 MOVIES:")
    print("-" * 70)
    movies = conn.execute("SELECT COUNT(*) as count FROM movies").fetchone()['count']
    print(f"  Total: {movies}")
    print()
    
    # Series
    print("📺 SERIES:")
    print("-" * 70)
    series = conn.execute("SELECT COUNT(*) as count FROM series").fetchone()['count']
    print(f"  Total: {series}")
    
    series_list = conn.execute("""
        SELECT id, title, total_seasons
        FROM series
        ORDER BY id
    """).fetchall()
    
    for s in series_list:
        print(f"  • {s['id']}: {s['title']} ({s['total_seasons']} seasons)")
    print()
    
    # Check if seasons table exists
    seasons_table_exists = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='seasons'
    """).fetchone()
    
    if seasons_table_exists:
        print("📁 SEASONS:")
        print("-" * 70)
        seasons_count = conn.execute("SELECT COUNT(*) as count FROM seasons").fetchone()['count']
        print(f"  Total: {seasons_count}")
        
        seasons_by_series = conn.execute("""
            SELECT series_id, COUNT(*) as season_count
            FROM seasons
            GROUP BY series_id
            ORDER BY series_id
        """).fetchall()
        
        for s in seasons_by_series:
            series_info = conn.execute(
                "SELECT title FROM series WHERE id = ?",
                (s['series_id'],)
            ).fetchone()
            series_title = series_info['title'] if series_info else "Unknown"
            print(f"  • {s['series_id']} ({series_title}): {s['season_count']} seasons")
        print()
    else:
        print("⚠️  SEASONS table does not exist!")
        print()
    
    # Episodes
    print("🎞 EPISODES:")
    print("-" * 70)
    episodes = conn.execute("SELECT COUNT(*) as count FROM episodes").fetchone()['count']
    print(f"  Total: {episodes}")
    
    episodes_by_series = conn.execute("""
        SELECT series_id, COUNT(*) as episode_count
        FROM episodes
        GROUP BY series_id
        ORDER BY series_id
    """).fetchall()
    
    for e in episodes_by_series:
        series_info = conn.execute(
            "SELECT title FROM series WHERE id = ?",
            (e['series_id'],)
        ).fetchone()
        series_title = series_info['title'] if series_info else "Unknown"
        print(f"  • {e['series_id']} ({series_title}): {e['episode_count']} episodes")
    print()
    
    # Summary
    print("=" * 70)
    print("📊 SUMMARY:")
    print("=" * 70)
    print(f"  🎬 Movies: {movies}")
    print(f"  📺 Series: {series}")
    if seasons_table_exists:
        print(f"  📁 Seasons: {seasons_count}")
    else:
        print(f"  📁 Seasons: N/A (table not created)")
    print(f"  🎞 Episodes: {episodes}")
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    check_status()

# Made with Bob
