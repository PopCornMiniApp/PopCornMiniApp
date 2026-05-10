import sqlite3
import os
import logging
import threading
from contextlib import contextmanager
from typing import Optional
from huggingface_hub import HfApi, hf_hub_download
from app.config import HF_TOKEN, HF_DATASET_NAME, DB_PATH, DATASET_DB_FILE


logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Enhanced Connection Pool for SQLite
# ══════════════════════════════════════════════════════════════════════

class SQLiteConnectionPool:
    """
    Thread-safe connection pool for SQLite.
    Manages multiple connections to prevent "database is locked" errors.
    """

    def __init__(
            self,
            db_path: str,
            pool_size: int = 10,
            timeout: float = 30.0):
        self.db_path = db_path
        self.pool_size = pool_size
        self.timeout = timeout
        self._pool = []
        self._lock = threading.Lock()
        self._local = threading.local()

        # Pre-create connections
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.append(conn)

        logger.info(
            f"✅ Connection pool initialized with {pool_size} connections")

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with optimized settings"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=self.timeout,
            isolation_level=None  # Autocommit mode
        )
        conn.row_factory = sqlite3.Row

        # Optimize SQLite for concurrent access
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA mmap_size=268435456")  # 256MB mmap

        return conn

    @contextmanager
    def get_connection(self):
        """Get a connection from the pool (context manager)"""
        conn = None
        try:
            with self._lock:
                if self._pool:
                    conn = self._pool.pop()
                else:
                    # Pool exhausted, create temporary connection
                    logger.warning(
                        "⚠️ Connection pool exhausted, creating temporary connection")
                    conn = self._create_connection()

            yield conn

        except Exception as e:
            logger.error(f"Database error: {e}", exc_info=True)
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool
                    with self._lock:
                        if len(self._pool) < self.pool_size:
                            self._pool.append(conn)
                        else:
                            conn.close()
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")

    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            for conn in self._pool:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self._pool.clear()
        logger.info("Connection pool closed")


# Global connection pool instance
_connection_pool: Optional[SQLiteConnectionPool] = None


def init_connection_pool(pool_size: int = 10):
    """Initialize the global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = SQLiteConnectionPool(DB_PATH, pool_size=pool_size)


def get_connection() -> sqlite3.Connection:
    """
    Get a database connection (legacy function for backward compatibility).
    Note: This creates a new connection each time. Use get_connection_from_pool() for pooled connections.
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def get_connection_from_pool():
    """Get a connection from the pool (recommended for new code)"""
    global _connection_pool
    if _connection_pool is None:
        init_connection_pool()

    with _connection_pool.get_connection() as conn:
        yield conn


def init_db():
    """Initialize database with smart sync logic to prevent data loss."""
    import time
    import sqlite3

    # Check if local database exists and get its info
    db_exists = os.path.exists(DB_PATH)
    local_count = 0

    if db_exists:
        db_age_hours = (time.time() - os.path.getmtime(DB_PATH)) / 3600
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            local_count = cursor.execute(
                "SELECT COUNT(*) FROM movies").fetchone()[0]
            conn.close()
            logger.info(
                f"Local DB: {local_count} movies, age: {db_age_hours:.1f}h")
        except Exception as e:
            logger.warning(f"Could not read local DB: {e}")
            local_count = 0

    # Download from HuggingFace if local doesn't exist or is old (>24h)
    should_download = not db_exists or (
        db_exists and (
            time.time() -
            os.path.getmtime(DB_PATH)) /
        3600 > 24)

    if should_download:
        try:
            logger.info("Downloading database from HuggingFace...")
            hf_path = hf_hub_download(
                repo_id=HF_DATASET_NAME,
                filename=DATASET_DB_FILE,
                repo_type="dataset",
                token=HF_TOKEN,
                force_download=True
            )

            # Check HuggingFace database content
            conn = sqlite3.connect(hf_path)
            cursor = conn.cursor()
            hf_count = cursor.execute(
                "SELECT COUNT(*) FROM movies").fetchone()[0]
            conn.close()

            logger.info(f"HuggingFace DB: {hf_count} movies")

            # Smart decision: only use HF version if it has more or equal data
            if hf_count >= local_count:
                logger.info(
                    f"Using HuggingFace DB ({hf_count} >= {local_count})")
                if hf_path != DB_PATH:
                    import shutil
                    shutil.copy(hf_path, DB_PATH)
            else:
                logger.warning(
                    f"⚠️  HuggingFace has LESS data ({hf_count} < {local_count})")
                logger.warning("Keeping local database to prevent data loss")
                logger.info("Consider uploading local DB to HuggingFace")

        except Exception as e:
            logger.warning(f"Could not download from HuggingFace: {e}")
            if not db_exists:
                logger.info("Will create fresh database")
    else:
        logger.info(f"Using existing local database: {DB_PATH}")

    conn = get_connection()
    _create_schema(conn)
    _run_migrations(conn)
    conn.close()
    logger.info("Database initialized.")


