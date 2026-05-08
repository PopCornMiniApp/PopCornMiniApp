#!/usr/bin/env python3
import sqlite3
import json

DB_PATH = "/tmp/popcorn.db"

print("🔍 Checking Series Database\n")

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check series count
    cursor.execute("SELECT COUNT(*) FROM series")
    series_count = cursor.fetchone()[0]
    print(f"1. Total Series: {series_count}")
    
    if series_count > 0:
        # Get first few series
        cursor.execute("SELECT id, title, total_seasons FROM series LIMIT 5")
        series = cursor.fetchall()
        print("\n2. Sample Series:")
        for series_id, title, seasons in series:
            print(f"   - {series_id}: {title} ({seasons} seasons)")
        
        # Check seasons count
        cursor.execute("SELECT COUNT(*) FROM seasons")
        seasons_count = cursor.fetchone()[0]
        print(f"\n3. Total Seasons: {seasons_count}")
        
        # Check episodes count
        cursor.execute("SELECT COUNT(*) FROM episodes")
        episodes_count = cursor.fetchone()[0]
        print(f"\n4. Total Episodes: {episodes_count}")
        
        # Get detailed info for first series
        first_id = series[0][0]
        print(f"\n5. Detailed info for {first_id}:")
        
        cursor.execute("SELECT * FROM series WHERE id = ?", (first_id,))
        series_info = cursor.fetchone()
        print(f"   Title: {series_info[2]}")
        print(f"   Overview: {series_info[4][:100] if series_info[4] else 'N/A'}...")
        print(f"   Total Seasons: {series_info[14]}")
        
        # Get seasons for this series
        cursor.execute("SELECT season_number, episode_count FROM seasons WHERE series_id = ? ORDER BY season_number", (first_id,))
        seasons_info = cursor.fetchall()
        print(f"\n6. Seasons for {first_id}:")
        for season_num, ep_count in seasons_info:
            print(f"   - Season {season_num}: {ep_count} episodes")
        
        # Get episodes for first season
        if seasons_info:
            first_season = seasons_info[0][0]
            cursor.execute("SELECT episode_number, title FROM episodes WHERE series_id = ? AND season_number = ? ORDER BY episode_number LIMIT 5", (first_id, first_season))
            episodes_info = cursor.fetchall()
            print(f"\n7. Sample Episodes from Season {first_season}:")
            for ep_num, ep_title in episodes_info:
                print(f"   - Episode {ep_num}: {ep_title}")
    else:
        print("\n⚠️ No series found in database!")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Made with Bob
