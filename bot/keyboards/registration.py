from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def goal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Похудеть", callback_data="reg_goal:lose")],
            [InlineKeyboardButton(text="Поддержать форму", callback_data="reg_goal:keep")],
            [InlineKeyboardButton(text="Набрать массу", callback_data="reg_goal:gain")],
        ]
    )


def level_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Новичок", callback_data="reg_level:beginner")],
            [InlineKeyboardButton(text="Средний", callback_data="reg_level:mid")],
            [InlineKeyboardButton(text="Продвинутый", callback_data="reg_level:advanced")],
        ]
    )


def frequency_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="2 раза", callback_data="reg_freq:2")],
            [InlineKeyboardButton(text="3 раза", callback_data="reg_freq:3")],
            [InlineKeyboardButton(text="4 раза", callback_data="reg_freq:4")],
            [InlineKeyboardButton(text="5 раз", callback_data="reg_freq:5")],
        ]
    )


def preferred_time_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Утро (7:00–9:00)", callback_data="reg_time:morning")],
            [InlineKeyboardButton(text="День (12:00–14:00)", callback_data="reg_time:day")],
            [InlineKeyboardButton(text="Вечер (18:00–20:00)", callback_data="reg_time:evening")],
            [InlineKeyboardButton(text="Своё время", callback_data="reg_time:custom")],
        ]
    )


def location_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Дома", callback_data="reg_loc:home")],
            [InlineKeyboardButton(text="В тренажёрном зале", callback_data="reg_loc:gym")],
        ]
    )