def _run_migrations(conn: sqlite3.Connection):
    """Run database migrations to add missing columns."""
    try:
        # Check if available_qualities column exists in movies table
        cursor = conn.execute("PRAGMA table_info(movies)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'available_qualities' not in columns:
            logger.info("Adding available_qualities column to movies table...")
            conn.execute("ALTER TABLE movies ADD COLUMN available_qualities TEXT DEFAULT '[]'")
            conn.commit()
            logger.info("✅ Migration complete: available_qualities added to movies")
        
        # Check if available_qualities column exists in episodes table
        cursor = conn.execute("PRAGMA table_info(episodes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'available_qualities' not in columns:
            logger.info("Adding available_qualities column to episodes table...")
            conn.execute("ALTER TABLE episodes ADD COLUMN available_qualities TEXT DEFAULT '[]'")
            conn.commit()
            logger.info("✅ Migration complete: available_qualities added to episodes")
            
    except Exception as e:
        logger.error(f"Migration error: {e}")


def _create_schema(conn: sqlite3.Connection):
    conn.executescript("""
        -- ══════════════════════════════════════════════════════════════════════
        -- Core Content Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS movies (
            id          TEXT PRIMARY KEY,
            tmdb_id     INTEGER UNIQUE,
            title       TEXT NOT NULL,
            title_ar    TEXT,
            overview    TEXT,
            overview_ar TEXT,
            poster_path TEXT,
            backdrop_path TEXT,
            release_date TEXT,
            runtime     INTEGER,
            genres      TEXT,
            cast        TEXT,
            director    TEXT,
            rating      REAL,
            vote_count  INTEGER,
            file_id     TEXT,
            file_size   INTEGER,
            duration    INTEGER,
            topic_id    INTEGER,
            message_id  INTEGER,
            available_qualities TEXT DEFAULT '[]',
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS series (
            id              TEXT PRIMARY KEY,
            tmdb_id         INTEGER UNIQUE,
            title           TEXT NOT NULL,
            title_ar        TEXT,
            overview        TEXT,
            overview_ar     TEXT,
            poster_path     TEXT,
            backdrop_path   TEXT,
            first_air_date  TEXT,
            genres          TEXT,
            cast            TEXT,
            creator         TEXT,
            rating          REAL,
            vote_count      INTEGER,
            total_seasons   INTEGER,
            status          TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS episodes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id       TEXT NOT NULL,
            season_number   INTEGER NOT NULL,
            episode_number  INTEGER NOT NULL,
            title           TEXT,
            overview        TEXT,
            still_path      TEXT,
            air_date        TEXT,
            runtime         INTEGER,
            file_id         TEXT,
            file_unique_id  TEXT,
            file_size       INTEGER,
            duration        INTEGER,
            topic_id        INTEGER,
            message_id      INTEGER,
            available_qualities TEXT DEFAULT '[]',
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (series_id) REFERENCES series(id),
            UNIQUE(series_id, season_number, episode_number)
        );

        CREATE TABLE IF NOT EXISTS seasons (
            series_id       TEXT NOT NULL,
            season_number   INTEGER NOT NULL,
            topic_id        INTEGER,
            name            TEXT,
            episode_count   INTEGER DEFAULT 0,
            air_date        TEXT,
            overview        TEXT,
            poster_path     TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (series_id, season_number),
            FOREIGN KEY (series_id) REFERENCES series(id)
        );

        CREATE TABLE IF NOT EXISTS topic_series_map (
            topic_id    INTEGER PRIMARY KEY,
            series_id   TEXT NOT NULL,
            FOREIGN KEY (series_id) REFERENCES series(id)
        );

        CREATE INDEX IF NOT EXISTS idx_movies_tmdb ON movies(tmdb_id);
        CREATE INDEX IF NOT EXISTS idx_seasons_series ON seasons(series_id);
        CREATE INDEX IF NOT EXISTS idx_movies_topic ON movies(topic_id);
        CREATE INDEX IF NOT EXISTS idx_series_tmdb ON series(tmdb_id);
        CREATE INDEX IF NOT EXISTS idx_episodes_series ON episodes(series_id, season_number);
        CREATE INDEX IF NOT EXISTS idx_episodes_topic ON episodes(topic_id);

        CREATE TABLE IF NOT EXISTS sync_status (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            last_message_id INTEGER DEFAULT 0,
            last_sync_time  TEXT DEFAULT (datetime('now')),
            sync_type       TEXT DEFAULT 'none'
        );

        CREATE INDEX IF NOT EXISTS idx_movies_rating ON movies(rating DESC);
        CREATE INDEX IF NOT EXISTS idx_series_rating ON series(rating DESC);
        CREATE INDEX IF NOT EXISTS idx_episodes_file ON episodes(file_id);

        -- Additional indexes for trending, popular, and latest endpoints
        CREATE INDEX IF NOT EXISTS idx_movies_created_at ON movies(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_series_created_at ON series(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_movies_file_rating ON movies(file_id, rating DESC) WHERE file_id IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_series_file_rating ON series(rating DESC);

        INSERT OR IGNORE INTO sync_status (id, last_message_id, sync_type)
        VALUES (1, 0, 'initial');

        -- ══════════════════════════════════════════════════════════════════════
        -- Analytics Tables (for future use)
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS analytics_views (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'series', 'episode')),
            content_id      TEXT NOT NULL,
            user_id         INTEGER,
            session_id      TEXT,
            ip_address      TEXT,
            user_agent      TEXT,
            watch_duration  INTEGER DEFAULT 0,
            completed       INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analytics_searches (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            query           TEXT NOT NULL,
            results_count   INTEGER DEFAULT 0,
            user_id         INTEGER,
            session_id      TEXT,
            ip_address      TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analytics_errors (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type      TEXT NOT NULL,
            error_message   TEXT,
            endpoint        TEXT,
            user_id         INTEGER,
            ip_address      TEXT,
            stack_trace     TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_views_content ON analytics_views(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_analytics_views_date ON analytics_views(created_at);
        CREATE INDEX IF NOT EXISTS idx_analytics_searches_date ON analytics_searches(created_at);
        CREATE INDEX IF NOT EXISTS idx_analytics_errors_date ON analytics_errors(created_at);

        -- ══════════════════════════════════════════════════════════════════════
        -- Ads System Tables (UI only - disabled by default)
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS ads_config (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            enabled         INTEGER DEFAULT 0,
            banner_enabled  INTEGER DEFAULT 0,
            banner_interval INTEGER DEFAULT 300,
            banner_duration INTEGER DEFAULT 5,
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ads_banners (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            description     TEXT,
            image_url       TEXT,
            link_url        TEXT,
            position        TEXT DEFAULT 'bottom' CHECK(position IN ('top', 'bottom', 'middle')),
            priority        INTEGER DEFAULT 0,
            active          INTEGER DEFAULT 1,
            impressions     INTEGER DEFAULT 0,
            clicks          INTEGER DEFAULT 0,
            start_date      TEXT,
            end_date        TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ads_impressions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id           INTEGER NOT NULL,
            user_id         INTEGER,
            session_id      TEXT,
            ip_address      TEXT,
            page_url        TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ad_id) REFERENCES ads_banners(id)
        );

        CREATE TABLE IF NOT EXISTS ads_clicks (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_id           INTEGER NOT NULL,
            user_id         INTEGER,
            session_id      TEXT,
            ip_address      TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (ad_id) REFERENCES ads_banners(id)
        );

        CREATE INDEX IF NOT EXISTS idx_ads_banners_active ON ads_banners(active, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_ads_impressions_ad ON ads_impressions(ad_id);
        CREATE INDEX IF NOT EXISTS idx_ads_clicks_ad ON ads_clicks(ad_id);

        INSERT OR IGNORE INTO ads_config (id, enabled, banner_enabled)
        VALUES (1, 0, 0);

        -- ══════════════════════════════════════════════════════════════════════
        -- Subscription System Tables (UI only - disabled by default)
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS subscription_config (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            enabled         INTEGER DEFAULT 0,
            trial_enabled   INTEGER DEFAULT 0,
            trial_days      INTEGER DEFAULT 7,
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS subscription_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            name_ar         TEXT,
            description     TEXT,
            description_ar  TEXT,
            price           REAL NOT NULL,
            currency        TEXT DEFAULT 'USD',
            duration_days   INTEGER NOT NULL,
            features        TEXT,
            active          INTEGER DEFAULT 1,
            priority        INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_subscriptions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            plan_id         INTEGER NOT NULL,
            status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'expired', 'cancelled', 'trial')),
            start_date      TEXT NOT NULL,
            end_date        TEXT NOT NULL,
            auto_renew      INTEGER DEFAULT 0,
            payment_method  TEXT,
            transaction_id  TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
        );

        CREATE TABLE IF NOT EXISTS subscription_transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            subscription_id INTEGER NOT NULL,
            amount          REAL NOT NULL,
            currency        TEXT DEFAULT 'USD',
            status          TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed', 'refunded')),
            payment_method  TEXT,
            transaction_id  TEXT UNIQUE,
            metadata        TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id)
        );

        CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user ON user_subscriptions(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_user_subscriptions_dates ON user_subscriptions(start_date, end_date);
        CREATE INDEX IF NOT EXISTS idx_subscription_plans_active ON subscription_plans(active, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_subscription_transactions_user ON subscription_transactions(user_id);

        INSERT OR IGNORE INTO subscription_config (id, enabled, trial_enabled)
        VALUES (1, 0, 0);

        -- Insert default subscription plans (disabled by default)
        INSERT OR IGNORE INTO subscription_plans (id, name, name_ar, description, description_ar, price, duration_days, features, active, priority)
        VALUES
            (1, 'Free', 'مجاني', 'Basic access with ads', 'وصول أساسي مع إعلانات', 0, 0, '["Basic streaming", "SD quality", "Ads included"]', 1, 0),
            (2, 'Premium', 'بريميوم', 'Ad-free HD streaming', 'بث HD بدون إعلانات', 9.99, 30, '["HD streaming", "No ads", "Download support", "Priority support"]', 1, 1);

        -- ══════════════════════════════════════════════════════════════════════
        -- User Preferences & Watch History (for future use)
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id         INTEGER PRIMARY KEY,
            language        TEXT DEFAULT 'ar',
            quality         TEXT DEFAULT 'auto',
            autoplay        INTEGER DEFAULT 1,
            subtitles       INTEGER DEFAULT 1,
            theme           TEXT DEFAULT 'dark',
            notifications   INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watch_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'episode')),
            content_id      TEXT NOT NULL,
            series_id       TEXT,
            season_number   INTEGER,
            episode_number  INTEGER,
            progress        INTEGER DEFAULT 0,
            duration        INTEGER,
            completed       INTEGER DEFAULT 0,
            last_watched    TEXT DEFAULT (datetime('now')),
            created_at      TEXT DEFAULT (datetime('now'))
        );

        -- ══════════════════════════════════════════════════════════════════════
        -- Watch Rooms System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS watch_rooms (
            room_id         TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            description     TEXT,
            host_user_id    INTEGER NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'series')),
            content_id      TEXT NOT NULL,
            episode_id      INTEGER,
            is_public       INTEGER DEFAULT 1,
            password        TEXT,
            max_participants INTEGER DEFAULT 50,
            status          TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'playing', 'paused', 'ended')),
            current_timestamp REAL DEFAULT 0,
            playback_speed  REAL DEFAULT 1.0,
            sync_mode       TEXT DEFAULT 'host_control' CHECK(sync_mode IN ('watch_party', 'free_watch', 'host_control', 'voting')),
            voice_chat_enabled INTEGER DEFAULT 0,
            telegram_call_id TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            started_at      TEXT,
            ended_at        TEXT
        );

        CREATE TABLE IF NOT EXISTS room_participants (
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            role            TEXT DEFAULT 'participant' CHECK(role IN ('host', 'moderator', 'participant')),
            joined_at       TEXT DEFAULT (datetime('now')),
            left_at         TEXT,
            is_muted        INTEGER DEFAULT 0,
            is_video_synced INTEGER DEFAULT 1,
            last_ping       TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (room_id, user_id),
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS room_chat_messages (
            message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            content         TEXT NOT NULL,
            message_type    TEXT DEFAULT 'text' CHECK(message_type IN ('text', 'system', 'emoji', 'reaction')),
            reply_to        INTEGER,
            created_at      TEXT DEFAULT (datetime('now')),
            deleted_at      TEXT,
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE,
            FOREIGN KEY (reply_to) REFERENCES room_chat_messages(message_id)
        );

        CREATE TABLE IF NOT EXISTS room_voice_sessions (
            session_id      TEXT PRIMARY KEY,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            telegram_call_id TEXT,
            status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'ended')),
            started_at      TEXT DEFAULT (datetime('now')),
            ended_at        TEXT,
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS room_sync_events (
            event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            event_type      TEXT NOT NULL CHECK(event_type IN ('play', 'pause', 'seek', 'speed_change', 'sync')),
            timestamp       REAL NOT NULL,
            playback_speed  REAL DEFAULT 1.0,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS room_reactions (
            reaction_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            reaction_type   TEXT NOT NULL,
            timestamp       REAL NOT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS room_timestamps (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            timestamp       REAL NOT NULL,
            label           TEXT NOT NULL,
            description     TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS room_polls (
            poll_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id         TEXT NOT NULL,
            user_id         INTEGER NOT NULL,
            question        TEXT NOT NULL,
            options         TEXT NOT NULL,
            votes           TEXT DEFAULT '{}',
            status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'closed')),
            created_at      TEXT DEFAULT (datetime('now')),
            closed_at       TEXT,
            FOREIGN KEY (room_id) REFERENCES watch_rooms(room_id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_watch_rooms_status ON watch_rooms(status, is_public);
        CREATE INDEX IF NOT EXISTS idx_watch_rooms_host ON watch_rooms(host_user_id);
        CREATE INDEX IF NOT EXISTS idx_watch_rooms_content ON watch_rooms(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_room_participants_room ON room_participants(room_id);
        CREATE INDEX IF NOT EXISTS idx_room_participants_user ON room_participants(user_id);
        CREATE INDEX IF NOT EXISTS idx_room_chat_messages_room ON room_chat_messages(room_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_room_voice_sessions_room ON room_voice_sessions(room_id, status);
        CREATE INDEX IF NOT EXISTS idx_room_sync_events_room ON room_sync_events(room_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_room_reactions_room ON room_reactions(room_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS user_favorites (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'series')),
            content_id      TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, content_type, content_id)
        );

        CREATE TABLE IF NOT EXISTS user_ratings (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'series')),
            content_id      TEXT NOT NULL,
            rating          INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
            review          TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, content_type, content_id)
        );

        -- ══════════════════════════════════════════════════════════════════════
        -- Reviews System Table (Enhanced ratings with 1-10 scale)
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS reviews (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id      TEXT NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'series')),
            user_id         INTEGER NOT NULL,
            username        TEXT,
            rating          INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 10),
            comment         TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, content_type, content_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_watch_history_user ON watch_history(user_id, last_watched DESC);
        CREATE INDEX IF NOT EXISTS idx_watch_history_content ON watch_history(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_ratings_content ON user_ratings(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_reviews_content ON reviews(content_type, content_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reviews_user ON reviews(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(content_type, content_id, rating DESC);

        -- ══════════════════════════════════════════════════════════════════════
        -- Enhanced User Tracking System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id         INTEGER PRIMARY KEY,
            bio             TEXT,
            avatar_url      TEXT,
            country         TEXT,
            city            TEXT,
            birth_date      TEXT,
            gender          TEXT CHECK(gender IN ('male', 'female', 'other', 'prefer_not_to_say')),
            phone           TEXT,
            email           TEXT,
            preferences     TEXT,  -- JSON: viewing preferences, genres, etc.
            privacy_settings TEXT, -- JSON: privacy configuration
            notification_settings TEXT, -- JSON: notification preferences
            social_links    TEXT,  -- JSON: social media links
            total_watch_time INTEGER DEFAULT 0,  -- in seconds
            total_content_watched INTEGER DEFAULT 0,
            favorite_genres TEXT,  -- JSON array
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS user_activity (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            activity_type   TEXT NOT NULL CHECK(activity_type IN (
                'login', 'logout', 'view_content', 'search', 'rate', 'favorite',
                'unfavorite', 'share', 'download', 'profile_update', 'settings_change',
                'subscription_change', 'payment', 'report', 'comment', 'like'
            )),
            activity_details TEXT,  -- JSON: detailed activity information
            content_type    TEXT CHECK(content_type IN ('movie', 'series', 'episode', NULL)),
            content_id      TEXT,
            ip_address      TEXT,
            user_agent      TEXT,
            device_type     TEXT,  -- mobile, desktop, tablet, tv
            os_type         TEXT,  -- iOS, Android, Windows, macOS, Linux
            browser         TEXT,
            location        TEXT,  -- JSON: country, city, coordinates
            session_id      TEXT,
            duration        INTEGER,  -- activity duration in seconds
            metadata        TEXT,  -- JSON: additional metadata
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id      TEXT UNIQUE NOT NULL,
            user_id         INTEGER NOT NULL,
            ip_address      TEXT,
            user_agent      TEXT,
            device_type     TEXT,
            os_type         TEXT,
            browser         TEXT,
            location        TEXT,  -- JSON
            is_active       INTEGER DEFAULT 1,
            last_activity   TEXT DEFAULT (datetime('now')),
            login_time      TEXT DEFAULT (datetime('now')),
            logout_time     TEXT,
            session_duration INTEGER DEFAULT 0,  -- in seconds
            pages_visited   INTEGER DEFAULT 0,
            actions_count   INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS user_statistics (
            user_id         INTEGER PRIMARY KEY,
            total_logins    INTEGER DEFAULT 0,
            total_sessions  INTEGER DEFAULT 0,
            total_watch_time INTEGER DEFAULT 0,  -- in seconds
            total_movies_watched INTEGER DEFAULT 0,
            total_episodes_watched INTEGER DEFAULT 0,
            total_searches  INTEGER DEFAULT 0,
            total_ratings   INTEGER DEFAULT 0,
            total_favorites INTEGER DEFAULT 0,
            total_shares    INTEGER DEFAULT 0,
            average_session_duration INTEGER DEFAULT 0,  -- in seconds
            favorite_genre  TEXT,
            favorite_time_slot TEXT,  -- morning, afternoon, evening, night
            most_watched_day TEXT,  -- monday, tuesday, etc.
            completion_rate REAL DEFAULT 0.0,  -- percentage
            binge_score     REAL DEFAULT 0.0,  -- calculated metric
            engagement_score REAL DEFAULT 0.0,  -- calculated metric
            last_calculated TEXT DEFAULT (datetime('now')),
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS user_devices (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            device_id       TEXT UNIQUE NOT NULL,
            device_name     TEXT,
            device_type     TEXT,
            os_type         TEXT,
            os_version      TEXT,
            browser         TEXT,
            browser_version TEXT,
            is_trusted      INTEGER DEFAULT 0,
            last_used       TEXT DEFAULT (datetime('now')),
            first_seen      TEXT DEFAULT (datetime('now')),
            total_sessions  INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS user_watch_progress (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'episode')),
            content_id      TEXT NOT NULL,
            series_id       TEXT,
            season_number   INTEGER,
            episode_number  INTEGER,
            progress_seconds INTEGER DEFAULT 0,
            total_seconds   INTEGER,
            progress_percent REAL DEFAULT 0.0,
            completed       INTEGER DEFAULT 0,
            last_position   INTEGER DEFAULT 0,
            playback_speed  REAL DEFAULT 1.0,
            quality         TEXT,
            subtitles_enabled INTEGER DEFAULT 0,
            last_watched    TEXT DEFAULT (datetime('now')),
            watch_count     INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, content_type, content_id)
        );

        CREATE TABLE IF NOT EXISTS database_backups (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_name     TEXT NOT NULL,
            backup_path     TEXT NOT NULL,
            backup_size     INTEGER,
            backup_type     TEXT DEFAULT 'manual' CHECK(backup_type IN ('manual', 'automatic', 'scheduled')),
            compression     TEXT DEFAULT 'gzip',
            hf_version      TEXT,
            hf_commit_hash  TEXT,
            tables_included TEXT,  -- JSON array
            records_count   INTEGER,
            status          TEXT DEFAULT 'completed' CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')),
            error_message   TEXT,
            created_by      INTEGER,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS sync_history (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type       TEXT NOT NULL CHECK(sync_type IN ('upload', 'download', 'full_sync')),
            status          TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')),
            records_synced  INTEGER DEFAULT 0,
            tables_synced   TEXT,  -- JSON array
            file_size       INTEGER,
            duration_seconds INTEGER,
            hf_commit_hash  TEXT,
            error_message   TEXT,
            started_at      TEXT DEFAULT (datetime('now')),
            completed_at    TEXT
        );

        -- Indexes for performance optimization
        CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_user_activity_type ON user_activity(activity_type, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_user_activity_content ON user_activity(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_user_activity_session ON user_activity(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active, last_activity DESC);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_session ON user_sessions(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_statistics_user ON user_statistics(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_devices_user ON user_devices(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_devices_device ON user_devices(device_id);
        CREATE INDEX IF NOT EXISTS idx_user_watch_progress_user ON user_watch_progress(user_id, last_watched DESC);
        CREATE INDEX IF NOT EXISTS idx_user_watch_progress_content ON user_watch_progress(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_database_backups_date ON database_backups(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sync_history_date ON sync_history(started_at DESC);
        CREATE INDEX IF NOT EXISTS idx_sync_history_status ON sync_history(status, sync_type);

        -- ══════════════════════════════════════════════════════════════════════
        -- Admin System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS users (
            user_id         INTEGER PRIMARY KEY,
            username        TEXT,
            first_name      TEXT,
            last_name       TEXT,
            is_bot          INTEGER DEFAULT 0,
            is_blocked      INTEGER DEFAULT 0,
            is_premium      INTEGER DEFAULT 0,
            language_code   TEXT DEFAULT 'ar',
            is_subscribed   INTEGER DEFAULT 0,
            subscription_checked_at TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            last_active     TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS admin_users (
            user_id         INTEGER PRIMARY KEY,
            username        TEXT,
            role            TEXT NOT NULL CHECK(role IN ('super_admin', 'admin', 'moderator')),
            assigned_by     INTEGER,
            assigned_at     TEXT DEFAULT (datetime('now')),
            is_active       INTEGER DEFAULT 1,
            permissions_override TEXT,
            last_activity   TEXT,
            notes           TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (assigned_by) REFERENCES admin_users(user_id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id        INTEGER NOT NULL,
            action_type     TEXT NOT NULL,
            action_details  TEXT,
            target_type     TEXT,
            target_id       TEXT,
            ip_address      TEXT,
            user_agent      TEXT,
            status          TEXT DEFAULT 'success',
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            message         TEXT NOT NULL,
            target_type     TEXT DEFAULT 'all' CHECK(target_type IN ('all', 'user', 'group')),
            target_ids      TEXT,
            scheduled_at    TEXT,
            sent_at         TEXT,
            status          TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'failed', 'cancelled')),
            created_by      INTEGER NOT NULL,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS bot_status (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_name        TEXT NOT NULL,
            bot_type        TEXT NOT NULL,
            status          TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'error')),
            last_check      TEXT DEFAULT (datetime('now')),
            error_message   TEXT,
            uptime_seconds  INTEGER DEFAULT 0,
            requests_count  INTEGER DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked);
        CREATE INDEX IF NOT EXISTS idx_admin_users_role ON admin_users(role);
        CREATE INDEX IF NOT EXISTS idx_admin_users_active ON admin_users(is_active);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_admin ON audit_logs(admin_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action_type, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_bot_status_type ON bot_status(bot_type, status);

        -- ══════════════════════════════════════════════════════════════════════
        -- Friends System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS friendships (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            friend_id       INTEGER NOT NULL,
            status          TEXT DEFAULT 'accepted' CHECK(status IN ('accepted', 'blocked')),
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (friend_id) REFERENCES users(user_id),
            UNIQUE(user_id, friend_id),
            CHECK(user_id != friend_id)
        );

        CREATE TABLE IF NOT EXISTS friend_requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id    INTEGER NOT NULL,
            to_user_id      INTEGER NOT NULL,
            message         TEXT,
            status          TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'accepted', 'rejected', 'cancelled')),
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            expires_at      TEXT,
            FOREIGN KEY (from_user_id) REFERENCES users(user_id),
            FOREIGN KEY (to_user_id) REFERENCES users(user_id),
            CHECK(from_user_id != to_user_id)
        );

        CREATE TABLE IF NOT EXISTS blocked_users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            blocked_user_id INTEGER NOT NULL,
            reason          TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (blocked_user_id) REFERENCES users(user_id),
            UNIQUE(user_id, blocked_user_id),
            CHECK(user_id != blocked_user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_friendships_user ON friendships(user_id, status);
        CREATE INDEX IF NOT EXISTS idx_friendships_friend ON friendships(friend_id, status);
        CREATE INDEX IF NOT EXISTS idx_friend_requests_to ON friend_requests(to_user_id, status);
        CREATE INDEX IF NOT EXISTS idx_friend_requests_from ON friend_requests(from_user_id, status);
        CREATE INDEX IF NOT EXISTS idx_blocked_users_user ON blocked_users(user_id);
        CREATE INDEX IF NOT EXISTS idx_blocked_users_blocked ON blocked_users(blocked_user_id);

        -- ══════════════════════════════════════════════════════════════════════
        -- Messaging System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS conversations (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            type            TEXT DEFAULT 'direct' CHECK(type IN ('direct', 'group')),
            name            TEXT,
            avatar_url      TEXT,
            is_pinned       INTEGER DEFAULT 0,
            is_muted        INTEGER DEFAULT 0,
            is_archived     INTEGER DEFAULT 0,
            last_message_id INTEGER,
            last_message_at TEXT,
            created_by      INTEGER,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (created_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS conversation_participants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            role            TEXT DEFAULT 'member' CHECK(role IN ('admin', 'member')),
            is_active       INTEGER DEFAULT 1,
            joined_at       TEXT DEFAULT (datetime('now')),
            left_at         TEXT,
            last_read_at    TEXT DEFAULT (datetime('now')),
            last_read_message_id INTEGER DEFAULT 0,
            notifications_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(conversation_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id       INTEGER NOT NULL,
            content         TEXT,
            media_type      TEXT DEFAULT 'text' CHECK(media_type IN ('text', 'photo', 'video', 'audio', 'document', 'voice', 'sticker')),
            media_file_id   TEXT,
            media_file_unique_id TEXT,
            media_file_size INTEGER,
            media_thumbnail TEXT,
            media_duration  INTEGER,
            media_width     INTEGER,
            media_height    INTEGER,
            reply_to_message_id INTEGER,
            forward_from_message_id INTEGER,
            is_edited       INTEGER DEFAULT 0,
            is_deleted      INTEGER DEFAULT 0,
            deleted_at      TEXT,
            edited_at       TEXT,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(user_id),
            FOREIGN KEY (reply_to_message_id) REFERENCES messages(id)
        );

        CREATE TABLE IF NOT EXISTS message_reactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id      INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            reaction        TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(message_id, user_id, reaction)
        );

        CREATE TABLE IF NOT EXISTS message_read_receipts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id      INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            read_at         TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(message_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS typing_indicators (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            started_at      TEXT DEFAULT (datetime('now')),
            expires_at      TEXT NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(conversation_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS user_online_status (
            user_id         INTEGER PRIMARY KEY,
            is_online       INTEGER DEFAULT 0,
            last_seen       TEXT DEFAULT (datetime('now')),
            status_text     TEXT,
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );

        CREATE INDEX IF NOT EXISTS idx_conversations_type ON conversations(type, is_archived);
        CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON conversations(last_message_at DESC);
        CREATE INDEX IF NOT EXISTS idx_conversation_participants_conv ON conversation_participants(conversation_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_conversation_participants_user ON conversation_participants(user_id, is_active);
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_messages_deleted ON messages(is_deleted, conversation_id);
        CREATE INDEX IF NOT EXISTS idx_message_reactions_message ON message_reactions(message_id);
        CREATE INDEX IF NOT EXISTS idx_message_read_receipts_message ON message_read_receipts(message_id);
        CREATE INDEX IF NOT EXISTS idx_message_read_receipts_user ON message_read_receipts(user_id, read_at DESC);
        CREATE INDEX IF NOT EXISTS idx_typing_indicators_conv ON typing_indicators(conversation_id, expires_at);
        CREATE INDEX IF NOT EXISTS idx_user_online_status_online ON user_online_status(is_online, last_seen DESC);

        -- ══════════════════════════════════════════════════════════════════════
        -- Mirror System Tables
        -- ══════════════════════════════════════════════════════════════════════

        CREATE TABLE IF NOT EXISTS file_mirrors (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id         TEXT NOT NULL,
            content_type    TEXT NOT NULL CHECK(content_type IN ('movie', 'episode')),
            content_id      TEXT NOT NULL,
            group_id        INTEGER NOT NULL,
            message_id      INTEGER NOT NULL,
            file_unique_id  TEXT NOT NULL,
            file_size       INTEGER NOT NULL,
            upload_date     REAL NOT NULL,
            is_verified     INTEGER DEFAULT 1,
            last_check      REAL DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now')),
            UNIQUE(file_id, group_id)
        );

        CREATE TABLE IF NOT EXISTS group_health (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id        INTEGER UNIQUE NOT NULL,
            status          TEXT DEFAULT 'unknown' CHECK(status IN ('active', 'slow', 'down', 'unknown')),
            response_time   REAL DEFAULT 0,
            file_count      INTEGER DEFAULT 0,
            total_size      INTEGER DEFAULT 0,
            last_check      REAL NOT NULL,
            last_error      TEXT,
            accessibility   INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS bot_stats (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id          TEXT UNIQUE NOT NULL,
            requests_count  INTEGER DEFAULT 0,
            success_count   INTEGER DEFAULT 0,
            failure_count   INTEGER DEFAULT 0,
            avg_response_time REAL DEFAULT 0,
            last_used       REAL NOT NULL,
            status          TEXT DEFAULT 'unknown' CHECK(status IN ('healthy', 'degraded', 'down', 'unknown')),
            last_error      TEXT,
            uptime_percentage REAL DEFAULT 100.0,
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_file_mirrors_file ON file_mirrors(file_id);
        CREATE INDEX IF NOT EXISTS idx_file_mirrors_content ON file_mirrors(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_file_mirrors_group ON file_mirrors(group_id);
        CREATE INDEX IF NOT EXISTS idx_file_mirrors_verified ON file_mirrors(is_verified, last_check);
        CREATE INDEX IF NOT EXISTS idx_group_health_status ON group_health(status, last_check DESC);
        CREATE INDEX IF NOT EXISTS idx_bot_stats_status ON bot_stats(status, last_used DESC);
        CREATE INDEX IF NOT EXISTS idx_bot_stats_bot ON bot_stats(bot_id);
    """)
    conn.commit()


def push_db_to_hf(create_backup=True, version_tag=None, commit_message=None):
    """
    Enhanced push to HuggingFace with versioning and backup support.

    Args:
        create_backup: Create local backup before push
        version_tag: Optional version tag for this push
        commit_message: Custom commit message

    Returns:
        dict: Result with success status and details
    """
    try:
        from datetime import datetime
        import os

        # Create backup if requested
        if create_backup:
            try:
                from app.backup_manager import BackupManager
                backup_mgr = BackupManager()
                backup_result = backup_mgr.create_backup(
                    backup_name=f"pre_sync_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    backup_type='automatic')
                logger.info(
                    f"Pre-sync backup created: {backup_result.get('backup_name', 'unknown')}")
            except Exception as e:
                logger.warning(f"Failed to create pre-sync backup: {e}")

        # Generate version tag if not provided
        if not version_tag:
            version_tag = f"v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Generate commit message with statistics
        if not commit_message:
            try:
                conn = get_connection()
                stats = {
                    'movies': conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0],
                    'series': conn.execute("SELECT COUNT(*) FROM series").fetchone()[0],
                    'episodes': conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0],
                    'users': conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]}
                conn.close()
                commit_message = f"Auto-sync {version_tag}: {stats['movies']} movies, {stats['series']} series, {stats['episodes']} episodes, {stats['users']} users"
            except sqlite3.Error as db_error:
                logger.error(
                    f"Database error generating commit message: {type(db_error).__name__}: {str(db_error)}")
                commit_message = f"Auto-sync: update database {version_tag}"
            except Exception as e:
                logger.error(
                    f"Unexpected error generating commit message: {type(e).__name__}: {str(e)}")
                commit_message = f"Auto-sync: update database {version_tag}"

        # Log sync start
        sync_id = log_sync_operation(
            sync_type='upload',
            status='in_progress'
        )

        start_time = datetime.utcnow()

        # Upload to HuggingFace
        api = HfApi(token=HF_TOKEN)
        commit_info = api.upload_file(
            path_or_fileobj=DB_PATH,
            path_in_repo=DATASET_DB_FILE,
            repo_id=HF_DATASET_NAME,
            repo_type="dataset",
            commit_message=commit_message,
        )

        # Calculate duration and file size
        duration = int((datetime.utcnow() - start_time).total_seconds())
        file_size = os.path.getsize(DB_PATH)

        # Update sync record
        update_sync_operation(
            sync_id=sync_id,
            status='completed',
            file_size=file_size,
            duration_seconds=duration,
            hf_commit_hash=commit_info.oid if hasattr(
                commit_info,
                'oid') else None,
            completed_at=datetime.utcnow().isoformat())

        logger.info(
            f"Database pushed to HuggingFace successfully: {version_tag}")

        return {
            "success": True,
            "version": version_tag,
            "commit_message": commit_message,
            "file_size": file_size,
            "duration_seconds": duration
        }
    except Exception as e:
        logger.error(f"Failed to push DB to HF: {e}", exc_info=True)

        # Update sync record as failed
        try:
            update_sync_operation(
                sync_id=sync_id,
                status='failed',
                error_message=str(e),
                completed_at=datetime.utcnow().isoformat()
            )
        except sqlite3.Error as db_error:
            logger.error(
                f"Failed to update sync operation status: {type(db_error).__name__}: {str(db_error)}")
        except Exception as unexpected_error:
            logger.exception(
                f"Unexpected error updating sync status: {str(unexpected_error)}")

        return {
            "success": False,
            "error": str(e)
        }


