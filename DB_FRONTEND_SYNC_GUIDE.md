# Database-to-Frontend Synchronization Guide

## Overview

This guide explains the complete synchronization system between the PopCorn database and frontend JSON files, ensuring real-time content updates and data consistency.

## Architecture

```
┌─────────────────┐
│  Telegram Bot   │
│   (Scanner)     │
└────────┬────────┘
         │ Adds content
         ▼
┌─────────────────┐
│   Database      │
│  (popcorn.db)   │
└────────┬────────┘
         │ Sync
         ▼
┌─────────────────┐      ┌──────────────┐
│  Sync Scripts   │─────▶│ JSON Files   │
│                 │      │ (Frontend)   │
└────────┬────────┘      └──────┬───────┘
         │                      │
         │ Notifications        │ Loads
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   WebSocket     │─────▶│   Frontend   │
│   Handler       │      │   (React)    │
└─────────────────┘      └──────────────┘
```

## Components

### 1. Database Schema

The database contains the following main tables:

- **movies**: Movie metadata and file information
- **series**: TV series metadata
- **seasons**: Season information for each series
- **episodes**: Episode details with file references
- **sync_status**: Tracks last sync operation

### 2. Sync Scripts

#### `sync_db_to_frontend.py`

Main synchronization script that extracts data from database and generates JSON files.

**Features:**
- Full database extraction
- Data validation
- Atomic file writes (prevents corruption)
- Comprehensive error handling
- Progress logging
- Statistics generation

**Usage:**
```bash
# Full sync (default)
python sync_db_to_frontend.py

# Custom database path
python sync_db_to_frontend.py --db /path/to/popcorn.db

# Custom output directory
python sync_db_to_frontend.py --output /path/to/frontend/src

# Incremental sync (future feature)
python sync_db_to_frontend.py --incremental
```

**Generated Files:**
- `frontend_data.json` - Complete dataset (movies, series, episodes, stats)
- `movies_data.json` - Movies only
- `series_data.json` - Series with episodes
- `stats_data.json` - Platform statistics and top content

#### `verify_frontend_sync.py`

Verification script that compares database content with frontend JSON files.

**Features:**
- Count verification
- ID matching
- Data integrity checks
- Freshness validation
- Detailed reporting

**Usage:**
```bash
# Basic verification
python verify_frontend_sync.py

# Save report to JSON
python verify_frontend_sync.py --json-report sync_report.json

# Custom paths
python verify_frontend_sync.py --db popcorn.db --frontend frontend/src
```

**Checks Performed:**
1. ✅ Content counts match (movies, series, episodes)
2. ✅ All database IDs present in JSON
3. ✅ No orphaned IDs in JSON
4. ✅ Files are fresh (< 24 hours old)
5. ✅ Required fields present
6. ✅ Data structure valid

### 3. WebSocket Notifications

Real-time update system for connected clients.

**Notification Types:**

