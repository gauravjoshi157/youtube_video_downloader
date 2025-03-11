# config.py
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in .env file")

# YouTube API configuration
DOWNLOAD_FOLDER = "./downloads"
MAX_FILESIZE_MB = 50  # Telegram Bot API limit for free bots

# Application settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
WEBHOOK_MODE = os.getenv("WEBHOOK_MODE", "False").lower() in ("true", "1", "t")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", 8443))

# Create download directory if it doesn't exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)