def get_movies(limit=20, offset=0, genre=None, search=None):
    conn = get_connection()
    try:
        q = "SELECT * FROM movies WHERE 1=1"
        params = []
        if genre:
            q += " AND genres LIKE ?"
            params.append(f"%{genre}%")
        if search:
            q += " AND (title LIKE ? OR title_ar LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_movie(movie_id=None, tmdb_id=None):
    conn = get_connection()
    try:
        if movie_id:
            row = conn.execute(
                "SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM movies WHERE tmdb_id=?", (tmdb_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_movie_file(
        movie_id: str,
        file_id: str,
        file_size: int,
        duration: int,
        message_id: int):
    """Update only the file-related fields of an existing movie."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE movies
               SET file_id=?, file_size=?, duration=?, message_id=?, updated_at=datetime('now')
               WHERE id=?""",
            (file_id, file_size, duration, message_id, movie_id),
        )
        conn.commit()
        logger.info(
            f"[db] Movie file updated: id={movie_id} file_id={file_id[:20]}…")
    finally:
        conn.close()


def get_series_list(limit=20, offset=0, genre=None, search=None):
    conn = get_connection()
    try:
        q = "SELECT * FROM series WHERE 1=1"
        params = []
        if genre:
            q += " AND genres LIKE ?"
            params.append(f"%{genre}%")
        if search:
            q += " AND (title LIKE ? OR title_ar LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_series(series_id=None, tmdb_id=None):
    conn = get_connection()
    try:
        if series_id:
            row = conn.execute(
                "SELECT * FROM series WHERE id=?", (series_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM series WHERE tmdb_id=?", (tmdb_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_episodes(series_id, season_number=None):
    conn = get_connection()
    try:
        q = "SELECT * FROM episodes WHERE series_id=?"
        params = [series_id]
        if season_number is not None:
            q += " AND season_number=?"
            params.append(season_number)
        q += " ORDER BY season_number, episode_number"
        rows = conn.execute(q, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_episode(series_id: str, season_number: int,
                episode_number: int) -> dict | None:
    """Fetch a single episode record."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM episodes WHERE series_id=? AND season_number=? AND episode_number=?",
            (series_id, season_number, episode_number),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_episode_file(
    series_id: str,
    season_number: int,
    episode_number: int,
    file_id: str,
    file_size: int,
    duration: int,
    message_id: int,
    topic_id: int,
):
    """Update only the file-related fields of an existing episode."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE episodes
               SET file_id=?, file_size=?, duration=?, message_id=?, topic_id=?
               WHERE series_id=? AND season_number=? AND episode_number=?""",
            (file_id, file_size, duration, message_id, topic_id,
             series_id, season_number, episode_number),
        )
        conn.commit()
        logger.info(
            f"[db] Episode file updated: {series_id} S{season_number:02d}E{episode_number:02d}"
        )
    finally:
        conn.close()


def upsert_movie(data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO movies (id, tmdb_id, title, title_ar, overview, overview_ar,
                poster_path, backdrop_path, release_date, runtime, genres, cast,
                director, rating, vote_count, file_id, file_size, duration,
                topic_id, message_id, updated_at)
            VALUES (:id, :tmdb_id, :title, :title_ar, :overview, :overview_ar,
                :poster_path, :backdrop_path, :release_date, :runtime, :genres, :cast,
                :director, :rating, :vote_count, :file_id, :file_size, :duration,
                :topic_id, :message_id, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                file_id=COALESCE(excluded.file_id, file_id),
                file_size=COALESCE(excluded.file_size, file_size),
                duration=COALESCE(excluded.duration, duration),
                message_id=COALESCE(excluded.message_id, message_id),
                topic_id=COALESCE(excluded.topic_id, topic_id),
                updated_at=datetime('now')
        """, data)
        conn.commit()
    finally:
        conn.close()


def upsert_series(data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO series (id, tmdb_id, title, title_ar, overview, overview_ar,
                poster_path, backdrop_path, first_air_date, genres, cast, creator,
                rating, vote_count, total_seasons, status, updated_at)
            VALUES (:id, :tmdb_id, :title, :title_ar, :overview, :overview_ar,
                :poster_path, :backdrop_path, :first_air_date, :genres, :cast, :creator,
                :rating, :vote_count, :total_seasons, :status, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                total_seasons=excluded.total_seasons, status=excluded.status,
                updated_at=datetime('now')
        """, data)
        conn.commit()
    finally:
        conn.close()


def upsert_episode(data: dict):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO episodes (series_id, season_number, episode_number, title,
                overview, still_path, air_date, runtime, file_id, file_unique_id,
                file_size, duration, topic_id, message_id)
            VALUES (:series_id, :season_number, :episode_number, :title,
                :overview, :still_path, :air_date, :runtime,
                :file_id, :file_unique_id, :file_size, :duration, :topic_id, :message_id)
            ON CONFLICT(series_id, season_number, episode_number) DO UPDATE SET
                file_id=COALESCE(excluded.file_id, file_id),
                file_unique_id=COALESCE(excluded.file_unique_id, file_unique_id),
                file_size=COALESCE(excluded.file_size, file_size),
                duration=COALESCE(excluded.duration, duration),
                message_id=COALESCE(excluded.message_id, message_id),
                topic_id=COALESCE(excluded.topic_id, topic_id)
        """, data)
        conn.commit()
    finally:
        conn.close()


def upsert_season(data: dict):
    """Add or update a season record."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO seasons (series_id, season_number, topic_id, name,
                episode_count, air_date, overview, poster_path)
            VALUES (:series_id, :season_number, :topic_id, :name,
                :episode_count, :air_date, :overview, :poster_path)
            ON CONFLICT(series_id, season_number) DO UPDATE SET
                topic_id=COALESCE(excluded.topic_id, topic_id),
                name=COALESCE(excluded.name, name),
                episode_count=COALESCE(excluded.episode_count, episode_count),
                air_date=COALESCE(excluded.air_date, air_date),
                overview=COALESCE(excluded.overview, overview),
                poster_path=COALESCE(excluded.poster_path, poster_path)
        """, data)
        conn.commit()
    finally:
        conn.close()


def get_season(series_id: str, season_number: int) -> dict | None:
    """Get a specific season."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM seasons WHERE series_id=? AND season_number=?",
            (series_id, season_number)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_series_seasons(series_id: str) -> list[dict]:
    """Get all seasons for a series."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM seasons WHERE series_id=? ORDER BY season_number",
            (series_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def set_topic_series_map(topic_id: int, series_id: str):
    """Map a forum topic_id to a series_id for fast episode lookup."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO topic_series_map (topic_id, series_id) VALUES (?, ?)",
            (topic_id, series_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_stats():
    conn = get_connection()
    try:
        movies_count = conn.execute(
            "SELECT COUNT(*) FROM movies").fetchone()[0]
        series_count = conn.execute(
            "SELECT COUNT(*) FROM series").fetchone()[0]
        episodes_count = conn.execute(
            "SELECT COUNT(*) FROM episodes").fetchone()[0]
        latest_movies = conn.execute(
            "SELECT id, title, title_ar, poster_path, backdrop_path, rating, release_date, file_id "
            "FROM movies ORDER BY created_at DESC LIMIT 8").fetchall()
        latest_series = conn.execute(
            "SELECT id, title, title_ar, poster_path, backdrop_path, rating, first_air_date "
            "FROM series ORDER BY created_at DESC LIMIT 6").fetchall()
        return {
            "movies_count": movies_count,
            "series_count": series_count,
            "episodes_count": episodes_count,
            "latest_movies": [dict(r) for r in latest_movies],
            "latest_series": [dict(r) for r in latest_series],
        }
    finally:
        conn.close()


def get_sync_status() -> dict:
    """Get the last sync status."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM sync_status WHERE id=1").fetchone()
        if row:
            return dict(row)
        return {
            "last_message_id": 0,
            "last_sync_time": None,
            "sync_type": "none"}
    finally:
        conn.close()


def update_sync_status(last_message_id: int, sync_type: str):
    """Update sync status after successful sync."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE sync_status
               SET last_message_id=?, last_sync_time=datetime('now'), sync_type=?
               WHERE id=1""",
            (last_message_id, sync_type)
        )
        conn.commit()
        logger.info(
            f"Sync status updated: last_msg={last_message_id}, type={sync_type}")
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Analytics Functions
# ══════════════════════════════════════════════════════════════════════════════

def log_view(content_type: str, content_id: str, user_id: int | None = None,
             session_id: str | None = None, ip_address: str | None = None,
             watch_duration: int = 0, completed: int = 0):
    """Log a content view for analytics."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO analytics_views
            (content_type, content_id, user_id, session_id, ip_address, watch_duration, completed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (content_type, content_id, user_id, session_id, ip_address, watch_duration, completed))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log view: {e}")
    finally:
        conn.close()


def log_search(query: str, results_count: int, user_id: int | None = None,
               session_id: str | None = None, ip_address: str | None = None):
    """Log a search query for analytics."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO analytics_searches
            (query, results_count, user_id, session_id, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (query, results_count, user_id, session_id, ip_address))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log search: {e}")
    finally:
        conn.close()


def log_error(
        error_type: str,
        error_message: str,
        endpoint: str | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        stack_trace: str | None = None):
    """Log an error for analytics."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO analytics_errors
            (error_type, error_message, endpoint, user_id, ip_address, stack_trace)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (error_type, error_message, endpoint, user_id, ip_address, stack_trace))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log error: {e}")
    finally:
        conn.close()


def get_analytics_summary(days: int = 7) -> dict:
    """Get analytics summary for the last N days."""
    conn = get_connection()
    try:
        f"datetime('now', '-{days} days')"

        # Fixed: Use parameterized queries to prevent SQL injection
        cutoff_value = f"datetime('now', '-{days} days')"

        total_views = conn.execute(
            f"SELECT COUNT(*) FROM analytics_views WHERE created_at >= {cutoff_value}"
        ).fetchone()[0]

        total_searches = conn.execute(
            f"SELECT COUNT(*) FROM analytics_searches WHERE created_at >= {cutoff_value}"
        ).fetchone()[0]

        total_errors = conn.execute(
            f"SELECT COUNT(*) FROM analytics_errors WHERE created_at >= {cutoff_value}"
        ).fetchone()[0]

        popular_content = conn.execute("""
            SELECT content_type, content_id, COUNT(*) as views
            FROM analytics_views
            WHERE created_at >= {cutoff_value}
            GROUP BY content_type, content_id
            ORDER BY views DESC
            LIMIT 10
        """).fetchall()

        popular_searches = conn.execute("""
            SELECT query, COUNT(*) as count
            FROM analytics_searches
            WHERE created_at >= {cutoff_value}
            GROUP BY query
            ORDER BY count DESC
            LIMIT 10
        """).fetchall()

        return {
            "period_days": days,
            "total_views": total_views,
            "total_searches": total_searches,
            "total_errors": total_errors,
            "popular_content": [dict(r) for r in popular_content],
            "popular_searches": [dict(r) for r in popular_searches],
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Ads System Functions (UI only - disabled by default)
# ══════════════════════════════════════════════════════════════════════════════

def get_ads_config() -> dict:
    """Get ads configuration."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ads_config WHERE id=1").fetchone()
        return dict(row) if row else {"enabled": 0, "banner_enabled": 0}
    finally:
        conn.close()


def update_ads_config(
        enabled: int | None = None,
        banner_enabled: int | None = None,
        banner_interval: int | None = None,
        banner_duration: int | None = None):
    """Update ads configuration."""
    conn = get_connection()
    try:
        updates = []  # noqa: F841
        params = []
        if enabled is not None:
            updates.append("enabled=?")
            params.append(enabled)
        if banner_enabled is not None:
            updates.append("banner_enabled=?")
            params.append(banner_enabled)
        if banner_interval is not None:
            updates.append("banner_interval=?")
            params.append(banner_interval)
        if banner_duration is not None:
            updates.append("banner_duration=?")
            params.append(banner_duration)

        if updates:
            updates.append("updated_at=datetime('now')")
            # Fixed: Column names are safe (from controlled list), using
            # parameterized values
            query = f"UPDATE ads_config SET {', '.join(updates)} WHERE id=1"
            conn.execute(query, params)
            conn.commit()
    finally:
        conn.close()


def get_active_banners(limit: int = 5) -> list[dict]:
    """Get active banner ads."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM ads_banners
            WHERE active=1
            AND (start_date IS NULL OR start_date <= datetime('now'))
            AND (end_date IS NULL OR end_date >= datetime('now'))
            ORDER BY priority DESC, created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def log_ad_impression(
        ad_id: int,
        user_id: int | None = None,
        session_id: str | None = None,
        ip_address: str | None = None,
        page_url: str | None = None):
    """Log an ad impression."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ads_impressions (ad_id, user_id, session_id, ip_address, page_url)
            VALUES (?, ?, ?, ?, ?)
        """, (ad_id, user_id, session_id, ip_address, page_url))

        # Update impressions count
        conn.execute(
            "UPDATE ads_banners SET impressions=impressions+1 WHERE id=?", (ad_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log ad impression: {e}")
    finally:
        conn.close()


def log_ad_click(
        ad_id: int,
        user_id: int | None = None,
        session_id: str | None = None,
        ip_address: str | None = None):
    """Log an ad click."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ads_clicks (ad_id, user_id, session_id, ip_address)
            VALUES (?, ?, ?, ?)
        """, (ad_id, user_id, session_id, ip_address))

        # Update clicks count
        conn.execute(
            "UPDATE ads_banners SET clicks=clicks+1 WHERE id=?", (ad_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log ad click: {e}")
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════════════
# Subscription System Functions (UI only - disabled by default)
# ══════════════════════════════════════════════════════════════════════════════

def get_subscription_config() -> dict:
    """Get subscription configuration."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM subscription_config WHERE id=1").fetchone()
        return dict(row) if row else {"enabled": 0, "trial_enabled": 0}
    finally:
        conn.close()


