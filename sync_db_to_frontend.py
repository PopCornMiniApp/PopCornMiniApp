#!/usr/bin/env python3
"""
Comprehensive Database-to-Frontend Synchronization Script
Extracts all content from database and generates optimized JSON files for frontend
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseToFrontendSync:
    """Handles synchronization from database to frontend JSON files"""
    
    def __init__(self, db_path: str = 'popcorn.db', output_dir: str = 'frontend/src'):
        self.db_path = db_path
        self.output_dir = output_dir
        self.stats = {
            'movies': 0,
            'series': 0,
            'episodes': 0,
            'seasons': 0,
            'errors': []
        }
        
    def connect_db(self) -> sqlite3.Connection:
        """Create database connection with row factory"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def extract_movies(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Extract all movies with complete metadata"""
        logger.info("📽️  Extracting movies from database...")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id, tmdb_id, title, title_ar, overview, overview_ar,
                poster_path, backdrop_path, release_date, runtime,
                genres, cast, director, rating, vote_count,
                file_id, file_size, duration, 
                created_at, updated_at
            FROM movies
            WHERE file_id IS NOT NULL
            ORDER BY created_at DESC
        """)
        
        movies = []
        for row in cursor.fetchall():
            movie = dict(row)
            
            # Parse JSON fields
            if movie['genres']:
                try:
                    movie['genres'] = json.loads(movie['genres']) if isinstance(movie['genres'], str) else movie['genres']
                except json.JSONDecodeError:
                    movie['genres'] = []
            
            if movie['cast']:
                try:
                    movie['cast'] = json.loads(movie['cast']) if isinstance(movie['cast'], str) else movie['cast']
                except json.JSONDecodeError:
                    movie['cast'] = []
            
            movies.append(movie)
        
        self.stats['movies'] = len(movies)
        logger.info(f"   ✅ Extracted {len(movies)} movies")
        return movies
    
    def extract_series_with_episodes(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Extract all series with their seasons and episodes"""
        logger.info("📺 Extracting series from database...")
        
        cursor = conn.cursor()
        
        # Get all series
        cursor.execute("""
            SELECT 
                id, tmdb_id, title, title_ar, overview, overview_ar,
                poster_path, backdrop_path, first_air_date, genres,
                cast, creator, rating, vote_count, total_seasons,
                status, created_at, updated_at
            FROM series
            ORDER BY created_at DESC
        """)
        
        series_list = []
        for row in cursor.fetchall():
            series = dict(row)
            series_id = series['id']
            
            # Parse JSON fields
            if series['genres']:
                try:
                    series['genres'] = json.loads(series['genres']) if isinstance(series['genres'], str) else series['genres']
                except json.JSONDecodeError:
                    series['genres'] = []
            
            if series['cast']:
                try:
                    series['cast'] = json.loads(series['cast']) if isinstance(series['cast'], str) else series['cast']
                except json.JSONDecodeError:
                    series['cast'] = []
            
            # Get seasons for this series
            cursor.execute("""
                SELECT 
                    season_number, topic_id, name, episode_count,
                    air_date, overview, poster_path, created_at
                FROM seasons
                WHERE series_id = ?
                ORDER BY season_number
            """, (series_id,))
            
            seasons = [dict(season_row) for season_row in cursor.fetchall()]
            
            # Get episodes for this series
            cursor.execute("""
                SELECT 
                    id, series_id, season_number, episode_number,
                    title, overview, still_path, air_date, runtime,
                    file_id, file_size, duration, created_at
                FROM episodes
                WHERE series_id = ?
                ORDER BY season_number, episode_number
            """, (series_id,))
            
            episodes = [dict(ep_row) for ep_row in cursor.fetchall()]
            
            # Organize episodes by season
            seasons_with_episodes = []
            for season in seasons:
                season_num = season['season_number']
                season_episodes = [ep for ep in episodes if ep['season_number'] == season_num]
                
                season_data = {
                    'season_number': season_num,
                    'name': season['name'],
                    'episode_count': len(season_episodes),
                    'air_date': season['air_date'],
                    'overview': season['overview'],
                    'poster_path': season['poster_path'],
                    'episodes': season_episodes
                }
                seasons_with_episodes.append(season_data)
            
            series['seasons'] = seasons_with_episodes
            series['episodes'] = episodes  # Keep flat list for backward compatibility
            series['total_episodes'] = len(episodes)
            
            series_list.append(series)
            self.stats['episodes'] += len(episodes)
        
        self.stats['series'] = len(series_list)
        self.stats['seasons'] = sum(len(s['seasons']) for s in series_list)
        
        logger.info(f"   ✅ Extracted {len(series_list)} series with {self.stats['episodes']} episodes")
        return series_list
    
    def extract_seasons(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        """Extract all seasons (for backward compatibility)"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                series_id, season_number, topic_id, name, episode_count,
                air_date, overview, poster_path, created_at
            FROM seasons
            ORDER BY series_id, season_number
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_user_stats(self, conn: sqlite3.Connection) -> Dict[str, int]:
        """Get user statistics (if user tracking is enabled)"""
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM user_profiles")
            user_count = cursor.fetchone()['count']
        except sqlite3.OperationalError:
            user_count = 0
        
        return {'total_users': user_count}
    
    def get_content_mirrors(self, conn: sqlite3.Connection) -> Dict[str, List[Dict]]:
        """Get mirror information for content"""
        cursor = conn.cursor()
        mirrors = {'movies': {}, 'episodes': {}}
        
        try:
            # Check if content_mirrors table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='content_mirrors'
            """)
            
            if cursor.fetchone():
                cursor.execute("""
                    SELECT content_type, content_id, mirror_url, quality, size
                    FROM content_mirrors
                    WHERE active = 1
                """)
                
                for row in cursor.fetchall():
                    content_type = row['content_type']
                    content_id = row['content_id']
                    
                    if content_type not in mirrors:
                        mirrors[content_type] = {}
                    
                    if content_id not in mirrors[content_type]:
                        mirrors[content_type][content_id] = []
                    
                    mirrors[content_type][content_id].append({
                        'url': row['mirror_url'],
                        'quality': row['quality'],
                        'size': row['size']
                    })
        except sqlite3.OperationalError:
            logger.warning("⚠️  content_mirrors table not found, skipping mirror data")
        
        return mirrors
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate extracted data before writing"""
        required_keys = ['movies', 'series', 'stats', 'last_updated']
        
        for key in required_keys:
            if key not in data:
                logger.error(f"❌ Missing required key: {key}")
                return False
        
        if not isinstance(data['movies'], list):
            logger.error("❌ Movies must be a list")
            return False
        
        if not isinstance(data['series'], list):
            logger.error("❌ Series must be a list")
            return False
        
        logger.info("✅ Data validation passed")
        return True
    
    def write_json_file(self, filename: str, data: Any, indent: int = 2) -> bool:
        """Write data to JSON file with error handling"""
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.output_dir, exist_ok=True)
            
            # Write to temporary file first
            temp_filepath = filepath + '.tmp'
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            # Rename to final file (atomic operation)
            os.replace(temp_filepath, filepath)
            
            file_size = os.path.getsize(filepath)
            logger.info(f"   ✅ {filename} ({file_size:,} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error writing {filename}: {e}")
            self.stats['errors'].append(f"Failed to write {filename}: {str(e)}")
            return False
    
    def sync(self, full_sync: bool = True) -> bool:
        """
        Perform full synchronization from database to frontend
        
        Args:
            full_sync: If True, regenerate all files. If False, incremental update.
        
        Returns:
            True if sync successful, False otherwise
        """
        logger.info("=" * 70)
        logger.info("🔄 Starting Database-to-Frontend Synchronization")
        logger.info("=" * 70)
        
        try:
            # Connect to database
            conn = self.connect_db()
            logger.info(f"✅ Connected to database: {self.db_path}")
            
            # Extract data
            movies = self.extract_movies(conn)
            series = self.extract_series_with_episodes(conn)
            seasons = self.extract_seasons(conn)
            user_stats = self.get_user_stats(conn)
            mirrors = self.get_content_mirrors(conn)
            
            # Close connection
            conn.close()
            
            # Prepare complete dataset
            timestamp = datetime.utcnow().isoformat() + 'Z'
            
            complete_data = {
                'last_updated': timestamp,
                'stats': {
                    'total_movies': self.stats['movies'],
                    'total_series': self.stats['series'],
                    'total_episodes': self.stats['episodes'],
                    'total_seasons': self.stats['seasons'],
                    'total_users': user_stats['total_users']
                },
                'movies': movies,
                'series': series,
                'seasons': seasons
            }
            
            # Validate data
            if not self.validate_data(complete_data):
                logger.error("❌ Data validation failed")
                return False
            
            # Write JSON files
            logger.info("\n💾 Writing JSON files...")
            
            success = True
            
            # 1. Complete frontend data
            success &= self.write_json_file('frontend_data.json', complete_data)
            
            # 2. Movies only
            movies_data = {
                'movies': movies,
                'count': len(movies),
                'last_updated': timestamp
            }
            success &= self.write_json_file('movies_data.json', movies_data)
            
            # 3. Series only
            series_data = {
                'series': series,
                'count': len(series),
                'last_updated': timestamp
            }
            success &= self.write_json_file('series_data.json', series_data)
            
            # 4. Stats only
            stats_data = {
                'last_updated': timestamp,
                'movies': self.stats['movies'],
                'series': self.stats['series'],
                'episodes': self.stats['episodes'],
                'seasons': self.stats['seasons'],
                'users': user_stats['total_users'],
                'recent_movies': movies[:10] if movies else [],
                'recent_series': series[:10] if series else [],
                'top_rated_movies': sorted(movies, key=lambda x: x.get('rating', 0), reverse=True)[:10],
                'top_rated_series': sorted(series, key=lambda x: x.get('rating', 0), reverse=True)[:10]
            }
            success &= self.write_json_file('stats_data.json', stats_data)
            
            # Print summary
            logger.info("\n" + "=" * 70)
            logger.info("✅ Synchronization Complete!")
            logger.info("=" * 70)
            logger.info(f"\n📊 Summary:")
            logger.info(f"   🎬 Movies: {self.stats['movies']}")
            logger.info(f"   📺 Series: {self.stats['series']}")
            logger.info(f"   🎞️  Episodes: {self.stats['episodes']}")
            logger.info(f"   📅 Seasons: {self.stats['seasons']}")
            logger.info(f"   👥 Users: {user_stats['total_users']}")
            
            logger.info(f"\n📁 Files Generated:")
            logger.info(f"   - frontend_data.json (complete dataset)")
            logger.info(f"   - movies_data.json ({len(movies)} movies)")
            logger.info(f"   - series_data.json ({len(series)} series)")
            logger.info(f"   - stats_data.json (statistics)")
            
            if self.stats['errors']:
                logger.warning(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
                for error in self.stats['errors']:
                    logger.warning(f"   - {error}")
            
            return success
            
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return False
        except sqlite3.Error as e:
            logger.error(f"❌ Database error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Sync database content to frontend JSON files'
    )
    parser.add_argument(
        '--db',
        default='popcorn.db',
        help='Path to database file (default: popcorn.db)'
    )
    parser.add_argument(
        '--output',
        default='frontend/src',
        help='Output directory for JSON files (default: frontend/src)'
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Perform incremental sync (default: full sync)'
    )
    
    args = parser.parse_args()
    
    # Create syncer and run
    syncer = DatabaseToFrontendSync(
        db_path=args.db,
        output_dir=args.output
    )
    
    success = syncer.sync(full_sync=not args.incremental)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
