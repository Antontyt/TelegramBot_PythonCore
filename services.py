import json  # добавить к импортам в начало файла
from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from config import OPENAI_API_KEY
from stats import add_gpt_request

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

RANDOM_PROMPT = "Расскажи один короткий интересный научный факт на русском языке. 2-3 предложения."

PERSONS = {
    "musk": {
        "name": "Элон Маск",
        "prompt": (
            "Ты — Элон Маск, предприниматель (Tesla, SpaceX). "
            "Отвечай смело, о технологиях, космосе и будущем. "
            "Иногда с юмором и амбициозно. Говори на русском."
        ),
    },
    "jobs": {
        "name": "Стив Джобс",
        "prompt": (
            "Ты — Стив Джобс, сооснователь Apple. "
            "Отвечай о простоте, дизайне, упорстве и продукте. "
            "Уверенно и вдохновляюще. Говори на русском."
        ),
    },
    "oprah": {
        "name": "Опра Уинфри",
        "prompt": (
            "Ты — Опра Уинфри, телеведущая и мотиватор. "
            "Отвечай тепло, вдохновляюще и поддерживающе, "
            "с заботой о собеседнике. Говори на русском."
        ),
    },
}

# ---------- КВИЗ ----------

QUIZ_TOPICS_PROMPT = (
    "Сгенерируй 4 разнообразные темы для викторины. "
    'Верни строго JSON без пояснений: {"topics": ["тема1", "тема2", "тема3", "тема4"]}. '
    "Каждая тема — 1–3 слова, на русском, без нумерации."
)

# Резервные темы на случай сбоя генерации/парсинга
FALLBACK_TOPICS = ["История", "Наука", "Космос", "Кино"]

# Модель по умолчанию — если вызывающая функция не указала свою
DEFAULT_MODEL = "gpt-5.4-nano"

async def ask_gpt(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """
    Базовая функция: отправляет любой текст в ChatGPT и возвращает ответ.
    Ловит ошибки и возвращает понятное сообщение пользователю.
    Используется всеми функциями, работающими с LLM.
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        add_gpt_request()
        return response.choices[0].message.content

    except APIStatusError as e:
        print(f"[OpenAI Error] status={e.status_code}: {e}")   # лог для разработчика
        if e.status_code == 403:
            return "🌍 Сервис недоступен из вашего региона. Мы работаем над решением."
        elif e.status_code == 401:
            return "🔑 Ошибка авторизации сервиса. Попробуйте позже."
        elif e.status_code == 429:
            return "⏳ Слишком много запросов. Подождите немного и попробуйте снова."
        else:
            return "😔 Сервис временно недоступен. Попробуйте позже."

    except RateLimitError:
        print("[OpenAI Error] rate limit")
        return "⏳ Превышен лимит запросов. Попробуйте через минуту."

    except APIConnectionError:
        print("[OpenAI Error] connection failed")
        return "📡 Не удалось связаться с сервисом. Проверьте соединение."

    except Exception as e:
        print(f"[OpenAI Error] unexpected: {e}")
        return "😔 Что-то пошло не так. Попробуйте позже."

async def get_random_fact() -> str:
    """Запрашивает случайный факт (использует ask_gpt)."""
    return await ask_gpt(RANDOM_PROMPT)   # модель по умолчанию

async def ask_assistant(user_question: str) -> str:
    """
    Обрабатывает вопрос пользователя из команды /gpt.
    Оборачивает вопрос в промпт и задаёт свою модель.
    """
    prompt = (
        "Ответь вдумчиво и по существу на вопрос пользователя. "
        "Опирайся только на проверенные факты, рассуждай пошагово. "
        "Если не уверен — честно скажи об этом, не выдумывай.\n\n"
        f"Вопрос пользователя: {user_question}"
    )
    return await ask_gpt(prompt, model="gpt-5.4-mini")

async def talk_to_person(person_prompt: str, user_message: str) -> str:
    """
    Обёртка над ask_gpt для диалога с личностью.
    Склеиваем промпт роли + сообщение пользователя.
    """
    full_prompt = (
        f"{person_prompt}\n\n"
        f"Собеседник написал: {user_message}\n"
        f"Ответь от лица этой личности."
    )
    return await ask_gpt(full_prompt)   # ← используем ОСНОВУ как есть

async def quiz_get_topics() -> list[str]:
    """
    Возвращает список тем для квиза.
    Использует ask_gpt. При сбое парсинга — резервные темы.
    """
    raw = await ask_gpt(QUIZ_TOPICS_PROMPT)
    try:
        data = json.loads(raw)
        topics = data["topics"][:4]
        if topics:
            return topics
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"[Quiz] не удалось распарсить темы: {raw!r}")
    return FALLBACK_TOPICS

async def quiz_get_question(topic: str) -> dict | None:
    """
    Генерирует вопрос + эталонный ответ по теме
    Возвращает {"question": ..., "correct_answer": ...} или None при сбое.
    """
    prompt = (
        f'Сгенерируй один вопрос для квиза по теме "{topic}". '
        "Верни строго JSON без пояснений: "
        '{"question": "текст вопроса", "correct_answer": "эталонный правильный ответ"}. '
        "Вопрос на русском, без вариантов ответа."
    )
    raw = await ask_gpt(prompt)
    try:
        data = json.loads(raw)
        if "question" in data and "correct_answer" in data:
            return data
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"[Quiz] не удалось распарсить вопрос: {raw!r}")
    return None

async def quiz_check_answer(question: str, correct_answer: str, user_answer: str) -> dict:
    """
    Проверяет ответ пользователя.
    Возвращает dict:
        {"is_correct": bool, "verdict": str}
    При сбое возвращает is_correct=None и текст ошибки в verdict.
    """
    prompt = (
        "Ты — ведущий квиза. Проверь ответ игрока.\n\n"
        f"Вопрос: {question}\n"
        f"Правильный ответ: {correct_answer}\n"
        f"Ответ игрока: {user_answer}\n\n"
        "Оцени, верен ли ответ игрока по смыслу (не придирайся к формулировке, "
        "опечаткам и регистру).\n"
        "Верни СТРОГО JSON без пояснений и markdown, в формате:\n"
        '{"is_correct": true/false, "verdict": "текст с пояснением"}\n\n'
        "В поле verdict начни с эмодзи ✅ если верно или ❌ если неверно, "
        "затем короткое дружелюбное пояснение (1-2 предложения). "
        "Если неверно — укажи правильный ответ."
    )

    raw = await ask_gpt(prompt)

    # --- fallback-парсинг ---
    try:
        # убираем возможные ```
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        is_correct = bool(data["is_correct"])
        verdict = str(data["verdict"])
        return {"is_correct": is_correct, "verdict": verdict}

    except (json.JSONDecodeError, KeyError, TypeError):
        # модель вернула не-JSON — не роняем бота
        return {
            "is_correct": None,
            "verdict": "😔 Не удалось проверить ответ. Попробуй ещё раз.",
        }

async def speech_to_text(file_path: str) -> str | None:
    """
    Распознаёт речь из аудиофайла через Whisper.
    Возвращает текст или None при ошибке.
    file_path — путь к .ogg файлу в tmp.
    """
    try:
        with open(file_path, "rb") as audio:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language="ru",        # ← жёстко задаём русский
            )
        return transcript.text

    except (APIStatusError, APIConnectionError, RateLimitError) as e:
        print(f"[Whisper Error] {e}")
        return None
    except Exception as e:
        print(f"[Whisper Error] unexpected: {e}")
        return None