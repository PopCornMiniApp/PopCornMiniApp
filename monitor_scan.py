#!/usr/bin/env python3
"""
Monitor Full Scan Progress
Checks database counts periodically
"""
import sqlite3
import time
from datetime import datetime

DB_PATH = "/tmp/popcorn.db"

def get_counts():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    movies = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    series = cursor.execute("SELECT COUNT(*) FROM series").fetchone()[0]
    
    try:
        seasons = cursor.execute("SELECT COUNT(*) FROM seasons").fetchone()[0]
    except:
        seasons = 0
    
    episodes = cursor.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    
    conn.close()
    return movies, series, seasons, episodes

def main():
    print("🔍 Monitoring Full Scan Progress\n")
    print("Press Ctrl+C to stop\n")
    
    prev_counts = None
    
    while True:
        try:
            counts = get_counts()
            movies, series, seasons, episodes = counts
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 🎬 {movies} movies | 📺 {series} series | 📁 {seasons} seasons | 🎞 {episodes} episodes")
            
            if prev_counts and counts != prev_counts:
                print("           ⬆️  Changes detected!")
            
            if series >= 9 and seasons >= 25:
                print("\n✅ Target reached! All series registered.")
                break
            
            prev_counts = counts
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n\n⏸️  Monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()

# Made with Bob
