import sqlite3
import os
import logging
from huggingface_hub import HfApi, hf_hub_download
from app.config import HF_TOKEN, HF_DATASET_NAME, DB_PATH, DATASET_DB_FILE

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


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
            local_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            conn.close()
            logger.info(f"Local DB: {local_count} movies, age: {db_age_hours:.1f}h")
        except Exception as e:
            logger.warning(f"Could not read local DB: {e}")
            local_count = 0
    
    # Download from HuggingFace if local doesn't exist or is old (>24h)
    should_download = not db_exists or (db_exists and (time.time() - os.path.getmtime(DB_PATH)) / 3600 > 24)
    
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
            hf_count = cursor.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
            conn.close()
            
            logger.info(f"HuggingFace DB: {hf_count} movies")
            
            # Smart decision: only use HF version if it has more or equal data
            if hf_count >= local_count:
                logger.info(f"Using HuggingFace DB ({hf_count} >= {local_count})")
                if hf_path != DB_PATH:
                    import shutil
                    shutil.copy(hf_path, DB_PATH)
            else:
                logger.warning(f"⚠️  HuggingFace has LESS data ({hf_count} < {local_count})")
                logger.warning(f"Keeping local database to prevent data loss")
                logger.info(f"Consider uploading local DB to HuggingFace")
                
        except Exception as e:
            logger.warning(f"Could not download from HuggingFace: {e}")
            if not db_exists:
                logger.info("Will create fresh database")
    else:
        logger.info(f"Using existing local database: {DB_PATH}")

    conn = get_connection()
    _create_schema(conn)
    conn.close()
    logger.info("Database initialized.")


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
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (series_id) REFERENCES series(id),
            UNIQUE(series_id, season_number, episode_number)
        );

        CREATE TABLE IF NOT EXISTS topic_series_map (
            topic_id    INTEGER PRIMARY KEY,
            series_id   TEXT NOT NULL,
            FOREIGN KEY (series_id) REFERENCES series(id)
        );

        CREATE INDEX IF NOT EXISTS idx_movies_tmdb ON movies(tmdb_id);
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
        
        CREATE INDEX IF NOT EXISTS idx_watch_history_user ON watch_history(user_id, last_watched DESC);
        CREATE INDEX IF NOT EXISTS idx_watch_history_content ON watch_history(content_type, content_id);
        CREATE INDEX IF NOT EXISTS idx_user_favorites_user ON user_favorites(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_ratings_content ON user_ratings(content_type, content_id);
    """)
    conn.commit()


def push_db_to_hf():
    """Upload SQLite DB to HuggingFace Dataset."""
    try:
        api = HfApi(token=HF_TOKEN)
        api.upload_file(
            path_or_fileobj=DB_PATH,
            path_in_repo=DATASET_DB_FILE,
            repo_id=HF_DATASET_NAME,
            repo_type="dataset",
            commit_message="Auto-sync: update database",
        )
        logger.info("Database pushed to HuggingFace Dataset successfully.")
    except Exception as e:
        logger.error(f"Failed to push DB to HF: {e}")


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
            row = conn.execute("SELECT * FROM movies WHERE id=?", (movie_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM movies WHERE tmdb_id=?", (tmdb_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_movie_file(movie_id: str, file_id: str, file_size: int, duration: int, message_id: int):
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
        logger.info(f"[db] Movie file updated: id={movie_id} file_id={file_id[:20]}…")
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
            row = conn.execute("SELECT * FROM series WHERE id=?", (series_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM series WHERE tmdb_id=?", (tmdb_id,)).fetchone()
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


def get_episode(series_id: str, season_number: int, episode_number: int) -> dict | None:
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
        movies_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
        series_count = conn.execute("SELECT COUNT(*) FROM series").fetchone()[0]
        episodes_count = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
        latest_movies = conn.execute(
            "SELECT id, title, title_ar, poster_path, backdrop_path, rating, release_date, file_id "
            "FROM movies ORDER BY created_at DESC LIMIT 8"
        ).fetchall()
        latest_series = conn.execute(
            "SELECT id, title, title_ar, poster_path, backdrop_path, rating, first_air_date "
            "FROM series ORDER BY created_at DESC LIMIT 6"
        ).fetchall()
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
        return {"last_message_id": 0, "last_sync_time": None, "sync_type": "none"}
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
        logger.info(f"Sync status updated: last_msg={last_message_id}, type={sync_type}")
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


def log_error(error_type: str, error_message: str, endpoint: str | None = None,
              user_id: int | None = None, ip_address: str | None = None, stack_trace: str | None = None):
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
        cutoff = f"datetime('now', '-{days} days')"
        
        total_views = conn.execute(
            f"SELECT COUNT(*) FROM analytics_views WHERE created_at >= {cutoff}"
        ).fetchone()[0]
        
        total_searches = conn.execute(
            f"SELECT COUNT(*) FROM analytics_searches WHERE created_at >= {cutoff}"
        ).fetchone()[0]
        
        total_errors = conn.execute(
            f"SELECT COUNT(*) FROM analytics_errors WHERE created_at >= {cutoff}"
        ).fetchone()[0]
        
        popular_content = conn.execute(f"""
            SELECT content_type, content_id, COUNT(*) as views
            FROM analytics_views 
            WHERE created_at >= {cutoff}
            GROUP BY content_type, content_id
            ORDER BY views DESC
            LIMIT 10
        """).fetchall()
        
        popular_searches = conn.execute(f"""
            SELECT query, COUNT(*) as count
            FROM analytics_searches 
            WHERE created_at >= {cutoff}
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


def update_ads_config(enabled: int | None = None, banner_enabled: int | None = None,
                      banner_interval: int | None = None, banner_duration: int | None = None):
    """Update ads configuration."""
    conn = get_connection()
    try:
        updates = []
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


def log_ad_impression(ad_id: int, user_id: int | None = None, session_id: str | None = None,
                      ip_address: str | None = None, page_url: str | None = None):
    """Log an ad impression."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ads_impressions (ad_id, user_id, session_id, ip_address, page_url)
            VALUES (?, ?, ?, ?, ?)
        """, (ad_id, user_id, session_id, ip_address, page_url))
        
        # Update impressions count
        conn.execute("UPDATE ads_banners SET impressions=impressions+1 WHERE id=?", (ad_id,))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log ad impression: {e}")
    finally:
        conn.close()


