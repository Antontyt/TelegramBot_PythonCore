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
