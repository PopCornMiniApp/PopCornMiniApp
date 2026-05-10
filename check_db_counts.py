#!/usr/bin/env python3
"""Quick database count check"""
import sqlite3

DB_PATH = "/tmp/popcorn.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 60)
print("💾 DATABASE COUNTS")
print("=" * 60)

movies = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
series = cursor.execute("SELECT COUNT(*) FROM series").fetchone()[0]
episodes = cursor.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]

print(f"🎬 Movies: {movies}")
print(f"📺 Series: {series}")
print(f"🎞 Episodes: {episodes}")
print()

# List all movies
print("=" * 60)
print("🎬 ALL MOVIES IN DATABASE")
print("=" * 60)
movies_list = cursor.execute("SELECT id, title FROM movies ORDER BY id").fetchall()
for movie_id, title in movies_list:
    print(f"  {movie_id}: {title}")

print()
print("=" * 60)
print("📺 ALL SERIES IN DATABASE")
print("=" * 60)
series_list = cursor.execute("SELECT id, title FROM series ORDER BY id").fetchall()
for series_id, title in series_list:
    print(f"  {series_id}: {title}")

conn.close()

# Made with Bob
