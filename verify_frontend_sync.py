#!/usr/bin/env python3
"""
Frontend Sync Verification Script
Compares database content with frontend JSON files to identify discrepancies
"""

import sqlite3
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FrontendSyncVerifier:
    """Verifies synchronization between database and frontend JSON files"""
    
    def __init__(self, db_path: str = 'popcorn.db', frontend_dir: str = 'frontend/src'):
        self.db_path = db_path
        self.frontend_dir = frontend_dir
        self.discrepancies = []
        self.warnings = []
        
    def connect_db(self) -> sqlite3.Connection:
        """Create database connection"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def load_json_file(self, filename: str) -> Dict[str, Any]:
        """Load and parse JSON file"""
        filepath = os.path.join(self.frontend_dir, filename)
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"JSON file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_db_counts(self, conn: sqlite3.Connection) -> Dict[str, int]:
        """Get content counts from database"""
        cursor = conn.cursor()
        
        counts = {}
        
        # Movies with files
        cursor.execute("SELECT COUNT(*) as count FROM movies WHERE file_id IS NOT NULL")
        counts['movies'] = cursor.fetchone()['count']
        
        # Series
        cursor.execute("SELECT COUNT(*) as count FROM series")
        counts['series'] = cursor.fetchone()['count']
        
        # Episodes
        cursor.execute("SELECT COUNT(*) as count FROM episodes")
        counts['episodes'] = cursor.fetchone()['count']
        
        # Seasons
        cursor.execute("SELECT COUNT(*) as count FROM seasons")
        counts['seasons'] = cursor.fetchone()['count']
        
        return counts
    
    def get_db_movie_ids(self, conn: sqlite3.Connection) -> set:
        """Get all movie IDs from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM movies WHERE file_id IS NOT NULL")
        return {row['id'] for row in cursor.fetchall()}
    
    def get_db_series_ids(self, conn: sqlite3.Connection) -> set:
        """Get all series IDs from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM series")
        return {row['id'] for row in cursor.fetchall()}
    
    def get_db_episode_ids(self, conn: sqlite3.Connection) -> set:
        """Get all episode IDs from database"""
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM episodes")
        return {row['id'] for row in cursor.fetchall()}
    
    def verify_counts(self, db_counts: Dict[str, int], json_data: Dict[str, Any]) -> bool:
        """Verify content counts match"""
        logger.info("\n📊 Verifying Content Counts...")
        
        all_match = True
        
        # Check movies
        json_movie_count = len(json_data.get('movies', []))
        if db_counts['movies'] != json_movie_count:
            self.discrepancies.append(
                f"Movie count mismatch: DB={db_counts['movies']}, JSON={json_movie_count}"
            )
            logger.error(f"   ❌ Movies: DB={db_counts['movies']}, JSON={json_movie_count}")
            all_match = False
        else:
            logger.info(f"   ✅ Movies: {db_counts['movies']}")
        
        # Check series
        json_series_count = len(json_data.get('series', []))
        if db_counts['series'] != json_series_count:
            self.discrepancies.append(
                f"Series count mismatch: DB={db_counts['series']}, JSON={json_series_count}"
            )
            logger.error(f"   ❌ Series: DB={db_counts['series']}, JSON={json_series_count}")
            all_match = False
        else:
            logger.info(f"   ✅ Series: {db_counts['series']}")
        
        # Check episodes (from series data)
        json_episode_count = sum(len(s.get('episodes', [])) for s in json_data.get('series', []))
        if db_counts['episodes'] != json_episode_count:
            self.discrepancies.append(
                f"Episode count mismatch: DB={db_counts['episodes']}, JSON={json_episode_count}"
            )
            logger.error(f"   ❌ Episodes: DB={db_counts['episodes']}, JSON={json_episode_count}")
            all_match = False
        else:
            logger.info(f"   ✅ Episodes: {db_counts['episodes']}")
        
        return all_match
    
    def verify_movie_ids(self, conn: sqlite3.Connection, json_data: Dict[str, Any]) -> bool:
        """Verify all movie IDs are present"""
        logger.info("\n🎬 Verifying Movie IDs...")
        
        db_ids = self.get_db_movie_ids(conn)
        json_ids = {movie['id'] for movie in json_data.get('movies', [])}
        
        missing_in_json = db_ids - json_ids
        extra_in_json = json_ids - db_ids
        
        all_match = True
        
        if missing_in_json:
            self.discrepancies.append(
                f"Missing {len(missing_in_json)} movies in JSON: {list(missing_in_json)[:5]}"
            )
            logger.error(f"   ❌ Missing {len(missing_in_json)} movies in JSON")
            logger.error(f"      Examples: {list(missing_in_json)[:5]}")
            all_match = False
        
        if extra_in_json:
            self.warnings.append(
                f"Extra {len(extra_in_json)} movies in JSON (not in DB): {list(extra_in_json)[:5]}"
            )
            logger.warning(f"   ⚠️  Extra {len(extra_in_json)} movies in JSON")
            logger.warning(f"      Examples: {list(extra_in_json)[:5]}")
        
        if all_match and not extra_in_json:
            logger.info(f"   ✅ All {len(db_ids)} movie IDs match")
        
        return all_match
    
    def verify_series_ids(self, conn: sqlite3.Connection, json_data: Dict[str, Any]) -> bool:
        """Verify all series IDs are present"""
        logger.info("\n📺 Verifying Series IDs...")
        
        db_ids = self.get_db_series_ids(conn)
        json_ids = {series['id'] for series in json_data.get('series', [])}
        
        missing_in_json = db_ids - json_ids
        extra_in_json = json_ids - db_ids
        
        all_match = True
        
        if missing_in_json:
            self.discrepancies.append(
                f"Missing {len(missing_in_json)} series in JSON: {list(missing_in_json)[:5]}"
            )
            logger.error(f"   ❌ Missing {len(missing_in_json)} series in JSON")
            logger.error(f"      Examples: {list(missing_in_json)[:5]}")
            all_match = False
        
        if extra_in_json:
            self.warnings.append(
                f"Extra {len(extra_in_json)} series in JSON (not in DB): {list(extra_in_json)[:5]}"
            )
            logger.warning(f"   ⚠️  Extra {len(extra_in_json)} series in JSON")
            logger.warning(f"      Examples: {list(extra_in_json)[:5]}")
        
        if all_match and not extra_in_json:
            logger.info(f"   ✅ All {len(db_ids)} series IDs match")
        
        return all_match
    
    def verify_file_freshness(self, json_data: Dict[str, Any]) -> bool:
        """Check if JSON files are recent"""
        logger.info("\n🕐 Verifying File Freshness...")
        
        last_updated = json_data.get('last_updated')
        if not last_updated:
            self.warnings.append("No last_updated timestamp in JSON")
            logger.warning("   ⚠️  No last_updated timestamp found")
            return False
        
        try:
            updated_time = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
            now = datetime.now(updated_time.tzinfo)
            age_hours = (now - updated_time).total_seconds() / 3600
            
            if age_hours > 24:
                self.warnings.append(f"JSON files are {age_hours:.1f} hours old")
                logger.warning(f"   ⚠️  Files are {age_hours:.1f} hours old (last updated: {last_updated})")
                return False
            else:
                logger.info(f"   ✅ Files are fresh ({age_hours:.1f} hours old)")
                return True
        except Exception as e:
            self.warnings.append(f"Could not parse timestamp: {e}")
            logger.warning(f"   ⚠️  Could not parse timestamp: {e}")
            return False
    
    def verify_data_integrity(self, json_data: Dict[str, Any]) -> bool:
        """Verify data structure and required fields"""
        logger.info("\n🔍 Verifying Data Integrity...")
        
        all_valid = True
        
        # Check movies have required fields
        movies = json_data.get('movies', [])
        for i, movie in enumerate(movies[:10]):  # Check first 10
            required_fields = ['id', 'title', 'file_id']
            missing = [f for f in required_fields if not movie.get(f)]
            if missing:
                self.discrepancies.append(
                    f"Movie {movie.get('id', i)} missing fields: {missing}"
                )
                logger.error(f"   ❌ Movie {movie.get('id', i)} missing: {missing}")
                all_valid = False
        
        # Check series have required fields
        series = json_data.get('series', [])
        for i, s in enumerate(series[:10]):  # Check first 10
            required_fields = ['id', 'title', 'episodes']
            missing = [f for f in required_fields if f not in s]
            if missing:
                self.discrepancies.append(
                    f"Series {s.get('id', i)} missing fields: {missing}"
                )
                logger.error(f"   ❌ Series {s.get('id', i)} missing: {missing}")
                all_valid = False
        
        if all_valid:
            logger.info("   ✅ Data structure is valid")
        
        return all_valid
    
    def verify(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform complete verification
        
        Returns:
            Tuple of (success, report_dict)
        """
        logger.info("=" * 70)
        logger.info("🔍 Starting Frontend Sync Verification")
        logger.info("=" * 70)
        
        try:
            # Connect to database
            conn = self.connect_db()
            logger.info(f"✅ Connected to database: {self.db_path}")
            
            # Load JSON data
            json_data = self.load_json_file('frontend_data.json')
            logger.info(f"✅ Loaded frontend_data.json")
            
            # Get database counts
            db_counts = self.get_db_counts(conn)
            
            # Run verifications
            counts_match = self.verify_counts(db_counts, json_data)
            movies_match = self.verify_movie_ids(conn, json_data)
            series_match = self.verify_series_ids(conn, json_data)
            fresh = self.verify_file_freshness(json_data)
            valid = self.verify_data_integrity(json_data)
            
            # Close connection
            conn.close()
            
            # Determine overall status
            all_passed = counts_match and movies_match and series_match and valid
            
            # Generate report
            report = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'database': self.db_path,
                'frontend_dir': self.frontend_dir,
                'status': 'PASSED' if all_passed else 'FAILED',
                'checks': {
                    'counts_match': counts_match,
                    'movie_ids_match': movies_match,
                    'series_ids_match': series_match,
                    'files_fresh': fresh,
                    'data_valid': valid
                },
                'database_counts': db_counts,
                'json_counts': {
                    'movies': len(json_data.get('movies', [])),
                    'series': len(json_data.get('series', [])),
                    'episodes': sum(len(s.get('episodes', [])) for s in json_data.get('series', []))
                },
                'discrepancies': self.discrepancies,
                'warnings': self.warnings
            }
            
            # Print summary
            logger.info("\n" + "=" * 70)
            if all_passed:
                logger.info("✅ VERIFICATION PASSED - Database and Frontend are in sync!")
            else:
                logger.error("❌ VERIFICATION FAILED - Discrepancies found!")
            logger.info("=" * 70)
            
            if self.discrepancies:
                logger.error(f"\n❌ Discrepancies ({len(self.discrepancies)}):")
                for disc in self.discrepancies:
                    logger.error(f"   - {disc}")
            
            if self.warnings:
                logger.warning(f"\n⚠️  Warnings ({len(self.warnings)}):")
                for warn in self.warnings:
                    logger.warning(f"   - {warn}")
            
            if not all_passed:
                logger.info("\n💡 Recommendations:")
                logger.info("   1. Run: python sync_db_to_frontend.py")
                logger.info("   2. Check database for missing content")
                logger.info("   3. Verify Telegram sync is working")
            
            return all_passed, report
            
        except FileNotFoundError as e:
            logger.error(f"❌ {e}")
            return False, {'error': str(e)}
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False, {'error': str(e)}


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Verify frontend sync status'
    )
    parser.add_argument(
        '--db',
        default='popcorn.db',
        help='Path to database file (default: popcorn.db)'
    )
    parser.add_argument(
        '--frontend',
        default='frontend/src',
        help='Frontend directory (default: frontend/src)'
    )
    parser.add_argument(
        '--json-report',
        help='Save report to JSON file'
    )
    
    args = parser.parse_args()
    
    # Create verifier and run
    verifier = FrontendSyncVerifier(
        db_path=args.db,
        frontend_dir=args.frontend
    )
    
    success, report = verifier.verify()
    
    # Save JSON report if requested
    if args.json_report:
        with open(args.json_report, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"\n📄 Report saved to: {args.json_report}")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()

# Made with Bob
