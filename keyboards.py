from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def random_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Хочу ещё факт", callback_data="more_fact")
    builder.button(text="Закончить", callback_data="finish")
    builder.adjust(1)   # по одной кнопке в ряд
    return builder.as_markup()