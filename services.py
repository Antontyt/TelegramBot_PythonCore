from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

RANDOM_PROMPT = "Расскажи один короткий интересный научный факт на русском языке. 2-3 предложения."

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
    return await ask_gpt(RANDOM_PROMPT, model="gpt-4o-mini")
