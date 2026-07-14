import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL")  # напр. https://dental-bot.onrender.com

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_BASE_URL}{WEBHOOK_PATH}" if WEBHOOK_BASE_URL else None

# id группы/чата, куда падают уведомления о новых записях на подтверждение
ADMIN_NOTIFY_CHAT_ID = os.getenv("ADMIN_NOTIFY_CHAT_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан — проверь .env")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задан — проверь .env")
