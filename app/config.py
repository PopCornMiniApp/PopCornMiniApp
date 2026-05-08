import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_DATASET_NAME = os.getenv("HF_DATASET_NAME", "ToolKit-backend/PopCornDB")
HF_SPACE_NAME = os.getenv("HF_SPACE_NAME", "ToolKit-backend/PopCorn")

MAIN_BOT_TOKEN = os.getenv("MAIN_BOT_TOKEN", "")
STREAM_BOT_1 = os.getenv("STREAM_BOT_1", "")
STREAM_BOT_2 = os.getenv("STREAM_BOT_2", "")

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@MLk_JAMAL")

# Support both PRIVATE_GROUP_ID and PRIVATE_GROUPE_1_ID (historical typo)
_raw_group = os.getenv("PRIVATE_GROUP_ID") or os.getenv("PRIVATE_GROUPE_1_ID", "0")
PRIVATE_GROUP_ID = int(_raw_group or 0)

PUBLIC_CHANNEL_ID = int(os.getenv("PUBLIC_CHANNEL_ID", "0"))

SESSION_1_API_ID = int(os.getenv("SESSION_1_API_ID", "0"))
SESSION_1_API_HASH = os.getenv("SESSION_1_API_HASH", "")
SESSION_2_API_ID = int(os.getenv("SESSION_2_API_ID", "0"))
SESSION_2_API_HASH = os.getenv("SESSION_2_API_HASH", "")

DB_PATH = "/tmp/popcorn.db"
DATASET_DB_FILE = "popcorn.db"
