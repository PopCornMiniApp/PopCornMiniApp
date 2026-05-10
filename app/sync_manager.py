"""
Synchronization Manager for PopCorn Bot
Manages all synchronization between Telegram group, Database, and Frontend JSON files.
Fixes the "Peer id invalid" error and ensures data consistency.
"""
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict
from pathlib import Path

from pyrogram import Client
from pyrogram.errors import PeerIdInvalid, FloodWait, ChannelPrivate

from app.config import (
    PRIVATE_GROUP_ID,
    SESSION_1_API_ID,
    SESSION_1_API_HASH
)
from app import database as db
from app.scanner import run_full_scan

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Sync Status Tracking
# ══════════════════════════════════════════════════════════════════════════════


class SyncStatus:
    """Track synchronization status."""

    def __init__(self):
        self.telegram_to_db_status = "idle"
        self.db_to_frontend_status = "idle"
        self.last_telegram_sync = None
        self.last_frontend_sync = None
        self.telegram_sync_errors = []
        self.frontend_sync_errors = []
        self.telegram_sync_count = 0
        self.frontend_sync_count = 0

    def to_dict(self) -> Dict:
        """Convert status to dictionary."""
        return {
            "telegram_to_db": {
                "status": self.telegram_to_db_status,
                "last_sync": self.last_telegram_sync,
                "sync_count": self.telegram_sync_count,
                "errors": self.telegram_sync_errors[-5:]  # Last 5 errors
            },
            "db_to_frontend": {
                "status": self.db_to_frontend_status,
                "last_sync": self.last_frontend_sync,
                "sync_count": self.frontend_sync_count,
                "errors": self.frontend_sync_errors[-5:]
            }
        }


# Global sync status
sync_status = SyncStatus()


# ══════════════════════════════════════════════════════════════════════════════
# Telegram to Database Sync
# ══════════════════════════════════════════════════════════════════════════════

async def sync_telegram_to_database(
    force_full_scan: bool = False,
    progress_callback=None
) -> Dict:
    """
    Sync content from Telegram group to database.
    Fixes the "Peer id invalid" error by using proper Pyrogram client.

    Args:
        force_full_scan: If True, perform full scan instead of incremental
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with sync results
    """
    logger.info("🔄 Starting Telegram → Database sync...")
    sync_status.telegram_to_db_status = "running"

    result = {
        "success": False,
        "message": "",
        "movies_synced": 0,
        "series_synced": 0,
        "episodes_synced": 0,
        "errors": [],
        "duration": 0
    }

    start_time = datetime.now()

    try:
        # Validate configuration
        if not SESSION_1_API_ID or not SESSION_1_API_HASH:
            error_msg = "❌ Pyrogram session credentials not configured"
            logger.error(error_msg)
            result["message"] = error_msg
            result["errors"].append(error_msg)
            sync_status.telegram_sync_errors.append({
                "time": datetime.now().isoformat(),
                "error": error_msg
            })
            return result

        if not PRIVATE_GROUP_ID:
            error_msg = "❌ Private group ID not configured"
            logger.error(error_msg)
            result["message"] = error_msg
            result["errors"].append(error_msg)
            sync_status.telegram_sync_errors.append({
                "time": datetime.now().isoformat(),
                "error": error_msg
            })
            return result

        # Create Pyrogram client to fix "Peer id invalid" error
        logger.info("📱 Initializing Pyrogram client...")
        app = Client(
            "popcorn_sync_session",
            api_id=SESSION_1_API_ID,
            api_hash=SESSION_1_API_HASH,
            workdir="/tmp"
        )

        async with app:
            logger.info("✅ Pyrogram client connected")

            # Verify group access
            try:
                chat = await app.get_chat(PRIVATE_GROUP_ID)
                logger.info(f"✅ Group verified: {chat.title}")

                if progress_callback:
                    await progress_callback(f"📱 Connected to: {chat.title}")

            except PeerIdInvalid:
                error_msg = f"❌ Invalid peer ID: {PRIVATE_GROUP_ID}. Make sure the bot is a member of the group."
                logger.error(error_msg)
                result["message"] = error_msg
                result["errors"].append(error_msg)
                sync_status.telegram_sync_errors.append({
                    "time": datetime.now().isoformat(),
                    "error": error_msg
                })
                return result

            except ChannelPrivate:
                error_msg = f"❌ Group is private or bot doesn't have access: {PRIVATE_GROUP_ID}"
                logger.error(error_msg)
                result["message"] = error_msg
                result["errors"].append(error_msg)
                sync_status.telegram_sync_errors.append({
                    "time": datetime.now().isoformat(),
                    "error": error_msg
                })
                return result

            # Perform sync using scanner
            logger.info("🔍 Starting content scan...")

            if progress_callback:
                await progress_callback("🔍 Scanning Telegram group for content...")

            # Use the existing scanner with the Pyrogram client
            try:
                await run_full_scan(app)

                # Get sync statistics
                stats = db.get_stats()
                result["movies_synced"] = stats.get("total_movies", 0)
                result["series_synced"] = stats.get("total_series", 0)
                result["episodes_synced"] = stats.get("total_episodes", 0)

                result["success"] = True
                result["message"] = "✅ Telegram sync completed successfully"

                logger.info(
                    f"✅ Sync completed: {result['movies_synced']} movies, "
                    f"{result['series_synced']} series, {result['episodes_synced']} episodes")

                if progress_callback:
                    await progress_callback(
                        f"✅ Synced: {result['movies_synced']} movies, "
                        f"{result['series_synced']} series, {result['episodes_synced']} episodes"
                    )

            except FloodWait as e:
                error_msg = f"⏳ Flood wait: {e.value} seconds"
                logger.warning(error_msg)
                result["errors"].append(error_msg)
                await asyncio.sleep(e.value)

            except Exception as e:
                error_msg = f"❌ Scan error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                result["errors"].append(error_msg)
                sync_status.telegram_sync_errors.append({
                    "time": datetime.now().isoformat(),
                    "error": error_msg
                })

        # Update sync status
        sync_status.last_telegram_sync = datetime.now().isoformat()
        sync_status.telegram_sync_count += 1

        # Log sync operation
        duration = (datetime.now() - start_time).total_seconds()
        result["duration"] = duration

        db.log_sync_operation(
            sync_type="telegram_to_db",
            status="completed" if result["success"] else "failed",
            records_synced=result["movies_synced"] +
            result["series_synced"] +
            result["episodes_synced"],
            duration_seconds=int(duration),
            error_message="; ".join(
                result["errors"]) if result["errors"] else None)

    except Exception as e:
        error_msg = f"❌ Sync failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result["message"] = error_msg
        result["errors"].append(error_msg)
        sync_status.telegram_sync_errors.append({
            "time": datetime.now().isoformat(),
            "error": error_msg
        })

        # Log failed sync
        db.log_sync_operation(
            sync_type="telegram_to_db",
            status="failed",
            error_message=error_msg
        )

    finally:
        sync_status.telegram_to_db_status = "idle"

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Database to Frontend Sync
# ══════════════════════════════════════════════════════════════════════════════

