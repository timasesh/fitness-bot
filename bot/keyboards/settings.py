from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_kb(*, reminders_enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Напоминания: {'ВКЛ' if reminders_enabled else 'ВЫКЛ'}",
                    callback_data="settings:toggle_reminders",
                )
            ],
            [InlineKeyboardButton(text="Изменить норму воды", callback_data="settings:water_norm")],
            [
                InlineKeyboardButton(text="🆕 Новый план", callback_data="qa:plan_new"),
                InlineKeyboardButton(text="🆕 Новое питание", callback_data="qa:nutrition_new"),
            ],
        ]
    )

