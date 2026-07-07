import asyncio
#from os import getenv

#from dotenv import load_dotenv
from config import TELEGRAM_TOKEN
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import (
    TelegramUnauthorizedError,
    TelegramNetworkError,
    TelegramConflictError,
)

#load_dotenv()

#TELEGRAM_TOKEN = getenv("TELEGRAM_TOKEN")
#if not TELEGRAM_TOKEN or not TELEGRAM_TOKEN.strip():
#    raise ValueError(
#        "TELEGRAM_TOKEN не найден или пустой. "
#        "Проверь, что в .env есть строка TELEGRAM_TOKEN=твой_токен"
#    )
#print("Успешно получен TELEGRAM_TOKEN")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.answer("Hello! I'm a bot and this is my first message.")

async def main():
    try:
        print("Бот запущен")
        await dp.start_polling(bot)
    except TelegramUnauthorizedError:
        print("Ошибка: неверный токен. Проверь корректный ли TELEGRAM_TOKEN в .env")
    except TelegramNetworkError:
        print("Ошибка сети: нет доступа к Telegram. Проверь интернет/VPN")
    except TelegramConflictError:
        print("Ошибка: этот токен уже используется другим запущенным ботом")
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())