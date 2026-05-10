"""
Reports Generator for PopCorn Bot
Generates detailed reports for user statistics, content, system health, and HuggingFace Spaces status.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict
import httpx
from pathlib import Path

from app.config import (
    HF_TOKEN
)
from app import database as db

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# HuggingFace Spaces Status
# ══════════════════════════════════════════════════════════════════════════════

# List of all HuggingFace Spaces to monitor
HF_SPACES = [
    "ToolKit-backend/PopCorn",
    "ToolKit-backend/PopCorn-Mirror-1",
    "ToolKit-backend/PopCorn-Mirror-2",
    "ToolKit-backend/PopCorn-Mirror-3",
    "ToolKit-backend/PopCorn-Mirror-4"
]


async def get_hf_space_status(space_name: str) -> Dict:
    """
    Get the build and runtime status of a HuggingFace Space.

    Args:
        space_name: Full space name (e.g., "username/space-name")

    Returns:
        Dict with space status information
    """
    status = {
        "space_name": space_name,
        "status": "unknown",
        "runtime": "unknown",
        "sdk": "unknown",
        "last_modified": None,
        "error": None
    }

    try:
        url = f"https://huggingface.co/api/spaces/{space_name}"
        headers = {}
        if HF_TOKEN:
            headers["Authorization"] = f"Bearer {HF_TOKEN}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                status["status"] = data.get(
                    "runtime", {}).get(
                    "stage", "unknown")
                status["runtime"] = data.get(
                    "runtime",
                    {}).get(
                    "hardware",
                    {}).get(
                    "current",
                    "unknown")
                status["sdk"] = data.get("sdk", "unknown")
                status["last_modified"] = data.get("lastModified")

                # Determine if space is healthy
                stage = status["status"].lower()
                if stage in ["running", "running_building"]:
                    status["health"] = "healthy"
                elif stage in ["building", "app_starting"]:
                    status["health"] = "building"
                elif stage in ["stopped", "paused"]:
                    status["health"] = "stopped"
                else:
                    status["health"] = "error"
            else:
                status["error"] = f"HTTP {response.status_code}"
                status["health"] = "error"

    except Exception as e:
        logger.error(f"Error getting HF Space status for {space_name}: {e}")
        status["error"] = str(e)
        status["health"] = "error"

    return status


async def get_all_spaces_status() -> Dict:
    """Get status of all HuggingFace Spaces."""
    logger.info("🔍 Checking HuggingFace Spaces status...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "total_spaces": len(HF_SPACES),
        "healthy": 0,
        "building": 0,
        "stopped": 0,
        "error": 0,
        "spaces": []
    }

    for space_name in HF_SPACES:
        space_status = await get_hf_space_status(space_name)
        report["spaces"].append(space_status)

        # Count by health status
        health = space_status.get("health", "error")
        if health == "healthy":
            report["healthy"] += 1
        elif health == "building":
            report["building"] += 1
        elif health == "stopped":
            report["stopped"] += 1
        else:
            report["error"] += 1

    logger.info(
        f"✅ Spaces status: {report['healthy']} healthy, {report['building']} building, "
        f"{report['stopped']} stopped, {report['error']} error")

    return report


# ══════════════════════════════════════════════════════════════════════════════
# User Statistics Reports
# ══════════════════════════════════════════════════════════════════════════════

def generate_user_statistics_report() -> Dict:
    """Generate comprehensive user statistics report."""
    logger.info("📊 Generating user statistics report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "overview": {},
        "daily_activity": {},
        "top_users": [],
        "registration_trends": {}
    }

    try:
        # Get all users
        users = db.get_all_users()
        total_users = len(users)

        # Calculate statistics
        blocked_users = sum(1 for u in users if u.get("is_blocked"))
        premium_users = sum(1 for u in users if u.get("is_premium"))

        # Get active users (last 24 hours)
        now = datetime.now()
        day_ago = now - timedelta(days=1)
        active_today = sum(1 for u in users if u.get("last_active") and
                           datetime.fromisoformat(u["last_active"]) > day_ago)

        # Get active users (last 7 days)
        week_ago = now - timedelta(days=7)
        active_week = sum(1 for u in users if u.get("last_active") and
                          datetime.fromisoformat(u["last_active"]) > week_ago)

        report["overview"] = {
            "total_users": total_users,
            "active_today": active_today,
            "active_this_week": active_week,
            "blocked_users": blocked_users,
            "premium_users": premium_users,
            "free_users": total_users - premium_users
        }

        # Daily activity
        report["daily_activity"] = {
            "new_registrations_today": 0,  # Would need created_at filtering
            "active_sessions": len(db.get_active_sessions()),
            "total_views_today": 0,  # Would need analytics data
            "total_searches_today": 0
        }

        # Get top users by watch time
        top_users_data = []
        for user in users[:10]:  # Top 10 users
            user_stats = db.get_user_statistics(user["user_id"])
            if user_stats:
                top_users_data.append({
                    "user_id": user["user_id"],
                    "username": user.get("username"),
                    "total_watch_time": user_stats.get("total_watch_time", 0),
                    "total_content_watched": user_stats.get("total_movies_watched", 0) +
                    user_stats.get("total_episodes_watched", 0)
                })

        report["top_users"] = sorted(top_users_data,
                                     key=lambda x: x["total_watch_time"],
                                     reverse=True)[:10]

        logger.info(
            f"✅ User statistics report generated: {total_users} total users")

    except Exception as e:
        logger.error(f"❌ Error generating user statistics report: {e}")
        report["error"] = str(e)

    return report


# ══════════════════════════════════════════════════════════════════════════════
# Content Statistics Reports
# ══════════════════════════════════════════════════════════════════════════════

def generate_content_statistics_report() -> Dict:
    """Generate comprehensive content statistics report."""
    logger.info("📊 Generating content statistics report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "overview": {},
        "movies": {},
        "series": {},
        "recent_additions": {}
    }

    try:
        # Get content statistics
        stats = db.get_stats()

        report["overview"] = {
            "total_movies": stats.get(
                "total_movies",
                0),
            "total_series": stats.get(
                "total_series",
                0),
            "total_episodes": stats.get(
                "total_episodes",
                0),
            "total_content": stats.get(
                "total_movies",
                0) +
            stats.get(
                "total_series",
                0)}

        # Movies statistics
        movies = db.get_movies()
        movies_with_files = sum(1 for m in movies if m.get("file_id"))

        report["movies"] = {
            "total": len(movies),
            "with_files": movies_with_files,
            "without_files": len(movies) -
            movies_with_files,
            "average_rating": sum(
                m.get(
                    "rating",
                    0) for m in movies) /
            len(movies) if movies else 0}

        # Series statistics
        series_list = db.get_series_list()
        total_seasons = sum(s.get("total_seasons", 0) for s in series_list)

        report["series"] = {
            "total": len(series_list),
            "total_seasons": total_seasons,
            "total_episodes": stats.get(
                "total_episodes",
                0),
            "average_rating": sum(
                s.get(
                    "rating",
                    0) for s in series_list) /
            len(series_list) if series_list else 0}

        # Recent additions (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_movies = [m for m in movies if m.get("created_at") and
                         datetime.fromisoformat(m["created_at"]) > week_ago]
        recent_series = [s for s in series_list if s.get("created_at") and
                         datetime.fromisoformat(s["created_at"]) > week_ago]

        report["recent_additions"] = {
            "movies_last_7_days": len(recent_movies),
            "series_last_7_days": len(recent_series),
            "total_last_7_days": len(recent_movies) + len(recent_series)
        }

        logger.info(
            f"✅ Content statistics report generated: {report['overview']['total_content']} items")

    except Exception as e:
        logger.error(f"❌ Error generating content statistics report: {e}")
        report["error"] = str(e)

    return report


# ══════════════════════════════════════════════════════════════════════════════
# System Health Reports
# ══════════════════════════════════════════════════════════════════════════════

async def generate_system_health_report() -> Dict:
    """Generate comprehensive system health report."""
    logger.info("🏥 Generating system health report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "components": {},
        "recommendations": []
    }

    try:
        # Database health
        try:
            stats = db.get_stats()
            db_size = Path(
                "/tmp/popcorn.db").stat().st_size if Path("/tmp/popcorn.db").exists() else 0
            report["components"]["database"] = {
                "status": "healthy",
                "size_mb": round(
                    db_size /
                    (
                        1024 *
                        1024),
                    2),
                "total_records": stats.get(
                    "total_movies",
                    0) +
                stats.get(
                    "total_series",
                    0) +
                stats.get(
                    "total_episodes",
                    0)}
        except Exception as e:
            report["components"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            report["overall_status"] = "unhealthy"

        # HuggingFace Spaces health
        spaces_status = await get_all_spaces_status()
        report["components"]["huggingface_spaces"] = {
            "status": "healthy" if spaces_status["healthy"] >= 3 else "warning",
            "healthy_count": spaces_status["healthy"],
            "total_count": spaces_status["total_spaces"],
            "details": spaces_status["spaces"]}

        if spaces_status["healthy"] < 3:
            report["overall_status"] = "warning"
            report["recommendations"].append(
                "Less than 3 HuggingFace Spaces are healthy")

        # Sync status
        sync_history = db.get_sync_history(limit=10)
        recent_syncs = [
            s for s in sync_history if s.get("status") == "completed"]
        failed_syncs = [s for s in sync_history if s.get("status") == "failed"]

        report["components"]["sync_system"] = {
            "status": "healthy" if len(recent_syncs) > 0 else "warning",
            "recent_successful_syncs": len(recent_syncs),
            "recent_failed_syncs": len(failed_syncs),
            "last_sync": sync_history[0].get("started_at") if sync_history else None}

        if len(failed_syncs) > 3:
            report["overall_status"] = "warning"
            report["recommendations"].append("Multiple sync failures detected")

        # Error logs
        try:
            # Get recent errors from analytics_errors table
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as error_count
                FROM analytics_errors
                WHERE created_at > datetime('now', '-24 hours')
            """)
            error_count = cursor.fetchone()[0]

            report["components"]["error_logs"] = {
                "status": "healthy" if error_count < 10 else "warning",
                "errors_last_24h": error_count
            }

            if error_count > 10:
                report["recommendations"].append(
                    f"{error_count} errors in last 24 hours")

        except Exception as e:
            report["components"]["error_logs"] = {
                "status": "unknown",
                "error": str(e)
            }

        logger.info(
            f"✅ System health report generated: {report['overall_status']}")

    except Exception as e:
        logger.error(f"❌ Error generating system health report: {e}")
        report["error"] = str(e)
        report["overall_status"] = "error"

    return report


