#!/usr/bin/env python3
"""
Comprehensive Testing Script for PopCorn Mini App
Tests all 7 major systems and their components
"""

import sqlite3
import sys
import time
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import traceback

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_connection, init_db
from app.config import DB_PATH, HF_TOKEN, HF_DATASET_NAME, ADMIN_ID

class TestResults:
    """Store and manage test results"""
    def __init__(self):
        self.results = {
            'database': [],
            'structure': [],
            'content': [],
            'mirrors': [],
            'security': [],
            'performance': [],
            'integration': []
        }
        self.start_time = datetime.now()
        self.errors = []
        self.warnings = []
        
    def add_result(self, category: str, test_name: str, passed: bool, message: str = "", duration: float = 0):
        """Add a test result"""
        self.results[category].append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_error(self, error: str):
        """Add an error"""
        self.errors.append({
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        
    def add_warning(self, warning: str):
        """Add a warning"""
        self.warnings.append({
            'warning': warning,
            'timestamp': datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        total_tests = sum(len(tests) for tests in self.results.values())
        passed_tests = sum(
            sum(1 for test in tests if test['passed']) 
            for tests in self.results.values()
        )
        
        return {
            'total_tests': total_tests,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'errors': len(self.errors),
            'warnings': len(self.warnings)
        }

class SystemTester:
    """Main testing class"""
    
    def __init__(self):
        self.results = TestResults()
        self.conn = None
        
    def initialize(self):
        """Initialize test environment"""
        print("🔧 Initializing test environment...")
        try:
            # Initialize database
            init_db()
            
            # Connect to database
            self.conn = get_connection()
            print(f"✅ Database initialized: {DB_PATH}")
            print(f"✅ Database exists: {os.path.exists(DB_PATH)}")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize: {e}")
            self.results.add_error(f"Initialization failed: {e}")
            traceback.print_exc()
            return False
    
    def test_database_structure(self):
        """Test database structure and tables"""
        print("\n📊 Testing Database Structure...")
        category = 'structure'
        
        # Expected core tables
        expected_tables = [
            'users', 'movies', 'series', 'episodes', 'genres',
            'movie_genres', 'series_genres', 'watch_history', 'favorites',
            'ratings', 'reviews', 'playlists', 'playlist_items',
            'friends', 'friend_requests', 'messages', 'notifications',
            'watch_rooms', 'room_members', 'room_messages', 'room_invites',
            'user_preferences', 'viewing_sessions', 'content_recommendations',
            'user_achievements', 'achievement_progress', 'user_badges',
            'user_analytics', 'content_analytics', 'system_metrics',
            'error_logs', 'audit_logs', 'api_usage',
            'admin_actions', 'content_reports', 'user_reports',
            'moderation_queue', 'banned_users', 'ip_blacklist',
            'sync_status', 'mirror_groups', 'bot_configs',
            'sync_logs', 'health_checks'
        ]
        
        try:
            start = time.time()
            cursor = self.conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            # Check each expected table
            missing_tables = []
            for table in expected_tables:
                if table in existing_tables:
                    self.results.add_result(
                        category, 
                        f"Table exists: {table}", 
                        True,
                        duration=time.time() - start
                    )
                else:
                    missing_tables.append(table)
                    self.results.add_result(
                        category,
                        f"Table missing: {table}",
                        False,
                        f"Table {table} not found in database"
                    )
            
            if missing_tables:
                self.results.add_warning(f"Missing tables: {', '.join(missing_tables)}")
            
            # Check for unexpected tables
            unexpected = set(existing_tables) - set(expected_tables) - {'sqlite_sequence'}
            if unexpected:
                self.results.add_warning(f"Unexpected tables found: {', '.join(unexpected)}")
            
            print(f"✅ Found {len(existing_tables)} tables")
            print(f"   Expected: {len(expected_tables)}")
            print(f"   Missing: {len(missing_tables)}")
            if unexpected:
                print(f"   Unexpected: {len(unexpected)}")
                
        except Exception as e:
            self.results.add_result(category, "Database structure check", False, str(e))
            self.results.add_error(f"Database structure test failed: {e}")
            print(f"❌ Database structure test failed: {e}")
    
    def test_database_content(self):
        """Test database content"""
        print("\n📚 Testing Database Content...")
        category = 'content'
        
        tables_to_check = [
            ('users', 'User accounts'),
            ('movies', 'Movies'),
            ('series', 'TV Series'),
            ('episodes', 'Episodes'),
            ('genres', 'Genres'),
            ('watch_history', 'Watch history'),
            ('favorites', 'Favorites'),
        ]
        
        cursor = self.conn.cursor()
        
        for table, description in tables_to_check:
            try:
                start = time.time()
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                duration = time.time() - start
                
                self.results.add_result(
                    category,
                    f"{description} count",
                    True,
                    f"Found {count} records",
                    duration
                )
                print(f"✅ {description}: {count} records ({duration:.3f}s)")
                
            except Exception as e:
                self.results.add_result(category, f"{description} count", False, str(e))
                print(f"❌ {description} query failed: {e}")
    
    def test_database_operations(self):
        """Test CRUD operations"""
        print("\n🔄 Testing Database Operations...")
        category = 'database'
        
        cursor = self.conn.cursor()
        
        # Test SELECT operations
        queries = [
            ('Simple SELECT', 'SELECT COUNT(*) FROM movies'),
            ('JOIN query', 'SELECT m.id, m.title FROM movies m LEFT JOIN movie_genres mg ON m.id = mg.movie_id LIMIT 10'),
            ('Aggregation', 'SELECT COUNT(*) as total, AVG(vote_average) as avg_rating FROM movies'),
        ]
        
        for query_name, query in queries:
            try:
                start = time.time()
                cursor.execute(query)
                result = cursor.fetchall()
                duration = time.time() - start
                
                self.results.add_result(
                    category,
                    query_name,
                    True,
                    f"Returned {len(result)} rows",
                    duration
                )
                print(f"✅ {query_name}: {len(result)} rows ({duration:.3f}s)")
                
            except Exception as e:
                self.results.add_result(category, query_name, False, str(e))
                print(f"❌ {query_name} failed: {e}")
    
    def test_mirror_system(self):
        """Test mirror system"""
        print("\n🪞 Testing Mirror System...")
        category = 'mirrors'
        
        cursor = self.conn.cursor()
        
        try:
            # Check mirror groups table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mirror_groups'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM mirror_groups")
                count = cursor.fetchone()[0]
                
                self.results.add_result(
                    category,
                    "Mirror groups count",
                    count >= 9,
                    f"Found {count} mirror groups (expected 9)"
                )
                print(f"✅ Mirror groups: {count}")
            else:
                self.results.add_warning("mirror_groups table not found")
                print("⚠️  mirror_groups table not found")
            
            # Check bot configs table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_configs'")
            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM bot_configs")
                bot_count = cursor.fetchone()[0]
                
                self.results.add_result(
                    category,
                    "Bot configs count",
                    bot_count >= 21,
                    f"Found {bot_count} bots (expected 21)"
                )
                print(f"✅ Bot configs: {bot_count}")
            else:
                self.results.add_warning("bot_configs table not found")
                print("⚠️  bot_configs table not found")
                
        except Exception as e:
            self.results.add_result(category, "Mirror system check", False, str(e))
            print(f"❌ Mirror system test failed: {e}")
    
    def test_security_features(self):
        """Test security features"""
        print("\n🔒 Testing Security Features...")
        category = 'security'
        
        security_checks = [
            ('Admin ID configured', ADMIN_ID is not None and ADMIN_ID != ''),
            ('HF Token configured', HF_TOKEN is not None and HF_TOKEN != ''),
            ('Database path secure', DB_PATH.startswith('/tmp/') or DB_PATH.startswith('./data/')),
            ('HF Dataset configured', HF_DATASET_NAME is not None),
        ]
        
        for check_name, condition in security_checks:
            self.results.add_result(
                category,
                check_name,
                condition,
                "OK" if condition else "Failed"
            )
            
            if condition:
                print(f"✅ {check_name}")
            else:
                print(f"⚠️  {check_name}")
    
    def test_performance(self):
        """Test performance metrics"""
        print("\n⚡ Testing Performance...")
        category = 'performance'
        
        cursor = self.conn.cursor()
        
        # Test query performance
        queries = [
            ('Simple COUNT', 'SELECT COUNT(*) FROM movies'),
            ('JOIN with GROUP BY', 'SELECT g.name, COUNT(mg.movie_id) FROM genres g LEFT JOIN movie_genres mg ON g.id = mg.genre_id GROUP BY g.id LIMIT 10'),
            ('Complex aggregation', 'SELECT COUNT(*) as total, AVG(vote_average) as avg_rating, MAX(vote_count) as max_votes FROM movies WHERE vote_count > 0'),
        ]
        
        for query_name, query in queries:
            try:
                start = time.time()
                cursor.execute(query)
                cursor.fetchall()
                duration = time.time() - start
                
                # Performance threshold: should complete in less than 1 second
                passed = duration < 1.0
                
                self.results.add_result(
                    category,
                    query_name,
                    passed,
                    f"Duration: {duration:.3f}s",
                    duration
                )
                
                if passed:
                    print(f"✅ {query_name}: {duration:.3f}s")
                else:
                    print(f"⚠️  {query_name}: {duration:.3f}s (slow)")
                    
            except Exception as e:
                self.results.add_result(category, query_name, False, str(e))
                print(f"❌ {query_name} failed: {e}")
    
    def test_integration(self):
        """Test system integration"""
        print("\n🔗 Testing System Integration...")
        category = 'integration'
        
        cursor = self.conn.cursor()
        
        integration_tests = [
            ('Movies-Genres relationship', 
             'SELECT COUNT(*) FROM movies m INNER JOIN movie_genres mg ON m.id = mg.movie_id'),
            ('Series-Episodes relationship',
             'SELECT COUNT(*) FROM series s INNER JOIN episodes e ON s.id = e.series_id'),
            ('Users-Watch history relationship',
             'SELECT COUNT(*) FROM users u LEFT JOIN watch_history wh ON u.id = wh.user_id'),
        ]
        
        for test_name, query in integration_tests:
            try:
                start = time.time()
                cursor.execute(query)
                count = cursor.fetchone()[0]
                duration = time.time() - start
                
                self.results.add_result(
                    category,
                    test_name,
                    True,
                    f"Found {count} related records",
                    duration
                )
                print(f"✅ {test_name}: {count} records ({duration:.3f}s)")
                
            except Exception as e:
                self.results.add_result(category, test_name, False, str(e))
                print(f"❌ {test_name} failed: {e}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("=" * 80)
        print("🚀 PopCorn Mini App - Comprehensive Testing Suite")
        print("=" * 80)
        
        if not self.initialize():
            print("\n❌ Failed to initialize test environment")
            return False
        
        # Run all test suites
        self.test_database_structure()
        self.test_database_content()
        self.test_database_operations()
        self.test_mirror_system()
        self.test_security_features()
        self.test_performance()
        self.test_integration()
        
        # Print summary
        self.print_summary()
        
        # Save results
        self.save_results()
        
        # Close connection
        if self.conn:
            self.conn.close()
        
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        summary = self.results.get_summary()
        
        print(f"\n⏱️  Total Duration: {summary['duration']:.2f}s")
        print(f"📝 Total Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⚠️  Warnings: {summary['warnings']}")
        print(f"🔴 Errors: {summary['errors']}")
        
        # Category breakdown
        print("\n📋 Category Breakdown:")
        for category, tests in self.results.results.items():
            if tests:
                passed = sum(1 for t in tests if t['passed'])
                total = len(tests)
                print(f"   {category.capitalize()}: {passed}/{total} passed")
        
        # Show errors
        if self.results.errors:
            print("\n🔴 Errors:")
            for error in self.results.errors[:5]:  # Show first 5
                print(f"   - {error['error']}")
        
        # Show warnings
        if self.results.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.results.warnings[:5]:  # Show first 5
                print(f"   - {warning['warning']}")
        
        print("\n" + "=" * 80)
    
    def save_results(self):
        """Save test results to file"""
        try:
            results_file = Path(__file__).parent / 'test_results.json'
            
            output = {
                'summary': self.results.get_summary(),
                'results': self.results.results,
                'errors': self.results.errors,
                'warnings': self.results.warnings,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Results saved to: {results_file}")
            
        except Exception as e:
            print(f"⚠️  Failed to save results: {e}")

def main():
    """Main entry point"""
    tester = SystemTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# Made with Bob