async def sync_database_to_frontend(progress_callback=None) -> Dict:
    """
    Sync data from database to frontend JSON files.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with sync results
    """
    logger.info("🔄 Starting Database → Frontend sync...")
    sync_status.db_to_frontend_status = "running"

    result = {
        "success": False,
        "message": "",
        "files_updated": [],
        "errors": [],
        "duration": 0
    }

    start_time = datetime.now()

    try:
        # Define frontend data path
        frontend_data_path = Path("PopCorn/frontend/src/frontend_data.json")

        if progress_callback:
            await progress_callback("📊 Fetching data from database...")

        # Get data from database
        movies = db.get_movies()
        series_list = db.get_series_list()
        stats = db.get_stats()

        logger.info(
            f"📊 Fetched: {len(movies)} movies, {len(series_list)} series")

        # Prepare frontend data structure
        frontend_data = {
            "movies": [],
            "series": [],
            "stats": stats,
            "last_updated": datetime.now().isoformat()
        }

        # Process movies
        for movie in movies:
            if movie.get("file_id"):  # Only include movies with files
                frontend_data["movies"].append({
                    "id": movie["id"],
                    "tmdb_id": movie.get("tmdb_id"),
                    "title": movie["title"],
                    "title_ar": movie.get("title_ar"),
                    "overview": movie.get("overview"),
                    "overview_ar": movie.get("overview_ar"),
                    "poster_path": movie.get("poster_path"),
                    "backdrop_path": movie.get("backdrop_path"),
                    "release_date": movie.get("release_date"),
                    "runtime": movie.get("runtime"),
                    "genres": movie.get("genres"),
                    "rating": movie.get("rating"),
                    "vote_count": movie.get("vote_count"),
                    "has_file": True
                })

        # Process series
        for series in series_list:
            series_data = {
                "id": series["id"],
                "tmdb_id": series.get("tmdb_id"),
                "title": series["title"],
                "title_ar": series.get("title_ar"),
                "overview": series.get("overview"),
                "overview_ar": series.get("overview_ar"),
                "poster_path": series.get("poster_path"),
                "backdrop_path": series.get("backdrop_path"),
                "first_air_date": series.get("first_air_date"),
                "genres": series.get("genres"),
                "rating": series.get("rating"),
                "vote_count": series.get("vote_count"),
                "total_seasons": series.get("total_seasons", 0),
                "status": series.get("status"),
                "seasons": []
            }

            # Get seasons for this series
            seasons = db.get_series_seasons(series["id"])
            for season in seasons:
                season_data = {
                    "season_number": season["season_number"],
                    "name": season.get("name"),
                    "episode_count": season.get("episode_count", 0),
                    "air_date": season.get("air_date"),
                    "poster_path": season.get("poster_path")
                }
                series_data["seasons"].append(season_data)

            frontend_data["series"].append(series_data)

        if progress_callback:
            await progress_callback(f"💾 Writing data to {frontend_data_path}...")

        # Write to frontend JSON file
        frontend_data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(frontend_data_path, 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, ensure_ascii=False, indent=2)

        result["files_updated"].append(str(frontend_data_path))
        logger.info(f"✅ Updated: {frontend_data_path}")

        # Also update root-level frontend_data.json for backward compatibility
        root_frontend_path = Path("PopCorn/frontend_data.json")
        with open(root_frontend_path, 'w', encoding='utf-8') as f:
            json.dump(frontend_data, f, ensure_ascii=False, indent=2)

        result["files_updated"].append(str(root_frontend_path))
        logger.info(f"✅ Updated: {root_frontend_path}")

        result["success"] = True
        result["message"] = f"✅ Frontend sync completed: {len(movies)} movies, {len(series_list)} series"

        # Update sync status
        sync_status.last_frontend_sync = datetime.now().isoformat()
        sync_status.frontend_sync_count += 1

        # Log sync operation
        duration = (datetime.now() - start_time).total_seconds()
        result["duration"] = duration

        db.log_sync_operation(
            sync_type="db_to_frontend",
            status="completed",
            records_synced=len(movies) + len(series_list),
            duration_seconds=int(duration)
        )

        if progress_callback:
            await progress_callback(result["message"])

    except Exception as e:
        error_msg = f"❌ Frontend sync failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result["message"] = error_msg
        result["errors"].append(error_msg)
        sync_status.frontend_sync_errors.append({
            "time": datetime.now().isoformat(),
            "error": error_msg
        })

        # Log failed sync
        db.log_sync_operation(
            sync_type="db_to_frontend",
            status="failed",
            error_message=error_msg
        )

    finally:
        sync_status.db_to_frontend_status = "idle"

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Full Sync (Telegram → Database → Frontend)
# ══════════════════════════════════════════════════════════════════════════════

