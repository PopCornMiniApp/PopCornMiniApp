"""
PopCorn Telegram Bot - Fixed Version with Compatible Database Calls
Restored working bot with Arabic UI and proper database integration.
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from app.config import MAIN_BOT_TOKEN, SUBSCRIPTION_REQUIRED
from app import database as db
from app.subscription_checker import (
    check_subscription,
    send_subscription_prompt,
    handle_subscription_check
)

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Conversation States
# ══════════════════════════════════════════════════════════════════════════════

# Registration states
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
# User Registration System
# ══════════════════════════════════════════════════════════════════════════════


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with registration flow."""
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


async def registration_name(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Handle user name input during registration."""
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
# Callback Query Router
# ══════════════════════════════════════════════════════════════════════════════

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

    else:
        await query.answer("قريباً / Coming soon!", show_alert=True)


# ══════════════════════════════════════════════════════════════════════════════
# Bot Initialization
# ══════════════════════════════════════════════════════════════════════════════

def create_bot_application() -> Application:
    """Create and configure the bot application."""

    # Create application
    application = Application.builder().token(MAIN_BOT_TOKEN).build()

    # Registration conversation handler
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            REGISTRATION_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, registration_name)],
            REGISTRATION_LANGUAGE: [CallbackQueryHandler(registration_language, pattern="^lang_")]
        },
        fallbacks=[CommandHandler("cancel", cancel_registration)]
    )

    # Add handlers
    application.add_handler(registration_handler)
    application.add_handler(CommandHandler("menu", show_main_menu))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    logger.info("✅ Bot application created and configured")

    return application


# ══════════════════════════════════════════════════════════════════════════════
# Main Function
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    """Main function to run the bot."""
    logger.info("🤖 Starting PopCorn Bot...")

    # Initialize database
    db.init_db()

    # Create and run bot
    application = create_bot_application()

    logger.info("✅ Bot is running!")
    await application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# Made with Bob - Fixed Version
