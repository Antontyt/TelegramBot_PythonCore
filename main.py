from os import getenv

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
    raise ValueError(
        "TELEGRAM_TOKEN не найден или пустой. "
        "Проверь, что в .env есть строка TELEGRAM_TOKEN=твой_токен"
    )

print(f"Полученный токен для телеграмм: {TELEGRAM_TOKEN}")