from openai import AsyncOpenAI
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
    except Exception as e:
        return f"Не удалось получить факт: {e}"