#### Content Updates
```json
{
  "type": "content_update",
  "content_type": "movie|series|episode",
  "action": "added|updated|deleted",
  "data": {
    "id": "mid00001",
    "title": "Movie Title",
    "poster_path": "...",
    "rating": 8.5
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Sync Complete
```json
{
  "type": "sync_complete",
  "stats": {
    "total_movies": 38,
    "total_series": 16,
    "total_episodes": 449
  },
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### Database Update
```json
{
  "type": "database_update",
  "action": "refresh_required",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## JSON File Structure

### frontend_data.json

Complete dataset with all content:

```json
{
  "last_updated": "2024-01-01T00:00:00Z",
  "stats": {
    "total_movies": 38,
    "total_series": 16,
    "total_episodes": 449,
    "total_seasons": 45,
    "total_users": 100
  },
  "movies": [
    {
      "id": "mid00001",
      "tmdb_id": 12345,
      "title": "Movie Title",
      "title_ar": "عنوان الفيلم",
      "overview": "Description...",
      "overview_ar": "الوصف...",
      "poster_path": "https://image.tmdb.org/...",
      "backdrop_path": "https://image.tmdb.org/...",
      "release_date": "2024-01-01",
      "runtime": 120,
      "genres": ["Action", "Drama"],
      "cast": [
        {
          "name": "Actor Name",
          "character": "Character Name",
          "profile": "https://..."
        }
      ],
      "director": "Director Name",
      "rating": 8.5,
      "vote_count": 1000,
      "file_id": "telegram_file_id",
      "file_size": 1234567890,
      "duration": 7200,
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "series": [
    {
      "id": "sid00001",
      "tmdb_id": 67890,
      "title": "Series Title",
      "title_ar": "عنوان المسلسل",
      "overview": "Description...",
      "poster_path": "https://...",
      "backdrop_path": "https://...",
      "first_air_date": "2024-01-01",
      "genres": ["Drama", "Thriller"],
      "cast": [...],
      "creator": "Creator Name",
      "rating": 8.0,
      "vote_count": 500,
      "total_seasons": 3,
      "total_episodes": 30,
      "status": "Returning Series",
      "seasons": [
        {
          "season_number": 1,
          "name": "Season 1",
          "episode_count": 10,
          "air_date": "2024-01-01",
          "overview": "Season description...",
          "poster_path": "https://...",
          "episodes": [
            {
              "id": 1,
              "series_id": "sid00001",
              "season_number": 1,
              "episode_number": 1,
              "title": "Episode Title",
              "overview": "Episode description...",
              "still_path": "https://...",
              "air_date": "2024-01-01",
              "runtime": 45,
              "file_id": "telegram_file_id",
              "file_size": 987654321,
              "duration": 2700,
              "created_at": "2024-01-01T00:00:00"
            }
          ]
        }
      ],
      "episodes": [...],
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "seasons": [...]
}
```

### movies_data.json

Movies only with count:

```json
{
  "movies": [...],
  "count": 38,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### series_data.json

Series only with count:

```json
{
  "series": [...],
  "count": 16,
  "last_updated": "2024-01-01T00:00:00Z"
}
```

### stats_data.json

Platform statistics and featured content:

```json
{
  "last_updated": "2024-01-01T00:00:00Z",
  "movies": 38,
  "series": 16,
  "episodes": 449,
  "seasons": 45,
  "users": 100,
  "recent_movies": [...],
  "recent_series": [...],
  "top_rated_movies": [...],
  "top_rated_series": [...]
}
```

## Automation & Integration

### 1. Automatic Sync on Content Addition

Add to your Telegram scanner or content addition code:

```python
from app.websocket_handler import notify_new_movie, notify_frontend_sync_complete
import subprocess

# After adding movie to database
await notify_new_movie(movie_data)

# Trigger sync
subprocess.run(['python', 'sync_db_to_frontend.py'])

# Notify clients
await notify_frontend_sync_complete({
    'total_movies': movie_count,
    'total_series': series_count
})
```

### 2. Scheduled Sync (Cron Job)

Add to crontab for periodic sync:

```bash
# Sync every hour
0 * * * * cd /path/to/PopCorn && python sync_db_to_frontend.py >> sync.log 2>&1

# Verify sync every 6 hours
0 */6 * * * cd /path/to/PopCorn && python verify_frontend_sync.py >> verify.log 2>&1
```

### 3. GitHub Actions (CI/CD)

```yaml
name: Sync Frontend Data

on:
  schedule:
    - cron: '0 */2 * * *'  # Every 2 hours
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Sync Data
        run: python sync_db_to_frontend.py
      - name: Verify Sync
        run: python verify_frontend_sync.py
      - name: Commit Changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add frontend/src/*.json
          git commit -m "Auto-sync frontend data" || exit 0
          git push
```

## Troubleshooting

### Issue: Sync fails with "Database not found"

**Solution:**
```bash
# Check database path
ls -la popcorn.db

# Use absolute path
python sync_db_to_frontend.py --db /full/path/to/popcorn.db
```

### Issue: JSON files are outdated

**Solution:**
```bash
# Force full sync
python sync_db_to_frontend.py

# Check sync status
python verify_frontend_sync.py
```

### Issue: Count mismatch between DB and JSON

**Solution:**
```bash
# Verify what's missing
python verify_frontend_sync.py --json-report report.json

# Check report
cat report.json

# Re-sync
python sync_db_to_frontend.py
```

### Issue: WebSocket notifications not working

**Solution:**
```python
# Check WebSocket connection
from app.websocket_handler import get_websocket_stats

stats = get_websocket_stats()
print(f"Active connections: {stats['active_connections']}")
print(f"Active rooms: {stats['active_rooms']}")
```

## Performance Optimization

### 1. Incremental Sync (Future)

For large databases, implement incremental sync:

```python
# Only sync content added/updated since last sync
python sync_db_to_frontend.py --incremental --since "2024-01-01T00:00:00Z"
```

### 2. Compression

Compress JSON files for faster loading:

```bash
# Gzip JSON files
gzip -k frontend/src/*.json

# Frontend loads .json.gz if available
```

### 3. CDN Caching

Serve JSON files from CDN with appropriate cache headers:

```
Cache-Control: public, max-age=3600
ETag: "hash-of-content"
```

## Monitoring

### Health Check Endpoint

Add to your FastAPI app:

```python
@app.get("/api/sync/status")
async def sync_status():
    """Check sync status"""
    try:
        with open('frontend/src/stats_data.json') as f:
            data = json.load(f)
        
        last_updated = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
        age_hours = (datetime.now(last_updated.tzinfo) - last_updated).total_seconds() / 3600
        
        return {
            "status": "healthy" if age_hours < 24 else "stale",
            "last_updated": data['last_updated'],
            "age_hours": age_hours,
            "stats": data
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## Best Practices

1. **Always verify after sync**: Run `verify_frontend_sync.py` after each sync
2. **Use atomic writes**: Scripts use temporary files to prevent corruption
3. **Monitor sync age**: Alert if files are > 24 hours old
4. **Log everything**: Keep sync logs for debugging
5. **Test before deploy**: Verify sync in staging environment
6. **Backup before sync**: Keep database backups
7. **Handle errors gracefully**: Scripts continue on non-critical errors
8. **Use WebSocket notifications**: Keep clients updated in real-time

## Security Considerations

1. **File Permissions**: Ensure JSON files are readable by web server
2. **Path Traversal**: Scripts validate all file paths
3. **SQL Injection**: Use parameterized queries
4. **Rate Limiting**: Limit sync frequency to prevent abuse
5. **Access Control**: Protect sync endpoints with authentication

## Future Enhancements

- [ ] Incremental sync based on timestamps
- [ ] Differential updates (only changed fields)
- [ ] Compression support (gzip, brotli)
- [ ] Multi-language support (separate JSON per language)
- [ ] Image optimization and CDN integration
- [ ] Real-time sync via database triggers
- [ ] Sync queue for high-frequency updates
- [ ] Rollback mechanism for failed syncs

## Support

For issues or questions:
- Check logs: `sync.log`, `verify.log`
- Run verification: `python verify_frontend_sync.py`
- Review this guide
- Check database integrity: `sqlite3 popcorn.db "PRAGMA integrity_check;"`

---

**Last Updated**: 2024-01-01  
**Version**: 1.0.0  
**Maintainer**: PopCorn Team