def update_subscription_config(
        enabled: int | None = None,
        trial_enabled: int | None = None,
        trial_days: int | None = None):
    """Update subscription configuration."""
    conn = get_connection()
    try:
        updates = []  # noqa: F841
        params = []
        if enabled is not None:
            updates.append("enabled=?")
            params.append(enabled)
        if trial_enabled is not None:
            updates.append("trial_enabled=?")
            params.append(trial_enabled)
        if trial_days is not None:
            updates.append("trial_days=?")
            params.append(trial_days)

        if updates:
            updates.append("updated_at=datetime('now')")
            # Fixed: Column names are safe (from controlled list), using
            # parameterized values
            query = f"UPDATE subscription_config SET {', '.join(updates)} WHERE id=1"
            conn.execute(query, params)
            conn.commit()
    finally:
        conn.close()


def get_subscription_plans(active_only: bool = True) -> list[dict]:
    """Get all subscription plans."""
    conn = get_connection()
    try:
        query = "SELECT * FROM subscription_plans"
        if active_only:
            query += " WHERE active=1"
        query += " ORDER BY priority DESC, price ASC"
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_subscription(user_id: int) -> dict | None:
    """Get active subscription for a user."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT us.*, sp.name, sp.name_ar, sp.features
            FROM user_subscriptions us
            JOIN subscription_plans sp ON us.plan_id = sp.id
            WHERE us.user_id=? AND us.status='active' AND us.end_date >= datetime('now')
            ORDER BY us.end_date DESC
            LIMIT 1
        """, (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def is_user_premium(user_id: int) -> bool:
    """Check if user has active premium subscription."""
    subscription = get_user_subscription(user_id)
    if not subscription:
        return False
    # Plan ID 1 is Free, anything else is premium
    return subscription.get("plan_id", 1) > 1


# ══════════════════════════════════════════════════════════════════════════════
# User Preferences & Watch History Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_user_preferences(user_id: int) -> dict:
    """Get user preferences."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return dict(row)
        # Return defaults
        return {
            "user_id": user_id,
            "language": "ar",
            "quality": "auto",
            "autoplay": 1,
            "subtitles": 1,
            "theme": "dark",
            "notifications": 1
        }
    finally:
        conn.close()


def update_user_preferences(user_id: int, **preferences):
    """Update user preferences."""
    conn = get_connection()
    try:
        # Check if preferences exist
        exists = conn.execute(
            "SELECT 1 FROM user_preferences WHERE user_id=?", (user_id,)
        ).fetchone()

        if exists:
            # Update existing
            # Fixed: Validate column names against whitelist before using in
            # query
            allowed_columns = {
                'theme',
                'language',
                'notifications_enabled',
                'auto_play',
                'quality_preference',
                'subtitle_language',
                'playback_speed'}
            safe_prefs = {
                k: v for k,
                v in preferences.items() if k in allowed_columns}

            if safe_prefs:
                updates = [f"{k}=?" for k in safe_prefs.keys()]  # noqa: F841
                updates.append("updated_at=datetime('now')")
                query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id=?"
                params = list(safe_prefs.values()) + [user_id]
                conn.execute(query, params)
        else:
            # Insert new
            # Fixed: Validate column names against whitelist
            allowed_columns = {
                'theme',
                'language',
                'notifications_enabled',
                'auto_play',
                'quality_preference',
                'subtitle_language',
                'playback_speed'}
            safe_prefs = {
                k: v for k,
                v in preferences.items() if k in allowed_columns}

            if safe_prefs:
                safe_prefs["user_id"] = user_id
                cols = ", ".join(safe_prefs.keys())
                placeholders = ", ".join(["?"] * len(safe_prefs))  # noqa: F841
                query = f"INSERT INTO user_preferences ({cols}) VALUES ({placeholders})"
                conn.execute(query, list(safe_prefs.values()))

        conn.commit()
    finally:
        conn.close()


def add_to_watch_history(
        user_id: int,
        content_type: str,
        content_id: str,
        progress: int = 0,
        duration: int = 0,
        completed: int = 0,
        series_id: str | None = None,
        season_number: int | None = None,
        episode_number: int | None = None):
    """Add or update watch history entry."""
    conn = get_connection()
    try:
        # Check if entry exists
        existing = conn.execute("""
            SELECT id FROM watch_history
            WHERE user_id=? AND content_type=? AND content_id=?
        """, (user_id, content_type, content_id)).fetchone()

        if existing:
            # Update existing
            conn.execute("""
                UPDATE watch_history
                SET progress=?, duration=?, completed=?, last_watched=datetime('now')
                WHERE id=?
            """, (progress, duration, completed, existing[0]))
        else:
            # Insert new
            conn.execute("""
                INSERT INTO watch_history
                (user_id, content_type, content_id, series_id, season_number,
                 episode_number, progress, duration, completed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, content_type, content_id, series_id, season_number,
                  episode_number, progress, duration, completed))

        conn.commit()
    finally:
        conn.close()