# ══════════════════════════════════════════════════════════════════════════════
# Sync Status Reports
# ══════════════════════════════════════════════════════════════════════════════

def generate_sync_status_report() -> Dict:
    """Generate detailed synchronization status report."""
    logger.info("🔄 Generating sync status report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "overview": {},
        "recent_syncs": [],
        "sync_health": {}
    }

    try:
        # Get sync history
        sync_history = db.get_sync_history(limit=20)

        # Calculate statistics
        total_syncs = len(sync_history)
        completed_syncs = sum(
            1 for s in sync_history if s.get("status") == "completed")
        failed_syncs = sum(
            1 for s in sync_history if s.get("status") == "failed")

        report["overview"] = {
            "total_syncs": total_syncs,
            "completed": completed_syncs,
            "failed": failed_syncs,
            "success_rate": round(
                (completed_syncs / total_syncs * 100),
                2) if total_syncs > 0 else 0}

        # Recent syncs
        report["recent_syncs"] = sync_history[:10]

        # Sync health
        last_sync = sync_history[0] if sync_history else None
        if last_sync:
            last_sync_time = datetime.fromisoformat(last_sync["started_at"])
            hours_since_sync = (
                datetime.now() - last_sync_time).total_seconds() / 3600

            report["sync_health"] = {
                "last_sync": last_sync["started_at"],
                "hours_since_last_sync": round(hours_since_sync, 2),
                "last_sync_status": last_sync["status"],
                "health": "healthy" if hours_since_sync < 24 else "warning"
            }
        else:
            report["sync_health"] = {
                "health": "warning",
                "message": "No sync history found"
            }

        logger.info(
            f"✅ Sync status report generated: {completed_syncs}/{total_syncs} successful")

    except Exception as e:
        logger.error(f"❌ Error generating sync status report: {e}")
        report["error"] = str(e)

    return report


