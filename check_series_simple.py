#!/usr/bin/env python3
"""Check series details in current database structure"""
import sqlite3
from pathlib import Path

DB_PATH = Path("/tmp/popcorn.db")

def check_series():
    """Check series in current structure"""
    if not DB_PATH.exists():
        print(f"❌ Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("📺 SERIES IN DATABASE")
    print("=" * 80)
    
    # Get all series
    cursor.execute("""
        SELECT 
            id,
            title,
            title_ar,
            tmdb_id,
            total_seasons,
            status,
            first_air_date,
            rating,
            created_at
        FROM series
        ORDER BY id
    """)
    
    series_list = cursor.fetchall()
    
    print(f"\nTotal Series: {len(series_list)}\n")
    
    for sid, title, title_ar, tmdb_id, total_seasons, status, first_air, rating, created in series_list:
        print(f"🎬 {title}")
        if title_ar:
            print(f"   Arabic: {title_ar}")
        print(f"   SID: {sid}")
        print(f"   TMDB ID: {tmdb_id}")
        print(f"   Total Seasons: {total_seasons}")
        print(f"   Status: {status}")
        print(f"   First Air Date: {first_air}")
        print(f"   Rating: {rating}")
        print(f"   Created: {created}")
        print()
    
    # Check all tables
    print("=" * 80)
    print("📊 ALL TABLES IN DATABASE")
    print("=" * 80)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  {table_name}: {count} rows")
    
    conn.close()

if __name__ == "__main__":
    check_series()

# Made with Bob
