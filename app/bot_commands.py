import logging, sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes, CallbackQueryHandler
from app.config import ADMIN_ID
from app import database as db

logger = logging.getLogger(__name__)
MINI_APP_URL = "https://toolkit-backend-popcorn.hf.space"


def _main_kbd():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🍿 فتح PopCorn", web_app=WebAppInfo(url=MINI_APP_URL))],
        [InlineKeyboardButton("🎬 أفلام", web_app=WebAppInfo(url=f"{MINI_APP_URL}/#/movies")),
         InlineKeyboardButton("📺 مسلسلات", web_app=WebAppInfo(url=f"{MINI_APP_URL}/#/series"))],
        [InlineKeyboardButton("🔍 بحث", web_app=WebAppInfo(url=f"{MINI_APP_URL}/#/search"))],
    ])


def _quick_kbd():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🍿 فتح التطبيق", web_app=WebAppInfo(url=MINI_APP_URL))]])


def _admin_kbd():
    """Admin control panel keyboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 مزامنة المجموعة الآن", callback_data="admin_fullscan")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats_btn")],
        [InlineKeyboardButton("🆕 آخر الإضافات", callback_data="admin_new_btn")],
        [InlineKeyboardButton("🍿 فتح التطبيق", web_app=WebAppInfo(url=MINI_APP_URL))],
    ])


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first = user.first_name if user else "مستخدم"
    await update.effective_message.reply_text(
        f"أهلاً وسهلاً {first}! 🎉\n\n"
        "🍿 *PopCorn* — تطبيق الأفلام والمسلسلات\n\n"
        "✨ *ما يميّزنا:*\n"
        "• 🎬 أفلام ومسلسلات مختارة بعناية\n"
        "• 📡 بث مباشر بجودة عالية بدون تحميل\n"
        "• 🔍 بحث بالعربية والإنجليزية\n"
        "• 🌟 معلومات تفصيلية لكل عمل\n"
        "• 🎭 تصفية حسب التصنيف\n\n"
        "اضغط على الزر أدناه لفتح التطبيق 👇",
        parse_mode="Markdown", reply_markup=_main_kbd(),
    )


async def cmd_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "🍿 *PopCorn* — اضغط لفتح التطبيق:", parse_mode="Markdown", reply_markup=_main_kbd(),
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "📖 *دليل استخدام PopCorn*\n\n"
        "🔸 /start — الشاشة الرئيسية\n"
        "🔸 /app — فتح التطبيق مباشرة\n"
        "🔸 /new — آخر الإضافات\n"
        "🔸 /top — الأعلى تقييماً\n"
        "🔸 /stats — إحصائيات المكتبة\n"
        "🔸 /help — هذه القائمة\n\n"
        "💡 ابحث عن أي عمل بالعربية أو الإنجليزية داخل التطبيق",
        parse_mode="Markdown", reply_markup=_quick_kbd(),
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = db.get_stats()
    movies = stats.get("latest_movies", [])[:5]
    series = stats.get("latest_series", [])[:3]
    lines = ["🆕 *آخر الإضافات:*\n"]
    if movies:
        lines.append("🎬 *أفلام:*")
        for m in movies:
            title = m.get("title_ar") or m.get("title", "")
            lines.append(f"  {'✅' if m.get('file_id') else '⏳'} {title}")
    if series:
        lines.append("\n📺 *مسلسلات:*")
        for s in series:
            lines.append(f"  📺 {s.get('title_ar') or s.get('title', '')}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=_quick_kbd())


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.config import DB_PATH
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        top_movies = conn.execute(
            "SELECT title,title_ar,rating FROM movies WHERE file_id IS NOT NULL ORDER BY rating DESC LIMIT 5"
        ).fetchall()
        top_series = conn.execute(
            "SELECT title,title_ar,rating FROM series ORDER BY rating DESC LIMIT 3"
        ).fetchall()
    finally:
        conn.close()
    lines = ["⭐ *الأعلى تقييماً:*\n", "🎬 *أفلام:*"]
    for m in top_movies:
        lines.append(f"  ⭐ {m['rating']} — {m['title_ar'] or m['title']}")
    lines.append("\n📺 *مسلسلات:*")
    for s in top_series:
        lines.append(f"  ⭐ {s['rating']} — {s['title_ar'] or s['title']}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=_quick_kbd())


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = db.get_stats()
    is_admin = update.effective_user.id == ADMIN_ID
    text = (f"📊 *إحصائيات PopCorn*\n\n"
            f"🎬 أفلام: *{s['movies_count']}*\n"
            f"📺 مسلسلات: *{s['series_count']}*\n"
            f"🎞 حلقات: *{s['episodes_count']}*")
    if is_admin:
        text += f"\n\n👑 *لوحة الإدارة:* /admin"
    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=_quick_kbd())


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    s = db.get_stats()
    await update.effective_message.reply_text(
        f"👑 *لوحة إدارة PopCorn*\n\n"
        f"📊 الحالة الراهنة:\n"
        f"• 🎬 أفلام: *{s['movies_count']}*\n"
        f"• 📺 مسلسلات: *{s['series_count']}*\n"
        f"• 🎞 حلقات: *{s['episodes_count']}*\n\n"
        f"اضغط *🔄 مزامنة المجموعة الآن* لفحص المجموعة الخاصة\n"
        f"وإضافة أي محتوى جديد تلقائياً:",
        parse_mode="Markdown",
        reply_markup=_admin_kbd(),
    )


async def callback_admin_fullscan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline button handler: trigger full scan of private group."""
    query = update.callback_query
    if not query or update.effective_user.id != ADMIN_ID:
        if query:
            await query.answer("غير مصرح لك!", show_alert=True)
        return

    await query.answer("⏳ جارٍ بدء المسح...")
    await query.edit_message_text(
        "🔍 *جارٍ مسح المجموعة الخاصة...*\n\nيرجى الانتظار، قد يستغرق ذلك بضع دقائق.",
        parse_mode="Markdown",
    )
    try:
        from app.stream import _pyro_clients
        from app.scanner import run_full_scan
        if not _pyro_clients:
            await query.edit_message_text("❌ لا يوجد عميل Pyrogram متاح. تأكد من تشغيل الخدمة.")
            return
        results = await run_full_scan(_pyro_clients[0])
        s = db.get_stats()
        await query.edit_message_text(
            f"✅ *اكتمل المسح!*\n\n"
            f"📋 مواضيع مفحوصة: *{results['topics_scanned']}*\n"
            f"➕ محتوى جديد مسجّل: *{results['registered']}*\n"
            f"🎬 ملفات مرفقة: *{results['files_attached']}*\n"
            f"⚠️ أخطاء: *{results['errors']}*\n\n"
            f"📊 إجمالي المكتبة:\n"
            f"• أفلام: *{s['movies_count']}* | مسلسلات: *{s['series_count']}* | حلقات: *{s['episodes_count']}*",
            parse_mode="Markdown",
            reply_markup=_admin_kbd(),
        )
    except Exception as e:
        logger.error(f"callback_admin_fullscan error: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ حدث خطأ أثناء المسح:\n`{str(e)[:200]}`",
            parse_mode="Markdown",
            reply_markup=_admin_kbd(),
        )


