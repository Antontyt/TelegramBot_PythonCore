import asyncio

from config import TELEGRAM_TOKEN
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.exceptions import (
    TelegramUnauthorizedError,
    TelegramNetworkError,
    TelegramConflictError,
)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.answer("Welcome message for start command.")


@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    await message.answer(
        "📖 Справка:\n\n"
        "/start — запустить бота\n"
        "/help — показать это сообщение"
    )

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