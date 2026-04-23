from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏋️ План"), KeyboardButton(text="🥗 Питание")],
            [KeyboardButton(text="💧 Вода"), KeyboardButton(text="⏰ Расписание")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="📘 Последний план"), KeyboardButton(text="📊 Статус")],
            [KeyboardButton(text="🤖 AI тест")],
        ],
        resize_keyboard=True,
    )

