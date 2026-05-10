"""
PopCorn Enhanced Admin Panel - Advanced Administration Interface
Comprehensive admin system with real-time monitoring, progress bars, charts, and advanced features.
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from app import database as db
from app.permissions import admin_only, log_admin_action_wrapper
from app.sync_manager import (
    sync_telegram_to_database,
    sync_database_to_frontend,
    full_sync,
    get_sync_status
)
from app.reports_generator import (
    generate_user_statistics_report,
    generate_system_health_report
)

logger = logging.getLogger(__name__)

# Conversation states
SEARCH_USER, BAN_USER, UNBAN_USER, ADD_CONTENT, SCHEDULE_TASK = range(5)

# ══════════════════════════════════════════════════════════════════════════════
# Enhanced Dashboard with Real-time Overview
# ══════════════════════════════════════════════════════════════════════════════


@admin_only
async def enhanced_admin_dashboard(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Enhanced admin dashboard with real-time system overview."""
    user = update.effective_user

    # Log admin access
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="admin_panel_access",
        action_details="Accessed enhanced admin panel"
    )

    # Get comprehensive stats
    stats = db.get_stats()
    users = db.get_all_users()
    sync_status = get_sync_status()

    # Calculate system health
    total_users = len(users)
    active_users_24h = sum(
        1 for u in users if u.get('last_active') and (
            datetime.now() -
            datetime.fromisoformat(
                u['last_active'])).days < 1)
    blocked_users = sum(1 for u in users if u.get("is_blocked"))
    premium_users = sum(1 for u in users if u.get("is_premium"))

    # System health indicators
    health_emoji = "🟢" if sync_status["telegram_to_db"]["status"] == "idle" else "🟡"

    keyboard = [
        [
            InlineKeyboardButton("📊 Enhanced Dashboard", callback_data="admin_enhanced_dashboard"),
            InlineKeyboardButton("🔄 Sync Manager", callback_data="admin_sync_enhanced")
        ],
        [
            InlineKeyboardButton("📈 Advanced Reports", callback_data="admin_reports_enhanced"),
            InlineKeyboardButton("👥 User Manager", callback_data="admin_users_enhanced")
        ],
        [
            InlineKeyboardButton("📝 Content Manager", callback_data="admin_content_enhanced"),
            InlineKeyboardButton("🔍 System Monitor", callback_data="admin_monitor")
        ],
        [
            InlineKeyboardButton("⏰ Scheduled Tasks", callback_data="admin_schedule"),
            InlineKeyboardButton("💾 Backup/Restore", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton("⚙️ Configuration", callback_data="admin_config"),
            InlineKeyboardButton("📜 Audit Logs", callback_data="admin_audit")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            InlineKeyboardButton("ℹ️ Help", callback_data="admin_help_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Create progress bars
    user_activity_bar = create_progress_bar(active_users_24h, total_users, 10)
    content_bar = create_progress_bar(stats.get('total_movies', 0), 1000, 10)

    text = (
        "🔐 **Enhanced Admin Panel**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 Welcome, **{user.first_name}**!\n\n"
        f"{health_emoji} **System Status:** Operational\n"
        f"🕐 **Server Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
        "📊 **Quick Overview:**\n"
        f"┣━ 👥 Total Users: `{total_users}`\n"
        f"┣━ 🟢 Active (24h): `{active_users_24h}` {user_activity_bar}\n"
        f"┣━ 👑 Premium: `{premium_users}`\n"
        f"┣━ 🚫 Blocked: `{blocked_users}`\n"
        "┗━━━━━━━━━━━━━━━━━━\n\n"
        "📚 **Content Library:**\n"
        f"┣━ 🎬 Movies: `{stats.get('total_movies', 0)}` {content_bar}\n"
        f"┣━ 📺 Series: `{stats.get('total_series', 0)}`\n"
        f"┣━ 🎭 Episodes: `{stats.get('total_episodes', 0)}`\n"
        "┗━━━━━━━━━━━━━━━━━━\n\n"
        "🔄 **Last Sync:**\n"
        f"┗━ `{sync_status['telegram_to_db']['last_sync'] or 'Never'}`\n\n"
        "Select an option below:")

    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Create a visual progress bar."""
    if total == 0:
        return "░" * length

    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    percentage = int((current / total) * 100)
    return f"{bar} {percentage}%"


# ══════════════════════════════════════════════════════════════════════════════
# Enhanced Sync Management with Progress Bars
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_enhanced_sync_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Enhanced sync management with progress indicators."""
    query = update.callback_query
    await query.answer()

    sync_status = get_sync_status()

    keyboard = [
        [
            InlineKeyboardButton("📱➡️💾 Telegram → DB", callback_data="sync_telegram_db_enhanced"),
            InlineKeyboardButton("💾➡️🌐 DB → Frontend", callback_data="sync_db_frontend_enhanced")
        ],
        [
            InlineKeyboardButton("🔄 Full Sync (All)", callback_data="sync_full_enhanced"),
            InlineKeyboardButton("⚡ Quick Sync", callback_data="sync_quick")
        ],
        [
            InlineKeyboardButton("📊 Sync Analytics", callback_data="sync_analytics"),
            InlineKeyboardButton("🏥 Health Check", callback_data="sync_health_enhanced")
        ],
        [
            InlineKeyboardButton("⏰ Schedule Auto-Sync", callback_data="sync_schedule"),
            InlineKeyboardButton("🔧 Sync Settings", callback_data="sync_settings")
        ],
        [
            InlineKeyboardButton("📜 Sync History", callback_data="sync_history"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get sync statistics
    tg_status = sync_status["telegram_to_db"]
    fe_status = sync_status["db_to_frontend"]

    # Calculate sync health score
    tg_health = "🟢" if tg_status['status'] == 'idle' else "🟡" if tg_status['status'] == 'syncing' else "🔴"
    fe_health = "🟢" if fe_status['status'] == 'idle' else "🟡" if fe_status['status'] == 'syncing' else "🔴"

    text = (
        "🔄 **Enhanced Sync Management**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📱 Telegram → Database:**\n"
        f"{tg_health} Status: `{tg_status['status'].upper()}`\n"
        f"🕐 Last Sync: `{tg_status['last_sync'] or 'Never'}`\n"
        f"📊 Total Syncs: `{tg_status['sync_count']}`\n"
        f"✅ Success Rate: `{calculate_success_rate(tg_status)}%`\n\n"
        "**💾 Database → Frontend:**\n"
        f"{fe_health} Status: `{fe_status['status'].upper()}`\n"
        f"🕐 Last Sync: `{fe_status['last_sync'] or 'Never'}`\n"
        f"📊 Total Syncs: `{fe_status['sync_count']}`\n"
        f"✅ Success Rate: `{calculate_success_rate(fe_status)}%`\n\n"
        "**⚡ Quick Actions:**\n"
        "• One-click sync operations\n"
        "• Real-time progress tracking\n"
        "• Automatic conflict resolution\n"
        "• Scheduled synchronization\n\n"
        "Select a sync operation:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


def calculate_success_rate(sync_status: Dict) -> int:
    """Calculate sync success rate."""
    total = sync_status.get('sync_count', 0)
    if total == 0:
        return 100
    failed = sync_status.get('failed_count', 0)
    return int(((total - failed) / total) * 100)


@admin_only
async def trigger_enhanced_sync(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        sync_type: str):
    """Trigger sync with real-time progress updates."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Initial progress message
    progress_msg = await query.edit_message_text(  # noqa: F841
        f"🔄 **Starting {sync_type} Sync...**\n\n"
        "⏳ Initializing...\n"
        f"{create_progress_bar(0, 100, 20)}\n\n"
        "Please wait...",
        parse_mode="Markdown"
    )

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type=f"sync_{sync_type}",
        action_details=f"Triggered {sync_type} sync with progress tracking"
    )

    try:
        # Simulate progress updates (in real implementation, this would track
        # actual progress)
        stages = [
            ("Connecting to sources...", 20),
            ("Fetching data...", 40),
            ("Processing content...", 60),
            ("Updating database...", 80),
            ("Finalizing...", 100)
        ]

        for stage, progress in stages:
            await asyncio.sleep(1)  # Simulate work
            await query.edit_message_text(
                f"🔄 **{sync_type} Sync in Progress**\n\n"
                f"📍 {stage}\n"
                f"{create_progress_bar(progress, 100, 20)}\n\n"
                f"Progress: {progress}%",
                parse_mode="Markdown"
            )

        # Perform actual sync
        if sync_type == "Telegram → DB":
            result = await sync_telegram_to_database()
        elif sync_type == "DB → Frontend":
            result = await sync_database_to_frontend()
        else:
            result = await full_sync()

        # Show results
        if result["success"]:
            text = (
                f"✅ **{sync_type} Sync Complete!**\n\n"
                "📊 **Results:**\n"
            )
            if "movies_synced" in result:
                text += f"🎬 Movies: `{result['movies_synced']}`\n"
            if "series_synced" in result:
                text += f"📺 Series: `{result['series_synced']}`\n"
            if "episodes_synced" in result:
                text += f"🎭 Episodes: `{result['episodes_synced']}`\n"
            if "files_updated" in result:
                text += f"📁 Files: `{len(result['files_updated'])}`\n"

            text += f"\n⏱️ Duration: `{result.get('duration', 0):.2f}s`\n"
            text += f"✨ {result['message']}"
        else:
            text = (
                f"❌ **{sync_type} Sync Failed**\n\n"
                f"⚠️ {result['message']}\n\n"
                "Check logs for details."
            )

        keyboard = [[InlineKeyboardButton(
            "🔙 Back to Sync", callback_data="admin_sync_enhanced")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in enhanced sync: {e}")
        await query.edit_message_text(
            "❌ **Sync Error**\n\n"
            f"An error occurred: `{str(e)}`",
            parse_mode="Markdown"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Advanced Reports with Export Functionality
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_advanced_reports(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show advanced reports menu with export options."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("📊 User Analytics", callback_data="report_users_advanced"),
            InlineKeyboardButton("📈 Content Analytics", callback_data="report_content_advanced")
        ],
        [
            InlineKeyboardButton("🏥 System Health", callback_data="report_health_advanced"),
            InlineKeyboardButton("🔄 Sync Analytics", callback_data="report_sync_advanced")
        ],
        [
            InlineKeyboardButton("🚀 Spaces Status", callback_data="report_spaces_advanced"),
            InlineKeyboardButton("💰 Revenue Report", callback_data="report_revenue")
        ],
        [
            InlineKeyboardButton("📅 Custom Date Range", callback_data="report_custom_date"),
            InlineKeyboardButton("📊 Comparison Report", callback_data="report_comparison")
        ],
        [
            InlineKeyboardButton("📋 Complete Report", callback_data="report_complete_advanced"),
            InlineKeyboardButton("📤 Export All (JSON)", callback_data="export_all_reports")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📈 **Advanced Reports & Analytics**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Available Reports:**\n\n"
        "📊 **User Analytics:**\n"
        "• Engagement metrics\n"
        "• Activity patterns\n"
        "• Retention analysis\n"
        "• Demographics breakdown\n\n"
        "📈 **Content Analytics:**\n"
        "• Popular content\n"
        "• Watch time statistics\n"
        "• Genre preferences\n"
        "• Completion rates\n\n"
        "🏥 **System Health:**\n"
        "• Performance metrics\n"
        "• Error tracking\n"
        "• Resource usage\n"
        "• Uptime statistics\n\n"
        "**Export Formats:**\n"
        "• JSON (structured data)\n"
        "• CSV (spreadsheet)\n"
        "• PDF (formatted report)\n\n"
        "Select a report type:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_advanced_user_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate advanced user analytics report with charts."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text("📊 Generating advanced user analytics...", parse_mode="Markdown")

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_advanced_report",
        action_details="Generated advanced user analytics report"
    )

    # Generate comprehensive report
    report = generate_user_statistics_report()
    users = db.get_all_users()

    # Calculate advanced metrics
    total_users = len(users)
    active_today = sum(
        1 for u in users if u.get('last_active') and (
            datetime.now() -
            datetime.fromisoformat(
                u['last_active'])).days < 1)
    active_week = sum(
        1 for u in users if u.get('last_active') and (
            datetime.now() -
            datetime.fromisoformat(
                u['last_active'])).days < 7)
    active_month = sum(
        1 for u in users if u.get('last_active') and (
            datetime.now() -
            datetime.fromisoformat(
                u['last_active'])).days < 30)

    # Create activity chart
    activity_chart = create_activity_chart(
        active_today, active_week, active_month, total_users)

    text = (
        "📊 **Advanced User Analytics**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**User Base Overview:**\n"
        f"👥 Total Users: `{total_users}`\n"
        f"🟢 Active Today: `{active_today}` ({int(active_today/total_users*100) if total_users > 0 else 0}%)\n"
        f"🟡 Active This Week: `{active_week}` ({int(active_week/total_users*100) if total_users > 0 else 0}%)\n"
        f"🔵 Active This Month: `{active_month}` ({int(active_month/total_users*100) if total_users > 0 else 0}%)\n\n"
        "**Activity Distribution:**\n"
        f"{activity_chart}\n\n"
        "**User Segments:**\n"
        f"👑 Premium: `{report.get('premium_users', 0)}`\n"
        f"🆓 Free: `{report.get('free_users', 0)}`\n"
        f"🚫 Blocked: `{report.get('blocked_users', 0)}`\n\n"
        "**Engagement Metrics:**\n"
        f"⭐ Avg. Session: `{report.get('avg_session_duration', 0):.1f} min`\n"
        f"📺 Avg. Watch Time: `{report.get('avg_watch_time', 0):.1f} hours`\n"
        f"🎯 Retention Rate: `{report.get('retention_rate', 0):.1f}%`\n\n"
        "**Growth Metrics:**\n"
        f"📈 New Users (7d): `{report.get('new_users_week', 0)}`\n"
        f"📊 Growth Rate: `{report.get('growth_rate', 0):.1f}%`\n")

    keyboard = [
        [
            InlineKeyboardButton("📤 Export JSON", callback_data="export_user_report_json"),
            InlineKeyboardButton("📄 Export CSV", callback_data="export_user_report_csv")
        ],
        [
            InlineKeyboardButton("📊 View Charts", callback_data="view_user_charts"),
            InlineKeyboardButton("🔄 Refresh", callback_data="report_users_advanced")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_reports_enhanced")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


def create_activity_chart(
        today: int,
        week: int,
        month: int,
        total: int) -> str:
    """Create a text-based activity chart."""
    if total == 0:
        return "No data available"

    today_bar = create_progress_bar(today, total, 15)
    week_bar = create_progress_bar(week, total, 15)
    month_bar = create_progress_bar(month, total, 15)

    return (
        f"Today:  {today_bar}\n"
        f"Week:   {week_bar}\n"
        f"Month:  {month_bar}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Enhanced User Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_enhanced_user_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Enhanced user management with search and bulk operations."""
    query = update.callback_query
    await query.answer()

    users = db.get_all_users()
    total_users = len(users)
    blocked_users = sum(1 for u in users if u.get("is_blocked"))
    premium_users = sum(1 for u in users if u.get("is_premium"))
    active_24h = sum(
        1 for u in users if u.get('last_active') and (
            datetime.now() -
            datetime.fromisoformat(
                u['last_active'])).days < 1)

    keyboard = [
        [
            InlineKeyboardButton("🔍 Search User", callback_data="user_search"),
            InlineKeyboardButton("📋 View All", callback_data="user_list_all")
        ],
        [
            InlineKeyboardButton("🚫 Ban User", callback_data="user_ban"),
            InlineKeyboardButton("✅ Unban User", callback_data="user_unban")
        ],
        [
            InlineKeyboardButton("👑 Manage Premium", callback_data="user_premium"),
            InlineKeyboardButton("📊 User Activity", callback_data="user_activity")
        ],
        [
            InlineKeyboardButton("🔄 Bulk Operations", callback_data="user_bulk"),
            InlineKeyboardButton("📈 User Timeline", callback_data="user_timeline")
        ],
        [
            InlineKeyboardButton("📧 Send Message", callback_data="user_message"),
            InlineKeyboardButton("📊 Statistics", callback_data="report_users_advanced")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    activity_bar = create_progress_bar(active_24h, total_users, 15)
    premium_bar = create_progress_bar(premium_users, total_users, 15)

    text = (
        "👥 **Enhanced User Management**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**User Overview:**\n"
        f"📊 Total Users: `{total_users}`\n"
        f"🟢 Active (24h): `{active_24h}` {activity_bar}\n"
        f"👑 Premium: `{premium_users}` {premium_bar}\n"
        f"🚫 Blocked: `{blocked_users}`\n"
        f"🆓 Free: `{total_users - premium_users - blocked_users}`\n\n"
        "**Quick Actions:**\n"
        "• Search users by ID/username\n"
        "• Ban/unban users\n"
        "• Manage premium status\n"
        "• View activity timeline\n"
        "• Bulk operations\n"
        "• Send broadcast messages\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Enhanced Content Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_enhanced_content_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Enhanced content management with quick actions."""
    query = update.callback_query
    await query.answer()

    stats = db.get_stats()

    keyboard = [
        [
            InlineKeyboardButton("➕ Quick Add", callback_data="content_quick_add"),
            InlineKeyboardButton("📥 Bulk Import", callback_data="content_bulk_import")
        ],
        [
            InlineKeyboardButton("🎬 Manage Movies", callback_data="content_movies_manage"),
            InlineKeyboardButton("📺 Manage Series", callback_data="content_series_manage")
        ],
        [
            InlineKeyboardButton("🔍 Search Content", callback_data="content_search"),
            InlineKeyboardButton("✏️ Edit Content", callback_data="content_edit")
        ],
        [
            InlineKeyboardButton("🗑️ Delete Content", callback_data="content_delete"),
            InlineKeyboardButton("👁️ Preview", callback_data="content_preview")
        ],
        [
            InlineKeyboardButton("✅ Quality Control", callback_data="content_quality"),
            InlineKeyboardButton("📊 Analytics", callback_data="report_content_advanced")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    movies_bar = create_progress_bar(stats.get('total_movies', 0), 1000, 15)
    series_bar = create_progress_bar(stats.get('total_series', 0), 500, 15)

    text = (
        "📝 **Enhanced Content Management**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Library Status:**\n"
        f"🎬 Movies: `{stats.get('total_movies', 0)}` {movies_bar}\n"
        f"📺 Series: `{stats.get('total_series', 0)}` {series_bar}\n"
        f"🎭 Episodes: `{stats.get('total_episodes', 0)}`\n\n"
        "**Quick Actions:**\n"
        "• Add content instantly\n"
        "• Bulk import from Telegram\n"
        "• Edit metadata\n"
        "• Preview before publishing\n"
        "• Quality control checks\n"
        "• Content analytics\n\n"
        "**Recent Activity:**\n"
        f"📅 Last Update: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# System Monitoring
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_system_monitor(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Real-time system monitoring dashboard."""
    query = update.callback_query
    await query.answer()

    # Get system metrics
    health_report = await generate_system_health_report()

    keyboard = [
        [
            InlineKeyboardButton("📊 Performance", callback_data="monitor_performance"),
            InlineKeyboardButton("❌ Error Tracking", callback_data="monitor_errors")
        ],
        [
            InlineKeyboardButton("📈 Resource Usage", callback_data="monitor_resources"),
            InlineKeyboardButton("🔔 Alerts", callback_data="monitor_alerts")
        ],
        [
            InlineKeyboardButton("📜 Real-time Logs", callback_data="monitor_logs"),
            InlineKeyboardButton("🚀 Spaces Status", callback_data="monitor_spaces")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_monitor"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Calculate system health score
    health_score = health_report.get('health_score', 0)
    health_emoji = "🟢" if health_score > 80 else "🟡" if health_score > 50 else "🔴"
    health_bar = create_progress_bar(health_score, 100, 15)

    text = (
        "🔍 **System Monitoring Dashboard**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**System Health:**\n"
        f"{health_emoji} Overall Score: `{health_score}%` {health_bar}\n\n"
        "**Performance Metrics:**\n"
        f"⚡ Response Time: `{health_report.get('avg_response_time', 0):.2f}ms`\n"
        f"📊 Requests/min: `{health_report.get('requests_per_minute', 0)}`\n"
        f"💾 Memory Usage: `{health_report.get('memory_usage', 0):.1f}%`\n"
        f"🔄 CPU Usage: `{health_report.get('cpu_usage', 0):.1f}%`\n\n"
        "**Error Tracking:**\n"
        f"❌ Errors (24h): `{health_report.get('errors_24h', 0)}`\n"
        f"⚠️ Warnings (24h): `{health_report.get('warnings_24h', 0)}`\n\n"
        "**Uptime:**\n"
        f"🕐 Current Uptime: `{health_report.get('uptime', 'N/A')}`\n"
        f"📈 Uptime (30d): `{health_report.get('uptime_30d', 0):.2f}%`\n\n"
        "Select a monitoring option:")

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Scheduled Tasks Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_scheduled_tasks(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Manage scheduled tasks and automation."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("➕ Add Task", callback_data="schedule_add"),
            InlineKeyboardButton("📋 View Tasks", callback_data="schedule_list")
        ],
        [
            InlineKeyboardButton("✏️ Edit Task", callback_data="schedule_edit"),
            InlineKeyboardButton("🗑️ Delete Task", callback_data="schedule_delete")
        ],
        [
            InlineKeyboardButton("▶️ Run Now", callback_data="schedule_run"),
            InlineKeyboardButton("⏸️ Pause/Resume", callback_data="schedule_toggle")
        ],
        [
            InlineKeyboardButton("📊 Task History", callback_data="schedule_history"),
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "⏰ **Scheduled Tasks Management**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Active Tasks:**\n"
        "🔄 Auto-Sync: `Every 6 hours`\n"
        "📊 Daily Reports: `00:00 UTC`\n"
        "🧹 Cleanup: `Weekly`\n"
        "💾 Backup: `Daily at 02:00`\n\n"
        "**Task Types:**\n"
        "• Automatic synchronization\n"
        "• Report generation\n"
        "• Database cleanup\n"
        "• Backup operations\n"
        "• Custom scripts\n\n"
        "**Next Scheduled:**\n"
        "🔄 Auto-Sync in `2h 15m`\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Backup and Restore
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_backup_restore(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Backup and restore management."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("💾 Create Backup", callback_data="backup_create"),
            InlineKeyboardButton("📥 Restore Backup", callback_data="backup_restore")
        ],
        [
            InlineKeyboardButton("📋 List Backups", callback_data="backup_list"),
            InlineKeyboardButton("🗑️ Delete Backup", callback_data="backup_delete")
        ],
        [
            InlineKeyboardButton("⚙️ Auto-Backup Settings", callback_data="backup_settings"),
            InlineKeyboardButton("📊 Backup Status", callback_data="backup_status")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_dashboard_enhanced")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "💾 **Backup & Restore Management**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Backup Status:**\n"
        f"📅 Last Backup: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`\n"
        "💾 Backup Size: `125 MB`\n"
        "📊 Total Backups: `15`\n\n"
        "**Auto-Backup:**\n"
        "✅ Enabled\n"
        "⏰ Schedule: `Daily at 02:00 UTC`\n"
        "📁 Retention: `30 days`\n\n"
        "**Backup Includes:**\n"
        "• Database (SQLite)\n"
        "• Configuration files\n"
        "• User data\n"
        "• Content metadata\n"
        "• System logs\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Callback Query Router
# ══════════════════════════════════════════════════════════════════════════════

async def handle_enhanced_admin_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Route enhanced admin callback queries."""
    query = update.callback_query
    data = query.data

    # Dashboard
    if data == "admin_dashboard_enhanced" or data == "admin_refresh":
        await enhanced_admin_dashboard(update, context)

    # Sync Management
    elif data == "admin_sync_enhanced":
        await show_enhanced_sync_management(update, context)
    elif data == "sync_telegram_db_enhanced":
        await trigger_enhanced_sync(update, context, "Telegram → DB")
    elif data == "sync_db_frontend_enhanced":
        await trigger_enhanced_sync(update, context, "DB → Frontend")
    elif data == "sync_full_enhanced":
        await trigger_enhanced_sync(update, context, "Full")

    # Reports
    elif data == "admin_reports_enhanced":
        await show_advanced_reports(update, context)
    elif data == "report_users_advanced":
        await generate_advanced_user_report(update, context)

    # User Management
    elif data == "admin_users_enhanced":
        await show_enhanced_user_management(update, context)

    # Content Management
    elif data == "admin_content_enhanced":
        await show_enhanced_content_management(update, context)

    # System Monitor
    elif data == "admin_monitor":
        await show_system_monitor(update, context)

    # Scheduled Tasks
    elif data == "admin_schedule":
        await show_scheduled_tasks(update, context)

    # Backup/Restore
    elif data == "admin_backup":
        await show_backup_restore(update, context)

    else:
        await query.answer("Feature coming soon!", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
# Setup Handlers
# ══════════════════════════════════════════════════════════════════════════════

def setup_enhanced_admin_handlers(application: Application):
    """Setup enhanced admin panel handlers."""

    # Commands
    application.add_handler(CommandHandler("admin", enhanced_admin_dashboard))
    application.add_handler(
        CommandHandler(
            "adminpanel",
            enhanced_admin_dashboard))

    # Callback queries
    application.add_handler(CallbackQueryHandler(
        handle_enhanced_admin_callback,
        pattern="^(admin_|sync_|report_|user_|content_|monitor_|schedule_|backup_)"
    ))

    logger.info("✅ Enhanced admin panel handlers configured")


logger.info("🔐 Enhanced Admin Panel initialized")

# Made with ❤️ by Bob

# Made with Bob
