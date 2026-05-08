#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/tmp/popcorn.db')
cursor = conn.cursor()

# Count movies
cursor.execute('SELECT COUNT(*) FROM movies')
movie_count = cursor.fetchone()[0]
print(f'📊 Movies count: {movie_count}')

# Count series
cursor.execute('SELECT COUNT(*) FROM series')
series_count = cursor.fetchone()[0]
print(f'📺 Series count: {series_count}')

# Last 15 movies
print('\n🎬 Last 15 movies:')
cursor.execute('SELECT id, title, release_date FROM movies ORDER BY id DESC LIMIT 15')
for row in cursor.fetchall():
    year = row[2][:4] if row[2] else 'N/A'
    print(f'  {row[0]}: {row[1]} ({year})')

# Last 5 series
print('\n📺 Last 5 series:')
cursor.execute('SELECT id, title, first_air_date FROM series ORDER BY id DESC LIMIT 5')
for row in cursor.fetchall():
    year = row[2][:4] if row[2] else 'N/A'
    print(f'  {row[0]}: {row[1]} ({year})')

conn.close()

# Made with Bob
