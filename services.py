from openai import AsyncOpenAI, APIStatusError, APIConnectionError, RateLimitError
from config import OPENAI_API_KEY

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

RANDOM_PROMPT = "Расскажи один короткий интересный научный факт на русском языке. 2-3 предложения."


async def get_random_fact() -> str:
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": RANDOM_PROMPT}],
        )
        return response.choices[0].message.content

    except APIStatusError as e:
        print(f"[OpenAI Error] status={e.status_code}: {e}")   # простое логирование на текущий момент
        # Ошибки с кодом статуса (403, 401, 429 и т.д.)
        if e.status_code == 403:
            return "🌍 Сервис фактов недоступен из вашего региона. Мы работаем над решением."
        elif e.status_code == 401:
            return "🔑 Ошибка авторизации сервиса. Попробуйте позже."
        elif e.status_code == 429:
            return "⏳ Слишком много запросов. Подождите немного и попробуйте снова."
        else:
            return "😔 Сервис фактов временно недоступен. Попробуйте позже."

    except RateLimitError:
        return "⏳ Превышен лимит запросов. Попробуйте через минуту."

    except APIConnectionError:
        return "📡 Не удалось связаться с сервисом. Проверьте соединение."

    except Exception:
        return "😔 Что-то пошло не так. Попробуйте позже."
