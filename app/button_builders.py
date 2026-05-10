"""
PopCorn Button Builders Module
Comprehensive button building utilities for Telegram bot with Arabic UI.
Provides consistent button layouts across all bot interfaces.
"""
import logging
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════════

def create_inline_button(
        text: str,
        callback_data: str) -> InlineKeyboardButton:
    """
    Create a single inline keyboard button.

    Args:
        text: Button text to display
        callback_data: Callback data for the button

    Returns:
        InlineKeyboardButton instance
    """
    return InlineKeyboardButton(text, callback_data=callback_data)


def create_button_row(
        buttons: List[InlineKeyboardButton]) -> List[InlineKeyboardButton]:
    """
    Create a row of buttons.

    Args:
        buttons: List of InlineKeyboardButton instances

    Returns:
        List representing a button row
    """
    return buttons


def add_back_button(
    keyboard: List[List[InlineKeyboardButton]],
    callback_data: str,
    label: str = "🔙 رجوع"
) -> List[List[InlineKeyboardButton]]:
    """
    Add a back button to an existing keyboard.

    Args:
        keyboard: Existing keyboard layout
        callback_data: Callback data for back button
        label: Button label (default: "🔙 رجوع")

    Returns:
        Updated keyboard with back button
    """
    keyboard.append([create_inline_button(label, callback_data)])
    return keyboard


