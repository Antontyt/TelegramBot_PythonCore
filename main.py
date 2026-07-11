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

# ============ ЭМОДЗИ / ИКОНКИ ============

EMOJI_OK       = "✅"
EMOJI_ERROR    = "❌"
EMOJI_WARNING  = "⚠️"
EMOJI_THINK    = "🤔"
EMOJI_FACT     = "💡"
EMOJI_VOICE    = "🗣"
EMOJI_GEAR     = "⚙️"

EMOJI_START    = "🚀"
EMOJI_GPT      = "🤖"
EMOJI_TALK     = "🎭"
EMOJI_RANDOM   = "🎲"
EMOJI_QUIZ     = "🧠"
EMOJI_STATS    = "📊"
EMOJI_HELP     = "❓"

EMOJI_WAIT     = "⏳"
EMOJI_MIC      = "🎙️"
EMOJI_STAR     = "⭐️"
EMOJI_INFO     = "ℹ️"
EMOJI_DOWN     = "👇"
EMOJI_MUSCLE   = "💪"
EMOJI_SMILE    = "🙂"
EMOJI_BOOKMARK = "🔖"
EMOJI_WAVE     = "👋"
EMOJI_SAD      = "😔"
EMOJI_USERS    = "👥"
EMOJI_BOOK     = "📖"

# =========================================

# ── ЕДИНЫЙ СПИСОК КОМАНД ──
COMMANDS = {
    f"{EMOJI_START} /start":  "запустить бота",
    f"{EMOJI_GPT} /gpt": "задать вопрос ChatGPT",
    f"{EMOJI_TALK} /talk":   "поговорить с известной личностью",
    f"{EMOJI_RANDOM} /random": "получить рандомный факт",
    f"{EMOJI_QUIZ} /quiz": "играть в Квиз",
    f"{EMOJI_MIC} /voice": "пообщаться голосом",
    f"{EMOJI_STATS} /stats": "общедоступная статистика",
    f"{EMOJI_HELP} /help":   "показать это сообщение"
}