# ══════════════════════════════════════════════════════════════════════════════
# Complete System Report
# ══════════════════════════════════════════════════════════════════════════════

async def generate_complete_system_report() -> Dict:
    """Generate a complete system report with all statistics."""
    logger.info("📊 Generating complete system report...")

    report = {
        "timestamp": datetime.now().isoformat(),
        "report_type": "complete_system_report",
        "user_statistics": {},
        "content_statistics": {},
        "system_health": {},
        "sync_status": {},
        "huggingface_spaces": {}
    }

    try:
        # Generate all sub-reports
        report["user_statistics"] = generate_user_statistics_report()
        report["content_statistics"] = generate_content_statistics_report()
        report["system_health"] = await generate_system_health_report()
        report["sync_status"] = generate_sync_status_report()
        report["huggingface_spaces"] = await get_all_spaces_status()

        logger.info("✅ Complete system report generated successfully")

    except Exception as e:
        logger.error(f"❌ Error generating complete system report: {e}")
        report["error"] = str(e)

    return report


# ══════════════════════════════════════════════════════════════════════════════
# Report Formatting
# ══════════════════════════════════════════════════════════════════════════════

def format_user_statistics_report(report: Dict) -> str:
    """Format user statistics report for Telegram display."""
    overview = report.get("overview", {})

    text = "**📊 User Statistics Report**\n\n"
    text += "**Overview:**\n"
    text += f"• Total Users: `{overview.get('total_users', 0)}`\n"
    text += f"• Active Today: `{overview.get('active_today', 0)}`\n"
    text += f"• Active This Week: `{overview.get('active_this_week', 0)}`\n"
    text += f"• Premium Users: `{overview.get('premium_users', 0)}`\n"
    text += f"• Blocked Users: `{overview.get('blocked_users', 0)}`\n\n"

    daily = report.get("daily_activity", {})
    text += "**Daily Activity:**\n"
    text += f"• Active Sessions: `{daily.get('active_sessions', 0)}`\n\n"

    top_users = report.get("top_users", [])
    if top_users:
        text += "**Top Users (by watch time):**\n"
        for i, user in enumerate(top_users[:5], 1):
            watch_hours = user.get("total_watch_time", 0) / 3600
            text += f"{i}. User `{user.get('user_id')}`: {watch_hours:.1f}h\n"

    return text


