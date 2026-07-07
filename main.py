import asyncio
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

load_dotenv()

TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
    raise ValueError(
        "TELEGRAM_TOKEN не найден или пустой. "
        "Проверь, что в .env есть строка TELEGRAM_TOKEN=твой_токен"
    )
print("Успешно получен TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.answer("Hello! I'm a bot and this is my first message.")

async def main():
    print("Бот успешно запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())