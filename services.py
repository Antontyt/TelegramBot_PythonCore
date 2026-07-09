from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from config import OPENAI_API_KEY

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

# Модель по умолчанию — если вызывающая функция не указала свою
DEFAULT_MODEL = "gpt-4o-mini"

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
    return await ask_gpt(prompt, model="gpt-4o")

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