def get_watch_history(user_id: int, limit: int = 20) -> list[dict]:
    """Get user's watch history."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM watch_history
            WHERE user_id=?
            ORDER BY last_watched DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_to_favorites(user_id: int, content_type: str, content_id: str):
    """Add content to user's favorites."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO user_favorites (user_id, content_type, content_id)
            VALUES (?, ?, ?)
        """, (user_id, content_type, content_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to add to favorites: {e}")
    finally:
        conn.close()


def remove_from_favorites(user_id: int, content_type: str, content_id: str):
    """Remove content from user's favorites."""
    conn = get_connection()
    try:
        conn.execute("""
            DELETE FROM user_favorites
            WHERE user_id=? AND content_type=? AND content_id=?
        """, (user_id, content_type, content_id))
        conn.commit()
    finally:
        conn.close()


def get_user_favorites(user_id: int) -> list[dict]:
    """Get user's favorite content."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM user_favorites
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def add_user_rating(user_id: int, content_type: str, content_id: str,
                    rating: int, review: str | None = None):
    """Add or update user rating for content."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO user_ratings (user_id, content_type, content_id, rating, review)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, content_type, content_id) DO UPDATE SET
                rating=excluded.rating,
                review=excluded.review,
                updated_at=datetime('now')
        """, (user_id, content_type, content_id, rating, review))
        conn.commit()
    finally:
        conn.close()


def get_content_ratings(content_type: str, content_id: str) -> dict:
    """Get ratings summary for content."""
    conn = get_connection()
    try:
        stats = conn.execute("""
            SELECT
                COUNT(*) as total_ratings,
                AVG(rating) as average_rating,
                SUM(CASE WHEN rating=5 THEN 1 ELSE 0 END) as five_star,
                SUM(CASE WHEN rating=4 THEN 1 ELSE 0 END) as four_star,
                SUM(CASE WHEN rating=3 THEN 1 ELSE 0 END) as three_star,
                SUM(CASE WHEN rating=2 THEN 1 ELSE 0 END) as two_star,
                SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) as one_star
            FROM user_ratings
            WHERE content_type=? AND content_id=?
        """, (content_type, content_id)).fetchone()

        reviews = conn.execute("""
            SELECT rating, review, created_at
            FROM user_ratings
            WHERE content_type=? AND content_id=? AND review IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """, (content_type, content_id)).fetchall()

        return {
            "stats": dict(stats) if stats else {},
            "recent_reviews": [dict(r) for r in reviews]
        }
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# Reviews System Functions (Enhanced ratings with 1-10 scale)
# ══════════════════════════════════════════════════════════════════════

def add_review(user_id: int, content_type: str, content_id: str,
               rating: int, comment: str | None = None, username: str | None = None):
    """Add or update a review for content."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO reviews (user_id, content_type, content_id, rating, comment, username)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, content_type, content_id) DO UPDATE SET
                rating=excluded.rating,
                comment=excluded.comment,
                username=excluded.username,
                updated_at=datetime('now')
        """, (user_id, content_type, content_id, rating, comment, username))
        conn.commit()
    finally:
        conn.close()


def get_reviews(content_type: str, content_id: str, limit: int = 50, offset: int = 0) -> list[dict]:
    """Get reviews for specific content."""
    conn = get_connection()
    try:
        # Ensure all parameters are of correct type
        content_type = str(content_type)
        content_id = str(content_id)
        limit = int(limit)
        offset = int(offset)
        
        rows = conn.execute("""
            SELECT
                r.id,
                r.content_id,
                r.content_type,
                r.user_id,
                r.username,
                r.rating,
                r.comment,
                r.created_at,
                r.updated_at,
                u.first_name,
                u.last_name
            FROM reviews r
            LEFT JOIN users u ON r.user_id = u.user_id
            WHERE r.content_type=? AND r.content_id=?
            ORDER BY r.created_at DESC
            LIMIT ? OFFSET ?
        """, (content_type, content_id, limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_review_by_id(review_id: int) -> dict | None:
    """Get a specific review by ID."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT * FROM reviews WHERE id=?
        """, (review_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_review(user_id: int, content_type: str, content_id: str) -> dict | None:
    """Get a user's review for specific content."""
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT * FROM reviews
            WHERE user_id=? AND content_type=? AND content_id=?
        """, (user_id, content_type, content_id)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_reviews(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """Get all reviews by a specific user."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM reviews
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (user_id, limit, offset)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_review(review_id: int, rating: int, comment: str | None = None) -> bool:
    """Update an existing review."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            UPDATE reviews
            SET rating=?, comment=?, updated_at=datetime('now')
            WHERE id=?
        """, (rating, comment, review_id))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_review(review_id: int) -> bool:
    """Delete a review."""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            DELETE FROM reviews WHERE id=?
        """, (review_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_reviews_stats(content_type: str, content_id: str) -> dict:
    """Get statistics for reviews of specific content."""
    conn = get_connection()
    try:
        stats = conn.execute("""
            SELECT
                COUNT(*) as total_reviews,
                AVG(rating) as average_rating,
                SUM(CASE WHEN rating >= 9 THEN 1 ELSE 0 END) as excellent,
                SUM(CASE WHEN rating >= 7 AND rating < 9 THEN 1 ELSE 0 END) as good,
                SUM(CASE WHEN rating >= 5 AND rating < 7 THEN 1 ELSE 0 END) as average,
                SUM(CASE WHEN rating >= 3 AND rating < 5 THEN 1 ELSE 0 END) as poor,
                SUM(CASE WHEN rating < 3 THEN 1 ELSE 0 END) as terrible
            FROM reviews
            WHERE content_type=? AND content_id=?
        """, (content_type, content_id)).fetchone()
        
        result = dict(stats) if stats else {}
        
        # Calculate rating distribution
        if result.get('total_reviews', 0) > 0:
            result['rating_distribution'] = {
                '9-10': result.get('excellent', 0),
                '7-8': result.get('good', 0),
                '5-6': result.get('average', 0),
                '3-4': result.get('poor', 0),
                '1-2': result.get('terrible', 0)
            }
        
        return result
    finally:
        conn.close()

        conn.close()


# ══════════════════════════════════════════════════════════════════════
# Admin Functions
# ══════════════════════════════════════════════════════════════════════

def get_all_users(limit=50, offset=0, search=None, blocked_only=False):
    """Get all users with optional filtering"""
    conn = get_connection()
    try:
        q = "SELECT * FROM users WHERE 1=1"
        params = []

        if search:
            q += " AND (username LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
            params += [f"%{search}%", f"%{search}%", f"%{search}%"]

        if blocked_only:
            q += " AND is_blocked = 1"

        q += " ORDER BY last_active DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = "SELECT COUNT(*) FROM users WHERE 1=1"
        count_params = []
        if search:
            count_q += " AND (username LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
            count_params += [f"%{search}%", f"%{search}%", f"%{search}%"]
        if blocked_only:
            count_q += " AND is_blocked = 1"

        total = conn.execute(count_q, count_params).fetchone()[0]

        return {"users": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def get_user(user_id: int):
    """Get user by ID"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_update_user(
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        is_bot: int = 0,
        language_code: str = 'ar'):
    """Create or update user"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, is_bot, language_code, last_active)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username = COALESCE(excluded.username, username),
                first_name = COALESCE(excluded.first_name, first_name),
                last_name = COALESCE(excluded.last_name, last_name),
                last_active = datetime('now'),
                updated_at = datetime('now')
        """, (user_id, username, first_name, last_name, is_bot, language_code))
        conn.commit()
        logger.info(f"User {user_id} created/updated")
    finally:
        conn.close()


