"""
PopCorn Admin Panel - Complete Administration Interface
Comprehensive admin system with sync management, reports, user management, and system monitoring.
"""
import logging
from datetime import datetime

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
    get_sync_status,
    verify_sync_health
)
from app.reports_generator import (
    generate_user_statistics_report,
    generate_content_statistics_report,
    generate_system_health_report,
    get_all_spaces_status,
    generate_complete_system_report,
    format_user_statistics_report,
    format_content_statistics_report,
    format_system_health_report,
    format_spaces_status_report,
    export_report_to_json
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Admin Dashboard
# ══════════════════════════════════════════════════════════════════════════════


@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin panel command."""
    user = update.effective_user

    # Log admin access
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="admin_panel_access",
        action_details="Accessed admin panel"
    )

    keyboard = [
        [
            InlineKeyboardButton("🔄 Sync Management", callback_data="admin_sync"),
            InlineKeyboardButton("📊 Reports", callback_data="admin_reports")
        ],
        [
            InlineKeyboardButton("👥 User Management", callback_data="admin_users"),
            InlineKeyboardButton("📝 Content Management", callback_data="admin_content")
        ],
        [
            InlineKeyboardButton("🏥 System Health", callback_data="admin_health"),
            InlineKeyboardButton("📜 Logs", callback_data="admin_logs")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton("ℹ️ Help", callback_data="admin_help")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Get quick stats
    stats = db.get_stats()
    users = db.get_all_users()

    text = (
        "🔐 **Admin Panel**\n\n"
        f"Welcome, {user.first_name}!\n\n"
        "**Quick Stats:**\n"
        f"• Total Users: `{len(users)}`\n"
        f"• Total Movies: `{stats.get('total_movies', 0)}`\n"
        f"• Total Series: `{stats.get('total_series', 0)}`\n"
        f"• Total Episodes: `{stats.get('total_episodes', 0)}`\n\n"
        "Select an option below:"
    )

    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Sync Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_sync_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show sync management panel."""
    query = update.callback_query
    await query.answer()

    # Get current sync status
    sync_status = get_sync_status()

    keyboard = [
        [
            InlineKeyboardButton("📱 Telegram → DB", callback_data="sync_telegram_db"),
            InlineKeyboardButton("💾 DB → Frontend", callback_data="sync_db_frontend")
        ],
        [
            InlineKeyboardButton("🔄 Full Sync (All)", callback_data="sync_full")
        ],
        [
            InlineKeyboardButton("📊 Sync Status", callback_data="sync_status"),
            InlineKeyboardButton("🏥 Sync Health", callback_data="sync_health")
        ],
        [
            InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Format sync status
    tg_status = sync_status["telegram_to_db"]
    fe_status = sync_status["db_to_frontend"]

    text = (
        "🔄 **Sync Management**\n\n"
        "**Telegram → Database:**\n"
        f"• Status: `{tg_status['status']}`\n"
        f"• Last Sync: `{tg_status['last_sync'] or 'Never'}`\n"
        f"• Total Syncs: `{tg_status['sync_count']}`\n\n"
        "**Database → Frontend:**\n"
        f"• Status: `{fe_status['status']}`\n"
        f"• Last Sync: `{fe_status['last_sync'] or 'Never'}`\n"
        f"• Total Syncs: `{fe_status['sync_count']}`\n\n"
        "Select a sync operation:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def trigger_telegram_db_sync(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Trigger Telegram to Database sync."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Show progress message
    await query.edit_message_text(
        "🔄 **Starting Telegram → Database Sync...**\n\n"
        "This may take a few minutes. Please wait...",
        parse_mode="Markdown"
    )

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="sync_telegram_db",
        action_details="Triggered Telegram to Database sync"
    )

    # Perform sync
    result = await sync_telegram_to_database()

    # Format result message
    if result["success"]:
        text = (
            "✅ **Telegram → Database Sync Complete!**\n\n"
            f"📽️ Movies Synced: `{result['movies_synced']}`\n"
            f"📺 Series Synced: `{result['series_synced']}`\n"
            f"🎬 Episodes Synced: `{result['episodes_synced']}`\n"
            f"⏱️ Duration: `{result['duration']:.2f}s`\n\n"
            f"{result['message']}"
        )
    else:
        text = (
            "❌ **Sync Failed**\n\n"
            f"{result['message']}\n\n"
            "**Errors:**\n"
        )
        for error in result.get("errors", [])[:3]:
            text += f"• {error}\n"

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Sync", callback_data="admin_sync")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def trigger_db_frontend_sync(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Trigger Database to Frontend sync."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Show progress message
    await query.edit_message_text(
        "🔄 **Starting Database → Frontend Sync...**\n\n"
        "Please wait...",
        parse_mode="Markdown"
    )

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="sync_db_frontend",
        action_details="Triggered Database to Frontend sync"
    )

    # Perform sync
    result = await sync_database_to_frontend()

    # Format result message
    if result["success"]:
        text = (
            "✅ **Database → Frontend Sync Complete!**\n\n"
            f"📁 Files Updated: `{len(result['files_updated'])}`\n"
            f"⏱️ Duration: `{result['duration']:.2f}s`\n\n"
            f"{result['message']}"
        )
    else:
        text = (
            "❌ **Sync Failed**\n\n"
            f"{result['message']}"
        )

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Sync", callback_data="admin_sync")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def trigger_full_sync(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Trigger full synchronization (Telegram → DB → Frontend)."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Show progress message
    await query.edit_message_text(
        "🔄 **Starting Full Sync...**\n\n"
        "Step 1/2: Telegram → Database\n"
        "Step 2/2: Database → Frontend\n\n"
        "This may take several minutes. Please wait...",
        parse_mode="Markdown"
    )

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="sync_full",
        action_details="Triggered full synchronization"
    )

    # Perform full sync
    result = await full_sync()

    # Format result message
    if result["success"]:
        tg_result = result.get("telegram_sync", {})
        fe_result = result.get("frontend_sync", {})

        text = (
            "✅ **Full Sync Complete!**\n\n"
            "**Telegram → Database:**\n"
            f"• Movies: `{tg_result.get('movies_synced', 0)}`\n"
            f"• Series: `{tg_result.get('series_synced', 0)}`\n"
            f"• Episodes: `{tg_result.get('episodes_synced', 0)}`\n\n"
            "**Database → Frontend:**\n"
            f"• Files Updated: `{len(fe_result.get('files_updated', []))}`\n\n"
            f"⏱️ Total Duration: `{result['total_duration']:.2f}s`\n\n"
            f"{result['message']}"
        )
    else:
        text = (
            "❌ **Full Sync Failed**\n\n"
            f"{result['message']}"
        )

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Sync", callback_data="admin_sync")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def show_sync_health(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sync health check results."""
    query = update.callback_query
    await query.answer()

    # Show loading message
    await query.edit_message_text("🏥 Checking sync health...", parse_mode="Markdown")

    # Perform health check
    health = await verify_sync_health()

    # Format health report
    text = "🏥 **Sync Health Check**\n\n"
    text += f"**Overall Status:** `{health['overall_status'].upper()}`\n\n"

    for component, check in health["checks"].items():
        status_emoji = "✅" if check["status"] == "healthy" else "⚠️" if check["status"] == "warning" else "❌"
        text += f"{status_emoji} **{component.replace('_', ' ').title()}:**\n"
        text += f"{check['message']}\n\n"

    if health.get("recommendations"):
        text += "**⚠️ Recommendations:**\n"
        for rec in health["recommendations"]:
            text += f"• {rec}\n"

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Sync", callback_data="admin_sync")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Reports Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_reports_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show reports menu."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("👥 User Statistics", callback_data="report_users"),
            InlineKeyboardButton("📊 Content Statistics", callback_data="report_content")
        ],
        [
            InlineKeyboardButton("🏥 System Health", callback_data="report_health"),
            InlineKeyboardButton("🔄 Sync Status", callback_data="report_sync")
        ],
        [
            InlineKeyboardButton("🚀 HF Spaces Status", callback_data="report_spaces")
        ],
        [
            InlineKeyboardButton("📋 Complete Report", callback_data="report_complete")
        ],
        [
            InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📊 **Reports & Analytics**\n\n"
        "Generate detailed reports about:\n"
        "• User activity and statistics\n"
        "• Content library status\n"
        "• System health and performance\n"
        "• Synchronization status\n"
        "• HuggingFace Spaces status\n\n"
        "Select a report type:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_user_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate and display user statistics report."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text("📊 Generating user statistics report...", parse_mode="Markdown")

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_report",
        action_details="Generated user statistics report"
    )

    # Generate report
    report = generate_user_statistics_report()

    # Format and display
    text = format_user_statistics_report(report)

    keyboard = [
        [InlineKeyboardButton("💾 Export JSON", callback_data="export_user_report")],
        [InlineKeyboardButton("🔙 Back to Reports", callback_data="admin_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_content_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate and display content statistics report."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text("📊 Generating content statistics report...", parse_mode="Markdown")

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_report",
        action_details="Generated content statistics report"
    )

    # Generate report
    report = generate_content_statistics_report()

    # Format and display
    text = format_content_statistics_report(report)

    keyboard = [
        [InlineKeyboardButton("💾 Export JSON", callback_data="export_content_report")],
        [InlineKeyboardButton("🔙 Back to Reports", callback_data="admin_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_health_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate and display system health report."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text("🏥 Generating system health report...", parse_mode="Markdown")

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_report",
        action_details="Generated system health report"
    )

    # Generate report
    report = await generate_system_health_report()

    # Format and display
    text = format_system_health_report(report)

    keyboard = [
        [InlineKeyboardButton("💾 Export JSON", callback_data="export_health_report")],
        [InlineKeyboardButton("🔙 Back to Reports", callback_data="admin_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_spaces_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate and display HuggingFace Spaces status report."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text("🚀 Checking HuggingFace Spaces status...", parse_mode="Markdown")

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_report",
        action_details="Generated HF Spaces status report"
    )

    # Generate report
    report = await get_all_spaces_status()

    # Format and display
    text = format_spaces_status_report(report)

    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="report_spaces")],
        [InlineKeyboardButton("🔙 Back to Reports", callback_data="admin_reports")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def generate_complete_report(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Generate complete system report."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    await query.edit_message_text(
        "📋 Generating complete system report...\n\n"
        "This may take a moment...",
        parse_mode="Markdown"
    )

    # Log action
    await log_admin_action_wrapper(
        user_id=user.id,
        action_type="generate_report",
        action_details="Generated complete system report"
    )

    # Generate complete report
    report = await generate_complete_system_report()

    # Export to JSON
    filename = f"complete_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = export_report_to_json(report, filename)

    text = (
        "✅ **Complete System Report Generated**\n\n"
        f"📅 Timestamp: `{report['timestamp']}`\n\n"
        "**Report Includes:**\n"
        "• User Statistics\n"
        "• Content Statistics\n"
        "• System Health\n"
        "• Sync Status\n"
        "• HuggingFace Spaces Status\n\n"
        f"📁 Exported to: `{filepath}`"
    )

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Reports", callback_data="admin_reports")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# User Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_user_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show user management panel."""
    query = update.callback_query
    await query.answer()

    # Get user statistics
    users = db.get_all_users()
    total_users = len(users)
    blocked_users = sum(1 for u in users if u.get("is_blocked"))
    premium_users = sum(1 for u in users if u.get("is_premium"))

    keyboard = [
        [
            InlineKeyboardButton("📋 View All Users", callback_data="users_list"),
            InlineKeyboardButton("🔍 Search User", callback_data="users_search")
        ],
        [
            InlineKeyboardButton("🚫 Blocked Users", callback_data="users_blocked"),
            InlineKeyboardButton("👑 Premium Users", callback_data="users_premium")
        ],
        [
            InlineKeyboardButton("📊 User Statistics", callback_data="report_users")
        ],
        [
            InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "👥 **User Management**\n\n"
        "**Overview:**\n"
        f"• Total Users: `{total_users}`\n"
        f"• Blocked Users: `{blocked_users}`\n"
        f"• Premium Users: `{premium_users}`\n"
        f"• Free Users: `{total_users - premium_users}`\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Content Management
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_content_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show content management panel."""
    query = update.callback_query
    await query.answer()

    # Get content statistics
    stats = db.get_stats()

    keyboard = [
        [
            InlineKeyboardButton(
                "🎬 Manage Movies", callback_data="content_movies"), InlineKeyboardButton(
                "📺 Manage Series", callback_data="content_series")], [
                    InlineKeyboardButton(
                        "📊 Content Statistics", callback_data="report_content")], [
                            InlineKeyboardButton(
                                "🔙 Back to Admin", callback_data="admin_dashboard")]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📝 **Content Management**\n\n"
        "**Library Overview:**\n"
        f"• Total Movies: `{stats.get('total_movies', 0)}`\n"
        f"• Total Series: `{stats.get('total_series', 0)}`\n"
        f"• Total Episodes: `{stats.get('total_episodes', 0)}`\n\n"
        "Select an option:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# System Logs
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_system_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system logs panel."""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton("📜 Admin Actions", callback_data="logs_admin"),
            InlineKeyboardButton("❌ Error Logs", callback_data="logs_errors")
        ],
        [
            InlineKeyboardButton("🔄 Sync History", callback_data="logs_sync"),
            InlineKeyboardButton("👤 User Activity", callback_data="logs_activity")
        ],
        [
            InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_dashboard")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "📜 **System Logs**\n\n"
        "View detailed logs for:\n"
        "• Admin actions and operations\n"
        "• System errors and issues\n"
        "• Synchronization history\n"
        "• User activity tracking\n\n"
        "Select a log type:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def show_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent admin action logs."""
    query = update.callback_query
    await query.answer()

    # Get recent admin logs
    logs = db.get_audit_logs(limit=10)

    text = "📜 **Recent Admin Actions**\n\n"

    if not logs:
        text += "No admin actions logged yet."
    else:
        for log in logs:
            admin_id = log.get("admin_id")
            action = log.get("action_type")
            timestamp = log.get("created_at", "")[:19]
            status = log.get("status", "unknown")
            status_emoji = "✅" if status == "success" else "❌"

            text += f"{status_emoji} `{timestamp}`\n"
            text += f"Admin: `{admin_id}` | Action: `{action}`\n\n"

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Logs", callback_data="admin_logs")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@admin_only
async def show_sync_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show sync history logs."""
    query = update.callback_query
    await query.answer()

    # Get sync history
    sync_history = db.get_sync_history(limit=10)

    text = "🔄 **Sync History**\n\n"

    if not sync_history:
        text += "No sync operations logged yet."
    else:
        for sync in sync_history:
            sync_type = sync.get("sync_type", "unknown")
            status = sync.get("status", "unknown")
            timestamp = sync.get("started_at", "")[:19]
            records = sync.get("records_synced", 0)
            status_emoji = "✅" if status == "completed" else "❌"

            text += f"{status_emoji} `{timestamp}`\n"
            text += f"Type: `{sync_type}` | Records: `{records}`\n\n"

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Logs", callback_data="admin_logs")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Admin Help
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def show_admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin help and documentation."""
    query = update.callback_query
    await query.answer()

    text = (
        "ℹ️ **Admin Panel Help**\n\n"
        "**Available Commands:**\n"
        "• `/admin` - Open admin panel\n"
        "• `/stats` - Quick statistics\n\n"
        "**Sync Management:**\n"
        "• Telegram → DB: Sync content from Telegram group\n"
        "• DB → Frontend: Update frontend JSON files\n"
        "• Full Sync: Complete synchronization\n\n"
        "**Reports:**\n"
        "• Generate detailed reports on demand\n"
        "• Export reports to JSON format\n"
        "• Monitor system health\n\n"
        "**User Management:**\n"
        "• View and manage all users\n"
        "• Block/unblock users\n"
        "• Manage premium status\n\n"
        "**System Monitoring:**\n"
        "• Check HuggingFace Spaces status\n"
        "• View error logs\n"
        "• Track admin actions\n\n"
        "For more information, check the documentation."
    )

    keyboard = [[InlineKeyboardButton(
        "🔙 Back to Admin", callback_data="admin_dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Callback Query Router
# ══════════════════════════════════════════════════════════════════════════════

async def handle_admin_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Route admin callback queries to appropriate handlers."""
    query = update.callback_query
    data = query.data

    # Dashboard
    if data == "admin_dashboard":
        await admin_command(update, context)

    # Sync Management
    elif data == "admin_sync":
        await show_sync_management(update, context)
    elif data == "sync_telegram_db":
        await trigger_telegram_db_sync(update, context)
    elif data == "sync_db_frontend":
        await trigger_db_frontend_sync(update, context)
    elif data == "sync_full":
        await trigger_full_sync(update, context)
    elif data == "sync_health":
        await show_sync_health(update, context)

    # Reports
    elif data == "admin_reports":
        await show_reports_menu(update, context)
    elif data == "report_users":
        await generate_user_report(update, context)
    elif data == "report_content":
        await generate_content_report(update, context)
    elif data == "report_health":
        await generate_health_report(update, context)
    elif data == "report_spaces":
        await generate_spaces_report(update, context)
    elif data == "report_complete":
        await generate_complete_report(update, context)

    # User Management
    elif data == "admin_users":
        await show_user_management(update, context)

    # Content Management
    elif data == "admin_content":
        await show_content_management(update, context)

    # Logs
    elif data == "admin_logs":
        await show_system_logs(update, context)
    elif data == "logs_admin":
        await show_admin_logs(update, context)
    elif data == "logs_sync":
        await show_sync_logs(update, context)

    # Help
    elif data == "admin_help":
        await show_admin_help(update, context)

    else:
        await query.answer("Feature coming soon!", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
# Quick Stats Command
# ══════════════════════════════════════════════════════════════════════════════

@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick statistics command."""
    stats = db.get_stats()
    users = db.get_all_users()
    sync_history = db.get_sync_history(limit=1)

    last_sync = sync_history[0].get("started_at") if sync_history else "Never"

    text = (
        "📊 **Quick Statistics**\n\n"
        "**Users:**\n"
        f"• Total: `{len(users)}`\n\n"
        "**Content:**\n"
        f"• Movies: `{stats.get('total_movies', 0)}`\n"
        f"• Series: `{stats.get('total_series', 0)}`\n"
        f"• Episodes: `{stats.get('total_episodes', 0)}`\n\n"
        f"**Last Sync:** `{last_sync[:19] if last_sync != 'Never' else 'Never'}`")

    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Admin Panel Integration
# ══════════════════════════════════════════════════════════════════════════════

def setup_admin_handlers(application: Application):
    """Setup admin panel handlers."""

    # Commands
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Callback queries
    application.add_handler(CallbackQueryHandler(
        handle_admin_callback,
        pattern="^(admin_|sync_|report_|users_|content_|logs_)"
    ))

    logger.info("✅ Admin panel handlers configured")


# ══════════════════════════════════════════════════════════════════════════════
# Initialization
# ══════════════════════════════════════════════════════════════════════════════

logger.info("🔐 Admin Panel initialized")

# Made with Bob
