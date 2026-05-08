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
    """Download DB from HF Dataset if exists, otherwise create fresh."""
    try:
        local_path = hf_hub_download(
            repo_id=HF_DATASET_NAME,
            filename=DATASET_DB_FILE,
            repo_type="dataset",
            token=HF_TOKEN,
            local_dir="/tmp",
        )
        logger.info(f"Downloaded DB from HuggingFace: {local_path}")
        if local_path != DB_PATH:
            import shutil
            shutil.copy(local_path, DB_PATH)
    except Exception as e:
        logger.warning(f"Could not download DB from HF (will create fresh): {e}")

    conn = get_connection()
    _create_schema(conn)
    conn.close()
    logger.info("Database initialized.")


def _create_schema(conn: sqlite3.Connection):
    conn.executescript("""
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