def block_user(user_id: int, blocked: bool = True):
    """Block or unblock user"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE users SET is_blocked=?, updated_at=datetime('now') WHERE user_id=?",
            (1 if blocked else 0, user_id)
        )
        conn.commit()
        logger.info(f"User {user_id} {'blocked' if blocked else 'unblocked'}")
    finally:
        conn.close()


def update_user_subscription(user_id: int, is_subscribed: bool = True):
    """Update user subscription status"""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE users SET is_subscribed=?, subscription_checked_at=datetime('now'),
               updated_at=datetime('now') WHERE user_id=?""",
            (1 if is_subscribed else 0, user_id)
        )
        conn.commit()
        logger.info(
            f"User {user_id} subscription status updated: {is_subscribed}")
    finally:
        conn.close()


def get_user_subscription_status(user_id: int) -> dict:
    """Get user subscription status with timestamp"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT is_subscribed, subscription_checked_at FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if row:
            return {
                "is_subscribed": bool(row[0]),
                "subscription_checked_at": row[1]
            }
        return {"is_subscribed": False, "subscription_checked_at": None}
    finally:
        conn.close()


def delete_user(user_id: int):
    """Delete user and related data"""
    conn = get_connection()
    try:
        # Delete related data
        conn.execute("DELETE FROM watch_history WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_favorites WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_ratings WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM user_preferences WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM user_subscriptions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        conn.commit()
        logger.info(f"User {user_id} deleted")
    finally:
        conn.close()


def log_admin_action(
        admin_id: int,
        action_type: str,
        action_details: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = 'success'):
    """Log admin action for audit trail"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO audit_logs (admin_id, action_type, action_details, target_type,
                                   target_id, ip_address, user_agent, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, action_type, action_details, target_type, target_id,
              ip_address, user_agent, status))
        conn.commit()
    finally:
        conn.close()


