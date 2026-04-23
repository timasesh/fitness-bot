from __future__ import annotations

import datetime as dt

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.water import water_kb
from bot.states.water import Water
from config import settings
from db.repositories.users import UsersRepository
from db.repositories.water import WaterRepository

router = Router()


def _progress_bar(total: int, norm: int, width: int = 10) -> str:
    ratio = 0.0 if norm <= 0 else min(total / norm, 1.0)
    filled = int(round(ratio * width))
    return "█" * filled + "░" * (width - filled)


async def _render_water(
    *,
    telegram_id: int,
    sessionmaker: async_sessionmaker[AsyncSession],
) -> str:
    today = dt.datetime.now(dt.timezone.utc).date()
    async with sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(telegram_id)
        if user is None:
            return "Сначала заполните анкету: /start"

        norm = user.water_norm_ml or settings.default_water_norm_ml
        water = WaterRepository(session)
        total = await water.total_for_date(user_id=user.id, date=today)

    percent = 0 if norm <= 0 else min(int(total * 100 / norm), 100)
    bar = _progress_bar(total, norm)
    return (
        "💧 <b>Трекер воды</b>\n"
        f"Выпито: <b>{total} мл</b> из <b>{norm} мл</b>\n"
        f"Прогресс: <code>{bar}</code> <b>{percent}%</b>"
    )


@router.message(Command("water"))
async def water_cmd(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await state.clear()
    text = await _render_water(telegram_id=message.from_user.id, sessionmaker=db_sessionmaker)
    await message.answer(text, reply_markup=water_kb())


@router.message(F.text.in_({"💧 Вода", "Вода", "💧 вода", "вода"}))
async def water_btn(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    await water_cmd(message, db_sessionmaker, state)


@router.callback_query(F.data == "water:refresh")
async def water_refresh(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    text = await _render_water(telegram_id=cb.from_user.id, sessionmaker=db_sessionmaker)
    await cb.message.edit_text(text, reply_markup=water_kb())
    await cb.answer()


@router.callback_query(F.data.startswith("water:add:"))
async def water_add(cb: CallbackQuery, db_sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    amount = int(cb.data.split(":")[-1])
    today = dt.datetime.now(dt.timezone.utc).date()

    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(cb.from_user.id)
        if user is None:
            await cb.answer("Сначала /start", show_alert=True)
            return

        water = WaterRepository(session)
        await water.add(user_id=user.id, amount_ml=amount)
        total = await water.total_for_date(user_id=user.id, date=today)
        await session.commit()

        norm = user.water_norm_ml or settings.default_water_norm_ml

    percent = 0 if norm <= 0 else min(int(total * 100 / norm), 100)
    bar = _progress_bar(total, norm)
    await cb.message.edit_text(
        "💧 <b>Трекер воды</b>\n"
        f"Выпито: <b>{total} мл</b> из <b>{norm} мл</b>\n"
        f"Прогресс: <code>{bar}</code> <b>{percent}%</b>",
        reply_markup=water_kb(),
    )
    await cb.answer("Добавлено")


@router.callback_query(F.data == "water:manual")
async def water_manual(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Water.manual_amount)
    await cb.message.edit_text("Введите количество воды в мл (например, 350).")
    await cb.answer()


@router.message(Water.manual_amount)
async def water_manual_amount(message: Message, db_sessionmaker: async_sessionmaker[AsyncSession], state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit():
        await message.answer("Нужно число в мл (например, 350).")
        return
    amount = int(raw)
    if amount <= 0 or amount > 5000:
        await message.answer("Введите разумное значение (1…5000 мл).")
        return

    today = dt.datetime.now(dt.timezone.utc).date()
    async with db_sessionmaker() as session:
        users = UsersRepository(session)
        user = await users.get_by_telegram_id(message.from_user.id)
        if user is None:
            await message.answer("Сначала заполните анкету: /start")
            await state.clear()
            return

        water = WaterRepository(session)
        await water.add(user_id=user.id, amount_ml=amount)
        total = await water.total_for_date(user_id=user.id, date=today)
        await session.commit()
        norm = user.water_norm_ml or settings.default_water_norm_ml

    await state.clear()
    percent = 0 if norm <= 0 else min(int(total * 100 / norm), 100)
    bar = _progress_bar(total, norm)
    await message.answer(
        "💧 <b>Трекер воды</b>\n"
        f"Выпито: <b>{total} мл</b> из <b>{norm} мл</b>\n"
        f"Прогресс: <code>{bar}</code> <b>{percent}%</b>",
        reply_markup=water_kb(),
    )

