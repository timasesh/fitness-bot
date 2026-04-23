from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

DAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def schedule_days_kb(selected: set[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for day in range(7):
        mark = "✅" if day in selected else "⬜"
        row.append(InlineKeyboardButton(text=f"{mark} {DAY_LABELS[day]}", callback_data=f"sch:day:{day}"))
        if len(row) == 4:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton(text="Сохранить", callback_data="sch:save")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def schedule_toggle_kb(is_active: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Напоминания: {'ВКЛ' if is_active else 'ВЫКЛ'}", callback_data="sch:toggle")],
        ]
    )