async def callback_admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or update.effective_user.id != ADMIN_ID:
        if query: await query.answer("غير مصرح!", show_alert=True)
        return
    await query.answer()
    s = db.get_stats()
    await query.edit_message_text(
        f"👑 *لوحة إدارة PopCorn*\n\n"
        f"📊 الحالة الراهنة:\n"
        f"• 🎬 أفلام: *{s['movies_count']}*\n"
        f"• 📺 مسلسلات: *{s['series_count']}*\n"
        f"• 🎞 حلقات: *{s['episodes_count']}*\n\n"
        f"اضغط *🔄 مزامنة المجموعة الآن* لفحص المجموعة الخاصة:",
        parse_mode="Markdown",
        reply_markup=_admin_kbd(),
    )


async def callback_admin_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    await query.answer()
    stats = db.get_stats()
    movies = stats.get("latest_movies", [])[:5]
    lines = ["🆕 *آخر الإضافات:*\n"]
    if movies:
        for m in movies:
            title = m.get("title_ar") or m.get("title", "")
            lines.append(f"  {'✅' if m.get('file_id') else '⏳'} {title}")
    await query.edit_message_text(
        "\n".join(lines), parse_mode="Markdown", reply_markup=_admin_kbd()
    )


def get_callback_handlers():
    """Return list of CallbackQueryHandlers to register in main.py."""
    return [
        CallbackQueryHandler(callback_admin_fullscan, pattern="^admin_fullscan$"),
        CallbackQueryHandler(callback_admin_stats,    pattern="^admin_stats_btn$"),
        CallbackQueryHandler(callback_admin_new,      pattern="^admin_new_btn$"),
    ]
