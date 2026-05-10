import os
from dotenv import load_dotenv

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# HuggingFace Configuration
# ══════════════════════════════════════════════════════════════════════════════

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_DATASET_NAME = os.getenv("HF_DATASET_NAME", "ToolKit-backend/PopCornDB")
HF_SPACE_NAME = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")
HF_DATASET_URL = f"https://huggingface.co/datasets/{HF_DATASET_NAME}"

# Sync settings
HF_SYNC_ENABLED = os.getenv("HF_SYNC_ENABLED", "true").lower() == "true"
HF_SYNC_INTERVAL = int(os.getenv("HF_SYNC_INTERVAL", "600"))  # 10 minutes
HF_AUTO_BACKUP = os.getenv("HF_AUTO_BACKUP", "true").lower() == "true"
HF_BACKUP_INTERVAL = int(os.getenv("HF_BACKUP_INTERVAL", "3600"))  # 1 hour
HF_COMPRESSION_ENABLED = os.getenv(
    "HF_COMPRESSION_ENABLED",
    "true").lower() == "true"
HF_VERSIONING_ENABLED = os.getenv(
    "HF_VERSIONING_ENABLED",
    "true").lower() == "true"

# Backup retention policy
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))
BACKUP_KEEP_COUNT = int(os.getenv("BACKUP_KEEP_COUNT", "10"))

# ══════════════════════════════════════════════════════════════════════════════
# Telegram Bot Configuration
# ══════════════════════════════════════════════════════════════════════════════

MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "")
STREAM_BOT_1 = os.getenv("STREAM_BOT_1", "")
STREAM_BOT_2 = os.getenv("STREAM_BOT_2", "")

# ══════════════════════════════════════════════════════════════════════════════
# TMDB Configuration
# ══════════════════════════════════════════════════════════════════════════════

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

# ══════════════════════════════════════════════════════════════════════════════
# Admin Configuration
# ══════════════════════════════════════════════════════════════════════════════

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@MLk_JAMAL")

# Admin Role System
SUPER_ADMIN_IDS = [ADMIN_ID]  # List of super admin user IDs
ENABLE_ADMIN_SYSTEM = os.getenv(
    "ENABLE_ADMIN_SYSTEM",
    "true").lower() == "true"
ADMIN_SESSION_TIMEOUT = int(
    os.getenv(
        "ADMIN_SESSION_TIMEOUT",
        "3600"))  # 1 hour
ADMIN_ACTIVITY_LOG_ENABLED = os.getenv(
    "ADMIN_ACTIVITY_LOG_ENABLED",
    "true").lower() == "true"

# ══════════════════════════════════════════════════════════════════════════════
# Telegram Groups/Channels
# ══════════════════════════════════════════════════════════════════════════════

# Support both PRIVATE_GROUP_ID and PRIVATE_GROUPE_1_ID (historical typo)
_raw_group = os.getenv("PRIVATE_GROUP_ID") or os.getenv(
    "PRIVATE_GROUPE_1_ID", "0")
PRIVATE_GROUP_ID = int(_raw_group or 0)

PUBLIC_CHANNEL_ID = int(os.getenv("PUBLIC_CHANNEL_ID", "-1003944402689"))

# Mandatory Subscription Channel
SUBSCRIPTION_CHANNEL_ID = PUBLIC_CHANNEL_ID
SUBSCRIPTION_CHANNEL_URL = os.getenv(
    "SUBSCRIPTION_CHANNEL_URL",
    "https://t.me/PopCornAppChannel")
SUBSCRIPTION_REQUIRED = os.getenv(
    "SUBSCRIPTION_REQUIRED",
    "true").lower() == "true"
SUBSCRIPTION_CACHE_TTL = int(
    os.getenv(
        "SUBSCRIPTION_CACHE_TTL",
        "300"))  # 5 minutes

# ══════════════════════════════════════════════════════════════════════════════
# Pyrogram Sessions
# ══════════════════════════════════════════════════════════════════════════════

SESSION_1_API_ID = int(os.getenv("SESSION_1_API_ID", "0"))
SESSION_1_API_HASH = os.getenv("SESSION_1_API_HASH", "")
SESSION_2_API_ID = int(os.getenv("SESSION_2_API_ID", "0"))
SESSION_2_API_HASH = os.getenv("SESSION_2_API_HASH", "")

# ══════════════════════════════════════════════════════════════════════════════
# Database Configuration
# ══════════════════════════════════════════════════════════════════════════════

DB_PATH = "/tmp/popcorn.db"
DATASET_DB_FILE = "popcorn.db"

# ══════════════════════════════════════════════════════════════════════════════
# User Tracking Configuration
# ══════════════════════════════════════════════════════════════════════════════

