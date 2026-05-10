"""
PopCorn Bot Commands - Merged Version
Contains both user commands and admin commands with proper database integration.
Fixed to use correct database calls without limit/offset parameters.
"""
import logging
from typing import List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler
)

from app.config import SUBSCRIPTION_REQUIRED
from app import database as db
from app.subscription_checker import (
    check_subscription,
    send_subscription_prompt,
    handle_subscription_check
)
from app.admin_permissions import (
    Permission,
    require_permission,
    require_admin,
    get_role_display_name
)
from app.bot_tracking import track_bot_interaction
from app.button_builders import (
    build_admin_panel,
    build_admin_content_menu,
    build_admin_user_menu,
    build_admin_analytics_menu,
    build_back_button,
    build_confirmation_buttons
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

# Conversation States
REGISTRATION_NAME, REGISTRATION_LANGUAGE = range(2)

# Pagination settings
ITEMS_PER_PAGE = 10

# ══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════════


def get_user_language(user_id: int) -> str:
    """Get user's preferred language."""
    try:
        profile = db.get_user_profile(user_id)
        if profile and 'preferences' in profile:
            prefs = profile.get('preferences', {})
            if isinstance(prefs, str):
                import json
                prefs = json.loads(prefs)
            return prefs.get('language', 'ar')
        return 'ar'
    except Exception:
        return 'ar'


def is_user_premium(user_id: int) -> bool:
    """Check if user has premium subscription."""
    try:
        user = db.get_user(user_id)
        return user.get('is_premium', False) if user else False
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════════════════════
# User Commands - Required by main.py
# ══════════════════════════════════════════════════════════════════════════════


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - entry point for registration."""
    user = update.effective_user

    # Check subscription first if required
    if SUBSCRIPTION_REQUIRED:
        is_subscribed, status = await check_subscription(user.id, context.bot)
        if not is_subscribed:
            await send_subscription_prompt(update, context)
            return ConversationHandler.END

    # Check if user exists
    existing_user = db.get_user(user.id)

    if existing_user:
        # User already registered, show main menu
        await show_main_menu(update, context)
        return ConversationHandler.END

    # New user - start registration with Arabic interface
    welcome_text = (
        "🍿 **مرحباً بك في PopCorn!**\n\n"
        f"أهلاً {user.first_name}! 👋\n\n"
        "PopCorn هو وجهتك المثالية لمشاهدة الأفلام والمسلسلات.\n\n"
        "دعنا نبدأ! الرجاء إدخال اسمك المفضل:"
    )

    await update.message.reply_text(welcome_text, parse_mode="Markdown")

    return REGISTRATION_NAME


async def cmd_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /app command - show web app link."""
    user = update.effective_user
    language = get_user_language(user.id)

    text = (
        "🌐 **تطبيق الويب PopCorn**\n\n"
        "يمكنك الوصول إلى PopCorn من خلال متصفح الويب:\n"
        "🔗 https://your-app-url.com\n\n"
        "استمتع بتجربة مشاهدة أفضل على الشاشة الكبيرة! 🍿"
    ) if language == 'ar' else (
        "🌐 **PopCorn Web App**\n\n"
        "Access PopCorn through your web browser:\n"
        "🔗 https://your-app-url.com\n\n"
        "Enjoy a better viewing experience on the big screen! 🍿"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show help information."""
    user = update.effective_user
    language = get_user_language(user.id)

    text = (
        "❓ **مساعدة PopCorn**\n\n"
        "**الأوامر المتاحة:**\n"
        "/start - بدء البوت أو التسجيل\n"
        "/menu - عرض القائمة الرئيسية\n"
        "/app - رابط تطبيق الويب\n"
        "/help - عرض هذه المساعدة\n"
        "/new - أحدث المحتوى\n"
        "/top - الأعلى تقييماً\n"
        "/stats - إحصائياتك\n\n"
        "**كيفية الاستخدام:**\n"
        "1️⃣ استخدم /start للبدء\n"
        "2️⃣ تصفح الأفلام والمسلسلات\n"
        "3️⃣ اختر ما تريد مشاهدته\n"
        "4️⃣ استمتع! 🍿"
    ) if language == 'ar' else (
        "❓ **PopCorn Help**\n\n"
        "**Available Commands:**\n"
        "/start - Start bot or register\n"
        "/menu - Show main menu\n"
        "/app - Web app link\n"
        "/help - Show this help\n"
        "/new - Latest content\n"
        "/top - Top rated\n"
        "/stats - Your statistics\n\n"
        "**How to Use:**\n"
        "1️⃣ Use /start to begin\n"
        "2️⃣ Browse movies and series\n"
        "3️⃣ Select what you want to watch\n"
        "4️⃣ Enjoy! 🍿"
    )

    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - show latest content."""
    user = update.effective_user
    language = get_user_language(user.id)

    try:
        # Get all movies and series, then sort by date
        movies = db.get_movies()
        series_list = db.get_series_list()

        # Sort by date (newest first)
        movies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        series_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        # Get top 5 of each
        latest_movies = movies[:5]
        latest_series = series_list[:5]

        text = "🆕 **أحدث المحتوى**\n\n" if language == 'ar' else "🆕 **Latest Content**\n\n"

        if latest_movies:
            text += "**🎬 أفلام جديدة:**\n" if language == 'ar' else "**🎬 New Movies:**\n"
            for movie in latest_movies:
                text += f"• {movie.get('title', 'Unknown')} ⭐ {movie.get('rating', 0):.1f}\n"
            text += "\n"

        if latest_series:
            text += "**📺 مسلسلات جديدة:**\n" if language == 'ar' else "**📺 New Series:**\n"
            for series in latest_series:
                text += f"• {series.get('title', 'Unknown')} ⭐ {series.get('rating', 0):.1f}\n"

        keyboard = [[InlineKeyboardButton(
            "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in cmd_new: {e}", exc_info=True)
        await update.message.reply_text("❌ حدث خطأ / Error occurred")


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /top command - show top rated content."""
    user = update.effective_user
    language = get_user_language(user.id)

    try:
        # Get all movies and series, then sort by rating
        movies = db.get_movies()
        series_list = db.get_series_list()

        # Sort by rating (highest first)
        movies.sort(key=lambda x: x.get('rating', 0), reverse=True)
        series_list.sort(key=lambda x: x.get('rating', 0), reverse=True)

        # Get top 5 of each
        top_movies = movies[:5]
        top_series = series_list[:5]

        text = "⭐ **الأعلى تقييماً**\n\n" if language == 'ar' else "⭐ **Top Rated**\n\n"

        if top_movies:
            text += "**🎬 أفضل الأفلام:**\n" if language == 'ar' else "**🎬 Top Movies:**\n"
            for i, movie in enumerate(top_movies, 1):
                text += f"{i}. {movie.get('title', 'Unknown')} ⭐ {movie.get('rating', 0):.1f}\n"
            text += "\n"

        if top_series:
            text += "**📺 أفضل المسلسلات:**\n" if language == 'ar' else "**📺 Top Series:**\n"
            for i, series in enumerate(top_series, 1):
                text += f"{i}. {series.get('title', 'Unknown')} ⭐ {series.get('rating', 0):.1f}\n"

        keyboard = [[InlineKeyboardButton(
            "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in cmd_top: {e}", exc_info=True)
        await update.message.reply_text("❌ حدث خطأ / Error occurred")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show user statistics."""
    user = update.effective_user
    language = get_user_language(user.id)

    try:
        # Get user statistics
        watch_count = db.get_user_watch_count(user.id)
        favorites_count = db.get_user_favorites_count(user.id)
        user_data = db.get_user(user.id)
        is_premium = user_data.get('is_premium', False) if user_data else False

        text = (
            "📊 **إحصائياتك**\n\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🎭 الحالة: {'👑 بريميوم' if is_premium else '⭐ عادي'}\n"
            f"🎬 المشاهدات: {watch_count}\n"
            f"⭐ المفضلة: {favorites_count}\n"
        ) if language == 'ar' else (
            "📊 **Your Statistics**\n\n"
            f"👤 Name: {user.first_name}\n"
            f"🎭 Status: {'👑 Premium' if is_premium else '⭐ Regular'}\n"
            f"🎬 Watched: {watch_count}\n"
            f"⭐ Favorites: {favorites_count}\n"
        )

        keyboard = [[InlineKeyboardButton(
            "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error in cmd_stats: {e}", exc_info=True)
        await update.message.reply_text("❌ حدث خطأ / Error occurred")


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - show admin panel."""
    return await admin_command(update, context)


async def registration_name(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Handle user name input during registration."""
    update.effective_user
    name = update.message.text.strip()

    # Store name in context
    context.user_data['registration_name'] = name

    # Ask for language preference with Arabic first
    keyboard = [
        [
            InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"رائع، {name}! 👍\n\nالآن، الرجاء اختيار لغتك المفضلة:",
        reply_markup=reply_markup
    )

    return REGISTRATION_LANGUAGE


async def registration_language(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection and complete registration."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = query.data.split("_")[1]  # Extract 'en' or 'ar'
    name = context.user_data.get('registration_name', user.first_name)

    # Create user in database
    try:
        db.create_or_update_user({
            "user_id": user.id,
            "username": user.username,
            "first_name": name,
            "last_name": user.last_name,
            "language_code": language,
            "is_bot": False,
            "is_blocked": False,
            "is_premium": False
        })

        # Create user profile
        db.create_or_update_user_profile(
            user_id=user.id,
            preferences={"language": language}
        )

        # Log registration activity
        db.log_user_activity(
            user_id=user.id,
            activity_type="registration",
            activity_details="First registration completed"
        )

        success_text = (
            "✅ **اكتمل التسجيل!**\n\n"
            f"مرحباً بك، {name}! 🎉\n\n"
            "أصبح لديك الآن وصول كامل إلى مكتبتنا من الأفلام والمسلسلات.\n\n"
            "استخدم القائمة أدناه لبدء الاستكشاف! 🍿") if language == 'ar' else (
            "✅ **Registration Complete!**\n\n"
            f"Welcome aboard, {name}! 🎉\n\n"
            "You now have access to our entire library of movies and series.\n\n"
            "Use the menu below to start exploring! 🍿")

        await query.edit_message_text(success_text, parse_mode="Markdown")

        # Show main menu
        await show_main_menu_callback(update, context)

    except Exception as e:
        logger.error(f"Registration error for user {user.id}: {e}")
        await query.edit_message_text(
            "❌ حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى.\n"
            "Registration failed. Please try again with /start",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cancel_registration(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Cancel registration process."""
    await update.message.reply_text(
        "تم إلغاء التسجيل. استخدم /start للبدء مرة أخرى.\n"
        "Registration cancelled. Use /start to begin again.",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
# Main Menu
# ══════════════════════════════════════════════════════════════════════════════

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu to user."""
    user = update.effective_user
    language = get_user_language(user.id)

    # Get user info
    user_data = db.get_user(user.id)
    is_premium = user_data.get("is_premium", False) if user_data else False

    keyboard = [
        [
            InlineKeyboardButton("🎬 الأفلام" if language == 'ar' else "🎬 Movies", callback_data="browse_movies"),
            InlineKeyboardButton("📺 المسلسلات" if language == 'ar' else "📺 Series", callback_data="browse_series")
        ],
        [
            InlineKeyboardButton("🔍 بحث" if language == 'ar' else "🔍 Search", callback_data="search_content"),
            InlineKeyboardButton("⭐ المفضلة" if language == 'ar' else "⭐ Favorites", callback_data="my_favorites")
        ],
        [
            InlineKeyboardButton("👤 حسابي" if language == 'ar' else "👤 My Profile", callback_data="my_profile"),
            InlineKeyboardButton("📜 السجل" if language == 'ar' else "📜 History", callback_data="my_history")
        ]
    ]

    if is_premium:
        keyboard.append([InlineKeyboardButton("👑 الميزات المميزة" if language ==
                        'ar' else "👑 Premium Features", callback_data="premium_features")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "🍿 **PopCorn - القائمة الرئيسية**\n\n"
        f"مرحباً بعودتك، {user.first_name}! 👋\n\n"
        "ماذا تريد أن تشاهد اليوم؟"
    ) if language == 'ar' else (
        "🍿 **PopCorn - Main Menu**\n\n"
        f"Welcome back, {user.first_name}! 👋\n\n"
        "What would you like to watch today?"
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_main_menu_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show main menu from callback query."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)
    user_data = db.get_user(user.id)
    is_premium = user_data.get("is_premium", False) if user_data else False

    keyboard = [
        [
            InlineKeyboardButton("🎬 الأفلام" if language == 'ar' else "🎬 Movies", callback_data="browse_movies"),
            InlineKeyboardButton("📺 المسلسلات" if language == 'ar' else "📺 Series", callback_data="browse_series")
        ],
        [
            InlineKeyboardButton("🔍 بحث" if language == 'ar' else "🔍 Search", callback_data="search_content"),
            InlineKeyboardButton("⭐ المفضلة" if language == 'ar' else "⭐ Favorites", callback_data="my_favorites")
        ],
        [
            InlineKeyboardButton("👤 حسابي" if language == 'ar' else "👤 My Profile", callback_data="my_profile"),
            InlineKeyboardButton("📜 السجل" if language == 'ar' else "📜 History", callback_data="my_history")
        ]
    ]

    if is_premium:
        keyboard.append([InlineKeyboardButton("👑 الميزات المميزة" if language ==
                        'ar' else "👑 Premium Features", callback_data="premium_features")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "🍿 **PopCorn - القائمة الرئيسية**\n\n"
        f"مرحباً بعودتك، {user.first_name}! 👋\n\n"
        "ماذا تريد أن تشاهد اليوم؟"
    ) if language == 'ar' else (
        "🍿 **PopCorn - Main Menu**\n\n"
        f"Welcome back, {user.first_name}! 👋\n\n"
        "What would you like to watch today?"
    )

    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Browse Movies - FIXED VERSION
# ══════════════════════════════════════════════════════════════════════════════

async def browse_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse movies with pagination - FIXED to use actual database functions."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)

    # Parse page number from callback data
    page = 0
    if "_" in query.data:
        try:
            page = int(query.data.split("_")[-1])
        except (ValueError, IndexError):
            page = 0

    try:
        # Get ALL movies from database (using actual function signature)
        movies = db.get_movies()

        # Filter movies with files only
        movies_with_files = [m for m in movies if m.get("file_id")]

        # Sort by rating
        movies_with_files.sort(key=lambda x: x.get("rating", 0), reverse=True)

        # Pagination in Python
        total_movies = len(movies_with_files)
        total_pages = (total_movies + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_movies = movies_with_files[start_idx:end_idx]

        if not page_movies:
            text = "❌ لا توجد أفلام متاحة حالياً." if language == 'ar' else "❌ No movies available at the moment."
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Back to Menu",
                        callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            return

        # Build keyboard with movie buttons
        keyboard = []
        for movie in page_movies:
            title = movie.get("title", "Unknown")
            rating = movie.get("rating", 0)
            button_text = f"🎬 {title} ⭐ {rating:.1f}"
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"movie_{movie['id']}")])

        # Pagination buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ السابق" if language == 'ar' else "⬅️ Previous",
                    callback_data=f"browse_movies_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    "التالي ➡️" if language == 'ar' else "Next ➡️",
                    callback_data=f"browse_movies_{page+1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Back button
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية" if language ==
                        'ar' else "🔙 Back to Menu", callback_data="main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "🎬 **مكتبة الأفلام**\n\n"
            f"📊 إجمالي الأفلام: {total_movies}\n"
            f"📄 الصفحة {page + 1} من {total_pages}\n\n"
            "اختر فيلماً للمشاهدة:"
        ) if language == 'ar' else (
            "🎬 **Movies Library**\n\n"
            f"📊 Total Movies: {total_movies}\n"
            f"📄 Page {page + 1} of {total_pages}\n\n"
            "Select a movie to watch:"
        )

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error browsing movies: {e}", exc_info=True)
        text = "❌ حدث خطأ أثناء تحميل الأفلام." if language == 'ar' else "❌ Error loading movies."
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Back to Menu",
                    callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)


async def show_movie_details(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show detailed information about a movie."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)

    movie_id = query.data.split("_")[1]
    movie = db.get_movie(movie_id=movie_id)

    if not movie:
        text = "❌ الفيلم غير موجود." if language == 'ar' else "❌ Movie not found."
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 العودة للأفلام" if language == 'ar' else "🔙 Back to Movies",
                    callback_data="browse_movies")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return

    # Format movie details
    title = movie.get("title", "Unknown")
    title_ar = movie.get("title_ar", "")
    overview = movie.get("overview", "No description available")
    rating = movie.get("rating", 0)
    release_date = movie.get("release_date", "Unknown")
    runtime = movie.get("runtime", 0)
    genres = movie.get("genres", "")

    if language == 'ar':
        text = f"🎬 **{title}**\n"
        if title_ar:
            text += f"_{title_ar}_\n"
        text += f"\n⭐ التقييم: {rating:.1f}/10\n"
        text += f"📅 تاريخ الإصدار: {release_date}\n"
        text += f"⏱️ المدة: {runtime} دقيقة\n"
        if genres:
            text += f"🎭 التصنيفات: {genres}\n"
        text += f"\n📝 {overview[:200]}..."
    else:
        text = f"🎬 **{title}**\n"
        if title_ar:
            text += f"_{title_ar}_\n"
        text += f"\n⭐ Rating: {rating:.1f}/10\n"
        text += f"📅 Release: {release_date}\n"
        text += f"⏱️ Runtime: {runtime} min\n"
        if genres:
            text += f"🎭 Genres: {genres}\n"
        text += f"\n📝 {overview[:200]}..."

    # Buttons
    keyboard = [
        [InlineKeyboardButton("▶️ شاهد الآن" if language == 'ar' else "▶️ Watch Now", callback_data=f"watch_movie_{movie_id}")],
        [
            InlineKeyboardButton("⭐ أضف للمفضلة" if language == 'ar' else "⭐ Add to Favorites", callback_data=f"fav_add_movie_{movie_id}"),
            InlineKeyboardButton("📤 مشاركة" if language == 'ar' else "📤 Share", callback_data=f"share_movie_{movie_id}")
        ],
        [InlineKeyboardButton("🔙 العودة للأفلام" if language == 'ar' else "🔙 Back to Movies", callback_data="browse_movies")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Browse Series - FIXED VERSION
# ══════════════════════════════════════════════════════════════════════════════

async def browse_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse series with pagination - FIXED to use actual database functions."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)

    # Parse page number
    page = 0
    if "_" in query.data and query.data.split("_")[-1].isdigit():
        page = int(query.data.split("_")[-1])

    try:
        # Get ALL series from database (using actual function signature)
        series_list = db.get_series_list()

        # Sort by rating
        series_list.sort(key=lambda x: x.get("rating", 0), reverse=True)

        # Pagination in Python
        total_series = len(series_list)
        total_pages = (total_series + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_series = series_list[start_idx:end_idx]

        if not page_series:
            text = "❌ لا توجد مسلسلات متاحة حالياً." if language == 'ar' else "❌ No series available at the moment."
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Back to Menu",
                        callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
            return

        # Build keyboard
        keyboard = []
        for series in page_series:
            title = series.get("title", "Unknown")
            rating = series.get("rating", 0)
            seasons = series.get("total_seasons", 0)
            button_text = f"📺 {title} ({seasons}S) ⭐ {rating:.1f}"
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"series_{series['id']}")])

        # Pagination buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(
                    "⬅️ السابق" if language == 'ar' else "⬅️ Previous",
                    callback_data=f"browse_series_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(
                    "التالي ➡️" if language == 'ar' else "Next ➡️",
                    callback_data=f"browse_series_{page+1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        # Back button
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية" if language ==
                        'ar' else "🔙 Back to Menu", callback_data="main_menu")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        text = (
            "📺 **مكتبة المسلسلات**\n\n"
            f"📊 إجمالي المسلسلات: {total_series}\n"
            f"📄 الصفحة {page + 1} من {total_pages}\n\n"
            "اختر مسلسلاً للمشاهدة:"
        ) if language == 'ar' else (
            "📺 **Series Library**\n\n"
            f"📊 Total Series: {total_series}\n"
            f"📄 Page {page + 1} of {total_pages}\n\n"
            "Select a series to watch:"
        )

        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error browsing series: {e}", exc_info=True)
        text = "❌ حدث خطأ أثناء تحميل المسلسلات." if language == 'ar' else "❌ Error loading series."
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 القائمة الرئيسية" if language == 'ar' else "🔙 Back to Menu",
                    callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)


async def show_series_details(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show detailed information about a series."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)

    series_id = query.data.split("_")[1]
    series = db.get_series(series_id=series_id)

    if not series:
        text = "❌ المسلسل غير موجود." if language == 'ar' else "❌ Series not found."
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 العودة للمسلسلات" if language == 'ar' else "🔙 Back to Series",
                    callback_data="browse_series")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)
        return

    # Get seasons
    seasons = db.get_series_seasons(series_id)

    # Format series details
    title = series.get("title", "Unknown")
    title_ar = series.get("title_ar", "")
    overview = series.get("overview", "No description available")
    rating = series.get("rating", 0)
    first_air_date = series.get("first_air_date", "Unknown")
    total_seasons = series.get("total_seasons", 0)
    status = series.get("status", "Unknown")
    genres = series.get("genres", "")

    if language == 'ar':
        text = f"📺 **{title}**\n"
        if title_ar:
            text += f"_{title_ar}_\n"
        text += f"\n⭐ التقييم: {rating:.1f}/10\n"
        text += f"📅 أول عرض: {first_air_date}\n"
        text += f"📊 المواسم: {total_seasons}\n"
        text += f"📡 الحالة: {status}\n"
        if genres:
            text += f"🎭 التصنيفات: {genres}\n"
        text += f"\n📝 {overview[:200]}..."
    else:
        text = f"📺 **{title}**\n"
        if title_ar:
            text += f"_{title_ar}_\n"
        text += f"\n⭐ Rating: {rating:.1f}/10\n"
        text += f"📅 First Air: {first_air_date}\n"
        text += f"📊 Seasons: {total_seasons}\n"
        text += f"📡 Status: {status}\n"
        if genres:
            text += f"🎭 Genres: {genres}\n"
        text += f"\n📝 {overview[:200]}..."

    # Buttons for seasons
    keyboard = []
    for season in seasons:
        season_num = season["season_number"]
        episode_count = season.get("episode_count", 0)
        button_text = f"الموسم {season_num} ({episode_count} حلقة)" if language == 'ar' else f"Season {season_num} ({episode_count} episodes)"
        keyboard.append([InlineKeyboardButton(button_text,
                                              callback_data=f"season_{series_id}_{season_num}")])

    # Additional buttons
    keyboard.append(
        [
            InlineKeyboardButton(
                "⭐ أضف للمفضلة" if language == 'ar' else "⭐ Add to Favorites",
                callback_data=f"fav_add_series_{series_id}"),
            InlineKeyboardButton(
                "📤 مشاركة" if language == 'ar' else "📤 Share",
                callback_data=f"share_series_{series_id}")])
    keyboard.append([InlineKeyboardButton("🔙 العودة للمسلسلات" if language ==
                    'ar' else "🔙 Back to Series", callback_data="browse_series")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


async def show_season_episodes(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show episodes for a specific season."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    language = get_user_language(user.id)

    # Parse series_id and season_number
    parts = query.data.split("_")
    series_id = parts[1]
    season_number = int(parts[2])

    # Get episodes
    episodes = db.get_episodes(series_id, season_number)

    if not episodes:
        text = f"❌ لم يتم العثور على حلقات للموسم {season_number}." if language == 'ar' else f"❌ No episodes found for Season {season_number}."
        keyboard = [
            [
                InlineKeyboardButton(
                    "🔙 العودة للمسلسل" if language == 'ar' else "🔙 Back to Series",
                    callback_data=f"series_{series_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        return

    # Get series info
    series = db.get_series(series_id=series_id)
    series_title = series.get("title", "Unknown") if series else "Unknown"

    # Build keyboard
    keyboard = []
    for episode in episodes:
        ep_num = episode["episode_number"]
        ep_title = episode.get("title", f"Episode {ep_num}")
        has_file = "✅" if episode.get("file_id") else "❌"
        button_text = f"{has_file} ح{ep_num}: {ep_title}" if language == 'ar' else f"{has_file} E{ep_num}: {ep_title}"
        keyboard.append([InlineKeyboardButton(
            button_text, callback_data=f"episode_{series_id}_{season_number}_{ep_num}")])

    # Back button
    keyboard.append([InlineKeyboardButton("🔙 العودة للمسلسل" if language ==
                    'ar' else "🔙 Back to Series", callback_data=f"series_{series_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        f"📺 **{series_title}**\n"
        f"الموسم {season_number}\n\n"
        f"📊 إجمالي الحلقات: {len(episodes)}\n\n"
        "اختر حلقة للمشاهدة:"
    ) if language == 'ar' else (
        f"📺 **{series_title}**\n"
        f"Season {season_number}\n\n"
        f"📊 Total Episodes: {len(episodes)}\n\n"
        "Select an episode to watch:"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Admin Panel Main
# ══════════════════════════════════════════════════════════════════════════════

@require_admin
@track_bot_interaction("command")
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - show admin panel."""
    user = update.effective_user

    # Get permission manager
    perm_manager = context.bot_data.get('permission_manager')
    if not perm_manager:
        await update.message.reply_text("❌ خطأ في النظام / System error")
        return

    # Get admin role
    admin_role = perm_manager.get_admin_role(user.id)
    if not admin_role:
        await update.message.reply_text(
            "❌ ليس لديك صلاحيات إدارية\n"
            "You don't have admin permissions"
        )
        return

    role_name = get_role_display_name(admin_role, 'ar')

    text = (
        "🛠️ **لوحة التحكم**\n\n"
        f"مرحباً {user.first_name}!\n"
        f"**الدور:** {role_name}\n\n"
        "اختر العملية المطلوبة:"
    )

    reply_markup = build_admin_panel(admin_role.value)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@require_admin
@track_bot_interaction("callback")
async def show_admin_panel_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel via callback."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    perm_manager = context.bot_data.get('permission_manager')
    if not perm_manager:
        await query.edit_message_text("❌ خطأ في النظام / System error")
        return

    admin_role = perm_manager.get_admin_role(user.id)
    if not admin_role:
        await query.edit_message_text(
            "❌ ليس لديك صلاحيات إدارية\n"
            "You don't have admin permissions"
        )
        return

    role_name = get_role_display_name(admin_role, 'ar')

    text = (
        "🛠️ **لوحة التحكم**\n\n"
        f"مرحباً {user.first_name}!\n"
        f"**الدور:** {role_name}\n\n"
        "اختر العملية المطلوبة:"
    )

    reply_markup = build_admin_panel(admin_role.value)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard & Analytics
# ══════════════════════════════════════════════════════════════════════════════

@require_permission(Permission.VIEW_ANALYTICS)
@track_bot_interaction("callback")
async def show_admin_dashboard(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show admin dashboard with system statistics."""
    query = update.callback_query
    await query.answer()

    try:
        # Get system statistics
        total_users = db.get_total_users_count()
        total_movies = db.get_movies_count()
        total_series = db.get_series_count()
        active_users_today = db.get_active_users_count(days=1)

        text = (
            "📊 **لوحة المعلومات**\n\n"
            "**إحصائيات النظام:**\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🎬 إجمالي الأفلام: {total_movies}\n"
            f"📺 إجمالي المسلسلات: {total_series}\n"
            f"✅ المستخدمون النشطون اليوم: {active_users_today}\n"
        )

        reply_markup = build_back_button("admin_panel", "🔙 لوحة التحكم")
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error showing dashboard: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ حدث خطأ أثناء تحميل لوحة المعلومات\n"
            "Error loading dashboard"
        )


@require_permission(Permission.VIEW_ANALYTICS)
@track_bot_interaction("callback")
async def show_admin_analytics(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show analytics menu."""
    query = update.callback_query
    await query.answer()

    text = (
        "📈 **الإحصائيات والتحليلات**\n\n"
        "اختر نوع التقرير:"
    )

    reply_markup = build_admin_analytics_menu()
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
# Content Management
# ══════════════════════════════════════════════════════════════════════════════

@require_permission(Permission.VIEW_CONTENT)
@track_bot_interaction("callback")
async def show_admin_content_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show content management menu."""
    query = update.callback_query
    await query.answer()

    text = (
        "🎬 **إدارة المحتوى**\n\n"
        "اختر العملية المطلوبة:"
    )

    reply_markup = build_admin_content_menu()
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@require_permission(Permission.TRIGGER_SYNC)
@track_bot_interaction("callback")
async def admin_trigger_sync(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Trigger content synchronization."""
    query = update.callback_query
    await query.answer()

    update.effective_user

    text = (
        "🔄 **مزامنة المحتوى**\n\n"
        "هل تريد بدء عملية المزامنة؟\n"
        "سيتم مزامنة المحتوى من المجموعة إلى قاعدة البيانات."
    )

    reply_markup = build_confirmation_buttons(
        "admin_sync_confirm",
        "admin_content",
        "✅ بدء المزامنة",
        "❌ إلغاء"
    )

    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@require_permission(Permission.TRIGGER_SYNC)
@track_bot_interaction("callback")
async def admin_sync_confirm(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Confirm and execute sync operation."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    try:
        # Log admin action
        db.log_admin_action(
            admin_id=user.id,
            action="trigger_sync",
            details="Manual sync triggered from admin panel"
        )

        await query.edit_message_text(
            "✅ **تم بدء المزامنة**\n\n"
            "جاري مزامنة المحتوى... سيتم إشعارك عند الانتهاء.",
            parse_mode="Markdown"
        )

        # Trigger sync in background
        # This would call your sync system
        # await trigger_content_sync()

    except Exception as e:
        logger.error(f"Error triggering sync: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ حدث خطأ أثناء بدء المزامنة\n"
            "Error starting sync"
        )


# ══════════════════════════════════════════════════════════════════════════════
# User Management
# ══════════════════════════════════════════════════════════════════════════════

@require_permission(Permission.VIEW_USERS)
@track_bot_interaction("callback")
async def show_admin_user_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu."""
    query = update.callback_query
    await query.answer()

    text = (
        "👥 **إدارة المستخدمين**\n\n"
        "اختر العملية المطلوبة:"
    )

    reply_markup = build_admin_user_menu()
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@require_permission(Permission.VIEW_USERS)
@track_bot_interaction("callback")
async def show_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of users with pagination."""
    query = update.callback_query
    await query.answer()

    # Extract page number
    page = 0
    if query.data and '_' in query.data:
        try:
            page = int(query.data.split('_')[-1])
        except Exception:
            page = 0

    try:
        per_page = 10
        offset = page * per_page
        users = db.get_users_list(limit=per_page, offset=offset)
        total_count = db.get_total_users_count()
        total_pages = (total_count + per_page - 1) // per_page

        text = f"👥 **قائمة المستخدمين** (صفحة {page + 1}/{total_pages})\n\n"

        keyboard = []
        for user in users:
            user_id = user.get('user_id')
            username = user.get('username', 'No username')
            first_name = user.get('first_name', 'Unknown')

            button_text = f"{first_name} (@{username})" if username != 'No username' else first_name
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"admin_user_view_{user_id}")])

        # Pagination
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "⬅️ السابق",
                    callback_data=f"admin_users_list_{page-1}"))
        nav_row.append(
            InlineKeyboardButton(
                f"📄 {page+1}/{total_pages}",
                callback_data="page_info"))
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "التالي ➡️",
                    callback_data=f"admin_users_list_{page+1}"))

        keyboard.append(nav_row)
        keyboard.append([InlineKeyboardButton(
            "🔙 إدارة المستخدمين", callback_data="admin_users")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error showing users list: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ حدث خطأ أثناء تحميل قائمة المستخدمين\n"
            "Error loading users list"
        )


@require_permission(Permission.VIEW_USER_DETAILS)
@track_bot_interaction("callback")
async def show_user_details(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show detailed information about a specific user."""
    query = update.callback_query
    await query.answer()

    # Extract user ID
    try:
        user_id = int(query.data.split('_')[-1])
    except Exception:
        await query.edit_message_text("❌ خطأ في معرف المستخدم / Invalid user ID")
        return

    try:
        user = db.get_user(user_id)

        if not user:
            await query.edit_message_text("❌ المستخدم غير موجود / User not found")
            return

        # Get user statistics
        watch_count = db.get_user_watch_count(user_id)
        favorites_count = db.get_user_favorites_count(user_id)

        text = (
            "👤 **تفاصيل المستخدم**\n\n"
            f"**المعرف:** `{user_id}`\n"
            f"**الاسم:** {user.get('first_name', 'Unknown')}\n"
            f"**اسم المستخدم:** @{user.get('username', 'None')}\n"
            f"**الحالة:** {'👑 بريميوم' if user.get('is_premium') else '⭐ عادي'}\n"
            f"**محظور:** {'✅ نعم' if user.get('is_blocked') else '❌ لا'}\n"
            f"**عدد المشاهدات:** {watch_count}\n"
            f"**المفضلة:** {favorites_count}\n")

        # Build action buttons
        keyboard = []

        perm_manager = context.bot_data.get('permission_manager')
        if perm_manager:
            if perm_manager.has_permission(
                    update.effective_user.id,
                    Permission.BLOCK_USERS):
                if user.get('is_blocked'):
                    keyboard.append([InlineKeyboardButton(
                        "✅ إلغاء الحظر", callback_data=f"admin_user_unblock_{user_id}")])
                else:
                    keyboard.append([InlineKeyboardButton(
                        "🚫 حظر المستخدم", callback_data=f"admin_user_block_{user_id}")])

            if perm_manager.has_permission(
                    update.effective_user.id,
                    Permission.UPGRADE_USERS):
                if not user.get('is_premium'):
                    keyboard.append([InlineKeyboardButton(
                        "👑 ترقية للبريميوم", callback_data=f"admin_user_upgrade_{user_id}")])

        keyboard.append([InlineKeyboardButton(
            "🔙 قائمة المستخدمين", callback_data="admin_users_list_0")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error showing user details: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ حدث خطأ أثناء تحميل تفاصيل المستخدم\n"
            "Error loading user details"
        )


@require_permission(Permission.BLOCK_USERS)
@track_bot_interaction("callback")
async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block a user."""
    query = update.callback_query
    await query.answer()

    try:
        user_id = int(query.data.split('_')[-1])
    except Exception:
        await query.edit_message_text("❌ خطأ في معرف المستخدم / Invalid user ID")
        return

    try:
        db.block_user(user_id)

        # Log admin action
        db.log_admin_action(
            admin_id=update.effective_user.id,
            action="block_user",
            details=f"Blocked user {user_id}"
        )

        await query.answer("✅ تم حظر المستخدم / User blocked", show_alert=True)

        # Refresh user details
        context.user_data['refresh_user'] = user_id
        await show_user_details(update, context)

    except Exception as e:
        logger.error(f"Error blocking user: {e}", exc_info=True)
        await query.answer("❌ فشل حظر المستخدم / Failed to block user", show_alert=True)


@require_permission(Permission.UNBLOCK_USERS)
@track_bot_interaction("callback")
async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unblock a user."""
    query = update.callback_query
    await query.answer()

    try:
        user_id = int(query.data.split('_')[-1])
    except Exception:
        await query.edit_message_text("❌ خطأ في معرف المستخدم / Invalid user ID")
        return

    try:
        db.unblock_user(user_id)

        # Log admin action
        db.log_admin_action(
            admin_id=update.effective_user.id,
            action="unblock_user",
            details=f"Unblocked user {user_id}"
        )

        await query.answer("✅ تم إلغاء حظر المستخدم / User unblocked", show_alert=True)

        # Refresh user details
        context.user_data['refresh_user'] = user_id
        await show_user_details(update, context)

    except Exception as e:
        logger.error(f"Error unblocking user: {e}", exc_info=True)
        await query.answer("❌ فشل إلغاء الحظر / Failed to unblock user", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
# Admin Management (Super Admin Only)
# ══════════════════════════════════════════════════════════════════════════════

@require_permission(Permission.MANAGE_ADMINS)
@track_bot_interaction("callback")
async def show_admin_management(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Show admin management interface."""
    query = update.callback_query
    await query.answer()

    perm_manager = context.bot_data.get('permission_manager')
    if not perm_manager:
        await query.edit_message_text("❌ خطأ في النظام / System error")
        return

    try:
        admins = perm_manager.get_all_admins(include_inactive=False)

        text = f"👑 **إدارة المشرفين**\n\n**عدد المشرفين:** {len(admins)}\n\n"

        keyboard = []
        for admin in admins:
            role = admin.get('role', 'unknown')
            username = admin.get('username', 'No username')
            role_emoji = "👑" if role == "super_admin" else "🛡️" if role == "admin" else "👮"

            button_text = f"{role_emoji} {username}"
            keyboard.append([InlineKeyboardButton(
                button_text, callback_data=f"admin_view_admin_{admin['user_id']}")])

        keyboard.append([InlineKeyboardButton(
            "➕ إضافة مشرف", callback_data="admin_add_admin")])
        keyboard.append([InlineKeyboardButton(
            "🔙 لوحة التحكم", callback_data="admin_panel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error showing admin management: {e}", exc_info=True)
        await query.edit_message_text(
            "❌ حدث خطأ أثناء تحميل إدارة المشرفين\n"
            "Error loading admin management"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Callback Router for Admin Commands
# ══════════════════════════════════════════════════════════════════════════════

async def handle_admin_callback(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Route admin callback queries to appropriate handlers."""
    query = update.callback_query
    data = query.data

    # Admin panel
    if data == "admin_panel":
        await show_admin_panel_callback(update, context)

    # Dashboard
    elif data == "admin_dashboard":
        await show_admin_dashboard(update, context)

    # Content management
    elif data == "admin_content":
        await show_admin_content_menu(update, context)
    elif data == "admin_sync_telegram_db":
        await admin_trigger_sync(update, context)
    elif data == "admin_sync_confirm":
        await admin_sync_confirm(update, context)

    # User management
    elif data == "admin_users":
        await show_admin_user_menu(update, context)
    elif data.startswith("admin_users_list"):
        await show_users_list(update, context)
    elif data.startswith("admin_user_view"):
        await show_user_details(update, context)
    elif data.startswith("admin_user_block"):
        await block_user(update, context)
    elif data.startswith("admin_user_unblock"):
        await unblock_user(update, context)

    # Analytics
    elif data == "admin_analytics":
        await show_admin_analytics(update, context)

    # Admin management
    elif data == "admin_manage_admins":
        await show_admin_management(update, context)

    else:
        await query.answer("قريباً / Coming soon!", show_alert=True)


# Made with Bob


# ══════════════════════════════════════════════════════════════════════════════
# Callback Handlers Registration - Required by main.py
# ══════════════════════════════════════════════════════════════════════════════

def get_callback_handlers() -> List[CallbackQueryHandler]:
    """Return list of callback query handlers for registration."""
    return [
        CallbackQueryHandler(handle_callback_query),
        CallbackQueryHandler(handle_admin_callback, pattern="^admin_"),
    ]


async def handle_callback_query(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers."""
    query = update.callback_query
    data = query.data

    # Subscription check
    if data == "check_subscription":
        await handle_subscription_check(update, context)
        return

    # Main menu
    if data == "main_menu":
        await show_main_menu_callback(update, context)

    # Browse movies
    elif data.startswith("browse_movies"):
        await browse_movies(update, context)

    # Browse series
    elif data.startswith("browse_series"):
        await browse_series(update, context)

    # Movie details
    elif data.startswith("movie_") and not data.startswith("movie_watch"):
        await show_movie_details(update, context)

    # Series details
    elif data.startswith("series_"):
        await show_series_details(update, context)

    # Season episodes
    elif data.startswith("season_"):
        await show_season_episodes(update, context)

    # Admin callbacks
    elif data.startswith("admin_"):
        await handle_admin_callback(update, context)

    else:
        await query.answer("قريباً / Coming soon!", show_alert=True)


# Made with Bob - Merged and Fixed Version
