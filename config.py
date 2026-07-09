import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN_HERE")

# --- Экономика бота ---
START_BONUS = 1.0          # баллов при регистрации
SUB_REWARD = 0.5           # баллов начисляется подписчику за одну подписку
DEFAULT_SUB_PRICE = 1.0    # сколько баллов списывается с владельца канала за одного подписчика
RECHECK_HOURS = 24         # через сколько часов перепроверять подписку
SCHEDULER_INTERVAL_MIN = 15  # как часто планировщик проверяет "замороженные" подписки

DB_PATH = os.getenv("DB_PATH", "bot.db")