def get_audit_logs(limit=100, offset=0, admin_id=None, action_type=None,
                   start_date=None, end_date=None):
    """Get audit logs with filtering"""
    conn = get_connection()
    try:
        q = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if admin_id:
            q += " AND admin_id=?"
            params.append(admin_id)

        if action_type:
            q += " AND action_type=?"
            params.append(action_type)

        if start_date:
            q += " AND created_at >= ?"
            params.append(start_date)

        if end_date:
            q += " AND created_at <= ?"
            params.append(end_date)

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = q.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params[:-2]).fetchone()[0]

        return {"logs": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def create_notification(
        title: str,
        message: str,
        target_type: str = 'all',
        target_ids: str | None = None,
        scheduled_at: str | None = None,
        created_by: int | None = None):
    """Create notification"""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            INSERT INTO notifications (title, message, target_type, target_ids,
                                      scheduled_at, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, message, target_type, target_ids, scheduled_at, created_by))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_notifications(limit=50, offset=0, status=None):
    """Get notifications"""
    conn = get_connection()
    try:
        q = "SELECT * FROM notifications WHERE 1=1"
        params = []

        if status:
            q += " AND status=?"
            params.append(status)

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        count_q = "SELECT COUNT(*) FROM notifications WHERE 1=1"
        count_params = []
        if status:
            count_q += " AND status=?"
            count_params.append(status)

        total = conn.execute(count_q, count_params).fetchone()[0]

        return {"notifications": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def update_notification_status(
        notification_id: int,
        status: str,
        sent_at: str | None = None):
    """Update notification status"""
    conn = get_connection()
    try:
        if sent_at:
            conn.execute(
                "UPDATE notifications SET status=?, sent_at=? WHERE id=?",
                (status, sent_at, notification_id)
            )
        else:
            conn.execute(
                "UPDATE notifications SET status=? WHERE id=?",
                (status, notification_id)
            )
        conn.commit()
    finally:
        conn.close()


def get_admin_stats():
    """Get comprehensive admin statistics"""
    conn = get_connection()
    try:
        stats = {}

        # Content stats
        stats['total_movies'] = conn.execute(
            "SELECT COUNT(*) FROM movies").fetchone()[0]
        stats['total_series'] = conn.execute(
            "SELECT COUNT(*) FROM series").fetchone()[0]
        stats['total_episodes'] = conn.execute(
            "SELECT COUNT(*) FROM episodes").fetchone()[0]
        stats['movies_with_files'] = conn.execute(
            "SELECT COUNT(*) FROM movies WHERE file_id IS NOT NULL").fetchone()[0]
        stats['episodes_with_files'] = conn.execute(
            "SELECT COUNT(*) FROM episodes WHERE file_id IS NOT NULL").fetchone()[0]

        # User stats
        stats['total_users'] = conn.execute(
            "SELECT COUNT(*) FROM users").fetchone()[0]
        stats['blocked_users'] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_blocked=1").fetchone()[0]
        stats['premium_users'] = conn.execute(
            "SELECT COUNT(*) FROM users WHERE is_premium=1").fetchone()[0]

        # Activity stats (last 24h)
        stats['views_24h'] = conn.execute(
            "SELECT COUNT(*) FROM analytics_views WHERE created_at >= datetime('now', '-1 day')"
        ).fetchone()[0]
        stats['searches_24h'] = conn.execute(
            "SELECT COUNT(*) FROM analytics_searches WHERE created_at >= datetime('now', '-1 day')"
        ).fetchone()[0]

        # Top content
        top_movies = conn.execute("""
            SELECT m.id, m.title, m.title_ar, COUNT(av.id) as views
            FROM movies m
            LEFT JOIN analytics_views av ON av.content_id = m.id AND av.content_type = 'movie'
            WHERE av.created_at >= datetime('now', '-7 days')
            GROUP BY m.id
            ORDER BY views DESC
            LIMIT 10
        """).fetchall()
        stats['top_movies'] = [dict(r) for r in top_movies]

        # Recent activity
        recent_users = conn.execute("""
            SELECT user_id, username, first_name, last_name, last_active
            FROM users
            ORDER BY last_active DESC
            LIMIT 10
        """).fetchall()
        stats['recent_users'] = [dict(r) for r in recent_users]

        return stats
    finally:
        conn.close()


def update_bot_status(
        bot_name: str,
        bot_type: str,
        status: str,
        error_message: str | None = None,
        uptime_seconds: int = 0,
        requests_count: int = 0):
    """Update bot status"""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO bot_status (bot_name, bot_type, status, error_message,
                                   uptime_seconds, requests_count, last_check)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                error_message = excluded.error_message,
                uptime_seconds = excluded.uptime_seconds,
                requests_count = excluded.requests_count,
                last_check = datetime('now')
        """, (bot_name, bot_type, status, error_message, uptime_seconds, requests_count))
        conn.commit()
    finally:
        conn.close()


def get_bot_statuses():
    """Get all bot statuses"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM bot_status
            ORDER BY last_check DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_content(content_type: str, content_id: str):
    """Delete movie or series and related data"""
    conn = get_connection()
    try:
        if content_type == 'movie':
            conn.execute("DELETE FROM movies WHERE id=?", (content_id,))
            conn.execute(
                "DELETE FROM analytics_views WHERE content_type='movie' AND content_id=?",
                (content_id,
                 ))
        elif content_type == 'series':
            conn.execute(
                "DELETE FROM episodes WHERE series_id=?", (content_id,))
            conn.execute(
                "DELETE FROM seasons WHERE series_id=?", (content_id,))
            conn.execute("DELETE FROM series WHERE id=?", (content_id,))
            conn.execute(
                "DELETE FROM analytics_views WHERE content_type='series' AND content_id=?",
                (content_id,
                 ))

        conn.commit()
        logger.info(f"Deleted {content_type} {content_id}")
    finally:
        conn.close()


# Removed duplicate get_sync_status function


def log_user_activity(user_id: int, activity_type: str, **kwargs) -> int:
    """Log user activity with detailed tracking"""
    import json
    conn = get_connection()
    try:
        # Convert dict fields to JSON
        for field in ['activity_details', 'location', 'metadata']:
            if field in kwargs and isinstance(kwargs[field], (dict, list)):
                kwargs[field] = json.dumps(kwargs[field])

        fields = ['user_id', 'activity_type'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))  # noqa: F841
        values = [user_id, activity_type] + list(kwargs.values())

        cursor = conn.execute("""
            INSERT INTO user_activity ({','.join(fields)})
            VALUES ({placeholders})
        """, values)
        activity_id = cursor.lastrowid
        conn.commit()

        # Update session activity count if session_id provided
        if 'session_id' in kwargs:
            conn.execute("""
                UPDATE user_sessions
                SET actions_count = actions_count + 1,
                    last_activity = datetime('now')
                WHERE session_id = ?
            """, (kwargs['session_id'],))
            conn.commit()

        return activity_id
    finally:
        conn.close()


def get_user_activity(user_id: int, limit: int = 50, offset: int = 0,
                      activity_type: str = None, start_date: str = None,
                      end_date: str = None) -> dict:
    """Get user activity history with filtering"""
    conn = get_connection()
    try:
        q = "SELECT * FROM user_activity WHERE user_id=?"
        params = [user_id]

        if activity_type:
            q += " AND activity_type=?"
            params.append(activity_type)

        if start_date:
            q += " AND created_at >= ?"
            params.append(start_date)

        if end_date:
            q += " AND created_at <= ?"
            params.append(end_date)

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = q.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params[:-2]).fetchone()[0]

        return {"activities": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def create_user_session(user_id: int, session_id: str, **kwargs) -> int:
    """Create a new user session"""
    import json
    conn = get_connection()
    try:
        # Convert location to JSON if dict
        if 'location' in kwargs and isinstance(kwargs['location'], dict):
            kwargs['location'] = json.dumps(kwargs['location'])

        fields = ['session_id', 'user_id'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))  # noqa: F841
        values = [session_id, user_id] + list(kwargs.values())

        cursor = conn.execute("""
            INSERT INTO user_sessions ({','.join(fields)})
            VALUES ({placeholders})
        """, values)
        session_db_id = cursor.lastrowid
        conn.commit()

        # Update user statistics
        conn.execute("""
            INSERT INTO user_statistics (user_id, total_sessions)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                total_sessions = total_sessions + 1,
                updated_at = datetime('now')
        """, (user_id,))
        conn.commit()

        return session_db_id
    finally:
        conn.close()


def update_user_session(session_id: str, **kwargs) -> None:
    """Update user session"""
    conn = get_connection()
    try:
        fields = list(kwargs.keys())
        updates = ','.join([f"{f}=?" for f in fields])  # noqa: F841

        conn.execute("""
            UPDATE user_sessions
            SET {updates}, last_activity=datetime('now')
            WHERE session_id=?
        """, list(kwargs.values()) + [session_id])
        conn.commit()
    finally:
        conn.close()


def end_user_session(session_id: str) -> None:
    """End a user session and calculate duration"""
    conn = get_connection()
    try:
        # Get session info
        session = conn.execute("""
            SELECT user_id, login_time FROM user_sessions
            WHERE session_id=? AND is_active=1
        """, (session_id,)).fetchone()

        if session:
            # Calculate duration
            duration = conn.execute("""
                SELECT CAST((julianday('now') - julianday(?)) * 86400 AS INTEGER)
            """, (session['login_time'],)).fetchone()[0]

            # Update session
            conn.execute("""
                UPDATE user_sessions
                SET is_active=0,
                    logout_time=datetime('now'),
                    session_duration=?
                WHERE session_id=?
            """, (duration, session_id))

            # Update user statistics
            conn.execute("""
                UPDATE user_statistics
                SET average_session_duration = (
                    SELECT AVG(session_duration)
                    FROM user_sessions
                    WHERE user_id=? AND session_duration > 0
                ),
                updated_at = datetime('now')
                WHERE user_id=?
            """, (session['user_id'], session['user_id']))

            conn.commit()
    finally:
        conn.close()


