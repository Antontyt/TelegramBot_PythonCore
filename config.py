import os
from dotenv import load_dotenv

# Загружаем переменные из .env в окружение
load_dotenv()

# Читаем значения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_TOKEN = os.getenv("OPENAI_TOKEN")

# --- Telegram ---
if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
    raise ValueError(
        "TELEGRAM_TOKEN не найден или пустой. "
        "Проверь, что в .env есть строка TELEGRAM_TOKEN=твой_токен"
    )
print("Успешно получен TELEGRAM_TOKEN")

# --- OpenAI ---
if not OPENAI_TOKEN or not OPENAI_TOKEN.strip():
    raise ValueError(
        "OPENAI_TOKEN не найден или пустой. "
        "Проверь, что в .env есть строка OPENAI_TOKEN=твой_токен"
    )
print("Успешно получен OPENAI_TOKEN")
