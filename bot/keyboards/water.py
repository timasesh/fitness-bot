from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def water_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="+250 мл", callback_data="water:add:250"),
                InlineKeyboardButton(text="+500 мл", callback_data="water:add:500"),
            ],
            [InlineKeyboardButton(text="Ввести вручную", callback_data="water:manual")],
            [InlineKeyboardButton(text="Обновить", callback_data="water:refresh")],
        ]
    )