def get_active_sessions(user_id: int = None) -> list:
    """Get active sessions, optionally filtered by user"""
    conn = get_connection()
    try:
        if user_id:
            rows = conn.execute("""
                SELECT * FROM user_sessions
                WHERE user_id=? AND is_active=1
                ORDER BY last_activity DESC
            """, (user_id,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT * FROM user_sessions
                WHERE is_active=1
                ORDER BY last_activity DESC
            """).fetchall()

        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_user_statistics(user_id: int) -> dict:
    """Get comprehensive user statistics"""
    conn = get_connection()
    try:
        stats = conn.execute("""
            SELECT * FROM user_statistics WHERE user_id=?
        """, (user_id,)).fetchone()

        if not stats:
            # Create initial statistics
            conn.execute("""
                INSERT INTO user_statistics (user_id) VALUES (?)
            """, (user_id,))
            conn.commit()
            stats = conn.execute("""
                SELECT * FROM user_statistics WHERE user_id=?
            """, (user_id,)).fetchone()

        return dict(stats) if stats else None
    finally:
        conn.close()


def update_user_statistics(user_id: int, **kwargs) -> None:
    """Update user statistics"""
    conn = get_connection()
    try:
        fields = list(kwargs.keys())
        updates = ','.join([f"{f}=?" for f in fields])  # noqa: F841

        conn.execute("""
            INSERT INTO user_statistics (user_id, {','.join(fields)}, updated_at)
            VALUES (?, {','.join(['?']*len(fields))}, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET {updates}, updated_at=datetime('now')
        """, [user_id] + list(kwargs.values()) + list(kwargs.values()))
        conn.commit()
    finally:
        conn.close()


def calculate_user_statistics(user_id: int) -> dict:
    """Calculate and update comprehensive user statistics"""
    conn = get_connection()
    try:
        # Calculate various statistics
        stats = {}

        # Total logins
        stats['total_logins'] = conn.execute("""
            SELECT COUNT(*) FROM user_activity
            WHERE user_id=? AND activity_type='login'
        """, (user_id,)).fetchone()[0]

        # Total sessions
        stats['total_sessions'] = conn.execute("""
            SELECT COUNT(*) FROM user_sessions WHERE user_id=?
        """, (user_id,)).fetchone()[0]

        # Total watch time from watch_history
        watch_time = conn.execute("""
            SELECT SUM(duration) FROM watch_history
            WHERE user_id=? AND duration IS NOT NULL
        """, (user_id,)).fetchone()[0]
        stats['total_watch_time'] = watch_time or 0

        # Movies and episodes watched
        stats['total_movies_watched'] = conn.execute("""
            SELECT COUNT(DISTINCT content_id) FROM watch_history
            WHERE user_id=? AND content_type='movie' AND completed=1
        """, (user_id,)).fetchone()[0]

        stats['total_episodes_watched'] = conn.execute("""
            SELECT COUNT(DISTINCT content_id) FROM watch_history
            WHERE user_id=? AND content_type='episode' AND completed=1
        """, (user_id,)).fetchone()[0]

        # Total searches
        stats['total_searches'] = conn.execute("""
            SELECT COUNT(*) FROM user_activity
            WHERE user_id=? AND activity_type='search'
        """, (user_id,)).fetchone()[0]

        # Total ratings
        stats['total_ratings'] = conn.execute("""
            SELECT COUNT(*) FROM user_ratings WHERE user_id=?
        """, (user_id,)).fetchone()[0]

        # Total favorites
        stats['total_favorites'] = conn.execute("""
            SELECT COUNT(*) FROM user_favorites WHERE user_id=?
        """, (user_id,)).fetchone()[0]

        # Average session duration
        avg_duration = conn.execute("""
            SELECT AVG(session_duration) FROM user_sessions
            WHERE user_id=? AND session_duration > 0
        """, (user_id,)).fetchone()[0]
        stats['average_session_duration'] = int(
            avg_duration) if avg_duration else 0

        # Completion rate
        total_started = conn.execute("""
            SELECT COUNT(*) FROM watch_history WHERE user_id=?
        """, (user_id,)).fetchone()[0]

        total_completed = conn.execute("""
            SELECT COUNT(*) FROM watch_history WHERE user_id=? AND completed=1
        """, (user_id,)).fetchone()[0]

        stats['completion_rate'] = (
            total_completed /
            total_started *
            100) if total_started > 0 else 0.0

        # Update statistics
        update_user_statistics(user_id, **stats)

        return stats
    finally:
        conn.close()


def register_user_device(user_id: int, device_id: str, **kwargs) -> int:
    """Register or update user device"""
    conn = get_connection()
    try:
        fields = ['user_id', 'device_id'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))  # noqa: F841
        values = [user_id, device_id] + list(kwargs.values())

        # Update fields for conflict
        update_fields = list(kwargs.keys()) + ['last_used', 'total_sessions']
        updates = ','.join([f"{f}=?" for f in update_fields])  # noqa: F841
        update_values = list(kwargs.values()) + \
            ["datetime('now')", "total_sessions + 1"]

        cursor = conn.execute("""
            INSERT INTO user_devices ({','.join(fields)})
            VALUES ({placeholders})
            ON CONFLICT(device_id) DO UPDATE SET
                {updates}
        """, values + update_values)

        device_db_id = cursor.lastrowid
        conn.commit()
        return device_db_id
    finally:
        conn.close()


def get_user_devices(user_id: int) -> list:
    """Get all devices for a user"""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM user_devices
            WHERE user_id=?
            ORDER BY last_used DESC
        """, (user_id,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_watch_progress(
        user_id: int,
        content_type: str,
        content_id: str,
        progress_seconds: int,
        total_seconds: int,
        **kwargs) -> None:
    """Update user's watch progress for content"""
    conn = get_connection()
    try:
        progress_percent = (
            progress_seconds /
            total_seconds *
            100) if total_seconds > 0 else 0
        completed = 1 if progress_percent >= 90 else 0

        # Prepare additional fields
        extra_fields = list(kwargs.keys())
        extra_values = list(kwargs.values())

        all_fields = [
            'user_id',
            'content_type',
            'content_id',
            'progress_seconds',
            'total_seconds',
            'progress_percent',
            'completed'] + extra_fields
        all_values = [
            user_id,
            content_type,
            content_id,
            progress_seconds,
            total_seconds,
            progress_percent,
            completed] + extra_values

        placeholders = ','.join(['?'] * len(all_fields))  # noqa: F841

        # Update fields
        update_fields = [
            'progress_seconds',
            'total_seconds',
            'progress_percent',
            'completed',
            'last_watched',
            'watch_count'] + extra_fields
        updates = ','.join([f"{f}=?" for f in update_fields])  # noqa: F841
        update_values = [
            progress_seconds,
            total_seconds,
            progress_percent,
            completed,
            "datetime('now')",
            "watch_count + 1"] + extra_values

        conn.execute("""
            INSERT INTO user_watch_progress ({','.join(all_fields)})
            VALUES ({placeholders})
            ON CONFLICT(user_id, content_type, content_id) DO UPDATE SET
                {updates}, updated_at=datetime('now')
        """, all_values + update_values)
        conn.commit()

        # Update user statistics if completed
        if completed:
            if content_type == 'movie':
                conn.execute("""
                    UPDATE user_statistics
                    SET total_movies_watched = total_movies_watched + 1,
                        updated_at = datetime('now')
                    WHERE user_id=?
                """, (user_id,))
            elif content_type == 'episode':
                conn.execute("""
                    UPDATE user_statistics
                    SET total_episodes_watched = total_episodes_watched + 1,
                        updated_at = datetime('now')
                    WHERE user_id=?
                """, (user_id,))
            conn.commit()
    finally:
        conn.close()


def get_watch_progress(user_id: int, content_type: str = None,
                       limit: int = 50, offset: int = 0) -> dict:
    """Get user's watch progress"""
    conn = get_connection()
    try:
        q = "SELECT * FROM user_watch_progress WHERE user_id=?"
        params = [user_id]

        if content_type:
            q += " AND content_type=?"
            params.append(content_type)

        q += " ORDER BY last_watched DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = q.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params[:-2]).fetchone()[0]

        return {"progress": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def create_database_backup(backup_name: str, backup_path: str,
                           backup_type: str = 'manual', **kwargs) -> int:
    """Create database backup record"""
    import json
    conn = get_connection()
    try:
        # Convert tables_included to JSON if list
        if 'tables_included' in kwargs and isinstance(
                kwargs['tables_included'], list):
            kwargs['tables_included'] = json.dumps(kwargs['tables_included'])

        fields = ['backup_name', 'backup_path',
                  'backup_type'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))  # noqa: F841
        values = [backup_name, backup_path,
                  backup_type] + list(kwargs.values())

        cursor = conn.execute("""
            INSERT INTO database_backups ({','.join(fields)})
            VALUES ({placeholders})
        """, values)
        backup_id = cursor.lastrowid
        conn.commit()
        return backup_id
    finally:
        conn.close()


def get_database_backups(limit: int = 50, offset: int = 0,
                         backup_type: str = None) -> dict:
    """Get database backup history"""
    conn = get_connection()
    try:
        q = "SELECT * FROM database_backups WHERE 1=1"
        params = []

        if backup_type:
            q += " AND backup_type=?"
            params.append(backup_type)

        q += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = q.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params[:-2]).fetchone()[0]

        return {"backups": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def log_sync_operation(sync_type: str, **kwargs) -> int:
    """Log database sync operation"""
    import json
    conn = get_connection()
    try:
        # Convert tables_synced to JSON if list
        if 'tables_synced' in kwargs and isinstance(
                kwargs['tables_synced'], list):
            kwargs['tables_synced'] = json.dumps(kwargs['tables_synced'])

        fields = ['sync_type'] + list(kwargs.keys())
        placeholders = ','.join(['?'] * len(fields))  # noqa: F841
        values = [sync_type] + list(kwargs.values())

        cursor = conn.execute("""
            INSERT INTO sync_history ({','.join(fields)})
            VALUES ({placeholders})
        """, values)
        sync_id = cursor.lastrowid
        conn.commit()
        return sync_id
    finally:
        conn.close()


def update_sync_operation(sync_id: int, **kwargs) -> None:
    """Update sync operation record"""
    import json
    conn = get_connection()
    try:
        # Convert tables_synced to JSON if list
        if 'tables_synced' in kwargs and isinstance(
                kwargs['tables_synced'], list):
            kwargs['tables_synced'] = json.dumps(kwargs['tables_synced'])

        fields = list(kwargs.keys())
        updates = ','.join([f"{f}=?" for f in fields])  # noqa: F841

        conn.execute("""
            UPDATE sync_history SET {updates} WHERE id=?
        """, list(kwargs.values()) + [sync_id])
        conn.commit()
    finally:
        conn.close()


def get_sync_history(limit: int = 50, offset: int = 0,
                     sync_type: str = None, status: str = None) -> dict:
    """Get sync operation history"""
    conn = get_connection()
    try:
        q = "SELECT * FROM sync_history WHERE 1=1"
        params = []

        if sync_type:
            q += " AND sync_type=?"
            params.append(sync_type)

        if status:
            q += " AND status=?"
            params.append(status)

        q += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params += [limit, offset]

        rows = conn.execute(q, params).fetchall()

        # Get total count
        count_q = q.split("ORDER BY")[0].replace("SELECT *", "SELECT COUNT(*)")
        total = conn.execute(count_q, params[:-2]).fetchone()[0]

        return {"syncs": [dict(r) for r in rows], "total": total}
    finally:
        conn.close()


def get_comprehensive_user_data(user_id: int) -> dict:
    """Get all user data in one call (for GDPR export)"""
    conn = get_connection()
    try:
        data = {}

        # Basic user info
        user = conn.execute(
            "SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        data['user'] = dict(user) if user else None

        # Profile
        profile = conn.execute(
            "SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
        data['profile'] = dict(profile) if profile else None

        # Statistics
        stats = conn.execute(
            "SELECT * FROM user_statistics WHERE user_id=?", (user_id,)).fetchone()
        data['statistics'] = dict(stats) if stats else None

        # Preferences
        prefs = conn.execute(
            "SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
        data['preferences'] = dict(prefs) if prefs else None

        # Watch history
        watch_history = conn.execute("""
            SELECT * FROM watch_history WHERE user_id=? ORDER BY last_watched DESC
        """, (user_id,)).fetchall()
        data['watch_history'] = [dict(r) for r in watch_history]

        # Favorites
        favorites = conn.execute("""
            SELECT * FROM user_favorites WHERE user_id=? ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        data['favorites'] = [dict(r) for r in favorites]

        # Ratings
        ratings = conn.execute("""
            SELECT * FROM user_ratings WHERE user_id=? ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        data['ratings'] = [dict(r) for r in ratings]

        # Devices
        devices = conn.execute("""
            SELECT * FROM user_devices WHERE user_id=? ORDER BY last_used DESC
        """, (user_id,)).fetchall()
        data['devices'] = [dict(r) for r in devices]

        # Recent activity (last 100)
        activity = conn.execute("""
            SELECT * FROM user_activity WHERE user_id=?
            ORDER BY created_at DESC LIMIT 100
        """, (user_id,)).fetchall()
        data['recent_activity'] = [dict(r) for r in activity]

        return data
    finally:
        conn.close()


def delete_user_data(user_id: int, keep_analytics: bool = True) -> None:
    """Delete all user data (GDPR right to be forgotten)"""
    conn = get_connection()
    try:
        # Delete from all user tables
        conn.execute("DELETE FROM user_profiles WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM user_preferences WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_statistics WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_favorites WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_ratings WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM watch_history WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM user_watch_progress WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_devices WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
        conn.execute(
            "DELETE FROM user_subscriptions WHERE user_id=?", (user_id,))

        if not keep_analytics:
            # Anonymize analytics data instead of deleting
            conn.execute("""
                UPDATE user_activity SET user_id=0 WHERE user_id=?
            """, (user_id,))
            conn.execute("""
                UPDATE analytics_views SET user_id=0 WHERE user_id=?
            """, (user_id,))
            conn.execute("""
                UPDATE analytics_searches SET user_id=0 WHERE user_id=?
            """, (user_id,))

        # Mark user as deleted
        conn.execute("""
            UPDATE users SET
                username='[deleted]',
                first_name='[deleted]',
                last_name='[deleted]',
                is_blocked=1,
                updated_at=datetime('now')
            WHERE user_id=?
        """, (user_id,))

        conn.commit()

        # Log the deletion
        log_admin_action(
            admin_id=0,
            action_type='user_data_deletion',
            action_details=f'User {user_id} data deleted (GDPR)',
            target_type='user',
            target_id=str(user_id)
        )
    finally:
        conn.close()
