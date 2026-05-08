#!/usr/bin/env python3
"""
Monitor smart sync progress and report final results
"""
import sqlite3
import time
import requests
from datetime import datetime

def check_status():
    """Check current database and API status"""
    # Database check
    conn = sqlite3.connect('/tmp/popcorn.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM movies')
    movie_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM series')
    series_count = cursor.fetchone()[0]
    
    conn.close()
    
    # API check
    try:
        response = requests.get('http://localhost:8000/api/movies', timeout=5)
        api_data = response.json()
        api_movies = api_data.get('total', 0)
    except:
        api_movies = 'N/A'
    
    return movie_count, series_count, api_movies

def main():
    print("🔍 PopCorn Sync Monitor")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    initial_movies, initial_series, initial_api = check_status()
    print(f"📊 Initial Status:")
    print(f"   Movies in DB: {initial_movies}")
    print(f"   Series in DB: {initial_series}")
    print(f"   Movies via API: {initial_api}")
    print()
    
    print("⏳ Monitoring for changes (checking every 30 seconds)...")
    print("   Press Ctrl+C to stop")
    print()
    
    last_movies = initial_movies
    last_series = initial_series
    check_count = 0
    
    try:
        while True:
            time.sleep(30)
            check_count += 1
            
            current_movies, current_series, current_api = check_status()
            
            if current_movies != last_movies or current_series != last_series:
                print(f"✨ Change detected at {datetime.now().strftime('%H:%M:%S')}:")
                print(f"   Movies: {last_movies} → {current_movies} (+{current_movies - last_movies})")
                print(f"   Series: {last_series} → {current_series} (+{current_series - last_series})")
                print(f"   API: {current_api}")
                print()
                
                last_movies = current_movies
                last_series = current_series
            else:
                print(f"⏱️  Check #{check_count}: No changes (Movies: {current_movies}, Series: {current_series})")
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("📊 Final Status Report")
        print("=" * 60)
        
        final_movies, final_series, final_api = check_status()
        
        print(f"\n🎬 Movies:")
        print(f"   Initial: {initial_movies}")
        print(f"   Final: {final_movies}")
        print(f"   Change: +{final_movies - initial_movies}")
        
        print(f"\n📺 Series:")
        print(f"   Initial: {initial_series}")
        print(f"   Final: {final_series}")
        print(f"   Change: +{final_series - initial_series}")
        
        print(f"\n🌐 API Status: {final_api} movies")
        print(f"\n✅ Monitoring stopped at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()

# Made with Bob