TRACKING_ENABLED = os.getenv("TRACKING_ENABLED", "true").lower() == "true"
TRACK_IP_ADDRESSES = os.getenv("TRACK_IP_ADDRESSES", "true").lower() == "true"
TRACK_USER_AGENTS = os.getenv("TRACK_USER_AGENTS", "true").lower() == "true"
TRACK_DEVICE_INFO = os.getenv("TRACK_DEVICE_INFO", "true").lower() == "true"

# Session management
SESSION_TIMEOUT_MINUTES = int(
    os.getenv(
        "SESSION_TIMEOUT_MINUTES",
        "1440"))  # 24 hours
SESSION_CLEANUP_INTERVAL = int(
    os.getenv(
        "SESSION_CLEANUP_INTERVAL",
        "3600"))  # 1 hour

# ══════════════════════════════════════════════════════════════════════════════
# Analytics Configuration
# ══════════════════════════════════════════════════════════════════════════════

ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"
ANALYTICS_RETENTION_DAYS = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))
CALCULATE_STATISTICS_INTERVAL = int(
    os.getenv(
        "CALCULATE_STATISTICS_INTERVAL",
        "3600"))  # 1 hour

# ══════════════════════════════════════════════════════════════════════════════
# Security Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Encryption
ENCRYPTION_ENABLED = os.getenv("ENCRYPTION_ENABLED", "false").lower() == "true"
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

# GDPR Compliance
GDPR_ENABLED = os.getenv("GDPR_ENABLED", "true").lower() == "true"
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "365"))
ALLOW_DATA_EXPORT = os.getenv("ALLOW_DATA_EXPORT", "true").lower() == "true"
ALLOW_DATA_DELETION = os.getenv(
    "ALLOW_DATA_DELETION",
    "true").lower() == "true"

# Rate limiting
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# ══════════════════════════════════════════════════════════════════════════════
# Application Configuration
# ══════════════════════════════════════════════════════════════════════════════

APP_NAME = "PopCorn"
APP_VERSION = "4.3.0"
APP_DESCRIPTION = "Advanced Movie & Series Streaming Platform"
API_PREFIX = "/api"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", "/tmp/popcorn.log")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))

# Performance
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 minutes
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# ══════════════════════════════════════════════════════════════════════════════
# Mirror System Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Mirror redundancy (number of copies for each file)
MIRROR_REDUNDANCY = int(os.getenv("MIRROR_REDUNDANCY", "3"))

# Mirror verification interval (seconds)
MIRROR_VERIFICATION_INTERVAL = int(
    os.getenv(
        "MIRROR_VERIFICATION_INTERVAL",
        "3600"))  # 1 hour

# Mirror repair enabled
MIRROR_REPAIR_ENABLED = os.getenv(
    "MIRROR_REPAIR_ENABLED",
    "true").lower() == "true"

# Mirror maintenance interval (seconds)
MIRROR_MAINTENANCE_INTERVAL = int(
    os.getenv(
        "MIRROR_MAINTENANCE_INTERVAL",
        "3600"))  # 1 hour

# ══════════════════════════════════════════════════════════════════════════════
# Health Monitoring Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Health check interval (seconds)
HEALTH_CHECK_INTERVAL = int(
    os.getenv(
        "HEALTH_CHECK_INTERVAL",
        "300"))  # 5 minutes

# Health monitoring enabled
HEALTH_MONITORING_ENABLED = os.getenv(
    "HEALTH_MONITORING_ENABLED",
    "true").lower() == "true"

# Bot health check timeout (seconds)
BOT_HEALTH_TIMEOUT = int(os.getenv("BOT_HEALTH_TIMEOUT", "10"))

# Group health check timeout (seconds)
GROUP_HEALTH_TIMEOUT = int(os.getenv("GROUP_HEALTH_TIMEOUT", "10"))

# ══════════════════════════════════════════════════════════════════════════════
# Sync Configuration
# ══════════════════════════════════════════════════════════════════════════════

# Incremental sync interval (seconds)
INCREMENTAL_SYNC_INTERVAL = int(
    os.getenv(
        "INCREMENTAL_SYNC_INTERVAL",
        "60"))  # 1 minute

# Full sync interval (seconds)
FULL_SYNC_INTERVAL = int(os.getenv("FULL_SYNC_INTERVAL", "3600"))  # 1 hour

# Sync batch size
SYNC_BATCH_SIZE = int(os.getenv("SYNC_BATCH_SIZE", "5"))

# Max concurrent syncs
MAX_CONCURRENT_SYNCS = int(os.getenv("MAX_CONCURRENT_SYNCS", "3"))

# Multi-Space & Multi-Dataset Configuration
ENABLE_MULTI_SPACE = os.getenv("ENABLE_MULTI_SPACE", "true").lower() == "true"
ENABLE_MULTI_DATASET = os.getenv(
    "ENABLE_MULTI_DATASET",
    "true").lower() == "true"
LOAD_BALANCING_METHOD = os.getenv("LOAD_BALANCING_METHOD", "weighted")
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
