from aiogram.types import (
    InlineKeyboardMarkup,
    CallbackQuery
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

def random_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Хочу ещё факт", callback_data="more_fact")
    builder.button(text="Закончить", callback_data="finish")
    builder.adjust(1)              # по одной кнопке в ряд
    return builder.as_markup()

def talk_persons_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Илон Маск", callback_data="talk_person:musk")
    kb.button(text="Стив Джобс", callback_data="talk_person:jobs")
    kb.button(text="Опра Уинфри", callback_data="talk_person:oprah")
    kb.adjust(1)                   # по одной в строке
    return kb.as_markup()

def talk_finish_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Закончить", callback_data="talk_finish")
    return kb.as_markup()

def quiz_topics_kb(topics: list[str]) -> InlineKeyboardMarkup:
    # Кнопки выбора темы. Темы передаём индексами (лимит callback_data 64 байта)
    kb = InlineKeyboardBuilder()
    for i, t in enumerate(topics):
        kb.button(text=t, callback_data=f"topic:{i}")
    kb.adjust(1)                   # по одной в строке
    return kb.as_markup()

def quiz_after_answer_kb() -> InlineKeyboardMarkup:
    # Кнопки после ответа: ещё вопрос / сменить тему / закончить
    kb = InlineKeyboardBuilder()
    kb.button(text="Ещё вопрос", callback_data="quiz_next")
    kb.button(text="Сменить тему", callback_data="quiz_change")
    kb.button(text="Закончить квиз", callback_data="quiz_stop")
    kb.adjust(1)                   # по одной в строке
    return kb.as_markup()

def voice_finish_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Завершить", callback_data="voice_finish")
    return kb.as_markup()

async def hide_keyboard(callback: CallbackQuery):
    # Прячет inline-кнопки у сообщения безопасно
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass