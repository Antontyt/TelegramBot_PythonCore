from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def random_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Хочу ещё факт", callback_data="more_fact")
    builder.button(text="Закончить", callback_data="finish")
    builder.adjust(1)   # по одной кнопке в ряд
    return builder.as_markup()

def talk_persons_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Илон Маск", callback_data="talk_person:musk")
    kb.button(text="🍏 Стив Джобс", callback_data="talk_person:jobs")
    kb.button(text="💜 Опра Уинфри", callback_data="talk_person:oprah")
    kb.adjust(1)      # по одной в строке
    return kb.as_markup()

def talk_finish_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="👋 Закончить", callback_data="talk_finish")
    return kb.as_markup()

def quiz_topics_kb(topics: list[str]) -> InlineKeyboardMarkup:
    """Кнопки выбора темы. Темы передаём индексами (лимит callback_data 64 байта)."""
    rows = [
        [InlineKeyboardButton(text=t, callback_data=f"topic:{i}")]
        for i, t in enumerate(topics)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def quiz_after_answer_kb() -> InlineKeyboardMarkup:
    """Кнопки после ответа: ещё вопрос / сменить тему / закончить."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Ещё вопрос", callback_data="quiz:next")],
        [InlineKeyboardButton(text="📚 Сменить тему", callback_data="quiz:change")],
        [InlineKeyboardButton(text="🏁 Закончить квиз", callback_data="quiz:stop")],
    ])

def voice_finish_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Завершить", callback_data="voice_finish")
    return kb.as_markup()