FALLBACK_PHRASES = [
    f"Хм, я такого не понимаю {EMOJI_THINK}",
    f"Это что-то новенькое {EMOJI_SMILE} Я пока такому не обучен.",
    f"Я живой, честно! Просто не разобрал команду {EMOJI_GPT}",
    f"Мои нейроны напряглись, но не сработали {EMOJI_QUIZ}",
    f"Кажется, мы говорим на разных языках {EMOJI_SMILE}"
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

async def send_image_or_warning(message: Message, filename: str) -> bool:
    """
    Отправляет картинку из папки images/.
    Возвращает True — если фото отправлено,
    False — если файла нет (и юзеру ушло предупреждение).
    """
    photo_path = f"images/{filename}"

    if not os.path.exists(photo_path):
        await message.answer(
            f"{EMOJI_GEAR} Данный функционал временно не работает: \n"
            f"ведутся технические работы (отсутствует изображение {filename})."
        )
        return False

    photo = FSInputFile(photo_path)
    await message.answer_photo(photo)
    return True

GITHUB_URL = "https://github.com/Antontyt/TelegramBot_PythonCore"

MENU_HINT = (
    f"Вот что ещё можно попробовать {EMOJI_DOWN} \n\n"
    + build_commands_list(exclude={"/start", "/help"})
)

HELP_TEXT = (
    f"{EMOJI_BOOK} Справка:\n\n"
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
    if not await send_image_or_warning(message, "fact.jpg"):
        logger.debug("send_random заблокирован отсуствующей картинкой - fact.jpg")
        return

    # Сообщаем, что думаем (запрос к ChatGPT занимает время)
    wait_msg = await message.answer(f"Придумываю факт... {EMOJI_THINK}")

    # Запрос к ChatGPT
    fact = await get_random_fact()

    # Удаляем "думаю" и шлём факт с кнопками
    await wait_msg.delete()
    await message.answer(fact, reply_markup=random_keyboard())

async def send_talk(message: Message):
    # Проверяем и отправляем картинку
    if not await send_image_or_warning(message, "talk.jpg"):
        logger.debug("send_random заблокирован отсуствующей картинкой - talk.jpg")
        return

    # Показываем выбор личности
    await message.answer(
        f"С кем хочешь пообщаться? Выбери личность {EMOJI_DOWN}",
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
        f"{EMOJI_STATS} Статистика за всё время моей работы:\n"
        f"{EMOJI_USERS} Пользователей: {stats['users_count']}\n"
        f"{EMOJI_GPT} Запросов к ChatGPT: {stats['gpt_requests']}\n\n"
        "Привет! Я бот, и вот мои полезные сервисы для тебя:\n\n"
        f"{build_commands_list(exclude={'/start', '/help'})}"
        f"\n\n{EMOJI_FACT} Понравился проект?\nБуду рад обратной связи и звёздочке {EMOJI_STAR}"
        f"\n{GITHUB_URL}"
        f"\n{EMOJI_BOOKMARK} Версия: {BOT_VERSION}"
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
    if not await send_image_or_warning(message, "gpt.jpg"):
        logger.debug("send_random заблокирован отсуствующей картинкой - gpt.jpg")
        return

    # приглашаем задать вопрос
    await message.answer(f"Напиши свой вопрос для ChatGPT {EMOJI_GPT}")

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
        f"Напиши сообщение {EMOJI_DOWN}",
        reply_markup=talk_finish_keyboard()
    )

# --- обработка сообщений в режиме диалога ---
@dp.message(TalkStates.chatting)
async def process_talk(message: Message, state: FSMContext):
    data = await state.get_data()
    person_key = data.get("person_key")
    person = PERSONS[person_key]

    wait_msg = await message.answer(f"{EMOJI_THINK} Думаю над ответом...")

    # запрос к личности
    answer = await talk_to_person(person["prompt"], message.text)

    await wait_msg.delete()
    # отвечаем + снова кнопка "Закончить" (диалог продолжается)
    await message.answer(answer, reply_markup=talk_finish_keyboard())

@dp.message(GptStates.waiting_for_question)
async def process_gpt_question(message: Message, state: FSMContext):
    # диалог завершаем автоматически (требование ТЗ)
    await state.clear()

    wait_msg = await message.answer(f"{EMOJI_THINK} Думаю над ответом...")

    # запрос к ChatGPT с текстом сообщения
    answer = await ask_assistant(message.text)

    # передаём ответ пользователю текстом
    await wait_msg.delete()
    await message.answer(
        answer
        + "\n\n"
        + f"{EMOJI_WAVE} Диалог завершён.\n"
        + "Если нужно повторить — введи команду /gpt "
        + "или воспользуйся командой /start"
    )

@dp.message(Command("quiz"))
async def cmd_quiz(message: Message, state: FSMContext):
    await state.clear()

    # Проверяем и отправляем картинку
    if not await send_image_or_warning(message, "quiz.jpg"):
        logger.debug("send_random заблокирован отсуствующей картинкой - quiz.jpg")
        return

    topics = await quiz_get_topics()
    await state.update_data(topics=topics)

    await message.answer(
        f"{EMOJI_QUIZ} Выбери тему квиза:",
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

    wait_msg = await callback.message.answer(f"{EMOJI_THINK} Готовлю вопрос...")
    q = await quiz_get_question(topic)
    await wait_msg.delete()

    if q is None:
        await callback.message.answer(
            f"{EMOJI_SAD} Не удалось сгенерировать вопрос. Попробуй ещё раз: /quiz"
        )
        await state.clear()
        return

    await state.update_data(
        topic=topic,
        question=q["question"],
        correct=q["correct_answer"],
    )
    await callback.message.answer(
        f"Тема: <b>{topic}</b>\n\n {EMOJI_HELP} {q['question']}"
    )
    await state.set_state(QuizStates.waiting_answer)

# --- обработка ответа пользователя ---
@dp.message(QuizStates.waiting_answer)
async def quiz_process_answer(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправь ответ текстом.")
        return

    data = await state.get_data()

    wait_msg = await message.answer(f"{EMOJI_THINK} Проверяю ответ...")
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

    score_line = f"\n\n {EMOJI_STATS} Счёт: {EMOJI_OK} {correct_count} · {EMOJI_ERROR} {wrong_count}"
    await message.answer(
        verdict + score_line,
        reply_markup=quiz_after_answer_kb(),
    )

# --- дополнительные вопросы по выбранной теме QUIZ ---
@dp.callback_query(QuizStates.waiting_answer, F.data == "quiz:next")
async def quiz_next(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    wait_msg = await callback.message.answer(f"{EMOJI_THINK} Готовлю вопрос...")
    q = await quiz_get_question(data["topic"])
    await wait_msg.delete()

    if q is None:
        await callback.message.answer(f"{EMOJI_SAD} Не удалось сгенерировать вопрос. Попробуй ещё раз.")
        return

    await state.update_data(question=q["question"], correct=q["correct_answer"])
    await callback.message.answer(f"{EMOJI_HELP} {q['question']}")

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
    await callback.message.answer(f"{EMOJI_OK} Голосовая беседа завершена.")
    await send_start_message(callback.message)
    await callback.answer()

@dp.message(F.voice)
async def voice_handler(message: Message):
    user_id = message.from_user.id

    if user_id not in voice_mode:
        await message.answer(f"{EMOJI_INFO} Чтобы общаться голосом, включи режим командой /voice.")
        return

    os.makedirs("tmp", exist_ok=True)
    file_path = f"tmp/{user_id}_{uuid.uuid4().hex}.ogg"
    status_msg = None                       # ← держим статус-сообщение

    try:
        await message.bot.download(message.voice, destination=file_path)

        # Распознавание
        status_msg = await message.answer(f"{EMOJI_WAIT} Идёт обработка...")
        text = await speech_to_text(file_path)

        if not text:
            await status_msg.delete()
            await message.answer(
                f"{EMOJI_WARNING} Не удалось распознать речь. Попробуй ещё раз",
                reply_markup=voice_finish_keyboard(),
            )
            return

        await status_msg.delete()
        await message.answer(f"{EMOJI_VOICE} {text}")

        # Генерация ответа
        status_msg = await message.answer(f"{EMOJI_WAIT} Подготавливаю ответ...")
        answer = await ask_assistant(text)
        await status_msg.delete()

        await message.answer(f"{EMOJI_GPT} {answer}", reply_markup=voice_finish_keyboard())

    except Exception as e:
        await message.answer(f"{EMOJI_WARNING} Ошибка обработки голосового сообщения")
        logger.error(f"Voice Handler Error: {e}", exc_info=True)
    finally:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Удалён temp: {file_path}")
        except Exception as e:
            logger.warning(f"Не удалил temp {file_path}: {e}")

@dp.message(F.text, lambda m: m.from_user.id in voice_mode)
async def text_in_voice_mode(message: Message):
    await message.answer(
        "🎤 В этом режиме мы общаемся только голосовыми сообщениями.\n\n"
        f"Но ты всегда можешь воспользоваться другими режимами, которые у меня есть {EMOJI_SMILE}",
        reply_markup=voice_finish_keyboard(),
    )

@dp.message(Command("stats"))
async def command_stats_handler(message: Message):
    stats = get_stats()
    text = (
        f"{EMOJI_STATS} Статистика за всё время моей работы:\n"
        f"👥 Пользователей: {stats['users_count']}\n"
        f"{EMOJI_GPT} Запросов к ChatGPT: {stats['gpt_requests']}"
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
        f"и выполнил {requests} {req_word} к ChatGPT {EMOJI_MUSCLE}\n"
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