def log_ad_click(ad_id: int, user_id: int | None = None, session_id: str | None = None,
                 ip_address: str | None = None):
    """Log an ad click."""
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO ads_clicks (ad_id, user_id, session_id, ip_address)
            VALUES (?, ?, ?, ?)
        """, (ad_id, user_id, session_id, ip_address))
        
        # Update clicks count
        conn.execute("UPDATE ads_banners SET clicks=clicks+1 WHERE id=?", (ad_id,))
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
        row = conn.execute("SELECT * FROM subscription_config WHERE id=1").fetchone()
        return dict(row) if row else {"enabled": 0, "trial_enabled": 0}
    finally:
        conn.close()


def update_subscription_config(enabled: int | None = None, trial_enabled: int | None = None,
                                trial_days: int | None = None):
    """Update subscription configuration."""
    conn = get_connection()
    try:
        updates = []
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
        row = conn.execute("SELECT * FROM user_preferences WHERE user_id=?", (user_id,)).fetchone()
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
            updates = [f"{k}=?" for k in preferences.keys()]
            updates.append("updated_at=datetime('now')")
            query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id=?"
            params = list(preferences.values()) + [user_id]
            conn.execute(query, params)
        else:
            # Insert new
            preferences["user_id"] = user_id
            cols = ", ".join(preferences.keys())
            placeholders = ", ".join(["?"] * len(preferences))
            query = f"INSERT INTO user_preferences ({cols}) VALUES ({placeholders})"
            conn.execute(query, list(preferences.values()))
        
        conn.commit()
    finally:
        conn.close()


def add_to_watch_history(user_id: int, content_type: str, content_id: str,
                         progress: int = 0, duration: int = 0, completed: int = 0,
                         series_id: str | None = None, season_number: int | None = None,
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