def format_content_statistics_report(report: Dict) -> str:
    """Format content statistics report for Telegram display."""
    overview = report.get("overview", {})

    text = "**📊 Content Statistics Report**\n\n"
    text += "**Overview:**\n"
    text += f"• Total Movies: `{overview.get('total_movies', 0)}`\n"
    text += f"• Total Series: `{overview.get('total_series', 0)}`\n"
    text += f"• Total Episodes: `{overview.get('total_episodes', 0)}`\n"
    text += f"• Total Content: `{overview.get('total_content', 0)}`\n\n"

    movies = report.get("movies", {})
    text += "**Movies:**\n"
    text += f"• With Files: `{movies.get('with_files', 0)}`\n"
    text += f"• Without Files: `{movies.get('without_files', 0)}`\n"
    text += f"• Avg Rating: `{movies.get('average_rating', 0):.1f}/10`\n\n"

    series = report.get("series", {})
    text += "**Series:**\n"
    text += f"• Total Seasons: `{series.get('total_seasons', 0)}`\n"
    text += f"• Avg Rating: `{series.get('average_rating', 0):.1f}/10`\n\n"

    recent = report.get("recent_additions", {})
    text += "**Recent Additions (7 days):**\n"
    text += f"• Movies: `{recent.get('movies_last_7_days', 0)}`\n"
    text += f"• Series: `{recent.get('series_last_7_days', 0)}`\n"

    return text


