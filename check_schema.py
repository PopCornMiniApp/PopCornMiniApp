#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/tmp/popcorn.db')
cursor = conn.cursor()

print('📊 Movies table columns:')
cursor.execute('PRAGMA table_info(movies)')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

print('\n📺 Series table columns:')
cursor.execute('PRAGMA table_info(series)')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

conn.close()

# Made with Bob
