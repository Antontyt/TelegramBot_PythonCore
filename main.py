import asyncio
import os
import random
import uuid
from logger import logger
from config import TELEGRAM_TOKEN, BOT_VERSION
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import (
    TelegramUnauthorizedError,
    TelegramNetworkError,
    TelegramConflictError,
)

# --- FSM ---
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# --- Keyboards ---
from keyboards import (
    random_keyboard,
    talk_persons_keyboard,
    talk_finish_keyboard,
    quiz_topics_kb,
    quiz_after_answer_kb,
    voice_finish_keyboard,
    hide_keyboard
)
from services import get_random_fact, ask_assistant, talk_to_person, PERSONS, quiz_get_topics, quiz_get_question, quiz_check_answer, speech_to_text
from stats import add_user, get_stats

storage = MemoryStorage()
bot = Bot(
    token=TELEGRAM_TOKEN,
    default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
dp = Dispatcher(storage=storage)
voice_mode: set[int] = set()

# ── ЕДИНЫЙ СПИСОК КОМАНД ──
COMMANDS = {
    "🚀 /start":  "запустить бота",
    "🤖 /gpt": "задать вопрос ChatGPT",
    "🎭 /talk":   "поговорить с известной личностью",
    "🎲 /random": "получить рандомный факт",
    "🧠 /quiz": "играть в Квиз",
    "🎙️ /voice": "пообщаться голосом",
    "📊 /stats": "общедоступная статистика",
    "❓ /help":   "показать это сообщение"
}

FALLBACK_PHRASES = [
    "Хм, я такого не понимаю 🤔",
    "Это что-то новенькое 😅 Я пока такому не обучен.",
    "Я живой, честно! Просто не разобрал команду 🤖",
    "Мои нейроны напряглись, но не сработали 🧠",
    "Кажется, мы говорим на разных языках 😄"
]

def build_commands_list(exclude: set = None) -> str:
    """Собирает список команд в текст. exclude — что скрыть."""
    exclude = exclude or set()
    lines = [
        f"{cmd} — {desc}"
        for cmd, desc in COMMANDS.items()
        if cmd not in exclude
    ]
    return "\n".join(lines)

async def send_image_or_block(message: Message, filename: str) -> bool:
    """
    Отправляет картинку из папки images/.
    Возвращает True — если фото отправлено,
    False — если файла нет (и юзеру ушло предупреждение).
    """
    photo_path = f"images/{filename}"

    if not os.path.exists(photo_path):
        await message.answer(
            f"⚙️ Данный функционал временно не работает: \n"
            f"ведутся технические работы (отсутствует изображение {filename})."
        )
        return False

    photo = FSInputFile(photo_path)
    await message.answer_photo(photo)
    return True

GITHUB_URL = "https://github.com/Antontyt/TelegramBot_PythonCore"

MENU_HINT = (
    "Вот что ещё можно попробовать 👇\n\n"
    + build_commands_list(exclude={"/start", "/help"})
)

HELP_TEXT = (
    "📖 Справка:\n\n"
    + build_commands_list()
)

# ---------- СОСТОЯНИЯ ----------
class GptStates(StatesGroup):
    waiting_for_question = State()

class TalkStates(StatesGroup):
    chatting = State()

class QuizStates(StatesGroup):
    choosing_topic = State()
    waiting_answer = State()

# ---------- ЛОГИКА (общие функции для команд и кнопок) ----------
async def send_random(message: Message):
    # Проверяем и отправляем картинку
    if not await send_image_or_block(message, "fact.jpg"):
        return

    # Сообщаем, что думаем (запрос к ChatGPT занимает время)
    wait_msg = await message.answer("Придумываю факт... 🤔")

    # Запрос к ChatGPT
    fact = await get_random_fact()

    # Удаляем "думаю" и шлём факт с кнопками
    await wait_msg.delete()
    await message.answer(fact, reply_markup=random_keyboard())

async def send_talk(message: Message):
    # Проверяем и отправляем картинку
    if not await send_image_or_block(message, "talk.jpg"):
        return

    # Показываем выбор личности
    await message.answer(
        "С кем хочешь пообщаться? Выбери личность 👇",
        reply_markup=talk_persons_keyboard()
    )

def plural(number: int, one: str, few: str, many: str) -> str:
    """
    number — число
    one  — форма для 1 (пользователь, запрос)
    few  — форма для 2-4 (пользователя, запроса)
    many — форма для 5-0 (пользователей, запросов)
    """
    n = abs(number) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many

# ---------- КОМАНДЫ ----------
async def send_start_message(message: Message):
    add_user(message.from_user.id)
    stats = get_stats()
    text = (
        "📊 Статистика за всё время моей работы:\n"
        f"👥 Пользователей: {stats['users_count']}\n"
        f"🤖 Запросов к ChatGPT: {stats['gpt_requests']}\n\n"
        "Привет! Я бот, и вот мои полезные сервисы для тебя:\n\n"
        f"{build_commands_list(exclude={'/start', '/help'})}"
        f"\n\n💡 Понравился проект?\nБуду рад обратной связи и звёздочке ⭐️"
        f"\n{GITHUB_URL}"
        f"\n🔖 Версия: {BOT_VERSION}"
    )
    await message.answer(text)

@dp.message(Command("start"))
async def command_start_handler(message: Message):
    await send_start_message(message)

@dp.message(Command("random"))
async def command_random_handler(message: Message):
    await send_random(message)

@dp.message(Command("gpt"))
async def cmd_gpt(message: Message, state: FSMContext):
    # Проверяем и отправляем картинку
    if not await send_image_or_block(message, "gpt.jpg"):
        return

    # приглашаем задать вопрос
    await message.answer("Напиши свой вопрос для ChatGPT 🤖")

    # входим в режим ожидания вопроса
    await state.set_state(GptStates.waiting_for_question)

@dp.message(Command("talk"))
async def cmd_talk(message: Message):
    await send_talk(message)

# --- выбор личности ---
@dp.callback_query(F.data.startswith("talk_person:"))
async def choose_person(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    person_key = callback.data.split(":")[1]
    person = PERSONS[person_key]

    # сохраняем выбранную личность в FSM
    await state.update_data(person_key=person_key)
    await state.set_state(TalkStates.chatting)

    # прячем кнопки выбора
    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(
        f"Ты общаешься с {person['name']}.\n"
        "Напиши сообщение 👇",
        reply_markup=talk_finish_keyboard()
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
        + "или воспользуйся командой /start"
    )

@dp.message(Command("quiz"))
async def cmd_quiz(message: Message, state: FSMContext):
    await state.clear()

    # Проверяем и отправляем картинку
    if not await send_image_or_block(message, "quiz.jpg"):
        return

    topics = await quiz_get_topics()
    await state.update_data(topics=topics)

    await message.answer(
        "🧠 Выбери тему квиза:",
        reply_markup=quiz_topics_kb(topics),
    )
    await state.set_state(QuizStates.choosing_topic)

# --- выбор темы ---
@dp.callback_query(QuizStates.choosing_topic, F.data.startswith("topic:"))
async def quiz_choose_topic(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    topics = data.get("topics", [])
    idx = int(callback.data.split(":")[1])

    if idx >= len(topics):
        await callback.message.answer("Тема недоступна. Начни заново: /quiz")
        return

    topic = topics[idx]

    # прячем кнопки выбора темы
    await callback.message.edit_reply_markup(reply_markup=None)

    wait_msg = await callback.message.answer("🤔 Готовлю вопрос...")
    q = await quiz_get_question(topic)
    await wait_msg.delete()

    if q is None:
        await callback.message.answer(
            "😔 Не удалось сгенерировать вопрос. Попробуй ещё раз: /quiz"
        )
        await state.clear()
        return

    await state.update_data(
        topic=topic,
        question=q["question"],
        correct=q["correct_answer"],
    )
    await callback.message.answer(
        f"Тема: <b>{topic}</b>\n\n❓ {q['question']}"
    )
    await state.set_state(QuizStates.waiting_answer)

# --- обработка ответа пользователя ---
@dp.message(QuizStates.waiting_answer)
async def quiz_process_answer(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправь ответ текстом.")
        return

    data = await state.get_data()

    wait_msg = await message.answer("🤔 Проверяю ответ...")
    result = await quiz_check_answer(
        data["question"], data["correct"], message.text
    )
    await wait_msg.delete()

    is_correct = result["is_correct"]
    verdict = result["verdict"]

    correct_count = data.get("correct_count", 0)
    wrong_count = data.get("wrong_count", 0)

    # надёжный учёт по флагу
    if is_correct is True:
        correct_count += 1
    elif is_correct is False:
        wrong_count += 1

    await state.update_data(
        correct_count=correct_count,
        wrong_count=wrong_count,
    )

    score_line = f"\n\n📊 Счёт: ✅ {correct_count} · ❌ {wrong_count}"
    await message.answer(
        verdict + score_line,
        reply_markup=quiz_after_answer_kb(),
    )

# --- ещё вопрос по той же теме ---
@dp.callback_query(QuizStates.waiting_answer, F.data == "quiz:next")
async def quiz_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    wait_msg = await callback.message.answer("🤔 Готовлю вопрос...")
    q = await quiz_get_question(data["topic"])
    await wait_msg.delete()

    if q is None:
        await callback.message.answer("😔 Не удалось сгенерировать вопрос. Попробуй ещё раз.")
        return

    await state.update_data(question=q["question"], correct=q["correct_answer"])
    await callback.message.answer(f"❓ {q['question']}")

# --- сменить тему ---
@dp.callback_query(QuizStates.waiting_answer, F.data == "quiz:change")
async def quiz_change(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    topics = await quiz_get_topics()
    await state.update_data(topics=topics)

    await callback.message.answer(
        "📚 Выбери новую тему:",
        reply_markup=quiz_topics_kb(topics),
    )
    await state.set_state(QuizStates.choosing_topic)

# --- закончить квиз ---
@dp.callback_query(QuizStates.waiting_answer, F.data == "quiz:stop")
async def quiz_stop(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "🏁 Квиз завершён. Спасибо за игру!\n"
        "Для нового — введи /quiz или /start"
    )

@dp.message(Command("voice"))
async def voice_command(message: Message):
    voice_mode.add(message.from_user.id)
    await message.answer(
        "🎤 Режим голосовой беседы включён.\n"
        "Отправляй голосовые сообщения — я буду отвечать.",
        reply_markup=voice_finish_keyboard(),
    )
@dp.callback_query(F.data == "voice_finish")
async def voice_finish(callback: CallbackQuery):
    voice_mode.discard(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Голосовая беседа завершена.")
    await send_start_message(callback.message)
    await callback.answer()

@dp.message(F.voice)
async def voice_handler(message: Message):
    user_id = message.from_user.id

    if user_id not in voice_mode:
        await message.answer("ℹ️ Чтобы общаться голосом, включи режим командой /voice.")
        return

    os.makedirs("tmp", exist_ok=True)
    file_path = f"tmp/{user_id}_{uuid.uuid4().hex}.ogg"
    status_msg = None                       # ← держим статус-сообщение

    try:
        await message.bot.download(message.voice, destination=file_path)

        # ЭТАП 1: распознавание
        status_msg = await message.answer("⏳ Идёт обработка...")
        text = await speech_to_text(file_path)

        if not text:
            await status_msg.delete()
            await message.answer(
                "⚠️ Не удалось распознать речь. Попробуй ещё раз 🎤",
                reply_markup=voice_finish_keyboard(),
            )
            return

        await status_msg.delete()
        await message.answer(f"🗣 {text}")

        # ЭТАП 2: генерация ответа
        status_msg = await message.answer("⏳ Подготавливаю ответ...")
        answer = await ask_assistant(text)
        await status_msg.delete()

        await message.answer(f"🤖 {answer}", reply_markup=voice_finish_keyboard())

    except Exception as e:
        await message.answer(f"⚠️ Ошибка обработки голосового сообщения")
        print(f"[Voice Handler] {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@dp.message(F.text, lambda m: m.from_user.id in voice_mode)
async def text_in_voice_mode(message: Message):
    await message.answer(
        "🎤 В этом режиме мы общаемся только голосовыми сообщениями.\n\n"
        "Но ты всегда можешь воспользоваться другими режимами, которые у меня есть 🙂",
        reply_markup=voice_finish_keyboard(),
    )

@dp.message(Command("stats"))
async def command_stats_handler(message: Message):
    stats = get_stats()
    text = (
        "📊 Статистика за всё время моей работы:\n"
        f"👥 Пользователей: {stats['users_count']}\n"
        f"🤖 Запросов к ChatGPT: {stats['gpt_requests']}"
    )
    await message.answer(text)

@dp.message(Command("help"))
async def command_help_handler(message: Message):
    await message.answer(HELP_TEXT)

@dp.message()
async def fallback(message: Message):
    stats = get_stats()
    users = stats['users_count']
    requests = stats['gpt_requests']

    users_word = plural(users, "пользователем", "пользователями", "пользователями")
    req_word = plural(requests, "запрос", "запроса", "запросов")

    text = (
        f"Я уже поработал с {users} {users_word} "
        f"и выполнил {requests} {req_word} к ChatGPT 💪\n"
        "\n"
        f"{random.choice(FALLBACK_PHRASES)}\n"
        "\n"
        "Вот что я могу тебе предложить:\n"
        f"{build_commands_list()}"
    )

    await message.answer(text)

# ---------- КНОПКИ ----------
@dp.callback_query(F.data == "finish")
async def finish_button(callback: CallbackQuery):
    await hide_keyboard(callback)
    await callback.message.answer(MENU_HINT)
    await callback.answer()

@dp.callback_query(F.data == "talk_finish")
async def talk_finish_button(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await hide_keyboard(callback)
    await send_start_message(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "more_fact")
async def more_fact_button(callback: CallbackQuery):
    await callback.answer()
    await send_random(callback.message)

async def main():
    logger.info("Запуск бота...")
    while True:
        try:
            logger.info("Подключение к Telegram...")
            await dp.start_polling(bot)
            break

        except TelegramNetworkError:
            logger.error("Ошибка сети: нет доступа к Telegram. "
                         "Проверь интернет/VPN. Перезапуск через 5 сек...")
            await asyncio.sleep(5)

        except TelegramUnauthorizedError:
            logger.error("Ошибка: неверный токен. Проверь корректный ли TELEGRAM_TOKEN в .env")
            break

        except TelegramConflictError:
            logger.error("Ошибка: этот токен уже используется другим запущенным ботом")
            break

        except Exception as e:
            logger.exception(f"Неизвестная ошибка: {e}. Перезапуск через 5 сек...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())