def format_system_health_report(report: Dict) -> str:
    """Format system health report for Telegram display."""
    text = "**🏥 System Health Report**\n\n"
    text += f"**Overall Status:** `{report.get('overall_status', 'unknown').upper()}`\n\n"

    components = report.get("components", {})

    # Database
    db_comp = components.get("database", {})
    text += "**Database:**\n"
    text += f"• Status: `{db_comp.get('status', 'unknown')}`\n"
    text += f"• Size: `{db_comp.get('size_mb', 0)} MB`\n"
    text += f"• Records: `{db_comp.get('total_records', 0)}`\n\n"

    # HuggingFace Spaces
    hf_comp = components.get("huggingface_spaces", {})
    text += "**HuggingFace Spaces:**\n"
    text += f"• Status: `{hf_comp.get('status', 'unknown')}`\n"
    text += f"• Healthy: `{hf_comp.get('healthy_count', 0)}/{hf_comp.get('total_count', 0)}`\n\n"

    # Sync System
    sync_comp = components.get("sync_system", {})
    text += "**Sync System:**\n"
    text += f"• Status: `{sync_comp.get('status', 'unknown')}`\n"
    text += f"• Recent Successful: `{sync_comp.get('recent_successful_syncs', 0)}`\n"
    text += f"• Recent Failed: `{sync_comp.get('recent_failed_syncs', 0)}`\n\n"

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        text += "**⚠️ Recommendations:**\n"
        for rec in recommendations:
            text += f"• {rec}\n"

    return text


def format_spaces_status_report(report: Dict) -> str:
    """Format HuggingFace Spaces status report for Telegram display."""
    text = "**🚀 HuggingFace Spaces Status**\n\n"
    text += "**Summary:**\n"
    text += f"• Total Spaces: `{report.get('total_spaces', 0)}`\n"
    text += f"• ✅ Healthy: `{report.get('healthy', 0)}`\n"
    text += f"• 🔨 Building: `{report.get('building', 0)}`\n"
    text += f"• ⏸️ Stopped: `{report.get('stopped', 0)}`\n"
    text += f"• ❌ Error: `{report.get('error', 0)}`\n\n"

    text += "**Spaces Details:**\n"
    for space in report.get("spaces", []):
        name = space["space_name"].split("/")[-1]
        health_emoji = {
            "healthy": "✅",
            "building": "🔨",
            "stopped": "⏸️",
            "error": "❌"
        }.get(space.get("health", "error"), "❓")

        text += f"{health_emoji} `{name}`: {space.get('status', 'unknown')}\n"

    return text


# ══════════════════════════════════════════════════════════════════════════════
# Export Functions
# ══════════════════════════════════════════════════════════════════════════════

def export_report_to_json(report: Dict, filename: str) -> str:
    """Export report to JSON file."""
    try:
        filepath = Path(f"/tmp/{filename}")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Report exported to {filepath}")
        return str(filepath)
    except Exception as e:
        logger.error(f"❌ Error exporting report: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Initialization
# ══════════════════════════════════════════════════════════════════════════════

logger.info("📊 Reports Generator initialized")

# Made with Bob