async def full_sync(progress_callback=None) -> Dict:
    """
    Perform full synchronization: Telegram → Database → Frontend.

    Args:
        progress_callback: Optional callback for progress updates

    Returns:
        Dict with complete sync results
    """
    logger.info("🔄 Starting FULL SYNC (Telegram → Database → Frontend)...")

    result = {
        "success": False,
        "message": "",
        "telegram_sync": {},
        "frontend_sync": {},
        "total_duration": 0
    }

    start_time = datetime.now()

    try:
        # Step 1: Telegram → Database
        if progress_callback:
            await progress_callback("📱 Step 1/2: Syncing Telegram → Database...")

        telegram_result = await sync_telegram_to_database(progress_callback=progress_callback)
        result["telegram_sync"] = telegram_result

        if not telegram_result["success"]:
            result["message"] = "❌ Telegram sync failed"
            return result

        # Step 2: Database → Frontend
        if progress_callback:
            await progress_callback("💾 Step 2/2: Syncing Database → Frontend...")

        frontend_result = await sync_database_to_frontend(progress_callback=progress_callback)
        result["frontend_sync"] = frontend_result

        if not frontend_result["success"]:
            result["message"] = "⚠️ Telegram sync succeeded but frontend sync failed"
            return result

        # Both syncs successful
        result["success"] = True
        result["message"] = "✅ Full sync completed successfully!"

        duration = (datetime.now() - start_time).total_seconds()
        result["total_duration"] = duration

        logger.info(f"✅ Full sync completed in {duration:.2f} seconds")

        if progress_callback:
            await progress_callback(f"✅ Full sync completed in {duration:.2f}s!")

    except Exception as e:
        error_msg = f"❌ Full sync failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        result["message"] = error_msg

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Sync Status and Monitoring
# ══════════════════════════════════════════════════════════════════════════════

def get_sync_status() -> Dict:
    """Get current synchronization status."""
    return sync_status.to_dict()


