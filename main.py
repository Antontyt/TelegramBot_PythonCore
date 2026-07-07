from os import getenv

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
print(f"Полученный токен для телеграмм: {TELEGRAM_TOKEN}")