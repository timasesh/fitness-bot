from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def quick_actions_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🏋️ План", callback_data="qa:plan"),
                InlineKeyboardButton(text="🥗 Питание", callback_data="qa:nutrition"),
            ],
            [
                InlineKeyboardButton(text="🆕 Новый план", callback_data="qa:plan_new"),
                InlineKeyboardButton(text="🆕 Новое питание", callback_data="qa:nutrition_new"),
            ],
            [
                InlineKeyboardButton(text="💧 Вода", callback_data="qa:water"),
                InlineKeyboardButton(text="📊 Статус", callback_data="qa:status"),
            ],
        ]
    )

