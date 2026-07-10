import os
from dotenv import load_dotenv

# Загружаем переменные из .env в окружение
load_dotenv()

# Версия бота — единое место истины 🎯
BOT_VERSION = "1.0.3"

# Читаем значения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Telegram ---
if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
    raise ValueError(
        "TELEGRAM_TOKEN не найден или пустой. "
        "Проверь, что в .env есть строка TELEGRAM_TOKEN=твой_токен"
    )
print("Успешно получен TELEGRAM_TOKEN")

# --- OpenAI ---
if not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
    raise ValueError(
        "OPENAI_API_KEY не найден или пустой. "
        "Проверь, что в .env есть строка OPENAI_API_KEY=твой_токен"
    )
print("Успешно получен OPENAI_API_KEY")
