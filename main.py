import asyncio
import os
from config import TELEGRAM_TOKEN
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import (
    TelegramUnauthorizedError,
    TelegramNetworkError,
    TelegramConflictError,
)

from keyboards import random_keyboard
from services import get_random_fact

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

START_TEXT = (
    "Привет! Я бот со случайными фактами.\n\n"
    "/random — получить факт\n"
    "/help — помощь"
)

MENU_HINT = (
    "Вот что ещё можно попробовать 👇\n\n"
    "🤖 /gpt — задать вопрос ChatGPT\n"
    "🎲 /random — получить случайный факт"
)


HELP_TEXT = (
    "📖 Справка:\n\n"
    "/start — запустить бота\n"
    "/random — случайный факт\n"
    "/help — показать это сообщение"
)

# ---------- ЛОГИКА (общие функции для команд и кнопок) ----------

async def send_start(message: Message):
    await message.answer(START_TEXT)

async def send_random(message: Message):
    # 1. Проверяем, есть ли картинка
    photo_path = "images/fact.jpg"
    if not os.path.exists(photo_path):
        await message.answer(
            "⚙️ Данный функционал временно не работает: "
            "ведутся технические работы (отсутствует изображение)."
        )
        return   # выходим — дальше не идём

    # 2. Отправляем заготовленное изображение
    photo = FSInputFile(photo_path)
    await message.answer_photo(photo)

    # 3. Сообщаем, что думаем (запрос к ChatGPT занимает время)
    wait_msg = await message.answer("Придумываю факт... 🤔")

    # 4. Запрос к ChatGPT
    fact = await get_random_fact()

    # 5. Удаляем "думаю" и шлём факт с кнопками
    await wait_msg.delete()
    await message.answer(fact, reply_markup=random_keyboard())

# ---------- КОМАНДЫ ----------

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await send_start(message)

@dp.message(Command("random"))
async def command_random_handler(message: Message):
    await send_random(message)

@dp.message(Command("help"))
async def command_help_handler(message: Message):
    await message.answer(HELP_TEXT)

# ---------- КНОПКИ ----------

@dp.callback_query(F.data == "finish")
async def finish_button(callback: CallbackQuery):
    await callback.answer()                          # убираем "часики"
    await callback.message.edit_reply_markup(reply_markup=None)  # прячем кнопки у факта
    await callback.message.answer(MENU_HINT)         # шлём подсказку

@dp.callback_query(F.data == "more_fact")
async def more_fact_button(callback: CallbackQuery):
    await callback.answer()
    await send_random(callback.message)  # работает как /random

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