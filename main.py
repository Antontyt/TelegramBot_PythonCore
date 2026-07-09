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

# --- FSM ---
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from keyboards import random_keyboard, talk_persons_keyboard, talk_finish_keyboard
from services import get_random_fact, ask_assistant, talk_to_person, PERSONS

storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=storage)

# ── ЕДИНЫЙ СПИСОК КОМАНД (правим только здесь!) ──
COMMANDS = {
    "🚀 /start":  "запустить бота",
    "🤖 /gpt": "задать вопрос ChatGPT",
    "🎭 /talk":   "поговорить с известной личностью",
    "🎲 /random": "получить рандомный факт",
    "❓ /help":   "показать это сообщение",
}

def build_commands_list(exclude: set = None) -> str:
    """Собирает список команд в текст. exclude — что скрыть."""
    exclude = exclude or set()
    lines = [
        f"{cmd} — {desc}"
        for cmd, desc in COMMANDS.items()
        if cmd not in exclude
    ]
    return "\n".join(lines)

START_TEXT = (
    "Привет! Я бот и вот мои полезные сервисы для тебя.\n\n"
    + build_commands_list(exclude={"/start"})   # в приветствии /start лишний
)

MENU_HINT = (
    "Вот что ещё можно попробовать 👇\n\n"
    + build_commands_list(exclude={"/start", "/help"})   # только основное
)

HELP_TEXT = (
    "📖 Справка:\n\n"
    + build_commands_list()   # тут показываем ВСЁ
)

# ---------- СОСТОЯНИЯ FSM ----------
class GptStates(StatesGroup):
    waiting_for_question = State()      # режим "ждём вопрос от юзера"

class TalkStates(StatesGroup):
    chatting = State()      # режим диалога с личностью

# ---------- ЛОГИКА (общие функции для команд и кнопок) ----------
async def send_start(message: Message):
    await message.answer(START_TEXT)

async def send_random(message: Message):
    # 1. Проверяем, есть ли картинка
    photo_path = "images/fact.jpg"
    if not os.path.exists(photo_path):
        await message.answer(
            "⚙️ Данный функционал временно не работает: "
            "ведутся технические работы (отсутствует изображение fact.jpg)."
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

async def send_talk(message: Message):
    # 1. Проверяем картинку
    photo_path = "images/talk.jpg"
    if not os.path.exists(photo_path):
        await message.answer(
            "⚙️ Данный функционал временно не работает: "
            "ведутся технические работы (отсутствует изображение talk.jpg)."
        )
        return

    # 2. Отправляем изображение
    photo = FSInputFile(photo_path)
    await message.answer_photo(photo)

    # 3. Показываем выбор личности
    await message.answer(
        "С кем хочешь пообщаться? Выбери личность 👇",
        reply_markup=talk_persons_keyboard(),
    )

# ---------- КОМАНДЫ ----------
@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await send_start(message)

@dp.message(Command("random"))
async def command_random_handler(message: Message):
    await send_random(message)

@dp.message(Command("gpt"))
async def cmd_gpt(message: Message, state: FSMContext):
    # отсылаем заготовленное изображение (требование ТЗ)
    photo = FSInputFile("images/gpt.jpg")
    await message.answer_photo(photo)

    # приглашаем задать вопрос
    await message.answer("Напиши свой вопрос для ChatGPT 🤖")

    # входим в режим ожидания вопроса
    await state.set_state(GptStates.waiting_for_question)

@dp.message(Command("talk"))
async def cmd_talk(message: Message):
    await send_talk(message)

# --- выбор личности (кнопки talk_musk / talk_jobs / talk_oprah) ---
@dp.callback_query(F.data.startswith("talk_person:"))
async def choose_person(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    person_key = callback.data.split(":")[1]     # talk_person:musk → musk
    person = PERSONS[person_key]

    # сохраняем выбранную личность в FSM
    await state.update_data(person_key=person_key)
    await state.set_state(TalkStates.chatting)

    # прячем кнопки выбора
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Ты общаешься с {person['name']}.\n"
        "Напиши сообщение 👇",
        reply_markup=talk_finish_keyboard(),
    )

# --- обработка сообщений в режиме диалога ---
@dp.message(TalkStates.chatting)
async def process_talk(message: Message, state: FSMContext):
    data = await state.get_data()
    person_key = data.get("person_key")
    person = PERSONS[person_key]

    wait_msg = await message.answer("🤔 Думаю над ответом...")

    # запрос к личности
    answer = await talk_to_person(person["prompt"], message.text)

    await wait_msg.delete()
    # отвечаем + снова кнопка "Закончить" (диалог продолжается)
    await message.answer(answer, reply_markup=talk_finish_keyboard())

# --- обработка сообщений в режиме диалога ---
@dp.message(TalkStates.chatting)
async def process_talk(message: Message, state: FSMContext):
    data = await state.get_data()
    person_key = data.get("person_key")
    person = PERSONS[person_key]

    wait_msg = await message.answer("🤔 Думаю над ответом...")

    # запрос к личности
    answer = await talk_to_person(person["prompt"], message.text)

    await wait_msg.delete()
    # отвечаем + снова кнопка "Закончить" (диалог продолжается)
    await message.answer(answer, reply_markup=talk_finish_keyboard())

@dp.message(GptStates.waiting_for_question)
async def process_gpt_question(message: Message, state: FSMContext):
    # диалог завершаем автоматически (требование ТЗ)
    await state.clear()

    wait_msg = await message.answer("🤔 Думаю над ответом...")

    # запрос к ChatGPT с текстом сообщения
    answer = await ask_assistant(message.text)

    # передаём ответ пользователю текстом
    await wait_msg.delete()
    await message.answer(
        answer
        + "\n\n"
        + "👋 Диалог завершён.\n"
        + "Если нужно повторить — введи команду /gpt "
        + "или воспользуйся командой /help"
    )

@dp.message(Command("help"))
async def command_help_handler(message: Message):
    await message.answer(HELP_TEXT)

# ---------- КНОПКИ ----------
@dp.callback_query(F.data == "finish")
async def finish_button(callback: CallbackQuery):
    await callback.answer()                          # убираем "часики"
    await callback.message.edit_reply_markup(reply_markup=None)  # прячем кнопки у факта
    await callback.message.answer(MENU_HINT)         # шлём подсказку

@dp.callback_query(F.data == "talk_finish")
async def talk_finish_button(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()                                    # выходим из диалога
    await callback.message.edit_reply_markup(reply_markup=None)  # прячем кнопку
    await send_start(callback.message)                     # ← как /start ✅

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