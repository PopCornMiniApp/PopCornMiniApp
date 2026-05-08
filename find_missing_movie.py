#!/usr/bin/env python3
"""Find the missing movie ID between mid00001 and mid00033"""

import sqlite3
import sys

def find_missing_movie():
    try:
        conn = sqlite3.connect('/tmp/popcorn.db')
        cursor = conn.cursor()
        
        # Get all movie IDs
        cursor.execute("SELECT id FROM movies ORDER BY id")
        movies = cursor.fetchall()
        
        print(f"📊 Total movies in database: {len(movies)}")
        print(f"📋 Expected: 33 movies (mid00001 to mid00033)")
        print(f"❌ Missing: {33 - len(movies)} movie(s)\n")
        
        # Extract numeric IDs
        movie_ids = []
        for (movie_id,) in movies:
            if movie_id.startswith('mid'):
                num = int(movie_id[3:])
                movie_ids.append(num)
        
        movie_ids.sort()
        
        # Find missing IDs
        expected_ids = set(range(1, 34))  # 1 to 33
        actual_ids = set(movie_ids)
        missing_ids = expected_ids - actual_ids
        
        if missing_ids:
            print("🔍 Missing Movie IDs:")
            for mid_num in sorted(missing_ids):
                movie_id = f"mid{mid_num:05d}"
                print(f"   ❌ {movie_id}")
                
                # Check if there's any trace in the database
                cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
                result = cursor.fetchone()
                if result:
                    print(f"      Found in DB: {result}")
        else:
            print("✅ No missing IDs found!")
        
        print("\n📝 All Movie IDs in database:")
        cursor.execute("SELECT id, title, tmdb_id FROM movies ORDER BY id")
        for movie_id, title, tmdb_id in cursor.fetchall():
            print(f"   {movie_id}: {title} (TMDB: {tmdb_id})")
        
        # Check for the TMDB error we saw in logs
        print("\n🔍 Checking for TMDB ID 15344 (from error logs):")
        cursor.execute("SELECT * FROM movies WHERE tmdb_id = 15344")
        result = cursor.fetchone()
        if result:
            print(f"   Found: {result}")
        else:
            print("   ❌ Not found in database - This might be the missing movie!")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    find_missing_movie()

# Made with Bob
