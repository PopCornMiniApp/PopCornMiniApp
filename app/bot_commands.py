import logging, sqlite3
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
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
    movies = stats.get("latest_movies",[])[:5]
    series = stats.get("latest_series",[])[:3]
    lines = ["🆕 *آخر الإضافات:*\n"]
    if movies:
        lines.append("🎬 *أفلام:*")
        for m in movies:
            title = m.get("title_ar") or m.get("title","")
            lines.append(f"  {'✅' if m.get('file_id') else '⏳'} {title}")
    if series:
        lines.append("\n📺 *مسلسلات:*")
        for s in series:
            lines.append(f"  📺 {s.get('title_ar') or s.get('title','')}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=_quick_kbd())

async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.config import DB_PATH
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    try:
        top_movies = conn.execute("SELECT title,title_ar,rating FROM movies WHERE file_id IS NOT NULL ORDER BY rating DESC LIMIT 5").fetchall()
        top_series = conn.execute("SELECT title,title_ar,rating FROM series ORDER BY rating DESC LIMIT 3").fetchall()
    finally: conn.close()
    lines = ["⭐ *الأعلى تقييماً:*\n","🎬 *أفلام:*"]
    for m in top_movies: lines.append(f"  ⭐ {m['rating']} — {m['title_ar'] or m['title']}")
    lines.append("\n📺 *مسلسلات:*")
    for s in top_series: lines.append(f"  ⭐ {s['rating']} — {s['title_ar'] or s['title']}")
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
    if update.effective_user.id != ADMIN_ID: return
    await update.effective_message.reply_text(
        "👑 *لوحة الإدارة*\n\n"
        "/stats — إحصائيات\n/sync\\_db — مزامنة DB\n/new — آخر الإضافات\n/top — الأعلى تقييماً\n\n"
        "📋 *صيغة التوبيكات:*\n"
        "```\nفيلم:   #Name #movies #mid00001 #TMDB_ID\nمسلسل: #Name #series #s1 #sid00001 #TMDB_ID```\n\n"
        "🎬 *صيغة caption الفيديو:*\n"
        "```\nفيلم:  #Name #Movie\nحلقة: #Name #S1 #E1```",
        parse_mode="Markdown",
    )
