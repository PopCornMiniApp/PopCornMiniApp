"""
PopCorn Subscription Checker Module
Enhanced subscription verification with caching, retry logic, and statistics tracking.
"""
import logging
import time
import asyncio
from typing import Optional, Tuple, Dict, Any
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError, RetryAfter, TimedOut

from app.config import PUBLIC_CHANNEL_ID, SUBSCRIPTION_CACHE_TTL

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════════════

CHANNEL_URL = "https://t.me/PopCornAppChannel"
CHANNEL_ID = PUBLIC_CHANNEL_ID  # -1003944402689
CACHE_TTL = SUBSCRIPTION_CACHE_TTL  # From config, default 5 minutes

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # Initial delay in seconds
RETRY_BACKOFF = 2  # Exponential backoff multiplier

# ══════════════════════════════════════════════════════════════════════════════
# In-Memory Cache with Enhanced Tracking
# ══════════════════════════════════════════════════════════════════════════════

_subscription_cache = {}  # {user_id: (is_subscribed, timestamp)}
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "expirations": 0,
    "api_calls": 0,
    "api_errors": 0,
    "last_reset": time.time()
}


def _get_cached_status(user_id: int) -> Optional[bool]:
    """Get cached subscription status if not expired."""
    if user_id in _subscription_cache:
        is_subscribed, timestamp = _subscription_cache[user_id]
        if time.time() - timestamp < CACHE_TTL:
            _cache_stats["hits"] += 1
            logger.debug(f"✅ Cache hit for user {user_id}: {is_subscribed}")
            return is_subscribed
        else:
            # Cache expired
            del _subscription_cache[user_id]
            _cache_stats["expirations"] += 1
            logger.debug(f"⏰ Cache expired for user {user_id}")

    _cache_stats["misses"] += 1
    return None


def _set_cached_status(user_id: int, is_subscribed: bool):
    """Cache subscription status with timestamp."""
    _subscription_cache[user_id] = (is_subscribed, time.time())
    logger.debug(f"💾 Cached status for user {user_id}: {is_subscribed}")


def clear_cache(user_id: Optional[int] = None):
    """Clear subscription cache for a user or all users."""
    if user_id:
        if user_id in _subscription_cache:
            del _subscription_cache[user_id]
            logger.info(f"🗑️ Cleared cache for user {user_id}")
    else:
        count = len(_subscription_cache)
        _subscription_cache.clear()
        logger.info(f"🗑️ Cleared all subscription cache ({count} entries)")


def reset_cache_stats():
    """Reset cache statistics."""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "expirations": 0,
        "api_calls": 0,
        "api_errors": 0,
        "last_reset": time.time()
    }
    logger.info("📊 Cache statistics reset")


# ══════════════════════════════════════════════════════════════════════════════
# Subscription Verification
# ══════════════════════════════════════════════════════════════════════════════

