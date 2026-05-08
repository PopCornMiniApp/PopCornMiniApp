"""
Bot command handlers for PopCorn main bot.
Handles /start, /app, and admin commands.
"""
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from app.config import ADMIN_ID, HF_SPACE_NAME

MINI_APP_URL = f"https://toolki-backend-popcorn.hf.space"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🍿 فتح PopCorn",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )],
        [InlineKeyboardButton("📢 القناة العامة", url="https://t.me/c/3944402689/1")]
    ])
    await update.effective_message.reply_text(
        f"مرحباً {user.first_name}! 👋\n\n"
        "🍿 *PopCorn* - تطبيق الأفلام والمسلسلات\n\n"
        "• أفلام ومسلسلات مختارة بعناية\n"
        "• جودة عالية مع بث مباشر\n"
        "• معلومات تفصيلية لكل عمل\n"
        "• محرك بحث متقدم\n\n"
        "اضغط على الزر أدناه لفتح التطبيق 👇",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def cmd_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "🍿 فتح PopCorn",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )]
    ])
    await update.effective_message.reply_text(
        "🍿 افتح تطبيق PopCorn للأفلام والمسلسلات",
        reply_markup=keyboard,
    )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.effective_message.reply_text(
        "👑 *لوحة الإدارة*\n\n"
        "الأوامر المتاحة:\n"
        "/stats - إحصائيات قاعدة البيانات\n"
        "/sync_db - مزامنة DB مع HuggingFace\n"
        "/register [topic_name] [topic_id] - تسجيل موضوع يدوياً\n\n"
        "📋 صيغة الموضوعات:\n"
        "فيلم: #Name #movies #mid00001 #TMDB_ID\n"
        "مسلسل: #Name #series #s1 #sid00001 #TMDB_ID",
        parse_mode="Markdown"
    )