# ══════════════════════════════════════════════════════════════════════════════
# Main Menu Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_main_menu(
        user_id: int,
        is_premium: bool = False) -> InlineKeyboardMarkup:
    """
    Build the main menu keyboard (القائمة الرئيسية).

    Args:
        user_id: Telegram user ID
        is_premium: Whether user has premium subscription

    Returns:
        InlineKeyboardMarkup for main menu
    """
    keyboard = [
        [
            create_inline_button("🎬 الأفلام", "browse_movies_0"),
            create_inline_button("📺 المسلسلات", "browse_series_0")
        ],
        [
            create_inline_button("🔍 بحث", "search_content"),
            create_inline_button("🔥 الأكثر مشاهدة", "filter_trending")
        ],
        [
            create_inline_button("⭐ المفضلة", "my_favorites"),
            create_inline_button("📜 السجل", "my_history")
        ],
        [
            create_inline_button("▶️ متابعة المشاهدة", "continue_watching")
        ],
        [
            create_inline_button("👤 حسابي", "my_profile")
        ]
    ]

    # Add premium button if not premium
    if not is_premium:
        keyboard.append([create_inline_button(
            "👑 الاشتراك المميز", "premium_features")])

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Browse Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_browse_buttons(
    content_type: str,
    page: int = 0,
    total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Build browse buttons with pagination for movies or series.

    Args:
        content_type: "movies" or "series"
        page: Current page number (0-indexed)
        total_pages: Total number of pages

    Returns:
        InlineKeyboardMarkup for browse interface
    """
    keyboard = []

    # Filter buttons
    if content_type == "movies":
        keyboard.append([
            create_inline_button("🎭 التصنيفات", "filter_genre"),
            create_inline_button("⭐ الأعلى تقييماً", "filter_top_rated")
        ])
        keyboard.append([
            create_inline_button("📅 الأحدث", "filter_newest"),
            create_inline_button("🔥 الأكثر مشاهدة", "filter_trending")
        ])
    else:  # series
        keyboard.append([
            create_inline_button("🎭 التصنيفات", "filter_genre_series"),
            create_inline_button("⭐ الأعلى تقييماً", "filter_top_rated_series")
        ])
        keyboard.append([
            create_inline_button("📅 الأحدث", "filter_newest_series"),
            create_inline_button("🔥 الأكثر مشاهدة", "filter_trending_series")
        ])

    # Pagination buttons
    pagination = build_pagination_buttons(
        f"browse_{content_type}",
        page,
        total_pages
    )
    if pagination:
        keyboard.extend(pagination.inline_keyboard)

    # Back to main menu
    keyboard.append([create_inline_button("🔙 القائمة الرئيسية", "main_menu")])

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Content Details Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_content_details_buttons(
    content_id: int,
    content_type: str,
    is_favorite: bool = False
) -> InlineKeyboardMarkup:
    """
    Build buttons for movie or series details page.

    Args:
        content_id: Movie or series ID
        content_type: "movie" or "series"
        is_favorite: Whether content is in user's favorites

    Returns:
        InlineKeyboardMarkup for content details
    """
    keyboard = []

    if content_type == "movie":
        # Watch button
        keyboard.append([
            create_inline_button("▶️ شاهد الآن", f"watch_movie_{content_id}")
        ])

        # Favorite and share buttons
        fav_text = "💔 إزالة من المفضلة" if is_favorite else "⭐ إضافة للمفضلة"
        fav_callback = f"fav_remove_movie_{content_id}" if is_favorite else f"fav_add_movie_{content_id}"

        keyboard.append([
            create_inline_button(fav_text, fav_callback),
            create_inline_button("📤 مشاركة", f"share_movie_{content_id}")
        ])

        # Additional info buttons
        keyboard.append([
            create_inline_button("💬 التقييمات", f"movie_reviews_{content_id}"),
            create_inline_button("ℹ️ المزيد", f"movie_info_{content_id}")
        ])

        # Back button
        keyboard.append([
            create_inline_button("🔙 العودة للأفلام", "browse_movies_0")
        ])

    else:  # series
        # View seasons button
        keyboard.append([create_inline_button(
            "📺 عرض المواسم", f"series_seasons_{content_id}")])

        # Favorite and share buttons
        fav_text = "💔 إزالة من المفضلة" if is_favorite else "⭐ إضافة للمفضلة"
        fav_callback = f"fav_remove_series_{content_id}" if is_favorite else f"fav_add_series_{content_id}"

        keyboard.append([
            create_inline_button(fav_text, fav_callback),
            create_inline_button("📤 مشاركة", f"share_series_{content_id}")
        ])

        # Additional info buttons
        keyboard.append([
            create_inline_button("💬 التقييمات", f"series_reviews_{content_id}"),
            create_inline_button("ℹ️ المزيد", f"series_info_{content_id}")
        ])

        # Back button
        keyboard.append([
            create_inline_button("🔙 العودة للمسلسلات", "browse_series_0")
        ])

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Season & Episode Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_season_buttons(
        series_id: int,
        seasons: List[dict]) -> InlineKeyboardMarkup:
    """
    Build season selection buttons for a series.

    Args:
        series_id: Series ID
        seasons: List of season dictionaries with 'season_number' and 'episode_count'

    Returns:
        InlineKeyboardMarkup for season selection
    """
    keyboard = []

    # Create season buttons (2 per row)
    for i in range(0, len(seasons), 2):
        row = []
        for j in range(2):
            if i + j < len(seasons):
                season = seasons[i + j]
                season_num = season.get('season_number', i + j + 1)
                episode_count = season.get('episode_count', 0)

                button_text = f"الموسم {season_num} ({episode_count} حلقة)"
                callback_data = f"season_{series_id}_{season_num}"
                row.append(create_inline_button(button_text, callback_data))

        keyboard.append(row)

    # Back button
    keyboard.append([
        create_inline_button("🔙 العودة للمسلسل", f"series_{series_id}")
    ])

    return InlineKeyboardMarkup(keyboard)


def build_episode_buttons(
    series_id: int,
    season_num: int,
    episodes: List[dict],
    page: int = 0
) -> InlineKeyboardMarkup:
    """
    Build episode list buttons with pagination.

    Args:
        series_id: Series ID
        season_num: Season number
        episodes: List of episode dictionaries
        page: Current page number

    Returns:
        InlineKeyboardMarkup for episode list
    """
    keyboard = []

    # Episodes per page
    per_page = 10
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(episodes))

    # Create episode buttons (2 per row)
    for i in range(start_idx, end_idx, 2):
        row = []
        for j in range(2):
            if i + j < end_idx:
                episode = episodes[i + j]
                ep_num = episode.get('episode_number', i + j + 1)
                ep_title = episode.get('title', f'الحلقة {ep_num}')

                # Truncate title if too long
                if len(ep_title) > 20:
                    ep_title = ep_title[:17] + "..."

                button_text = f"{ep_num}. {ep_title}"
                callback_data = f"episode_{series_id}_{season_num}_{ep_num}"
                row.append(create_inline_button(button_text, callback_data))

        keyboard.append(row)

    # Pagination if needed
    total_pages = (len(episodes) + per_page - 1) // per_page
    if total_pages > 1:
        pagination = build_pagination_buttons(
            f"episodes_{series_id}_{season_num}",
            page,
            total_pages
        )
        if pagination:
            keyboard.extend(pagination.inline_keyboard)

    # Back button
    keyboard.append([
        create_inline_button("🔙 العودة للمواسم", f"series_seasons_{series_id}")
    ])

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Profile Menu Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_profile_menu() -> InlineKeyboardMarkup:
    """
    Build user profile menu buttons.

    Returns:
        InlineKeyboardMarkup for profile menu
    """
    keyboard = [
        [
            create_inline_button("⭐ المفضلة", "my_favorites"),
            create_inline_button("📜 السجل", "my_history")
        ],
        [
            create_inline_button("▶️ متابعة المشاهدة", "continue_watching")
        ],
        [
            create_inline_button("👑 حالة الاشتراك", "premium_status"),
            create_inline_button("⚙️ الإعدادات", "user_settings")
        ],
        [
            create_inline_button("🔔 الإشعارات", "user_notifications"),
            create_inline_button("🌐 اللغة", "user_language")
        ],
        [
            create_inline_button("🗑️ مسح السجل", "clear_history")
        ],
        [
            create_inline_button("🔙 القائمة الرئيسية", "main_menu")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Admin Panel Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_admin_panel(admin_role: str) -> InlineKeyboardMarkup:
    """
    Build admin panel based on role.

    Args:
        admin_role: "super_admin", "admin", or "moderator"

    Returns:
        InlineKeyboardMarkup for admin panel
    """
    keyboard = []

    # Dashboard (all roles)
    keyboard.append([
        create_inline_button("📊 لوحة المعلومات", "admin_dashboard")
    ])

    # Content management (admin and super_admin)
    if admin_role in ["super_admin", "admin"]:
        keyboard.append([
            create_inline_button("🎬 إدارة المحتوى", "admin_content"),
            create_inline_button("👥 إدارة المستخدمين", "admin_users")
        ])

    # Moderator has limited access
    if admin_role == "moderator":
        keyboard.append([
            create_inline_button("👥 عرض المستخدمين", "admin_users"),
            create_inline_button("🎬 عرض المحتوى", "admin_content")
        ])

    # Sync operations (admin and super_admin)
    if admin_role in ["super_admin", "admin"]:
        keyboard.append([
            create_inline_button("🔄 المزامنة", "admin_sync"),
            create_inline_button("📈 الإحصائيات", "admin_analytics")
        ])

    # Analytics (all roles, but different access levels)
    if admin_role == "moderator":
        keyboard.append([
            create_inline_button("📈 إحصائيات أساسية", "admin_analytics")
        ])

    # System settings (super_admin only)
    if admin_role == "super_admin":
        keyboard.append([
            create_inline_button("⚙️ إعدادات النظام", "admin_settings"),
            create_inline_button("📋 السجلات", "admin_logs")
        ])
        keyboard.append([
            create_inline_button("👑 إدارة المشرفين", "admin_manage_admins")
        ])

    # Back to main menu
    keyboard.append([
        create_inline_button("🔙 القائمة الرئيسية", "main_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def build_admin_content_menu() -> InlineKeyboardMarkup:
    """
    Build content management menu for admins.

    Returns:
        InlineKeyboardMarkup for content management
    """
    keyboard = [
        [
            create_inline_button("🎬 الأفلام", "admin_content_movies"),
            create_inline_button("📺 المسلسلات", "admin_content_series")
        ],
        [
            create_inline_button("➕ إضافة محتوى", "admin_content_add")
        ],
        [
            create_inline_button("🔄 مزامنة المجموعة", "admin_sync_telegram_db")
        ],
        [
            create_inline_button("📊 إحصائيات المحتوى", "admin_content_stats")
        ],
        [
            create_inline_button("🔙 لوحة التحكم", "admin_panel")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def build_admin_user_menu() -> InlineKeyboardMarkup:
    """
    Build user management menu for admins.

    Returns:
        InlineKeyboardMarkup for user management
    """
    keyboard = [
        [
            create_inline_button("👥 قائمة المستخدمين", "admin_users_list_0"),
            create_inline_button("🔍 بحث عن مستخدم", "admin_users_search")
        ],
        [
            create_inline_button("🚫 المستخدمون المحظورون", "admin_users_blocked"),
            create_inline_button("👑 المشتركون المميزون", "admin_users_premium")
        ],
        [
            create_inline_button("📊 إحصائيات المستخدمين", "admin_users_stats")
        ],
        [
            create_inline_button("🔙 لوحة التحكم", "admin_panel")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def build_admin_analytics_menu() -> InlineKeyboardMarkup:
    """
    Build analytics dashboard menu for admins.

    Returns:
        InlineKeyboardMarkup for analytics
    """
    keyboard = [
        [
            create_inline_button("📊 إحصائيات عامة", "admin_report_system"),
            create_inline_button("👥 تحليلات المستخدمين", "admin_report_users")
        ],
        [
            create_inline_button("🎬 تحليلات المحتوى", "admin_report_content"),
            create_inline_button("🔥 المحتوى الأكثر شعبية", "admin_popular_content")
        ],
        [
            create_inline_button("☁️ حالة HuggingFace", "admin_report_h")
        ],
        [
            create_inline_button("📥 تصدير البيانات", "admin_analytics_export")
        ],
        [
            create_inline_button("🔙 لوحة التحكم", "admin_panel")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Pagination Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_pagination_buttons(
    callback_prefix: str,
    current_page: int,
    total_pages: int
) -> Optional[InlineKeyboardMarkup]:
    """
    Build generic pagination buttons.

    Args:
        callback_prefix: Prefix for callback data (e.g., "browse_movies")
        current_page: Current page number (0-indexed)
        total_pages: Total number of pages

    Returns:
        InlineKeyboardMarkup with pagination buttons or None if only one page
    """
    if total_pages <= 1:
        return None

    keyboard = []
    row = []

    # Previous button
    if current_page > 0:
        row.append(create_inline_button(
            "⬅️ السابق",
            f"{callback_prefix}_{current_page - 1}"
        ))

    # Page indicator
    row.append(create_inline_button(
        f"📄 {current_page + 1}/{total_pages}",
        f"page_info_{current_page}"
    ))

    # Next button
    if current_page < total_pages - 1:
        row.append(create_inline_button(
            "التالي ➡️",
            f"{callback_prefix}_{current_page + 1}"
        ))

    keyboard.append(row)

    return InlineKeyboardMarkup(keyboard)


def build_back_button(
    callback_data: str,
    label: str = "🔙 رجوع"
) -> InlineKeyboardMarkup:
    """
    Build a simple back button keyboard.

    Args:
        callback_data: Callback data for the back button
        label: Button label (default: "🔙 رجوع")

    Returns:
        InlineKeyboardMarkup with single back button
    """
    keyboard = [[create_inline_button(label, callback_data)]]
    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Search & Filter Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_search_type_buttons() -> InlineKeyboardMarkup:
    """
    Build search type selection buttons.

    Returns:
        InlineKeyboardMarkup for search type selection
    """
    keyboard = [
        [
            create_inline_button("🎬 بحث في الأفلام", "search_movies"),
            create_inline_button("📺 بحث في المسلسلات", "search_series")
        ],
        [
            create_inline_button("🔍 بحث شامل", "search_all")
        ],
        [
            create_inline_button("🔙 القائمة الرئيسية", "main_menu")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def build_genre_filter_buttons(
        content_type: str = "movie") -> InlineKeyboardMarkup:
    """
    Build genre filter buttons.

    Args:
        content_type: "movie" or "series"

    Returns:
        InlineKeyboardMarkup for genre selection
    """
    # Common genres
    genres = [
        ("🎭 دراما", "drama"),
        ("😂 كوميديا", "comedy"),
        ("🎬 أكشن", "action"),
        ("💕 رومانسي", "romance"),
        ("😱 رعب", "horror"),
        ("🔍 غموض", "mystery"),
        ("🚀 خيال علمي", "scifi"),
        ("🗡️ مغامرة", "adventure")
    ]

    keyboard = []

    # Create genre buttons (2 per row)
    for i in range(0, len(genres), 2):
        row = []
        for j in range(2):
            if i + j < len(genres):
                label, genre = genres[i + j]
                callback = f"genre_{content_type}_{genre}"
                row.append(create_inline_button(label, callback))
        keyboard.append(row)

    # Back button
    back_callback = "browse_movies_0" if content_type == "movie" else "browse_series_0"
    keyboard.append([create_inline_button("🔙 رجوع", back_callback)])

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Confirmation Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_confirmation_buttons(
    confirm_callback: str,
    cancel_callback: str,
    confirm_text: str = "✅ تأكيد",
    cancel_text: str = "❌ إلغاء"
) -> InlineKeyboardMarkup:
    """
    Build confirmation dialog buttons.

    Args:
        confirm_callback: Callback data for confirm button
        cancel_callback: Callback data for cancel button
        confirm_text: Confirm button text
        cancel_text: Cancel button text

    Returns:
        InlineKeyboardMarkup for confirmation dialog
    """
    keyboard = [
        [
            create_inline_button(confirm_text, confirm_callback),
            create_inline_button(cancel_text, cancel_callback)
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# ══════════════════════════════════════════════════════════════════════════════
# Premium Features Buttons
# ══════════════════════════════════════════════════════════════════════════════

def build_premium_buttons(is_premium: bool = False) -> InlineKeyboardMarkup:
    """
    Build premium features buttons.

    Args:
        is_premium: Whether user has premium subscription

    Returns:
        InlineKeyboardMarkup for premium features
    """
    keyboard = []

    if not is_premium:
        keyboard.append([
            create_inline_button("👑 الترقية للبريميوم", "upgrade_premium")
        ])
        keyboard.append([
            create_inline_button("ℹ️ مزايا البريميوم", "premium_benefits")
        ])
    else:
        keyboard.append([
            create_inline_button("✅ أنت مشترك بريميوم", "premium_status")
        ])
        keyboard.append([
            create_inline_button("📊 إحصائياتي", "premium_stats")
        ])

    keyboard.append([
        create_inline_button("🔙 القائمة الرئيسية", "main_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


# Made with Bob