async def check_subscription(user_id: int, bot) -> Tuple[bool, str]:
    """
    Check if user is subscribed to the mandatory channel with retry logic.

    Args:
        user_id: Telegram user ID
        bot: Telegram bot instance

    Returns:
        Tuple of (is_subscribed, status_message)
    """
    # Check cache first
    cached_status = _get_cached_status(user_id)
    if cached_status is not None:
        return cached_status, "cached"

    # Retry logic with exponential backoff
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            _cache_stats["api_calls"] += 1

            # Check channel membership using getChatMember
            member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)

            # Valid subscription statuses
            valid_statuses = ['creator', 'administrator', 'member']
            is_subscribed = member.status in valid_statuses

            # Cache the result
            _set_cached_status(user_id, is_subscribed)

            logger.info(
                f"✅ User {user_id} subscription check: {member.status} -> {is_subscribed}")
            return is_subscribed, member.status

        except RetryAfter as e:
            # Telegram rate limit - wait and retry
            wait_time = e.retry_after
            logger.warning(
                f"⏳ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
            await asyncio.sleep(wait_time)
            last_error = e
            continue

        except TimedOut as e:
            # Timeout - retry with backoff
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                logger.warning(
                    f"⏱️ Timeout, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(wait_time)
                last_error = e
                continue
            else:
                logger.error(f"❌ Max retries reached for user {user_id}: {e}")
                _cache_stats["api_errors"] += 1
                last_error = e
                break

        except TelegramError as e:
            # Handle specific errors
            error_msg = str(e).lower()

            if "user not found" in error_msg or "chat not found" in error_msg:
                logger.warning(f"⚠️ User {user_id} or channel not found: {e}")
                _cache_stats["api_errors"] += 1
                return False, "not_found"

            elif "forbidden" in error_msg:
                logger.warning(
                    f"⚠️ Bot doesn't have permission to check user {user_id}: {e}")
                # Fail-open: assume subscribed to avoid blocking legitimate
                # users
                return True, "permission_error"

            else:
                # Other Telegram errors - retry if attempts remain
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                    logger.warning(
                        f"⚠️ Telegram error, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                    last_error = e
                    continue
                else:
                    logger.error(
                        f"❌ Max retries reached for user {user_id}: {e}")
                    _cache_stats["api_errors"] += 1
                    # Fail-open for errors after retries
                    return True, "error"

        except Exception as e:
            logger.error(
                f"❌ Unexpected error checking subscription for user {user_id}: {e}",
                exc_info=True)
            _cache_stats["api_errors"] += 1
            # Fail-open for unexpected errors
            return True, "unexpected_error"

    # If we exhausted all retries
    logger.error(
        f"❌ All retry attempts failed for user {user_id}: {last_error}")
    _cache_stats["api_errors"] += 1
    # Fail-open to avoid blocking users due to temporary issues
    return True, "retry_exhausted"


async def send_subscription_prompt(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Send subscription prompt with channel link and check button."""
    user = update.effective_user

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("✅ Check Subscription", callback_data="check_subscription")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message_text = (
        "🍿 **Welcome to PopCorn!**\n\n"
        f"Hello {user.first_name}! 👋\n\n"
        "To use PopCorn bot and mini-app, you must join our official channel:\n\n"
        "📢 **PopCorn Channel**\n"
        f"🔗 {CHANNEL_URL}\n\n"
        "**Why join?**\n"
        "• Get latest movie & series updates\n"
        "• Exclusive content announcements\n"
        "• Important bot notifications\n\n"
        "👇 Click the button below to join, then check your subscription!")

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Decorator for Bot Commands
# ══════════════════════════════════════════════════════════════════════════════

def require_subscription(func):
    """
    Decorator to check subscription before executing command.
    Use this on all bot command handlers.
    """
    @wraps(func)
    async def wrapper(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            *args,
            **kwargs):
        user = update.effective_user

        # Check subscription
        is_subscribed, status = await check_subscription(user.id, context.bot)

        if not is_subscribed:
            logger.info(
                f"User {user.id} ({user.username}) not subscribed, blocking access")
            await send_subscription_prompt(update, context)
            return

        # User is subscribed, proceed with command
        logger.debug(f"User {user.id} is subscribed, allowing access")
        return await func(update, context, *args, **kwargs)

    return wrapper


# ══════════════════════════════════════════════════════════════════════════════
# Callback Handler for Subscription Check
# ══════════════════════════════════════════════════════════════════════════════

async def handle_subscription_check(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE):
    """Handle the 'Check Subscription' button callback."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    # Clear cache to force fresh check
    clear_cache(user.id)

    # Check subscription
    is_subscribed, status = await check_subscription(user.id, context.bot)

    if is_subscribed:
        # User is now subscribed
        success_text = (
            "✅ **Subscription Verified!**\n\n"
            f"Welcome aboard, {user.first_name}! 🎉\n\n"
            "You now have full access to PopCorn.\n\n"
            "Use /start to begin exploring our library! 🍿"
        )

        await query.edit_message_text(success_text, parse_mode="Markdown")

        # Update database subscription status
        from app import database as db
        try:
            db.update_user_subscription(user.id, is_subscribed=True)
        except Exception as e:
            logger.error(f"Error updating subscription status in DB: {e}")

    else:
        # Still not subscribed
        await send_subscription_prompt(update, context)


# ══════════════════════════════════════════════════════════════════════════════
# Utility Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive subscription cache statistics."""
    now = time.time()
    active_entries = sum(
        1 for _,
        (_,
         ts) in _subscription_cache.items() if now -
        ts < CACHE_TTL)

    # Calculate cache hit rate
    total_requests = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = (
        _cache_stats["hits"] /
        total_requests *
        100) if total_requests > 0 else 0

    # Calculate API success rate
    total_api_calls = _cache_stats["api_calls"]
    api_success_rate = (
        (total_api_calls -
         _cache_stats["api_errors"]) /
        total_api_calls *
        100) if total_api_calls > 0 else 0

    uptime = now - _cache_stats["last_reset"]

    return {
        # Cache statistics
        "total_entries": len(_subscription_cache),
        "active_entries": active_entries,
        "expired_entries": len(_subscription_cache) - active_entries,
        "cache_ttl_seconds": CACHE_TTL,

        # Performance metrics
        "cache_hits": _cache_stats["hits"],
        "cache_misses": _cache_stats["misses"],
        "cache_expirations": _cache_stats["expirations"],
        "hit_rate_percent": round(hit_rate, 2),

        # API statistics
        "api_calls": _cache_stats["api_calls"],
        "api_errors": _cache_stats["api_errors"],
        "api_success_rate_percent": round(api_success_rate, 2),

        # Configuration
        "channel_id": CHANNEL_ID,
        "channel_url": CHANNEL_URL,
        "max_retries": MAX_RETRIES,
        "retry_delay_seconds": RETRY_DELAY,

        # Uptime
        "uptime_seconds": round(uptime, 2),
        "last_reset": datetime.fromtimestamp(_cache_stats["last_reset"]).isoformat()
    }


async def verify_channel_access(bot) -> bool:
    """
    Verify that the bot has access to check channel membership.
    Should be called during bot initialization.
    """
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        logger.info(f"✅ Bot has access to channel: {chat.title}")
        return True
    except TelegramError as e:
        logger.error(f"❌ Bot cannot access channel {CHANNEL_ID}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error verifying channel access: {e}")
        return False

# Made with Bob