async def verify_sync_health() -> Dict:
    """
    Verify the health of all sync components.

    Returns:
        Dict with health check results
    """
    logger.info("🏥 Performing sync health check...")

    health = {
        "overall_status": "healthy",
        "checks": {
            "database": {"status": "unknown", "message": ""},
            "telegram_access": {"status": "unknown", "message": ""},
            "frontend_files": {"status": "unknown", "message": ""}
        },
        "recommendations": []
    }

    # Check database
    try:
        stats = db.get_stats()
        if stats:
            health["checks"]["database"]["status"] = "healthy"
            health["checks"]["database"][
                "message"] = f"✅ Database accessible ({stats.get('total_movies', 0)} movies, {stats.get('total_series', 0)} series)"
        else:
            health["checks"]["database"]["status"] = "warning"
            health["checks"]["database"]["message"] = "⚠️ Database empty"
            health["recommendations"].append(
                "Run Telegram sync to populate database")
    except Exception as e:
        health["checks"]["database"]["status"] = "error"
        health["checks"]["database"]["message"] = f"❌ Database error: {str(e)}"
        health["overall_status"] = "unhealthy"

    # Check Telegram access
    try:
        if SESSION_1_API_ID and SESSION_1_API_HASH and PRIVATE_GROUP_ID:
            health["checks"]["telegram_access"]["status"] = "healthy"
            health["checks"]["telegram_access"]["message"] = "✅ Telegram credentials configured"
        else:
            health["checks"]["telegram_access"]["status"] = "error"
            health["checks"]["telegram_access"]["message"] = "❌ Telegram credentials missing"
            health["overall_status"] = "unhealthy"
            health["recommendations"].append(
                "Configure Telegram API credentials in .env")
    except Exception as e:
        health["checks"]["telegram_access"]["status"] = "error"
        health["checks"]["telegram_access"]["message"] = f"❌ Error: {str(e)}"
        health["overall_status"] = "unhealthy"

    # Check frontend files
    try:
        frontend_path = Path("PopCorn/frontend/src/frontend_data.json")
        if frontend_path.exists():
            with open(frontend_path, 'r') as f:
                data = json.load(f)
                movies_count = len(data.get("movies", []))
                series_count = len(data.get("series", []))
                health["checks"]["frontend_files"]["status"] = "healthy"
                health["checks"]["frontend_files"][
                    "message"] = f"✅ Frontend data exists ({movies_count} movies, {series_count} series)"
        else:
            health["checks"]["frontend_files"]["status"] = "warning"
            health["checks"]["frontend_files"]["message"] = "⚠️ Frontend data file missing"
            health["recommendations"].append(
                "Run frontend sync to create data files")
    except Exception as e:
        health["checks"]["frontend_files"]["status"] = "error"
        health["checks"]["frontend_files"]["message"] = f"❌ Error: {str(e)}"
        health["overall_status"] = "unhealthy"

    return health


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

def format_sync_status(status: Dict) -> str:
    """Format sync status for display."""
    text = "**📊 Synchronization Status**\n\n"

    # Telegram → Database
    tg_status = status["telegram_to_db"]
    text += "**Telegram → Database:**\n"
    text += f"• Status: `{tg_status['status']}`\n"
    text += f"• Last Sync: `{tg_status['last_sync'] or 'Never'}`\n"
    text += f"• Total Syncs: `{tg_status['sync_count']}`\n"
    if tg_status['errors']:
        text += f"• Recent Errors: `{len(tg_status['errors'])}`\n"
    text += "\n"

    # Database → Frontend
    fe_status = status["db_to_frontend"]
    text += "**Database → Frontend:**\n"
    text += f"• Status: `{fe_status['status']}`\n"
    text += f"• Last Sync: `{fe_status['last_sync'] or 'Never'}`\n"
    text += f"• Total Syncs: `{fe_status['sync_count']}`\n"
    if fe_status['errors']:
        text += f"• Recent Errors: `{len(fe_status['errors'])}`\n"

    return text


def format_sync_result(result: Dict) -> str:
    """Format sync result for display."""
    text = f"**{result['message']}**\n\n"

    if result.get("movies_synced") is not None:
        text += f"📽️ Movies: `{result['movies_synced']}`\n"
    if result.get("series_synced") is not None:
        text += f"📺 Series: `{result['series_synced']}`\n"
    if result.get("episodes_synced") is not None:
        text += f"🎬 Episodes: `{result['episodes_synced']}`\n"

    if result.get("files_updated"):
        text += f"\n📁 Files Updated: `{len(result['files_updated'])}`\n"

    if result.get("duration"):
        text += f"\n⏱️ Duration: `{result['duration']:.2f}s`\n"

    if result.get("errors"):
        text += f"\n⚠️ Errors: `{len(result['errors'])}`\n"
        for error in result["errors"][:3]:  # Show first 3 errors
            text += f"• {error}\n"

    return text


# ══════════════════════════════════════════════════════════════════════════════
# Initialization
# ══════════════════════════════════════════════════════════════════════════════

logger.info("🔄 Sync Manager initialized")

# Made with Bob
