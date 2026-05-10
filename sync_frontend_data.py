#!/usr/bin/env python3
"""
Sync Frontend Data from Database
Creates JSON files for frontend consumption
"""

import sqlite3
import json
from datetime import datetime
import os

def export_to_json():
    """Export database content to JSON for frontend"""
    
    db_path = 'popcorn.db'
    if not os.path.exists(db_path):
        print('❌ Database not found')
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print('📊 Exporting Database to JSON for Frontend')
    print('='*60)
    
    # Export Movies
    print('\n🎬 Exporting Movies...')
    cursor.execute('''
        SELECT id, tmdb_id, title, title_ar, overview, overview_ar,
               poster_path, backdrop_path, release_date, runtime,
               genres, "cast", director, rating, vote_count,
               file_id, file_size, duration, created_at, updated_at
        FROM movies
        ORDER BY created_at DESC
    ''')
    movies = [dict(row) for row in cursor.fetchall()]
    print(f'   ✅ {len(movies)} movies exported')
    
    # Export Series
    print('\n📺 Exporting Series...')
    cursor.execute('''
        SELECT id, tmdb_id, title, title_ar, overview, overview_ar,
               poster_path, backdrop_path, first_air_date, genres,
               "cast", creator, rating, vote_count, total_seasons,
               status, created_at, updated_at
        FROM series
        ORDER BY created_at DESC
    ''')
    series = [dict(row) for row in cursor.fetchall()]
    print(f'   ✅ {len(series)} series exported')
    
    # Export Episodes with season info
    print('\n🎞 Exporting Episodes...')
    cursor.execute('''
        SELECT e.id, e.series_id, e.season_number, e.episode_number,
               e.title, e.overview, e.still_path, e.air_date, e.runtime,
               e.file_id, e.file_size, e.duration, e.created_at,
               s.title as series_title
        FROM episodes e
        JOIN series s ON e.series_id = s.id
        ORDER BY e.series_id, e.season_number, e.episode_number
    ''')
    episodes = [dict(row) for row in cursor.fetchall()]
    print(f'   ✅ {len(episodes)} episodes exported')
    
    # Group episodes by series
    series_episodes = {}
    for episode in episodes:
        series_id = episode['series_id']
        if series_id not in series_episodes:
            series_episodes[series_id] = []
        series_episodes[series_id].append(episode)
    
    # Add episodes to series
    for s in series:
        s['episodes'] = series_episodes.get(s['id'], [])
    
    # Export Seasons
    print('\n📅 Exporting Seasons...')
    cursor.execute('''
        SELECT series_id, season_number, topic_id, name, episode_count,
               air_date, overview, poster_path, created_at
        FROM seasons
        ORDER BY series_id, season_number
    ''')
    seasons = [dict(row) for row in cursor.fetchall()]
    print(f'   ✅ {len(seasons)} seasons exported')
    
    conn.close()
    
    # Create frontend data structure
    frontend_data = {
        'last_updated': datetime.now().isoformat(),
        'stats': {
            'total_movies': len(movies),
            'total_series': len(series),
            'total_episodes': len(episodes),
            'total_seasons': len(seasons)
        },
        'movies': movies,
        'series': series,
        'seasons': seasons
    }
    
    # Save to JSON files
    print('\n💾 Saving JSON files...')
    
    # Full data
    with open('frontend_data.json', 'w', encoding='utf-8') as f:
        json.dump(frontend_data, f, ensure_ascii=False, indent=2)
    print('   ✅ frontend_data.json')
    
    # Movies only
    with open('movies_data.json', 'w', encoding='utf-8') as f:
        json.dump({'movies': movies, 'count': len(movies)}, f, ensure_ascii=False, indent=2)
    print('   ✅ movies_data.json')
    
    # Series only
    with open('series_data.json', 'w', encoding='utf-8') as f:
        json.dump({'series': series, 'count': len(series)}, f, ensure_ascii=False, indent=2)
    print('   ✅ series_data.json')
    
    # Stats only
    stats_data = {
        'last_updated': datetime.now().isoformat(),
        'movies': len(movies),
        'series': len(series),
        'episodes': len(episodes),
        'seasons': len(seasons),
        'recent_movies': movies[:5],
        'recent_series': series[:5]
    }
    with open('stats_data.json', 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
    print('   ✅ stats_data.json')
    
    print('\n' + '='*60)
    print('✅ Frontend Data Export Complete!')
    print('='*60)
    print(f'\n📊 Summary:')
    print(f'   🎬 Movies: {len(movies)}')
    print(f'   📺 Series: {len(series)}')
    print(f'   🎞 Episodes: {len(episodes)}')
    print(f'   📅 Seasons: {len(seasons)}')
    print(f'\n📁 Files Created:')
    print(f'   - frontend_data.json (complete)')
    print(f'   - movies_data.json')
    print(f'   - series_data.json')
    print(f'   - stats_data.json')
    
    return frontend_data

if __name__ == '__main__':
    export_to_json()

# Made with Bob
